
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.modelos.ollama_adapter import (
    OllamaAdapter,
    ModeloIndisponivelError,
    RespostaModeloVaziaError,
)


@pytest.fixture
def adapter():
    return OllamaAdapter("modelo-teste")


def resposta_simulada(texto="Olá!", entrada=10, saida=5):
    return SimpleNamespace(
        message=SimpleNamespace(content=texto),
        prompt_eval_count=entrada,
        eval_count=saida,
    )


@patch("src.modelos.ollama_adapter.ollama.chat")
def test_gerar_retorna_texto(mock_chat, adapter):
    mock_chat.return_value = resposta_simulada()

    resultado = adapter.gerar([{"role": "user", "content": "Oi"}])

    assert resultado == "Olá!"


@patch("src.modelos.ollama_adapter.ollama.chat")
def test_gerar_com_detalhes_retorna_metricas(mock_chat, adapter):
    mock_chat.return_value = resposta_simulada(
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


@patch("src.modelos.ollama_adapter.ollama.chat")
def test_erro_ollama_e_convertido(mock_chat, adapter):
    mock_chat.side_effect = ConnectionError("Conexão recusada")

    with pytest.raises(ModeloIndisponivelError) as erro:
        adapter.gerar([{"role": "user", "content": "Oi"}])

    assert "Ollama" in str(erro.value)
    assert isinstance(erro.value.__cause__, ConnectionError)


@pytest.mark.parametrize("conteudo", ["", "   ", None])
@patch("src.modelos.ollama_adapter.ollama.chat")
def test_resposta_vazia_gera_erro(mock_chat, adapter, conteudo):
    mock_chat.return_value = resposta_simulada(texto=conteudo)

    with pytest.raises(RespostaModeloVaziaError):
        adapter.gerar([{"role": "user", "content": "Oi"}])
