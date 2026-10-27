from types import SimpleNamespace

import pytest

from src import agent as agente_mod
from src.api.agente_local import AgenteLocal
from src.api.catalogo import SelecaoModelo
from src.api.erros import ModeloNaoPermitido, ProvedorNaoConfigurado
from src.api.servico import ResultadoAgente
from src.api.erros import ProvedorTimeout
from src.modelos.ollama_adapter import ModeloIndisponivelError


class AdaptadorFalso:
    def __init__(self, modelo, api_key=None):
        self.modelo = modelo
        self.api_key = api_key

    def gerar(self, mensagens):
        return "Resposta simulada"


def test_agente_local_seleciona_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(
        "src.api.agente_local.OpenAIAdapter",
        AdaptadorFalso,
    )

    chamada = {}

    def responder(mensagem, usuario_id, memorias=None, adaptador=None):
        chamada["adaptador"] = adaptador
        return adaptador.gerar([{"role": "user", "content": mensagem}])

    monkeypatch.setattr(agente_mod, "responder", responder)

    resultado = AgenteLocal().responder(
        "u1", "Olá", [], SelecaoModelo("openai", "gpt-test")
    )

    assert resultado == ResultadoAgente(resposta="Resposta simulada")
    assert chamada["adaptador"].modelo == "gpt-test"
    assert chamada["adaptador"].api_key == "chave-de-teste"


def test_agente_local_openai_sem_chave(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agente = AgenteLocal()

    with pytest.raises(ProvedorNaoConfigurado):
        agente._adaptador("openai", "gpt-test")


def test_agente_local_recusa_provedor_sem_adaptador():
    agente = AgenteLocal()

    with pytest.raises(ModeloNaoPermitido):
        agente._adaptador("provedor-desconhecido", "modelo-teste")


def test_agente_local_preserva_erro_da_openai(monkeypatch):
    from src.api.erros import ProvedorIndisponivel
    from src import agent as agente_mod

    def falha_openai(mensagem, usuario_id, memorias=None, adaptador=None):
        raise ProvedorIndisponivel("Não foi possível consultar a OpenAI.")

    monkeypatch.setattr(agente_mod, "responder", falha_openai)

    agente = AgenteLocal()

    monkeypatch.setenv("OPENAI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(
        "src.api.agente_local.OpenAIAdapter",
        AdaptadorFalso,
    )

    with pytest.raises(ProvedorIndisponivel, match="OpenAI"):
        agente.responder(
            "u1",
            "Olá",
            [],
            SelecaoModelo("openai", "gpt-test"),
        )


def test_agente_local_converte_timeout_do_ollama(monkeypatch):
    from src.api import agente_local as modulo_agente

    def falha_ollama(mensagens):
        erro_original = TimeoutError("Tempo esgotado")
        raise ModeloIndisponivelError(
            "Falha no Ollama."
        ) from erro_original

    class AdaptadorOllamaFalso:
        def __init__(self, modelo):
            pass

        def gerar(self, mensagens):
            return falha_ollama(mensagens)

    monkeypatch.setattr(
        modulo_agente,
        "OllamaAdapter",
        AdaptadorOllamaFalso,
    )

    def responder(mensagem, usuario_id, memorias=None, adaptador=None):
        return adaptador.gerar(
            [{"role": "user", "content": mensagem}]
        )

    monkeypatch.setattr(agente_mod, "responder", responder)

    agente = AgenteLocal()

    with pytest.raises(ProvedorTimeout):
        agente.responder(
            "u1",
            "Olá",
            [],
            SelecaoModelo("ollama", "modelo-teste"),
        )