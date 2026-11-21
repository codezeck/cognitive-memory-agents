"""Controle direto validado apenas com transporte e subprocessos simulados."""
import json
import sys
from pathlib import Path

import httpx
import pytest

from src.interface import comparativo, controle_modelo
from src.interface.protocolos import fonte_v3
from eval import avaliar_comparativo  # Importação antes de substituir o transporte HTTP.


@pytest.fixture
def caso():
    return next(c for c in fonte_v3() if c['avaliacao']['tipo_resposta'] == 'factual')


def simular(monkeypatch, resposta=None, falha=None, status=200):
    chamadas, clientes, configuracoes = [], [], []
    original = httpx.Client
    def atender(request):
        chamadas.append(request)
        if falha:
            raise falha
        return httpx.Response(status, json=resposta)
    def cliente(**opcoes):
        configuracoes.append(opcoes)
        c = original(**opcoes, transport=httpx.MockTransport(atender))
        clientes.append(c)
        return c
    monkeypatch.setattr(controle_modelo.httpx, 'Client', cliente)
    monkeypatch.setenv('OLLAMA_HOST', 'http://ollama-simulado:11434')
    return chamadas, clientes, configuracoes


def retorno(texto, **campos):
    return {'done': True, 'message': {'role': 'assistant', 'content': texto},
            'prompt_eval_count': 20, 'eval_count': 3, **campos}


def test_payload_final_sem_agente_fatos_gabarito_ou_credenciais(monkeypatch, caso):
    monkeypatch.setenv('API_TOKENS', 'credencial-sintetica-nao-enviar')
    chamadas, clientes, config = simular(monkeypatch, retorno(caso['esperado']))
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'modelo-simulado')
    assert len(chamadas) == 1
    assert chamadas[0].url == 'http://ollama-simulado:11434/api/chat'
    assert json.loads(chamadas[0].content) == {
        'model': 'modelo-simulado', 'stream': False,
        'messages': [{'role': 'user', 'content': caso['mensagens'][-1]}]}
    assert 'authorization' not in chamadas[0].headers and 'cookie' not in chamadas[0].headers
    assert clientes[0].is_closed
    assert config[0]['trust_env'] is config[0]['follow_redirects'] is False
    assert config[0]['timeout'].read == 60 and config[0]['timeout'].connect == 10
    assert r['via'] == 'ollama_direto' and r['passou'] is True
    assert r['esperado'] == caso['esperado']
    assert r['tokens_total'] == 23 and r['chamadas_modelo'] == 1
    assert r['respostas_locais_confirmadas'] == 0
    assert r['tokens_por_etapa']['ingestao']['tokens_total'] == 0
    assert r['tokens_por_etapa']['pergunta_final']['tokens_total'] == 23
    assert r['memorias_usadas'] == r['memorias_esperadas'] == []
    assert r['latencia_api_total_ms'] is None and r['latencia_ollama_http_ms'] >= 0


@pytest.mark.parametrize('texto,aprovado', [('DESCONHECIDO', False), ('Curitiba', False)])
def test_abstencao_indevida_e_resposta_errada_nao_acertam_fato(monkeypatch, caso, texto, aprovado):
    chamadas, _, _ = simular(monkeypatch, retorno(texto))
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert r['julgamento']['acerto_factual']['valor'] is aprovado
    assert r['passou'] is False and len(chamadas) == 1
    assert r['chamadas_modelo'] == 1 and r['tokens_total'] == 23


def test_abstencao_exigida_e_correta_mas_veio_do_modelo(monkeypatch):
    caso = next(c for c in fonte_v3() if c['avaliacao']['tipo_resposta'] == 'abstencao')
    simular(monkeypatch, retorno('DESCONHECIDO'))
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert r['passou'] is True and r['chamadas_modelo'] == 1
    assert r['respostas_locais_confirmadas'] == 0 and r['tokens_total'] == 23


@pytest.mark.parametrize('valor', [None, 0, -1, True, '20', 1.5])
@pytest.mark.parametrize('campo', ['prompt_eval_count', 'eval_count'])
def test_consumo_ausente_ou_invalido_permanece_desconhecido(monkeypatch, caso, campo, valor):
    simular(monkeypatch, retorno(caso['esperado'], **{campo: valor}))
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert r['passou'] is True and r['chamadas_modelo'] == 1
    assert r['tokens_total'] is None and r['metricas_completas'] is False
    canal = 'tokens_entrada' if campo == 'prompt_eval_count' else 'tokens_saida'
    assert r[canal] is None


@pytest.mark.parametrize('resposta', [None, [], {'done': False},
    {'done': True, 'message': {}}, retorno(''), retorno('   '),
    {'done': True, 'message': {'role': 'user', 'content': 'eco'}},
    {'done': True, 'message': {'content': 'sem papel'}},
    retorno(None), retorno('texto', error='erro interno')])
