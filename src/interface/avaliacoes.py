"""Execuções locais explícitas com credenciais próprias, prazo e trava entre workers."""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from src.interface.protocolos import RAIZ, validar, validar_casos

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
PRAZO_SEGUNDOS = 4 * 3600


def impedimento():
    if os.getenv('HABILITAR_COMPARATIVO_INTERFACE') != '1':
        return 'Avaliações desativadas nesta instalação. Na demonstração local atualizada elas são habilitadas ao iniciar. Reconstrua a API usando o mesmo projeto e preservando volumes.'
    if os.getenv('USAR_FALSOS') == '1':
        return 'Modo simulado: a medição real exige Ollama e agente reais.'
    return None


def _encerrar(processo):
    if processo.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(processo.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    else:
        try:
            os.killpg(processo.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(processo.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        processo.wait(timeout=5)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(timeout=5)


def _liberar(job):
    trava = job.pop('trava', None)
    if trava:
        trava.close()


def _travar(pasta):
    arquivo = (pasta / '.execucao.lock').open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            arquivo.seek(0)
            if not arquivo.read(1):
                arquivo.write(b'0')
                arquivo.flush()
            arquivo.seek(0)
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        arquivo.close()
        raise HTTPException(409, 'Já existe uma avaliação em andamento. Aguarde sua conclusão.') from None
    return arquivo


def _expirar(codigo):
    with _lock:
        job = _jobs.get(codigo)
        if job and job['processo'].poll() is None:
            job['prazo_excedido'] = True
            _encerrar(job['processo'])
            _liberar(job)


def encerrar_avaliacoes():
    with _lock:
        for job in _jobs.values():
            if job.get('timer'):
                job['timer'].cancel()
            _encerrar(job['processo'])
            _liberar(job)


def ativa(usuario):
    with _lock:
        for codigo, job in _jobs.items():
            if job['processo'].poll() is None:
                return {'ocupada': True, 'id': codigo if job['usuario'] == usuario else None}
    return {'ocupada': False, 'id': None}


def iniciar(usuario: str, modelo: str, repeticoes: int, protocolo='comparativo_v3', casos=None) -> dict:
    motivo = impedimento()
    if motivo:
        raise HTTPException(409, motivo)
    try:
        validar(protocolo, repeticoes)
        if casos is not None:
            if protocolo != 'comparativo_v3':
                raise ValueError('Conjuntos próprios são exclusivos do comparativo; P6 exige seu roteiro e contratos integrais.')
            validar_casos(casos)
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from None
    with _lock:
        for job in _jobs.values():
            if job['processo'].poll() is None:
                raise HTTPException(409, 'Já existe uma avaliação em andamento. Aguarde sua conclusão.')
            _liberar(job)
        pasta = Path(os.getenv('DB_PATH', 'dados/memorias.db')).resolve().parent / 'avaliacoes-interface'
        pasta.mkdir(parents=True, exist_ok=True)
        trava = _travar(pasta)
        codigo = uuid.uuid4().hex
        rodada = pasta / codigo
        try:
            rodada.mkdir(exist_ok=False)
            with (rodada / 'dono.json').open('x', encoding='utf-8') as f:
                json.dump({'usuario': usuario, 'protocolo': protocolo, 'modelo': modelo,
                         **({'controle_sem_memoria': 'modelo_direto'} if protocolo == 'comparativo_v3' else {}),
                           'repeticoes': repeticoes, 'conjunto': 'próprio' if casos is not None else 'oficial',
                           'iniciada_em': datetime.now(timezone.utc).isoformat()}, f, ensure_ascii=False)
            saida, progresso = rodada / 'relatorio.json', rodada / 'progresso.json'
            argumentos = [sys.executable, '-B', '-m', 'src.interface.executar_avaliacao',
                          '--saida', str(saida), '--modelo', modelo, '--repeticoes', str(repeticoes),
                          '--protocolo', protocolo, '--progresso', str(progresso)]
            if casos is not None:
                dataset = rodada / 'conjunto-proprio.json'
                with dataset.open('x', encoding='utf-8') as f:
                    json.dump(casos, f, ensure_ascii=False, allow_nan=False)
                argumentos.extend(['--dataset-proprio', str(dataset)])
            ambiente = {**os.environ, 'API_TOKENS': '', 'API_TOKENS_FILE': '', 'OPENAI_API_KEY': '',
                        'DB_PATH': str(rodada / 'nao-usar-chat.db'), 'MODO_DEMONSTRACAO': '0',
                        'HABILITAR_COMPARATIVO_INTERFACE': '0', 'HABILITAR_OBSERVACAO_RAM': '0',
                        'USUARIOS_AVALIACAO_RAM': '', 'USAR_FALSOS': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
            opcoes = ({'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
                      if os.name == 'nt' else {'start_new_session': True, 'pass_fds': (trava.fileno(),)})
            with (rodada / 'execucao.log').open('xb') as arquivo:
                processo = subprocess.Popen(argumentos, cwd=RAIZ, env=ambiente,
                                            stdout=arquivo, stderr=subprocess.STDOUT, **opcoes)
            _jobs[codigo] = {'processo': processo, 'usuario': usuario, 'saida': saida,
                             'progresso': progresso, 'protocolo': protocolo, 'trava': trava,
                             'inicio': time.monotonic()}
            timer = threading.Timer(PRAZO_SEGUNDOS, _expirar, args=(codigo,))
            timer.daemon = True
            _jobs[codigo]['timer'] = timer
            timer.start()
        except Exception as erro:
            if codigo in _jobs:
                _encerrar(_jobs[codigo]['processo'])
                _jobs.pop(codigo)
            trava.close()
            if isinstance(erro, OSError):
                raise HTTPException(503, 'Não foi possível iniciar o processo isolado. Nenhuma bateria foi iniciada; confira os recursos locais e tente novamente.') from None
            raise
        return {'id': codigo, 'estado': 'executando', 'protocolo': protocolo}


def consultar(codigo: str, usuario: str) -> tuple[dict, Path | None]:
    with _lock:
        job = _jobs.get(codigo)
        if job is None:
            return _recuperar(codigo, usuario)
        if job['usuario'] != usuario:
            raise HTTPException(404, 'Avaliação não encontrada para este usuário. Se a API reiniciou, as evidências locais anteriores foram preservadas.')
        processo = job['processo']
        if processo.poll() is None and time.monotonic() - job['inicio'] > PRAZO_SEGUNDOS:
            _encerrar(processo)
            job['prazo_excedido'] = True
        progresso = None
        if job.get('progresso'):
            try:
                progresso = json.loads(job['progresso'].read_text(encoding='utf-8'))
            except (OSError, ValueError):
                pass
        publico = {'id': codigo, 'protocolo': job.get('protocolo'), 'progresso': progresso,
                   'decorridos_segundos': max(0, round(time.monotonic() - job['inicio']))}
        if processo.poll() is None:
            return {**publico, 'estado': 'executando'}, None
        if job.get('timer'):
            job['timer'].cancel()
        _liberar(job)
        documento = None
        try:
            documento = json.loads(job['saida'].read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
        falhou = processo.returncode != 0 or documento is None or _tem_falha_tecnica(documento)
        mensagem = ('A avaliação excedeu o prazo de quatro horas. Evidências parciais preservadas; nenhuma conclusão foi presumida.'
                    if job.get('prazo_excedido') else
                    'A avaliação não terminou integralmente. Confira Ollama e resultados parciais; evidências e log locais foram preservados.')
        if falhou and documento is not None and not job.get('prazo_excedido'):
            mensagem = _mensagem_falha_relatorio(documento)
        if falhou and not job.get('prazo_excedido'):
            mensagem = _falha_preparo(job['saida']) or mensagem
        return {**publico, 'estado': 'falhou' if falhou else 'concluido',
                'mensagem': mensagem if falhou else None, 'relatorio': documento}, job['saida'] if documento else None


def _recuperar(codigo, usuario):
    pasta = _pasta_segura(codigo)
    if pasta is None:
        raise HTTPException(404, 'Avaliação não encontrada para este usuário.')
    dono = _ler_objeto(pasta / 'dono.json', 16 * 1024)
    if not dono or dono.get('usuario') != usuario:
        raise HTTPException(404, 'Avaliação não encontrada para este usuário.')
    relatorio = pasta / 'relatorio.json'
    documento = _ler_objeto(relatorio)
    concluida = _concluida(documento)
    mensagem = (None if concluida else _mensagem_falha_relatorio(documento) if documento is not None else
                _falha_preparo(relatorio) or
                'O monitoramento foi interrompido após reinício da API. Evidências parciais preservadas; não há repetição automática.')
    return {'id': codigo, 'protocolo': dono.get('protocolo'), 'estado': 'concluido' if concluida else 'falhou', 'relatorio': documento,
            'mensagem': mensagem}, relatorio if documento else None


def _raiz_historico():
    return Path(os.getenv('DB_PATH', 'dados/memorias.db')).resolve().parent / 'avaliacoes-interface'


def _pasta_segura(codigo):
    if not isinstance(codigo, str) or not re.fullmatch(r'[a-f0-9]{32}', codigo):
        return None
    raiz = _raiz_historico().resolve()
    pasta = raiz / codigo
    try:
        if pasta.is_symlink() or pasta.resolve() != pasta or not pasta.is_dir():
            return None
    except OSError:
        return None
    return pasta


def _ler_objeto(arquivo, limite=8 * 1024 * 1024):
    try:
        if arquivo.is_symlink() or arquivo.resolve() != arquivo:
            return None
        with arquivo.open('rb') as f:
            dados = f.read(limite + 1)
        if len(dados) > limite:
            return None
        objeto = json.loads(dados)
        return objeto if isinstance(objeto, dict) else None
    except (OSError, ValueError):
        return None


def _interface(documento):
    interface = documento.get('interface') if isinstance(documento, dict) else None
    return interface if isinstance(interface, dict) else {}


def _tem_falha_tecnica(documento):
    if not isinstance(documento, dict):
        return False
    registros = documento.get('resultados')
    return isinstance(registros, list) and any(isinstance(r, dict) and
        (r.get('erro') or r.get('estado') == 'erro') for r in registros)


def _concluida(documento):
    codigo = _interface(documento).get('codigo_saida')
    return type(codigo) is int and codigo == 0 and documento.get('estado_orquestracao') != 'incompleta' and not _tem_falha_tecnica(documento)


def listar(usuario, deslocamento=0, limite=20):
    """Lista metadados do dono; não inicia, encerra ou repete processos."""
    raiz = _raiz_historico()
    candidatos = []
    try:
        pastas = list(raiz.iterdir())
    except OSError:
        pastas = []
    for entrada in pastas:
        pasta = _pasta_segura(entrada.name)
        if pasta is None:
            continue
        dono = _ler_objeto(pasta / 'dono.json', 16 * 1024)
        if not dono or dono.get('usuario') != usuario:
            continue
        try:
            data_arquivo = (pasta / 'dono.json').stat().st_mtime
        except OSError:
            continue
        data = dono.get('iniciada_em')
        try:
            instante = datetime.fromisoformat(data)
            if instante.tzinfo is None:
                raise ValueError()
            ordem = instante.timestamp()
            origem_data = 'inicio'
        except (TypeError, ValueError, OverflowError):
            ordem = data_arquivo
            data = datetime.fromtimestamp(data_arquivo, timezone.utc).isoformat()
            origem_data = 'arquivo_local'
        candidatos.append((ordem, entrada.name, pasta, dono, data, origem_data))
    candidatos.sort(key=lambda item: (item[0], item[1]), reverse=True)
    with _lock:
        estados = {codigo: ('executando' if job['processo'].poll() is None else
                            'falhou' if job.get('prazo_excedido') or job['processo'].returncode != 0 else None)
                   for codigo, job in _jobs.items() if job.get('usuario') == usuario}
    itens = []
    for _, codigo, pasta, dono, data, origem_data in candidatos[deslocamento:deslocamento + limite]:
        documento = _ler_objeto(pasta / 'relatorio.json')
        interface = _interface(documento)
        protocolo = dono.get('protocolo')
        if not isinstance(protocolo, str) or protocolo not in {'p6', 'comparativo_v3'}:
            protocolo = interface.get('protocolo')
        modelo = dono.get('modelo', interface.get('modelo'))
        repeticoes = dono.get('repeticoes', interface.get('repeticoes'))
        conjunto = dono.get('conjunto', interface.get('conjunto'))
        itens.append({'id': codigo, 'protocolo': protocolo if isinstance(protocolo, str) and protocolo in {'p6', 'comparativo_v3'} else None,
                      'modelo': modelo[:100] if isinstance(modelo, str) else None,
                      'repeticoes': repeticoes if type(repeticoes) is int and repeticoes in (1, 3) else None,
                      'conjunto': conjunto if isinstance(conjunto, str) and conjunto in {'oficial', 'próprio'} else None,
                      'controle_sem_memoria': (dono.get('controle_sem_memoria', interface.get('controle_sem_memoria'))
                            if dono.get('controle_sem_memoria', interface.get('controle_sem_memoria')) in ('modelo_direto', 'api_local') else None),
                      'data': data, 'origem_data': origem_data,
                      'estado': estados.get(codigo) or ('concluido' if _concluida(documento) else 'falhou'),
                      'relatorio_disponivel': documento is not None})
    proximo = deslocamento + len(itens)
    return {'avaliacoes': itens, 'total': len(candidatos),
            'proximo_deslocamento': proximo if proximo < len(candidatos) else None}


def _mensagem_falha_relatorio(documento):
    falhas = documento.get('falhas')
    quantidade = f' ({falhas} eventos em erro)' if type(falhas) is int else ''
    return ('Execução encerrada com falhas'+quantidade+'. O relatório preserva o que foi observado; '
            'eventos sem resposta e tokens ausentes continuam desconhecidos. Consulte os erros por pergunta e cenário. '
            'Nenhum lote foi repetido automaticamente.')


def _falha_preparo(saida):
    preparo = _ler_objeto(saida.with_name('falha-preparo.json'), 16 * 1024)
    if (preparo and preparo.get('etapa') == 'preparo_modelo'
            and isinstance(preparo.get('mensagem'), str)):
        return preparo['mensagem'][:700]
    return None
