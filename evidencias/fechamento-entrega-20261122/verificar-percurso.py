"""Percurso HTTP real em projeto descartável, após instalação pelo manual.

Não controla navegador nem grava cookies, tokens ou cabeçalhos. O projeto e
a porta são fixados para não atuar na aplicação habitual do usuário.
"""
import json
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = 'http://127.0.0.1:18022'
PROJETO = 'cma-fechamento-20261122'
PASTA = Path(__file__).resolve().parent
LOG = (PASTA/'percurso-http.jsonl').open('x', encoding='utf-8')
verificacoes = []


def registrar(tipo, **campos):
    LOG.write(json.dumps({'instante_utc': datetime.now(timezone.utc).isoformat(),
                          'tipo': tipo, **campos}, ensure_ascii=False)+'\n')
    LOG.flush()


def verificar(nome, condicao):
    verificacoes.append({'nome': nome, 'aprovado': bool(condicao)})
    registrar('verificacao', **verificacoes[-1])
    if not condicao:
        raise AssertionError(nome)


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.lower())
                   if not unicodedata.combining(c))


def docker(*args):
    return subprocess.check_output(['docker', *args], encoding='utf-8').strip()


api = docker('ps', '-q', '--filter', f'label=com.docker.compose.project={PROJETO}',
             '--filter', 'label=com.docker.compose.service=api')
verificar('uma_api_dedicada', bool(api) and '\n' not in api)
config = json.loads(docker('inspect', api))[0]
env = dict(item.split('=', 1) for item in config['Config']['Env'])
verificar('modelo_real_e_demonstracao', env.get('USAR_FALSOS') == '0'
          and env.get('MODO_DEMONSTRACAO') == '1')
registrar('ambiente', projeto=PROJETO, base=BASE, imagem=config['Image'],
          inicio_container=config['State']['StartedAt'],
          versao='bb3c659b5a01af19ccf677fb69ad732510c47895',
          observacao='Instalação Compose em volumes novos; fontes da PR #46, aplicação igual à master; percurso HTTP, sem inspeção visual nova.')

with httpx.Client(base_url=BASE, timeout=120, headers={'Origin': BASE}, trust_env=False) as c:
    verificar('chat_http_200', c.get('/').status_code == 200)
    verificar('saude', c.get('/saude').json() == {'status': 'ok'})

    def perfil(valor):
        r = c.post('/interface/demonstracao', json={'perfil': valor})
        r.raise_for_status()
        d = r.json()
        registrar('perfil', resultado=d)
        verificar('identidade_'+valor, d['usuario_id'] ==
                  ('demo_professor' if valor == 'a' else 'demo_visitante')
                  and d['modo_teste'] is False)

    def sessao():
        verificar('nova_sessao', c.post('/interface/nova-sessao').status_code == 204)

    def conversar(texto, etapa):
        r = c.post('/interface/conversas', json={'mensagem': texto})
        r.raise_for_status()
        d = r.json()
        registrar('conversa', etapa=etapa, mensagem=texto, resultado=d)
        return d

    perfil('a')
    d = conversar('Moro em Niteroi.', 'salvar')
    verificar('confirmacao_local_explicita', d['origem_uso'] == 'politica_local'
              and d['chamadas_modelo_observadas'] == 0)
    sessao()
    d = conversar('Em qual cidade eu moro?', 'recuperar')
    verificar('cidade_recuperada_pelo_modelo', 'niteroi' in normalizar(d['resposta'])
              and d['chamadas_modelo_observadas'] == 1)
    conversar('Agora moro em Sorocaba.', 'atualizar')
    sessao()
    d = conversar('Em qual cidade eu moro?', 'valor_atual')
    verificar('valor_atual', 'sorocaba' in normalizar(d['resposta'])
              and 'niteroi' not in normalizar(d['resposta']))
    inicio_antes = config['State']['StartedAt']
    docker('restart', api)
    for _ in range(60):
        try:
            if c.get('/saude', timeout=2).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(1)
    inicio_depois = json.loads(docker('inspect', api))[0]['State']['StartedAt']
    verificar('processo_reiniciado', inicio_antes != inicio_depois)
    registrar('reinicio', antes=inicio_antes, depois=inicio_depois)
    verificar('cookie_preservou_identidade', c.get('/interface/sessao').json()['usuario_id'] == 'demo_professor')
    d = conversar('Em qual cidade eu moro?', 'persistencia')
    verificar('persistiu_apos_reinicio', 'sorocaba' in normalizar(d['resposta']))
    perfil('b')
    d = conversar('Em qual cidade eu moro?', 'isolamento')
    verificar('isolamento_b', d['resposta'] == 'DESCONHECIDO')
    perfil('a')
    conversar('Esqueça minha cidade.', 'esquecer')
    sessao()
    d = conversar('Em qual cidade eu moro?', 'apos_esquecimento')
    verificar('abstencao_apos_esquecimento', d['resposta'] == 'DESCONHECIDO')
    d = conversar('Qual e a capital da Franca?', 'geral')
    verificar('pergunta_geral_no_modelo', 'paris' in normalizar(d['resposta'])
              and d['chamadas_modelo_observadas'] == 1)

resumo = {'tipo': 'fim', 'aprovadas': len(verificacoes), 'falhas': 0,
          'verificacoes': verificacoes, 'inspecao_visual_v3': False,
          'video_produzido': False}
registrar('fim', resumo=resumo)
(PASTA/'percurso-resumo.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'aprovadas': len(verificacoes), 'falhas': 0}))