def test_resposta_incompleta_nao_gera_acerto_falso_nem_zero(monkeypatch, caso, resposta):
    chamadas, clientes, _ = simular(monkeypatch, resposta)
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert len(chamadas) == 1 and clientes[0].is_closed
    assert r['erro'] and r['resposta'] is None and r['passou'] is False
    assert r['julgamento']['revisao_necessaria'] is True
    assert r['tokens_total'] is r['chamadas_modelo'] is None
    assert r['tokens_por_etapa']['sessao']['chamadas_previstas'] == 1
    assert r['tokens_por_etapa']['sessao']['chamadas_observadas'] == 0


@pytest.mark.parametrize('status', [302, 401, 500])
def test_erro_http_nao_redireciona_repete_ou_expoe_corpo(monkeypatch, caso, status):
    chamadas, _, _ = simular(monkeypatch, {'segredo': 'nao-expor'}, status=status)
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert len(chamadas) == 1 and r['tokens_total'] is None
    assert r['erro'] and 'nao-expor' not in json.dumps(r)


def test_timeout_nao_repete_e_preserva_desconhecido(monkeypatch, caso):
    chamadas, clientes, _ = simular(monkeypatch, falha=httpx.ReadTimeout('url-privada-nao-expor'))
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert len(chamadas) == 1 and clientes[0].is_closed
    assert r['erro'] and r['tokens_total'] is None
    assert 'url-privada' not in json.dumps(r)


def test_url_invalida_nao_expoe_configuracao_nem_perde_identificacao(monkeypatch, caso):
    monkeypatch.setenv('OLLAMA_HOST', 'http://privado:porta-invalida')
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert r['erro'] and r['via'] == 'ollama_direto' and r['tokens_total'] is None
    assert 'privado' not in json.dumps(r) and 'porta-invalida' not in json.dumps(r)


def test_json_invalido_e_encerrado_sem_fallback(monkeypatch, caso):
    original = httpx.Client
    chamadas = []
    def responder(request):
        chamadas.append(request)
        return httpx.Response(200, content=b'{invalido')
    cliente = original(transport=httpx.MockTransport(responder), trust_env=False)
    monkeypatch.setattr(controle_modelo.httpx, 'Client', lambda **kw: cliente)
    r = controle_modelo.executar_sem_memoria(caso, 'ollama', 'simulado')
    assert len(chamadas) == 1 and cliente.is_closed
    assert r['resposta'] is None and r['tokens_total'] is None and r['erro']


@pytest.mark.parametrize('falhar', [False, True])
@pytest.mark.parametrize('modo', ['api_local', 'modelo_direto'])
def test_wrapper_encaminha_cenarios_uma_vez_e_restaura_apos_falha(monkeypatch, tmp_path, caso, modo, falhar):
    from eval import avaliar_comparativo as avaliador
    saida = tmp_path / 'resultado.json'
    argv = ['comparativo', '--saida', str(saida), '--controle-sem-memoria', modo]
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setenv('USAR_FALSOS', '0')
    monkeypatch.setattr(comparativo.signal, 'signal', lambda *a: None)
    class Processo:
        returncode = None
        def __init__(self, *a, **kw): pass
        def poll(self): return self.returncode
        def terminate(self): self.returncode = 0
        def wait(self, **kw): return self.returncode
    class Saude:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(comparativo.subprocess, 'Popen', Processo)
    monkeypatch.setattr(comparativo, 'urlopen', lambda *a, **kw: Saude())
    chamadas = []
    def original(cliente, recebido, cenario, *a, **kw):
        chamadas.append(('original', cenario))
        return {'cenario': cenario}
    def direto(recebido, provedor, modelo, *, timeout=60):
        chamadas.append(('direto', 'sem_memoria'))
        assert recebido is caso and provedor == 'ollama'
        return {'cenario': 'sem_memoria', 'via': 'ollama_direto'}
    monkeypatch.setattr(avaliador, 'executar_cenario', original)
    monkeypatch.setattr(controle_modelo, 'executar_sem_memoria', direto)
    token_original = avaliador.carregar_token
    def executar():
        registros = [avaliador.executar_cenario(None, caso, c, 'ollama', 'simulado')
                     for c in avaliador.CENARIOS]
        if falhar:
            raise RuntimeError('falha simulada')
        saida.write_text(json.dumps({'resultados': registros, 'observacoes': []}), encoding='utf-8')
        return 0
    monkeypatch.setattr(avaliador, 'main', executar)
    if falhar:
        with pytest.raises(RuntimeError): comparativo.main()
    else:
        assert comparativo.main() == 0
        doc = json.loads(saida.read_text(encoding='utf-8'))
        assert (doc.get('controle_sem_memoria') == 'modelo_direto') is (modo == 'modelo_direto')
    assert len(chamadas) == 4
    assert ('direto', 'sem_memoria') in chamadas if modo == 'modelo_direto' else all(c[0] == 'original' for c in chamadas)
    assert avaliador.executar_cenario is original
    assert avaliador.carregar_token is token_original
    assert sys.argv is argv


def test_provedor_incompativel_recusado_antes_de_processo(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'argv', ['comparativo', '--saida', str(tmp_path/'saida.json'),
                                    '--provedor', 'openai', '--controle-sem-memoria', 'modelo_direto'])
    monkeypatch.setattr(comparativo.subprocess, 'Popen', lambda *a, **kw: pytest.fail('Não iniciar'))
    with pytest.raises(SystemExit): comparativo.main()
