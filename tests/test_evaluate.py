
from types import SimpleNamespace

from eval import evaluate


def test_resposta_correta_e_aprovada():
    assert evaluate.avaliar_resposta(
        "O projeto se chama Axis.",
        "Axis",
    )


def test_resposta_incorreta_e_reprovada():
    assert not evaluate.avaliar_resposta(
        "O projeto se chama Codezeck.",
        "Axis",
    )


def test_lista_de_termos_exige_todos():
    assert evaluate.avaliar_resposta(
        "Prefiro respostas curtas e objetivas.",
        ["curtas", "objetiva"],
    )

    assert not evaluate.avaliar_resposta(
        "Prefiro respostas curtas.",
        ["curtas", "objetiva"],
    )


def test_cenario_sem_memoria_usa_apenas_pergunta(monkeypatch):
    chamadas = []

    def modelo_simulado(model, messages, options):
        chamadas.append(messages)
        return SimpleNamespace(
            message=SimpleNamespace(content="Brasília"),
            prompt_eval_count=10,
            eval_count=2,
        )

    monkeypatch.setattr(
        evaluate.agent.ollama,
        "chat",
        modelo_simulado,
    )

    caso = {
        "id": "TEST001",
        "categoria": "contexto",
        "mensagens": [
            "Minha cidade favorita é Santos.",
            "Qual é a capital do Brasil?",
        ],
        "esperado": "Brasília",
    }

    resultado = evaluate.avaliar_caso(caso, "sem_memoria")

    assert resultado["passou"]
    assert resultado["tokens_total"] == 12
    assert resultado["chamadas_modelo"] == 1
    assert len(chamadas) == 1
    assert len(chamadas[0]) == 2
    assert "Santos" not in str(chamadas[0])


def test_memoria_externa_recebe_fatos_fornecidos(monkeypatch):
    chamadas = []

    def modelo_simulado(model, messages, options):
        chamadas.append(messages)
        return SimpleNamespace(
            message=SimpleNamespace(content="Codezeck"),
            prompt_eval_count=20,
            eval_count=3,
        )

    monkeypatch.setattr(
        evaluate.agent.ollama,
        "chat",
        modelo_simulado,
    )

    caso = {
        "id": "TEST002",
        "categoria": "atualizacao",
        "mensagens": [
            "Meu projeto mudou de nome.",
            "Qual é o nome atual?",
        ],
        "memorias": [
            "O nome atual do projeto é Codezeck."
        ],
        "esperado": "Codezeck",
    }

    resultado = evaluate.avaliar_caso(caso, "memoria_externa")

    assert resultado["passou"]
    assert resultado["tokens_entrada"] == 20
    assert resultado["tokens_saida"] == 3
    assert "Codezeck" in str(chamadas[0])


def test_resumo_calcula_metricas_e_ignora_erros_nas_taxas():
    resultados = [
        {
            "cenario": "sem_memoria",
            "passou": True,
            "tokens_entrada": 10,
            "tokens_saida": 2,
            "tokens_total": 12,
            "tempo_ms": 100,
            "chamadas_modelo": 1,
        },
        {
            "cenario": "sem_memoria",
            "passou": False,
            "tokens_entrada": 8,
            "tokens_saida": 2,
            "tokens_total": 10,
            "tempo_ms": 50,
            "chamadas_modelo": 1,
        },
        {
            "cenario": "sem_memoria",
            "passou": False,
            "erro": "falha simulada",
        },
    ]

    resumo = evaluate.resumir(resultados)["sem_memoria"]

    assert resumo["casos"] == 3
    assert resumo["executados"] == 2
    assert resumo["aprovados"] == 1
    assert resumo["taxa_aprovacao"] == 50.0
    assert resumo["tokens_total"] == 22
    assert resumo["chamadas_modelo"] == 2

def test_resposta_com_termo_esperado_mas_contradicao():
    assert not evaluate.avaliar_resposta(
        "O projeto não se chama Axis; ele se chama Codezeck.",
        "Axis",
    )


def test_resumo_informa_taxa_de_erro():
    resultados = [
        {
            "cenario": "sem_memoria",
            "passou": True,
            "tokens_entrada": 10,
            "tokens_saida": 2,
            "tokens_total": 12,
            "tempo_ms": 100,
            "chamadas_modelo": 1,
        },
        {
            "cenario": "sem_memoria",
            "passou": False,
            "erro": "falha simulada",
        },
    ]

    resumo = evaluate.resumir(resultados)["sem_memoria"]

    assert resumo["casos"] == 2
    assert resumo["executados"] == 1
    assert resumo["erros"] == 1
    assert resumo["taxa_erro"] == 50.0
