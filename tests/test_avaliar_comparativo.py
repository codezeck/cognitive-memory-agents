from eval.avaliar_comparativo import (
    avaliar_resposta_comparativo,
    texto_memoria,
    avaliar_resposta_controlada,
    resposta_esperada_cenario,
    resumir,
    avaliar_recuperacao_equivalente,
)


def caso_esquecimento_cidade():
    return {
        "id": "TEST-CIDADE",
        "categoria": "esquecimento",
        "mensagens": [
            "Moro em Osasco.",
            "Esqueça minha cidade.",
            "Em que cidade moro?",
        ],
        "esperado": ["não sei"],
    }


def caso_esquecimento_time():
    return {
        "id": "TEST-TIME",
        "categoria": "esquecimento",
        "mensagens": [
            "Torço pelo Vasco.",
            "Não torço mais pelo Vasco.",
            "Para qual time torço?",
        ],
        "esperado": ["não sei"],
    }


def test_resposta_desconhecida_explicita_e_aprovada():
    assert avaliar_resposta_comparativo(
        "Não sei.",
        caso_esquecimento_cidade(),
    )


def test_memoria_sem_informacao_e_aprovada():
    assert avaliar_resposta_comparativo(
        "A memória não contém informações sobre sua cidade.",
        caso_esquecimento_cidade(),
    )


def test_nao_aceita_desconhecimento_com_cidade_inventada():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas você mora em Osasco.",
        caso_esquecimento_cidade(),
    )


def test_nao_aceita_desconhecimento_com_time_inventado():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas você torce pelo Vasco.",
        caso_esquecimento_time(),
    )


def test_texto_de_memoria_cidade():
    assert texto_memoria("cidade", "Osasco") == "Moro em Osasco."


def test_texto_de_memoria_carro():
    assert texto_memoria("carro", "Corolla") == "Meu carro é um Corolla."

def test_rejeita_cidade_esquecida_com_ressalva():
    assert not avaliar_resposta_comparativo(
        "Não tenho informações, mas acredito que você esteja em Osasco.",
        caso_esquecimento_cidade(),
    )


def test_aceita_desconhecimento_sem_revelar_cidade():
    assert avaliar_resposta_comparativo(
        "Não posso fornecer informações pessoais sobre a cidade onde moro.",
        caso_esquecimento_cidade(),
    )


def test_rejeita_desconhecimento_com_cidade_inventada():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas moro em São Paulo.",
        caso_esquecimento_cidade(),
    )


def test_rejeita_desconhecimento_com_time_inventado():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas você torce pelo Santos.",
        caso_esquecimento_time(),
    )


def test_aceita_falta_de_local_fornecido():
    assert avaliar_resposta_comparativo(
        "Você não forneceu o local onde você mora.",
        caso_esquecimento_cidade(),
    )


def test_aceita_historico_sem_informacao_sobre_cidade():
    assert avaliar_resposta_comparativo(
        "Seu histórico não contém informações sobre a cidade onde você mora.",
        caso_esquecimento_cidade(),
    )


def test_aceita_impossibilidade_de_reconhecer_cidade():
    assert avaliar_resposta_comparativo(
        "Não posso reconhecer sua cidade.",
        caso_esquecimento_cidade(),
    )


def test_aceita_agente_sem_informacao_atualizada():
    assert avaliar_resposta_comparativo(
        "O agente não tem informações atualizadas "
        "sobre a localização exata do usuário.",
        caso_esquecimento_cidade(),
    )


def test_aceita_nao_posso_lembrar_da_cidade():
    assert avaliar_resposta_comparativo(
        "Não posso lembrar de sua cidade.",
        caso_esquecimento_cidade(),
    )


def test_rejeita_cidade_inventada_apos_esquecimento():
    assert not avaliar_resposta_comparativo(
        "Eu souvi que você mora em São Paulo, Brasil.",
        caso_esquecimento_cidade(),
    )


def test_avaliacao_controlada_aceita_valor_exato():
    assert avaliar_resposta_controlada("Campinas.", "Campinas")


def test_avaliacao_controlada_rejeita_frase_completa():
    assert not avaliar_resposta_controlada(
        "Você mora em Campinas.",
        "Campinas",
    )


def test_avaliacao_controlada_aceita_desconhecido():
    assert avaliar_resposta_controlada(
        "DESCONHECIDO.",
        "DESCONHECIDO",
    )


def test_sem_memoria_espera_desconhecido():
    assert resposta_esperada_cenario(
        {"esperado": "Osasco"},
        "sem_memoria",
    ) == "DESCONHECIDO"


def test_esquecimento_espera_desconhecido():
    assert resposta_esperada_cenario(
        {"esperado": ["não sei"]},
        "memoria_regras_api",
    ) == "DESCONHECIDO"


def test_memoria_persistente_preserva_fato_esperado():
    assert resposta_esperada_cenario(
        {"esperado": "Osasco"},
        "memoria_persistente_api",
    ) == "Osasco"


def test_resumo_contabiliza_falhas_na_taxa_aprovacao():
    resultados = [
        {
            "cenario": "sem_memoria",
            "passou": True,
            "tokens_total": 10,
            "latencia_api_total_ms": 100,
            "metricas_completas": True,
        },
        {
            "cenario": "sem_memoria",
            "passou": False,
            "erro": "Timeout na API",
        },
    ]

    resumo = resumir(resultados)["sem_memoria"]

    assert resumo["casos"] == 2
    assert resumo["executados"] == 1
    assert resumo["falhas"] == 1
    assert resumo["aprovados"] == 1
    assert resumo["taxa_aprovacao_pct"] == 50.0

def test_recuperacao_equivalente_aceita_variantes_conhecidas():
    assert avaliar_recuperacao_equivalente(
        ["Moro em Osasco."], ["Mora em Osasco."]
    )
    assert avaliar_recuperacao_equivalente(
        ["Pratico yoga."], ["Pratica yoga"]
    )
    assert avaliar_recuperacao_equivalente(
        ["Meu carro é um Corolla."], ["Carro: Corolla."]
    )
    assert avaliar_recuperacao_equivalente(
        ["Meu nome é Ezequiel."], ["Chama-se Ezequiel."]
    )


def test_recuperacao_equivalente_rejeita_valor_incorreto():
    assert not avaliar_recuperacao_equivalente(
        ["Moro em Osasco."], ["Mora em Campinas."]
    )


def test_recuperacao_equivalente_rejeita_fato_extra():
    assert not avaliar_recuperacao_equivalente(
        ["Moro em Osasco."],
        ["Mora em Osasco.", "Pratica yoga."],
    )


def test_recuperacao_equivalente_rejeita_duplicados():
    assert not avaliar_recuperacao_equivalente(
        ["Moro em Osasco."],
        ["Mora em Osasco.", "Moro em Osasco."],
    )


def test_recuperacao_equivalente_memoria_vazia():
    assert avaliar_recuperacao_equivalente([], [])
    assert not avaliar_recuperacao_equivalente(
        [], ["Mora em Osasco."]
    )


def test_recuperacao_equivalente_preserva_fatos_desconhecidos():
    assert avaliar_recuperacao_equivalente(
        ["fato personalizado ABC"],
        ["fato personalizado ABC"],
    )
    assert not avaliar_recuperacao_equivalente(
        ["fato personalizado ABC"],
        ["fato personalizado XYZ"],
    )
