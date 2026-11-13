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


@pytest.mark.parametrize("provedor", ["ollama", "openai"])
@pytest.mark.parametrize("modelo", [None, "", "  ", " modelo", "modelo ", 123])
def test_modelo_invalido_e_recusado_antes_de_criar_cliente(monkeypatch, provedor, modelo):
    from unittest.mock import Mock
    cliente = Mock(side_effect=AssertionError("não deve criar cliente"))
    monkeypatch.setattr("src.api.agente_local.OllamaAdapter", cliente)
    monkeypatch.setattr("src.api.agente_local.OpenAIAdapter", cliente)
    with pytest.raises(ModeloNaoPermitido):
        AgenteLocal()._adaptador(provedor, modelo)
    cliente.assert_not_called()


@pytest.mark.parametrize("provedor", [None, "", "anthropic", "OLLAMA", [], 123])
def test_provedor_invalido_nao_cria_cliente(monkeypatch, provedor):
    from unittest.mock import Mock
    cliente = Mock(side_effect=AssertionError("não deve criar cliente"))
    monkeypatch.setattr("src.api.agente_local.OllamaAdapter", cliente)
    monkeypatch.setattr("src.api.agente_local.OpenAIAdapter", cliente)
    with pytest.raises(ModeloNaoPermitido):
        AgenteLocal()._adaptador(provedor, "modelo-teste")
    cliente.assert_not_called()


@pytest.mark.parametrize("provedor", ["ollama", "openai"])
@pytest.mark.parametrize("falha", ["vazia", "conexao", "timeout", "http"])
def test_falhas_dos_provedores_preservam_historico_e_retornam_erro_publico(
    monkeypatch, provedor, falha,
):
    from unittest.mock import Mock
    import httpx
    import ollama
    from openai import APIConnectionError, APIStatusError, APITimeoutError
    from src.api.erros import ProvedorIndisponivel
    from src.modelos.ollama_adapter import OllamaAdapter
    from src.modelos.openai_adapter import OpenAIAdapter

    # Adaptadores reais, apenas os clientes de rede são substituídos.
    cliente = Mock()
    monkeypatch.setattr("src.modelos.ollama_adapter.ollama.Client", lambda **kwargs: cliente)
    monkeypatch.setattr("src.modelos.openai_adapter.OpenAI", lambda **kwargs: cliente)
    pedido = httpx.Request("POST", "http://provedor.invalid/chat")
    if provedor == "ollama":
        adaptador = OllamaAdapter("modelo-teste")
        chamada = cliente.chat
        erros = {"conexao": httpx.ConnectError("detalhe privado", request=pedido),
                 "timeout": httpx.ReadTimeout("detalhe privado", request=pedido),
                 "http": ollama.ResponseError("detalhe privado", status_code=500)}
        resposta_vazia = SimpleNamespace(message=SimpleNamespace(content="  "))
        resposta_ok = SimpleNamespace(message=SimpleNamespace(content="Resposta válida"),
                                      prompt_eval_count=12, eval_count=3)
    else:
        adaptador = OpenAIAdapter("modelo-teste", "chave-simulada")
        chamada = cliente.chat.completions.create
        erros = {"conexao": APIConnectionError(request=pedido),
                 "timeout": APITimeoutError(request=pedido),
                 "http": APIStatusError("detalhe privado",
                         response=httpx.Response(500, request=pedido), body=None)}
        resposta_vazia = SimpleNamespace(choices=[])
        resposta_ok = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Resposta válida"))],
                                      usage=SimpleNamespace(prompt_tokens=12, completion_tokens=3))
    if falha == "vazia":
        chamada.return_value = resposta_vazia
    else:
        chamada.side_effect = erros[falha]
    monkeypatch.setattr(agente_mod, "historicos_por_usuario", {
        "u1": [{"role": "system", "content": agente_mod.SYSTEM_PROMPT},
               {"role": "user", "content": "Conversa anterior"},
               {"role": "assistant", "content": "Resposta anterior"}],
        "u2": [{"role": "system", "content": agente_mod.SYSTEM_PROMPT}],
    })
    import copy
    antes = copy.deepcopy(agente_mod.historicos_por_usuario)
    agente = AgenteLocal()
    agente._adaptadores[(provedor, "modelo-teste")] = adaptador
    classe = ProvedorTimeout if falha == "timeout" else ProvedorIndisponivel
    with pytest.raises(classe) as captura:
        agente.responder("u1", "Tentativa que falha", [], SelecaoModelo(provedor, "modelo-teste"))
    assert "detalhe privado" not in str(captura.value)
    assert agente_mod.historicos_por_usuario == antes
    # Recuperação após falha continua usando o mesmo histórico e adaptador.
    chamada.side_effect = None
    chamada.return_value = resposta_ok
    resultado = agente.responder("u1", "Nova tentativa", [], SelecaoModelo(provedor, "modelo-teste"))
    assert resultado == ResultadoAgente("Resposta válida", 12, 3)
    assert len(agente_mod.historicos_por_usuario["u1"]) == len(antes["u1"]) + 2
    assert agente_mod.historicos_por_usuario["u2"] == antes["u2"]


@pytest.mark.parametrize("provedor", ["ollama", "openai"])
def test_resposta_vazia_e_http_503_sem_alterar_endpoint(monkeypatch, provedor):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.api.dependencias import get_catalogo, get_conversador
    from src.api.catalogo import Catalogo
    from src.api.config import Configuracao
    from src.api.servico import Conversador
    from src.memoria import MemoriaEmRam
    from src.modelos.base import RespostaModeloVaziaError
    from src.modelos.openai_adapter import RespostaOpenAIVaziaError

    class ModeloVazio:
        def gerar(self, mensagens):
            classe = RespostaOpenAIVaziaError if provedor == "openai" else RespostaModeloVaziaError
            raise classe("detalhe privado do provedor")

    agente = AgenteLocal()
    agente._adaptadores[(provedor, "modelo-teste")] = ModeloVazio()
    monkeypatch.setenv("API_TOKENS", "token-simulado:u1")
    monkeypatch.setenv("OPENAI_API_KEY", "chave-simulada")
    monkeypatch.setattr(agente_mod, "historicos_por_usuario", {})
    config = Configuracao(provedor, "modelo-teste", ((provedor, "modelo-teste"),))
    # Não instancia get_memoria(), não abre SQLite e não acessa a rede.
    overrides = dict(app.dependency_overrides)
    try:
        app.dependency_overrides[get_catalogo] = lambda: Catalogo(config)
        app.dependency_overrides[get_conversador] = lambda: Conversador(agente, MemoriaEmRam())
        with TestClient(app, raise_server_exceptions=False) as cliente:
            resposta = cliente.post("/conversas", json={"usuario_id": "u1", "mensagem": "Oi"},
                                    headers={"Authorization": "Bearer token-simulado"})
        assert resposta.status_code == 503
        assert resposta.json() == {"codigo": "provedor_indisponivel",
                                   "mensagem": "O provedor não retornou uma resposta válida."}
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
