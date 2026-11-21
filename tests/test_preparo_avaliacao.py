import json
import httpx
import pytest

from src.interface import executar_avaliacao as runner
from src.interface.preparo import FalhaPreparo, preparar_modelo


def cliente_falso(monkeypatch, responder):
    cliente = httpx.Client(transport=httpx.MockTransport(responder), trust_env=False)
    monkeypatch.setattr('src.interface.preparo.httpx.Client', lambda **kwargs: cliente)
    return cliente


def test_preparo_carrega_sem_prompt_de_teste_e_nao_baixa_pesos(monkeypatch, tmp_path):
    pedidos = []
    def responder(r):
        pedidos.append(r)
        if r.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'simulado', 'digest': 'digest-falso'}]})
        assert r.url.path == '/api/generate'
        assert json.loads(r.content) == {'model': 'simulado', 'prompt': '', 'stream': False}
        return httpx.Response(200, json={'done': True})
    cliente = cliente_falso(monkeypatch, responder)
    progresso = tmp_path / 'progresso.json'
    resultado = preparar_modelo('simulado', progresso, previstos=40, unidade='sessões')
    assert resultado['digest'] == 'digest-falso'
    assert resultado['incluido_nos_tokens_dos_casos'] is False
    assert resultado['prazo_segundos'] == 900
    assert cliente.is_closed and len(pedidos) == 2
    assert all('pull' not in str(r.url) for r in pedidos)
    assert json.loads(progresso.read_text(encoding='utf-8'))['concluidos'] == 0


@pytest.mark.parametrize('falha,codigo', [('modelo', 'modelo_ausente'), ('timeout', 'timeout_preparo'),
                                        ('http', 'ollama_indisponivel'), ('resposta', 'carregamento_nao_confirmado')])
def test_preparo_falha_com_diagnostico_seguro(monkeypatch, tmp_path, falha, codigo):
    pedidos = []
    def responder(r):
        pedidos.append(r)
        if r.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [] if falha == 'modelo' else [{'name': 'simulado'}]})
        if falha == 'timeout':
            raise httpx.ReadTimeout('Bearer segredo-nao-registrar', request=r)
        return httpx.Response(503 if falha == 'http' else 200, json={'done': False})
    cliente_falso(monkeypatch, responder)
    with pytest.raises(FalhaPreparo) as erro:
        preparar_modelo('simulado', tmp_path/'progresso.json', previstos=40, unidade='sessões')
    assert erro.value.codigo == codigo
    assert 'segredo' not in str(erro.value)
    assert len(pedidos) == (1 if falha == 'modelo' else 2)


def test_runner_nao_inicia_p6_quando_preparo_falha(monkeypatch, tmp_path):
    from tools import reproduzir_p6
    def falhar(*a, **kw):
        raise FalhaPreparo('timeout_preparo', 'O modelo não carregou; nenhuma tentativa iniciada.')
    monkeypatch.setattr(runner, 'preparar_modelo', falhar)
    def proibido(*a, **kw):
        pytest.fail('Não executar o roteiro antes de carregar o modelo')
    monkeypatch.setattr(reproduzir_p6, 'main', proibido)
    args = ['--protocolo', 'p6', '--modelo', 'simulado', '--saida', str(tmp_path/'relatorio.json'),
            '--progresso', str(tmp_path/'progresso.json')]
    assert runner.main(args) == 1
    falha = json.loads((tmp_path/'falha-preparo.json').read_text(encoding='utf-8'))
    assert falha['tentativas_iniciadas'] == 0
    assert not (tmp_path/'relatorio.json').exists()


def test_p6_recusa_fontes_invalidas_antes_do_preparo(monkeypatch, tmp_path):
    from tools import reproduzir_p6
    def fonte_invalida(*a, **kw):
        raise ValueError('Fonte difere do congelamento')
    monkeypatch.setattr(reproduzir_p6, 'preparar_protocolo', fonte_invalida)
    def proibido(*a, **kw):
        pytest.fail('Fonte inválida não pode iniciar sequer o carregamento do modelo')
    monkeypatch.setattr(runner, 'preparar_modelo', proibido)
    with pytest.raises(SystemExit) as erro:
        runner.main(['--protocolo', 'p6', '--modelo', 'simulado', '--saida', str(tmp_path/'relatorio.json'),
                     '--progresso', str(tmp_path/'progresso.json')])
    assert erro.value.code == 2
