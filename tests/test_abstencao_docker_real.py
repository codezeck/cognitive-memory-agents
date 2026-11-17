"""Regressao opt-in: API e Ollama reais, em instancia descartavel dedicada.

Nao carrega .env, nao executa P6 e nao usa datasets da avaliacao.
Exige ABSTENCAO_AMBIENTE_ISOLADO=1, URL, TOKEN_A, TOKEN_B e ARTEFATO
com prefixo ABSTENCAO_. O artefato deve ser novo; tentativas ficam registradas
antes dos pedidos, inclusive quando o teste falha. Nunca registrar os tokens.
"""
import itertools
import json
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest


PERGUNTA_CIDADE = (
    'Em que cidade eu moro? Responda somente a cidade registrada. '
    'Se nao souber, responda DESCONHECIDO.'
)
CASOS = (
    'disponivel', 'atualizado', 'nunca_informado', 'exclusao_individual',
    'exclusao_total', 'exclusao_nova_sessao', 'isolamento', 'geral',
    'mensagem_atual', 'historico_usuario', 'memoria_sem_suporte', 'conselho',
    'pergunta_mista',
)


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto.casefold())
    return ''.join(c for c in texto if not unicodedata.combining(c)).strip(' .!\n')


@pytest.fixture(scope='module')
def ambiente_real():
    if os.getenv('ABSTENCAO_AMBIENTE_ISOLADO') != '1':
        pytest.skip('requer API/Ollama reais e ambiente isolado opt-in')
    url = os.environ['ABSTENCAO_URL']
    parsed = urlsplit(url)
    if parsed.hostname not in {'127.0.0.1', 'localhost'} or parsed.port in {None, 8000}:
        pytest.fail('usar somente porta local dedicada, distinta da API existente')
    arquivo = Path(os.environ['ABSTENCAO_ARTEFATO']).open('x', encoding='utf-8')
    cliente = httpx.Client(base_url=url, timeout=90)
    # Falha de preparacao deve bloquear a bateria antes de qualquer mutacao.
    try:
        cliente.get('/saude').raise_for_status()
    except Exception:
        cliente.close()
        arquivo.close()
        raise
    contador = itertools.count(1)

    def gravar(**evento):
        evento['instante_utc'] = datetime.now(timezone.utc).isoformat()
        arquivo.write(json.dumps(evento, ensure_ascii=False) + '\n')
        arquivo.flush()

    def pedido(caso, repeticao, metodo, caminho, usuario='a', corpo=None):
        token = os.environ['ABSTENCAO_TOKEN_' + usuario.upper()]
        indice = next(contador)
        gravar(tipo='tentativa_http', caso=caso, repeticao=repeticao,
               indice=indice, metodo=metodo, caminho=caminho, corpo=corpo)
        resposta = cliente.request(metodo, caminho, json=corpo,
                                   headers={'Authorization': 'Bearer ' + token})
        try:
            dados = resposta.json()
        except ValueError:
            dados = resposta.text
        gravar(tipo='resposta_http', caso=caso, repeticao=repeticao,
               indice=indice, status=resposta.status_code, corpo=dados)
        resposta.raise_for_status()
        return dados

    gravar(tipo='inicio', url=url, repeticoes=5, casos=CASOS,
           dataset='exemplos_sinteticos_de_desenvolvimento',
           agente_falso=False, p6_executada=False)
    yield pedido, gravar
    cliente.close()
    arquivo.close()


