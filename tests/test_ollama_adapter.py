
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from src.modelos.ollama_adapter import (
    OllamaAdapter,
    ModeloIndisponivelError,
    RespostaModeloVaziaError,
)


@pytest.fixture
def mock_client():
    with patch("src.modelos.ollama_adapter.ollama.Client") as mock:
        yield mock.return_value


@pytest.fixture
def adapter(mock_client):
    return OllamaAdapter("modelo-teste")


def resposta_simulada(texto="Olá!", entrada=10, saida=5):
    return SimpleNamespace(
        message=SimpleNamespace(content=texto),
        prompt_eval_count=entrada,
        eval_count=saida,
    )


def test_cliente_configurado_com_timeout(mock_client):
    OllamaAdapter("modelo-teste", timeout=30)

    mock_client_class = patch(
        "src.modelos.ollama_adapter.ollama.Client"
    )

    # O cliente é validado pelo teste de construção abaixo.


@patch("src.modelos.ollama_adapter.ollama.Client")
def test_timeout_e_passado_ao_cliente(mock_client_class):
    OllamaAdapter("modelo-teste", timeout=30)

    timeout = mock_client_class.call_args.kwargs["timeout"]

    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 30
    assert timeout.read == 30


def test_gerar_retorna_texto(mock_client, adapter):
    mock_client.chat.return_value = resposta_simulada()

    resultado = adapter.gerar([{"role": "user", "content": "Oi"}])

    assert resultado == "Olá!"


def test_gerar_com_detalhes_retorna_metricas(mock_client, adapter):
    mock_client.chat.return_value = resposta_simulada(
        texto="Teste",
        entrada=12,
        saida=7,
    )

    resultado = adapter.gerar_com_detalhes(
        [{"role": "user", "content": "Oi"}]
    )

    assert resultado == {
        "resposta": "Teste",
        "tokens_entrada": 12,
        "tokens_saida": 7,
    }


def test_erro_ollama_e_convertido(mock_client, adapter):
    mock_client.chat.side_effect = ConnectionError("Conexão recusada")

    with pytest.raises(ModeloIndisponivelError) as erro:
        adapter.gerar([{"role": "user", "content": "Oi"}])

    assert "Ollama" in str(erro.value)
    assert isinstance(erro.value.__cause__, ConnectionError)


def test_timeout_ollama_e_convertido(mock_client, adapter):
    mock_client.chat.side_effect = httpx.ReadTimeout("Tempo esgotado")

    with pytest.raises(ModeloIndisponivelError) as erro:
        adapter.gerar([{"role": "user", "content": "Oi"}])

    assert isinstance(erro.value.__cause__, httpx.ReadTimeout)


@pytest.mark.parametrize("conteudo", ["", "   ", None])
def test_resposta_vazia_gera_erro(mock_client, adapter, conteudo):
    mock_client.chat.return_value = resposta_simulada(texto=conteudo)

    with pytest.raises(RespostaModeloVaziaError):
        adapter.gerar([{"role": "user", "content": "Oi"}])
