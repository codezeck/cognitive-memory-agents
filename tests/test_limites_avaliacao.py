"""Limites e perdas parciais: somente simulações, sem modelo/serviço real."""
import inspect
import json
import sys
from pathlib import Path

import httpx
import pytest

from eval import avaliar_comparativo as avaliador
from eval import historico_processo as processos
from src.interface import api_avaliacao, avaliacoes, comparativo, controle_modelo
from src.interface.protocolos import fonte_v3


@pytest.mark.parametrize('valor', [0, -1, float('inf'), float('nan'), True, '180'])
def test_limite_invalido_recusado_antes_de_criar_processo(monkeypatch, valor):
    monkeypatch.setattr(processos.multiprocessing, 'get_context', lambda *a: pytest.fail('Não criar processo'))
    with pytest.raises(ValueError):
        processos.executar_historico_em_processo({'mensagens': ['teste']}, 'ollama', 'simulado', timeout_modelo=valor)


@pytest.mark.parametrize('falhar', [False, True])
def test_api_dedicada_aplica_limite_e_restaura_fabricas(monkeypatch, falhar):
    import uvicorn
    from src.api import agente_local
    original_o, original_a = lambda modelo, timeout=60: timeout, lambda modelo, key, timeout=60: timeout
    monkeypatch.setattr(agente_local, 'OllamaAdapter', original_o)
    monkeypatch.setattr(agente_local, 'OpenAIAdapter', original_a)
    def executar(app, **opcoes):
        assert app == 'src.api.main:app' and opcoes == {'host': '127.0.0.1', 'port': 12345}
        assert agente_local.OllamaAdapter('simulado') == 180
        assert agente_local.OpenAIAdapter('simulado', 'chave-simulada') == 180
        if falhar:
            raise RuntimeError('falha simulada na API')
    monkeypatch.setattr(uvicorn, 'run', executar)
    if falhar:
        with pytest.raises(RuntimeError): api_avaliacao.main(['--port', '12345', '--timeout-modelo', '180'])
    else:
        api_avaliacao.main(['--port', '12345', '--timeout-modelo', '180'])
    assert agente_local.OllamaAdapter is original_o and agente_local.OpenAIAdapter is original_a
    assert agente_local.OllamaAdapter('simulado') == 60


def test_padrao_do_adaptador_do_chat_continua_60_segundos():
    from src.modelos.ollama_adapter import OllamaAdapter
    from src.modelos.openai_adapter import OpenAIAdapter
    assert inspect.signature(OllamaAdapter).parameters['timeout'].default == 60
    assert inspect.signature(OpenAIAdapter).parameters['timeout'].default == 60


def test_parcelas_do_filho_chegam_ao_relatorio_sem_inventar_chamada_ausente(monkeypatch):
    caso = fonte_v3()[0]
    caso = {**caso, 'mensagens': ['Fato um', 'Fato dois', caso['mensagens'][-1]]}
    erro = processos.FalhaProcessoHistorico('timeout simulado', ['ProvedorTimeout'])
    erro.chamadas_observadas = [{'tokens_entrada': 11, 'tokens_saida': 3}, {'tokens_entrada': 11, 'tokens_saida': 3}]
    def falhar(*a, **kw): raise erro
    monkeypatch.setattr(avaliador, 'executar_historico_em_processo', falhar)
    observacao = {}
    with pytest.raises(processos.FalhaProcessoHistorico):
        avaliador.executar_cenario(None, caso, 'historico_completo', 'ollama', 'simulado', observacao_tokens=observacao)
    assert observacao['ingestao']['tokens_total'] == 28
    assert observacao['pergunta_final']['tokens_total'] is None
    assert observacao['sessao']['tokens_total'] is None
    assert observacao['sessao']['tokens_total_observados'] == 28
    assert observacao['sessao']['chamadas_observadas'] == 2
    assert observacao['sessao']['chamadas_modelo'] is None