@pytest.mark.parametrize('repeticao', range(1, 6))
@pytest.mark.parametrize('caso', CASOS)
def test_abstencao_docker_real(ambiente_real, caso, repeticao):
    pedir, gravar = ambiente_real

    def http(metodo, caminho, usuario='a', corpo=None):
        return pedir(caso, repeticao, metodo, caminho, usuario, corpo)

    def conversar(mensagem, usuario='a'):
        return http('POST', '/conversas', usuario, {
            'usuario_id': 'professor_' + usuario, 'mensagem': mensagem,
            'provedor': 'ollama', 'modelo': 'qwen2.5-coder:3b',
        })

    def nova_sessao(usuario='a'):
        http('POST', '/usuarios/professor_' + usuario + '/sessoes', usuario)

    for usuario in ('a', 'b'):
        http('DELETE', '/usuarios/professor_' + usuario + '/memorias', usuario)

    esperado = 'desconhecido'
    resultado = None
    try:
        if caso in {'disponivel', 'atualizado', 'exclusao_individual',
                    'exclusao_total', 'exclusao_nova_sessao', 'isolamento'}:
            conversar('Moro em Niteroi.')
            nova_sessao()
            recuperada = conversar(PERGUNTA_CIDADE)
            assert normalizar(recuperada['resposta']) == 'niteroi'
            assert any('Niteroi' in m for m in recuperada['memorias_usadas'])
        if caso == 'disponivel':
            resultado, esperado = recuperada, 'niteroi'
        elif caso == 'atualizado':
            conversar('Agora moro em Vitoria.')
            resultado = conversar(PERGUNTA_CIDADE)
            esperado = 'vitoria'
            assert all('Niteroi' not in m for m in resultado['memorias_usadas'])
        elif caso == 'exclusao_individual':
            memorias = http('GET', '/usuarios/professor_a/memorias?consulta=Niteroi')
            assert len(memorias) == 1
            http('DELETE', '/usuarios/professor_a/memorias/' + memorias[0]['id'])
            resultado = conversar(PERGUNTA_CIDADE)
        elif caso in {'exclusao_total', 'exclusao_nova_sessao'}:
            http('DELETE', '/usuarios/professor_a/memorias')
            if caso == 'exclusao_nova_sessao':
                nova_sessao()
            resultado = conversar(PERGUNTA_CIDADE)
        elif caso == 'isolamento':
            resultado = conversar(PERGUNTA_CIDADE, 'b')
            assert resultado['memorias_usadas'] == []
            conversar('Moro em Maceio.', 'b')
            nova_sessao('b')
            b = conversar(PERGUNTA_CIDADE, 'b')
            assert normalizar(b['resposta']) == 'maceio'
            a = conversar(PERGUNTA_CIDADE)
            assert normalizar(a['resposta']) == 'niteroi'
        elif caso == 'geral':
            resultado = conversar('Qual e a capital da Franca? Responda somente o nome.')
            esperado = 'paris'
        elif caso == 'mensagem_atual':
            resultado = conversar('Minha palavra de exemplo e NEVOA. Qual palavra '
                                  'de exemplo acabei de informar? Responda somente a palavra.')
            esperado = 'nevoa'
            assert resultado['memorias_usadas'] == []
        elif caso == 'historico_usuario':
            conversar('Minha palavra de exemplo e BRISA.')
            resultado = conversar('Qual e a minha palavra de exemplo? Responda somente a palavra.')
            esperado = 'brisa'
            assert resultado['memorias_usadas'] == []
        elif caso == 'memoria_sem_suporte':
            http('POST', '/usuarios/professor_a/memorias', corpo={
                'texto': 'A cidade preferida para turismo e Natal. '
                         'Este registro nao informa onde o usuario mora.'})
            nova_sessao()
            resultado = conversar(PERGUNTA_CIDADE)
            assert resultado['memorias_usadas']
        elif caso == 'conselho':
            resultado = conversar('Como posso organizar meus estudos? De uma dica curta.')
            esperado = 'conselho_nao_vazio'
        elif caso == 'pergunta_mista':
            resultado = conversar('Qual e a minha cidade de residencia? E quanto e 2 + 3? '
                                  'Se faltar um dado pessoal, diga que nao sabe esse dado '
                                  'e responda a parte que souber.')
            esperado = 'abstencao_e_cinco'
        elif caso == 'nunca_informado':
            nova_sessao()
            resultado = conversar(PERGUNTA_CIDADE)

        texto = normalizar(resultado['resposta'])
        if esperado == 'conselho_nao_vazio':
            assert texto and 'desconhecido' not in texto and 'nao sei' not in texto
        elif esperado == 'abstencao_e_cinco':
            assert any(t in texto for t in ('desconhecido', 'nao sei', 'nao tenho', 'nao foi informad'))
            assert '5' in texto or 'cinco' in texto
        else:
            assert texto == esperado
    except Exception as erro:
        gravar(tipo='resultado_caso', caso=caso, repeticao=repeticao, aprovado=False,
               esperado=esperado, resposta=resultado, erro=str(erro))
        raise
    else:
        gravar(tipo='resultado_caso', caso=caso, repeticao=repeticao, aprovado=True,
               esperado=esperado, resposta=resultado)
