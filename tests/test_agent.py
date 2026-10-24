
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


from types import SimpleNamespace

from src import agent


def test_memoria_externa_e_incluida_no_contexto(monkeypatch):
    chamadas = []

    def modelo_simulado(model, messages):
        chamadas.append(messages)
        return SimpleNamespace(
            message=SimpleNamespace(
                content="O projeto se chama Axis."
            )
        )

    monkeypatch.setattr(agent.ollama, "chat", modelo_simulado)

    historico_original = agent.historico.copy()

    try:
        resposta = agent.responder(
            "Qual é o nome do projeto?",
            memorias=["O projeto se chama Axis."],
        )

        assert "Axis" in resposta

        mensagens = chamadas[0]
        assert any(
            "O projeto se chama Axis." in mensagem["content"]
            for mensagem in mensagens
        )

    finally:
        agent.historico[:] = historico_original


def test_sem_memorias_continua_funcionando(monkeypatch):
    chamadas = []

    def modelo_simulado(model, messages):
        chamadas.append(messages)
        return SimpleNamespace(
            message=SimpleNamespace(content="Olá!")
        )

    monkeypatch.setattr(agent.ollama, "chat", modelo_simulado)

    historico_original = agent.historico.copy()

    try:
        resposta = agent.responder("Olá!")

        assert resposta == "Olá!"
        assert len(chamadas) == 1
        assert not any(
            mensagem["role"] == "system"
            and "Contexto de memória:" in mensagem["content"]
            for mensagem in chamadas[0]
        )

    finally:
        agent.historico[:] = historico_original


def test_memoria_externa_nao_fica_no_historico_permanente():
    historico_original = agent.historico.copy()

    try:
        contexto = agent.formatar_memorias(
            ["O projeto se chama Axis."]
        )

        assert "Axis" in contexto
        assert all(
            "Contexto de memória:" not in mensagem["content"]
            for mensagem in agent.historico
        )

    finally:
        agent.historico[:] = historico_original