@pytest.mark.parametrize('falha_tecnica', [False, True])
def test_wrapper_limites_iguais_nos_quatro_cenarios_restaura_e_sinaliza_falha(monkeypatch, tmp_path, falha_tecnica):
    saida = tmp_path/'resultado.json'
    argv = ['comparativo', '--saida', str(saida), '--controle-sem-memoria', 'modelo_direto', '--timeout-modelo', '180']
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setenv('USAR_FALSOS', '0')
    monkeypatch.setattr(comparativo.signal, 'signal', lambda *a: None)
    processos_criados = []
    class Processo:
        returncode = None
        def __init__(self, args, **kw): processos_criados.append(args)
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
    def supervisor(caso, provedor, modelo, **opcoes):
        assert opcoes == {'timeout': None, 'timeout_modelo': 180}
        chamadas.append('historico')
        return []
    monkeypatch.setattr(avaliador, 'executar_historico_em_processo', supervisor)
    def original(cliente, caso, cenario, *a, **kw):
        chamadas.append(cenario)
        if cenario == 'historico_completo':
            avaliador.executar_historico_em_processo(caso, 'ollama', 'simulado')
        return {'cenario': cenario, **({'erro': 'timeout simulado'} if falha_tecnica and cenario == 'historico_completo' else {})}
    def direto(caso, provedor, modelo, **opcoes):
        assert opcoes == {'timeout': 180}
        chamadas.append('direto')
        return {'cenario': 'sem_memoria'}
    monkeypatch.setattr(avaliador, 'executar_cenario', original)
    monkeypatch.setattr(controle_modelo, 'executar_sem_memoria', direto)
    token = avaliador.carregar_token
    def executar():
        assert float(sys.argv[sys.argv.index('--timeout-api')+1]) == 210
        registros = [avaliador.executar_cenario(None, fonte_v3()[0], c, 'ollama', 'simulado') for c in avaliador.CENARIOS]
        saida.write_text(json.dumps({'resultados': registros, 'observacoes': []}), encoding='utf-8')
        return 0
    monkeypatch.setattr(avaliador, 'main', executar)
    assert comparativo.main() == int(falha_tecnica)
    assert 'src.interface.api_avaliacao' in processos_criados[0]
    assert processos_criados[0][-2:] == ['--timeout-modelo', '180.0']
    doc = json.loads(saida.read_text(encoding='utf-8'))
    assert doc['limites_execucao']['timeout_modelo_s'] == 180
    assert doc['limites_execucao']['timeout_api_s'] == 210
    assert doc['limites_execucao']['repeticao_automatica'] is False
    assert chamadas.count('direto') == chamadas.count('historico') == 1
    assert avaliador.executar_cenario is original
    assert avaliador.executar_historico_em_processo is supervisor
    assert avaliador.carregar_token is token and sys.argv is argv


def test_relatorio_antigo_com_erro_nao_e_sucesso_e_nao_e_reescrito(monkeypatch, tmp_path):
    monkeypatch.setenv('DB_PATH', str(tmp_path/'conversa.db'))
    monkeypatch.setattr(avaliacoes, '_jobs', {})
    pasta = tmp_path/'avaliacoes-interface'/('a'*32)
    pasta.mkdir(parents=True)
    (pasta/'dono.json').write_text(json.dumps({'usuario': 'demo', 'protocolo': 'comparativo_v3'}))
    arquivo = pasta/'relatorio.json'
    arquivo.write_text(json.dumps({'interface': {'codigo_saida': 0}, 'resultados': [{'erro': 'timeout'}]}))
    antes = arquivo.read_bytes()
    assert avaliacoes.consultar('a'*32, 'demo')[0]['estado'] == 'falhou'
    assert avaliacoes.listar('demo')['avaliacoes'][0]['estado'] == 'falhou'
    assert arquivo.read_bytes() == antes
