import pytest

from src import agent
from src.api.agente_local import AgenteLocal
from src.api.catalogo import SelecaoModelo


@pytest.fixture(autouse=True)
def historico_limpo():
    agent.historicos_por_usuario.clear()
    yield
    agent.historicos_por_usuario.clear()


class Modelo:
    def __init__(self):
        self.chamadas = []

    def gerar(self, mensagens):
        self.chamadas.append([dict(m) for m in mensagens])
        return 'Resposta de teste'


def test_api_reduz_contexto_sem_mudar_baseline_ou_historico_guardado(monkeypatch):
    modelo = Modelo()
    api = AgenteLocal()
    monkeypatch.setattr(api, '_adaptador', lambda *args: modelo)
    for i in range(8):
        agent.responder(f'Turno {i}', 'u', adaptador=modelo)
    api.responder('u', 'Continue', [], SelecaoModelo('ollama', 'teste'))
    assert [m['content'] for m in modelo.chamadas[-1] if m['role'] == 'user'] == [
        'Turno 5', 'Turno 6', 'Turno 7', 'Continue']
    assert len(agent.obter_historico('u')) == 19
    agent.responder('Baseline', 'u', adaptador=modelo)
    assert len([m for m in modelo.chamadas[-1] if m['role'] == 'user']) == 10


def test_orcamento_nao_corta_turno_nem_pergunta_atual_ou_memorias():
    modelo = Modelo()
    agent.responder('x' * 7000, 'u', adaptador=modelo)
    pergunta = 'Explique ' + 'y' * 7000
    agent.responder(pergunta, 'u', ['Fato importante.'], modelo, contexto_compacto=True)
    mensagens = modelo.chamadas[-1]
    assert mensagens[0]['content'] == agent.SYSTEM_PROMPT_COMPACTO
    assert mensagens[-1]['content'] == pergunta
    assert any('Fato importante.' in m['content'] for m in mensagens)
    assert not any(m['content'] == 'x' * 7000 for m in mensagens)
    assert len(agent.obter_historico('u')) == 5


def test_turno_recente_preserva_referencia_e_memoria_nao_e_repetida():
    modelo = Modelo()
    agent.responder('Compare as opções A e B.', 'u', adaptador=modelo)
    agent.responder('Explique a segunda.', 'u', ['Fato X.', {'texto': 'Fato X.'}], modelo,
                    contexto_compacto=True)
    enviados = modelo.chamadas[-1]
    assert enviados[-3]['content'] == 'Compare as opções A e B.'
    assert enviados[-2]['content'] == 'Resposta de teste'
    assert sum(m['content'].count('Fato X.') for m in enviados) == 1


def test_suporte_fora_do_contexto_nao_libera_geracao_sem_evidencia():
    modelo = Modelo()
    agent.responder('Moro em Joinville.', 'u', adaptador=modelo)
    for i in range(4):
        agent.responder(f'Conversa geral {i}', 'u', adaptador=modelo)
    antes = len(modelo.chamadas)
    resposta = agent.responder('Onde moro?', 'u', [], modelo, contexto_compacto=True)
    assert resposta == 'DESCONHECIDO'
    assert len(modelo.chamadas) == antes
    # A memória persistente recuperada continua permitindo a geração.
    agent.responder('Onde moro?', 'u', ['Mora em Joinville.'], modelo, contexto_compacto=True)
    assert len(modelo.chamadas) == antes + 1
