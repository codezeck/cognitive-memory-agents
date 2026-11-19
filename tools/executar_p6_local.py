"""P6 real em API/SQLite descartáveis, com evidência operacional automática.

Usa o Ollama indicado no ambiente. Não lê .env, não altera serviços existentes,
não publica portas e não declara revisão humana de terceiros.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import httpx

from eval import avaliar_sessoes_integradas as p6
from eval.sessoes_evidencias import VerificadorEvidencias
from eval.sessoes_transporte import Credencial, TransporteHTTP, TransporteHistorico, Evento

RAIZ = Path(__file__).resolve().parents[1]


def agora():
    return datetime.now(timezone.utc).isoformat()


def gravar(caminho, valor):
    caminho.write_text(json.dumps(valor, ensure_ascii=False, indent=2), encoding='utf-8')


def snapshot(caminho):
    with sqlite3.connect(f'file:{Path(caminho).as_posix()}?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(
            'SELECT id, usuario_id, texto, chave, metadados, ativa, criada_em, atualizada_em '
            'FROM memorias ORDER BY usuario_id, id')]


class APIIsolada:
    def __init__(self, pasta, db, usuarios, modelo):
        self.pasta, self.db, self.usuarios = pasta, db, usuarios
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.porta = s.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.porta}'
        self.env = {**os.environ, 'DB_PATH': str(db), 'LLM_PROVIDER': 'ollama',
                    'LLM_MODEL': modelo, 'MODELOS_PERMITIDOS': 'ollama:' + modelo,
                    'API_TOKENS': ','.join(c.token + ':' + c.usuario_id for c in usuarios.values()),
                    'API_TOKENS_FILE': '', 'OPENAI_API_KEY': '', 'USAR_FALSOS': '0',
                    'MODO_DEMONSTRACAO': '0', 'HABILITAR_OBSERVACAO_RAM': '1',
                    'USUARIOS_AVALIACAO_RAM': ','.join(c.usuario_id for c in usuarios.values()),
                    'PYTHONDONTWRITEBYTECODE': '1'}
        self.processo = None
        self.log = (pasta / 'api.log').open('ab')

    def iniciar(self):
        self.processo = subprocess.Popen(
            [sys.executable, '-B', '-m', 'uvicorn', 'src.api.main:app',
             '--host', '127.0.0.1', '--port', str(self.porta), '--workers', '1'],
            cwd=RAIZ, env=self.env, stdout=self.log, stderr=subprocess.STDOUT,
            **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
        limite = time.monotonic() + 40
        with httpx.Client(timeout=1) as c:
            while time.monotonic() < limite:
                if self.processo.poll() is not None:
                    raise RuntimeError('API isolada encerrou durante a inicialização; consultar api.log.')
                try:
                    if c.get(self.url + '/saude').status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(.2)
        raise TimeoutError('A API isolada não iniciou em 40 segundos.')

    def parar(self):
        if self.processo is not None and self.processo.poll() is None:
            self.processo.terminate()
            try:
                self.processo.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.processo.kill()
                self.processo.wait(timeout=5)

    def ram(self, uid, termos=()):
        alvos = [{'rotulo': f'alvo_{i}', 'termos': [v]} for i, v in enumerate(dict.fromkeys(termos))]
        c = self.usuarios[uid]
        r = httpx.post(self.url + '/avaliacao/ram',
                       headers={'Authorization': 'Bearer ' + c.token},
                       json={'alvos': alvos}, timeout=10)
        r.raise_for_status()
        return r.json()


class ColetorLocal(VerificadorEvidencias):
    def __init__(self, pasta, api, execucao, configuracao, anotacoes):
        super().__init__(pasta / 'evidencias-operacionais.json')
        self.pasta, self.api, self.anotacoes = pasta, api, anotacoes
        self.documento = {'execucao_id': execucao, 'api_url': api.url,
                          'ambiente_id': execucao, 'usuarios': {u: c.usuario_id for u, c in api.usuarios.items()},
                          'configuracao_efetiva': configuracao, 'eventos': {},
                          'revisao': 'coleta automática autorizada pelo usuário; sem aprovação atribuída a terceiros'}
        self.anteriores = {}

    def registrar(self, evento, observacao, detalhes):
        nome = evento.id.replace('/', '-') + '.json'
        gravar(self.pasta / nome, {'evento_id': evento.id, 'coletado_em': agora(), **detalhes})
        self.documento['eventos'][evento.id] = {
            'execucao_id': self.documento['execucao_id'], 'ambiente_id': self.documento['ambiente_id'],
            'usuario_id': evento.usuario_id, 'usuario_api_id': self.api.usuarios[evento.usuario_id].usuario_id,
            'sessao': evento.sessao, 'evento_id': evento.id, 'tipo': evento.tipo, 'chaves': list(evento.chaves),
            'aprovado': True, 'responsavel': 'coletor-local-v1 (automático)',
            'referencia': self.documento['configuracao_efetiva'].get('referencia_protocolo',
                              'docs/revisao-experimental/decisao-20261118.md'),
            'origem': nome, 'coletado_em': agora(), 'observacao': observacao}
        gravar(self.caminho, self.documento)

    def preparar_iniciais(self):
        # A API inicializa o repositório sob demanda. O GET materializa apenas
        # o esquema; a prova de vazio vem do SQLite e da RAM lidos em seguida.
        with httpx.Client(base_url=self.api.url, timeout=10) as cliente:
            for credencial in self.api.usuarios.values():
                resposta = cliente.get('/usuarios/' + credencial.usuario_id + '/estado-regras',
                    headers={'Authorization': 'Bearer ' + credencial.token})
                resposta.raise_for_status()
                if resposta.json() != {}:
                    raise ValueError('Estado inicial de regras não vazio.')
        dados = snapshot(self.api.db)
        for uid, c in self.api.usuarios.items():
            ram = self.api.ram(uid)
            linhas = [r for r in dados if r['usuario_id'] == c.usuario_id]
            if linhas or ram['mensagens_pessoais']:
                raise ValueError('A instância dedicada não está inicialmente vazia.')
            self.registrar(Evento(uid + '/s1/preflight', uid, 1, 'preflight'),
                           {'alvos_ativos': 0, 'alvos_substituidos': 0, 'alvos_no_historico': 0},
                           {'sqlite': linhas, 'ram': ram})

    def antes_da_acao(self, evento):
        self.anteriores[evento.usuario_id] = {
            'sqlite': snapshot(self.api.db),
            'ram': {u: self.api.ram(u) for u in self.api.usuarios},
            'coletado_em': agora()}

    def __call__(self, evento):
        if evento.tipo == 'checkpoint_persistencia':
            antes = snapshot(self.api.db)
            instancia_antes = self.api.ram(evento.usuario_id)
            self.api.parar()
            self.api.iniciar()
            depois = snapshot(self.api.db)
            instancia_depois = self.api.ram(evento.usuario_id)
            uid = self.api.usuarios[evento.usuario_id].usuario_id
            estado = lambda linhas: {r['id']: r for r in linhas if r['usuario_id'] == uid}
            observacao = {'reinicio_confirmado': instancia_antes['instancia_id'] != instancia_depois['instancia_id'],
                          'estado_antes': estado(antes), 'estado_depois': estado(depois),
                          'arquivo_db': str(self.api.db), 'processos_cobertos': 1}
            self.registrar(evento, observacao, {'sqlite_antes': antes, 'sqlite_depois': depois,
                                              'ram_antes': instancia_antes, 'ram_depois': instancia_depois})
        elif evento.tipo == 'checkpoint_exclusao':
            anterior = self.anteriores.pop(evento.usuario_id)
            depois = snapshot(self.api.db)
            uid = self.api.usuarios[evento.usuario_id].usuario_id
            alvo = lambda r: r['usuario_id'] == uid and (not evento.chaves or r['chave'] in evento.chaves)
            alvos = [r for r in anterior['sqlite'] if alvo(r)]
            termos = [str(json.loads(r['metadados']).get('valor', r['texto'])) for r in alvos]
            # Inclui valores anotados para verificar também fatos sem registro persistente.
            termos += [v for q, a in self.anotacoes.items() if q.startswith(evento.usuario_id + '/')
                       for v in a.get('informacoes_esquecidas', [])]
            ram = self.api.ram(evento.usuario_id, termos)
            outros_ram = {u: self.api.ram(u) for u in self.api.usuarios if u != evento.usuario_id}
            campos = ('mensagens_pessoais', 'instancia_id')
            outros_preservados = all(all(ram_u[k] == anterior['ram'][u][k] for k in campos)
                                      for u, ram_u in outros_ram.items())
            observacao = {
                'alvos_antes': len(alvos),
                'alvos_ativos': sum(alvo(r) and bool(r['ativa']) for r in depois),
                'alvos_substituidos': sum(alvo(r) and not r['ativa'] for r in depois),
                'alvos_no_historico': ram['alvos_no_historico'] if evento.chaves else ram['mensagens_pessoais'],
                'nao_alvos_preservados': outros_preservados and
                    [r for r in anterior['sqlite'] if not alvo(r)] == [r for r in depois if not alvo(r)]}
            self.registrar(evento, observacao, {'antes': anterior, 'sqlite_depois': depois,
                                              'ram_depois': ram, 'ram_outros_depois': outros_ram})
        return super().__call__(evento)


class TransporteObservado(TransporteHTTP):
    def executar(self, evento, **kwargs):
        print(f'P6 {evento.id} {evento.tipo}', flush=True)
        if evento.tipo in {'apagar_usuario', 'esquecer_chaves'}:
            self.verificar_checkpoint.antes_da_acao(evento)
        return super().executar(evento, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida-dir', type=Path, required=True)
    parser.add_argument('--commit-base', required=True)
    parser.add_argument('--protocolo', type=Path, required=True)
    parser.add_argument('--modelo', default='qwen2.5-coder:3b')
    args = parser.parse_args()
    protocolo = json.loads(args.protocolo.read_text(encoding='utf-8'))
    for campo, caminho in [('dataset_sha256', p6.DATASET),
                           ('anotacoes_sha256', RAIZ / 'eval/memoria/anotacoes_p6.json')]:
        if protocolo[campo] != hashlib.sha256(caminho.read_bytes()).hexdigest():
            parser.error('Fontes diferem da revisão congelada: ' + campo)
    if protocolo.get('execucao_autorizada') is not True:
        parser.error('Falta decisão explícita registrada para a execução.')
    args.saida_dir.mkdir(parents=True, exist_ok=False)
    pasta = args.saida_dir.resolve()
    dados = json.loads(p6.DATASET.read_text(encoding='utf-8'))
    anotacoes = json.loads((RAIZ / 'eval/memoria/anotacoes_p6.json').read_text(encoding='utf-8'))
    execucao = 'p6-' + secrets.token_hex(6)
    usuarios = {u['usuario_id']: Credencial('p6_' + execucao + '_' + u['usuario_id'], secrets.token_urlsafe(32))
                for u in dados['usuarios']}
    host = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
    tags = httpx.get(host + '/api/tags', timeout=10).json()['models']
    modelo = next(m for m in tags if m['name'] == args.modelo)
    backend = host + '/' + modelo['digest']
    fontes = {str(p.relative_to(RAIZ)): hashlib.sha256(p.read_bytes()).hexdigest()
              for raiz in ('src', 'eval', 'tools') for p in sorted((RAIZ / raiz).rglob('*.py'))}
    gravar(pasta / 'configuracao.json', {'execucao_id': execucao, 'commit_base': args.commit_base,
           'arvore_com_alteracoes': True, 'fontes_sha256': fontes, 'modelo': modelo,
           'plataforma': platform.platform(), 'python': sys.version,
           'protocolo': protocolo, 'iniciado_em': agora(), 'backend_id': backend})
    with tempfile.TemporaryDirectory(prefix='cma-p6-') as tmp:
        api = APIIsolada(pasta, Path(tmp) / 'memorias.db', usuarios, args.modelo)
        try:
            api.iniciar()
            config = {'agente_real': True, 'provedor': 'ollama', 'modelo': args.modelo,
                      'backend_id': backend, 'backend_historico_id': backend,
                      'referencia_protocolo': protocolo['referencia'],
                      'commit_api': args.commit_base + ' + árvore identificada em configuracao.json'}
            coletor = ColetorLocal(pasta, api, execucao, config, anotacoes)
            coletor.preparar_iniciais()
            cliente = httpx.Client(base_url=api.url, timeout=120)
            transportes = {'memoria_automatica': TransporteObservado(cliente, usuarios,
                                contratos=protocolo['contratos'], verificar_checkpoint=coletor),
                          'historico_completo': TransporteHistorico(contratos=protocolo['contratos'], timeout=3600)}
            resultado = p6.executar(dados, transportes, pasta / 'eventos.jsonl', provedor='ollama',
                                   modelo=args.modelo, anotacoes=anotacoes, execucao_id=execucao)
            gravar(pasta / 'resumo.json', {k: v for k, v in resultado.items() if k != 'resultados'})
            return 1 if resultado['estado_orquestracao'] != 'concluida' else 0
        finally:
            api.parar()
            api.log.close()


if __name__ == '__main__':
    raise SystemExit(main())
