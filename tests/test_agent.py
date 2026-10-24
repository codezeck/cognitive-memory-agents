
from unittest.mock import patch, Mock

import ollama

from src import agent


def setup_function():
    agent.historico.clear()
    agent.historico.append({
        "role": "system",
        "content": agent.SYSTEM_PROMPT,
    })


@patch("src.agent.ollama.chat")
def test_responder_retorna_resposta_do_modelo(mock_chat):
    mock_chat.return_value = Mock(
        message=Mock(content="Olá! Sou o agente.")
    )

    resposta = agent.responder("Olá")

    assert resposta == "Olá! Sou o agente."
    mock_chat.assert_called_once()


@patch("src.agent.ollama.chat")
def test_responder_mantem_historico(mock_chat):
    mock_chat.return_value = Mock(
        message=Mock(content="Seu projeto se chama Axis.")
    )

    agent.responder("Meu projeto se chama Axis.")

    assert agent.historico[-2] == {
        "role": "user",
        "content": "Meu projeto se chama Axis.",
    }
    assert agent.historico[-1] == {
        "role": "assistant",
        "content": "Seu projeto se chama Axis.",
    }


def test_mensagem_vazia_nao_consulta_modelo():
    with patch("src.agent.ollama.chat") as mock_chat:
        resposta = agent.responder("   ")

    assert resposta == ""
    mock_chat.assert_not_called()



import pytest


@patch("src.agent.ollama.chat")
def test_falha_ollama_remove_mensagem_incompleta(mock_chat):
    mock_chat.side_effect = RuntimeError("Ollama indisponível")

    with pytest.raises(RuntimeError, match="Ollama indisponível"):
        agent.responder("Olá")

    # Deve permanecer apenas a mensagem de sistema.
    assert len(agent.historico) == 1
    assert agent.historico[0]["role"] == "system"


@patch("src.agent.ollama.chat")
def test_agente_responde_apos_falha_anterior(mock_chat):
    mock_chat.side_effect = [
        RuntimeError("Falha temporária"),
        Mock(message=Mock(content="Consegui responder.")),
    ]

    with pytest.raises(RuntimeError):
        agent.responder("Primeira tentativa")

    resposta = agent.responder("Nova tentativa")

    assert resposta == "Consegui responder."
    assert agent.historico[-2]["content"] == "Nova tentativa"
    assert agent.historico[-1]["content"] == "Consegui responder."
