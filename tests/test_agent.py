
from unittest.mock import patch

import pytest

from src import agent


USUARIO_TESTE = "usuario_teste"


def setup_function():
    agent.historicos_por_usuario.clear()


@patch("src.agent.modelo_ia.gerar")
def test_responder_retorna_resposta_do_modelo(mock_gerar):
    mock_gerar.return_value = "Olá! Sou o agente."

    resposta = agent.responder("Olá", usuario_id=USUARIO_TESTE)

    assert resposta == "Olá! Sou o agente."
    mock_gerar.assert_called_once()


@patch("src.agent.modelo_ia.gerar")
def test_responder_mantem_historico(mock_gerar):
    mock_gerar.return_value = "Seu projeto se chama Axis."

    agent.responder(
        "Meu projeto se chama Axis.",
        usuario_id=USUARIO_TESTE,
    )

    historico = agent.obter_historico(USUARIO_TESTE)

    assert historico[-2] == {
        "role": "user",
        "content": "Meu projeto se chama Axis.",
    }
    assert historico[-1] == {
        "role": "assistant",
        "content": "Seu projeto se chama Axis.",
    }


def test_mensagem_vazia_nao_consulta_modelo():
    with patch("src.agent.modelo_ia.gerar") as mock_gerar:
        resposta = agent.responder("   ", usuario_id=USUARIO_TESTE)

    assert resposta == ""
    mock_gerar.assert_not_called()


@patch("src.agent.modelo_ia.gerar")
def test_falha_ollama_nao_adiciona_mensagem_ao_historico(mock_gerar):
    mock_gerar.side_effect = RuntimeError("Ollama indisponível")

    with pytest.raises(RuntimeError, match="Ollama indisponível"):
        agent.responder("Olá", usuario_id=USUARIO_TESTE)

    historico = agent.obter_historico(USUARIO_TESTE)

    assert len(historico) == 1
    assert historico[0]["role"] == "system"


@patch("src.agent.modelo_ia.gerar")
def test_agente_responde_apos_falha_anterior(mock_gerar):
    mock_gerar.side_effect = [
        RuntimeError("Falha temporária"),
        "Consegui responder.",
    ]

    with pytest.raises(RuntimeError):
        agent.responder("Primeira tentativa", usuario_id=USUARIO_TESTE)

    resposta = agent.responder(
        "Nova tentativa",
        usuario_id=USUARIO_TESTE,
    )

    historico = agent.obter_historico(USUARIO_TESTE)

    assert resposta == "Consegui responder."
    assert historico[-2]["content"] == "Nova tentativa"
    assert historico[-1]["content"] == "Consegui responder."


@patch("src.agent.modelo_ia.gerar")
def test_resposta_vazia_nao_altera_historico(mock_gerar):
    mock_gerar.side_effect = agent.RespostaModeloVaziaError(
        "O modelo retornou uma resposta vazia."
    )

    with pytest.raises(agent.RespostaModeloVaziaError):
        agent.responder("Olá", usuario_id=USUARIO_TESTE)

    historico = agent.obter_historico(USUARIO_TESTE)

    assert len(historico) == 1
    assert historico[0]["role"] == "system"

def test_memoria_externa_e_incluida_no_contexto(monkeypatch):
    chamadas = []

    def modelo_simulado(mensagens):
        chamadas.append(mensagens)
        return "O projeto se chama Axis."

    monkeypatch.setattr(agent.modelo_ia, "gerar", modelo_simulado)

    resposta = agent.responder(
        "Qual é o nome do projeto?",
        usuario_id=USUARIO_TESTE,
        memorias=["O projeto se chama Axis."],
    )

    assert "Axis" in resposta

    mensagens = chamadas[0]
    assert any(
        "O projeto se chama Axis." in mensagem["content"]
        for mensagem in mensagens
    )


def test_sem_memorias_continua_funcionando(monkeypatch):
    chamadas = []

    def modelo_simulado(mensagens):
        chamadas.append(mensagens)
        return "Olá!"

    monkeypatch.setattr(agent.modelo_ia, "gerar", modelo_simulado)

    resposta = agent.responder("Olá!", usuario_id=USUARIO_TESTE)

    assert resposta == "Olá!"
    assert len(chamadas) == 1
    assert not any(
        mensagem["role"] == "system"
        and "Contexto de memória:" in mensagem["content"]
        for mensagem in chamadas[0]
    )


def test_memoria_externa_nao_fica_no_historico_permanente():
    contexto = agent.formatar_memorias(["O projeto se chama Axis."])
    historico = agent.obter_historico(USUARIO_TESTE)

    assert "Axis" in contexto
    assert all(
        "Contexto de memória:" not in mensagem["content"]
        for mensagem in historico
    )


def test_historicos_sao_separados_por_usuario():
    historico_a = agent.obter_historico("usuario_a")
    historico_b = agent.obter_historico("usuario_b")

    historico_a.append({
        "role": "user",
        "content": "Informação privada do usuário A",
    })

    assert len(historico_b) == 1
    assert all(
        mensagem["content"] != "Informação privada do usuário A"
        for mensagem in historico_b
    )


def test_usuario_id_e_obrigatorio():
    with pytest.raises(ValueError, match="usuario_id"):
        agent.responder("Olá", usuario_id="")


def test_limpar_historico_afeta_apenas_usuario_escolhido():
    agent.obter_historico("usuario_a").append({
        "role": "user",
        "content": "Conversa A",
    })
    agent.obter_historico("usuario_b").append({
        "role": "user",
        "content": "Conversa B",
    })

    agent.limpar_historico("usuario_a")

    assert len(agent.obter_historico("usuario_a")) == 1
    assert agent.obter_historico("usuario_b")[-1]["content"] == "Conversa B"


def test_responder_com_detalhes_retorna_metricas():
    class AdaptadorComMetricas:
        def gerar_com_detalhes(self, mensagens):
            return {
                "resposta": "A memória registra apenas a frase de teste.",
                "tokens_entrada": 21,
                "tokens_saida": 9,
            }

    resultado = agent.responder(
        "O que foi registrado?",
        usuario_id=USUARIO_TESTE,
        memorias=["Teste memoria persistente no Docker"],
        adaptador=AdaptadorComMetricas(),
        retornar_detalhes=True,
    )

    assert resultado["resposta"] == "A memória registra apenas a frase de teste."
    assert resultado["tokens_entrada"] == 21
    assert resultado["tokens_saida"] == 9
