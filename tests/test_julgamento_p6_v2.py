import pytest

from eval.julgamento_p6 import julgar_resposta_p6


def caso(atributo, esperado, pergunta="", **a):
    return {
        "pergunta": pergunta,
        "esperado": esperado,
        "informacoes_esquecidas": [],
        "avaliacao": {
            "tipo_resposta": "factual",
            "atributo": atributo,
            "aliases_aceitos": [],
            "valores_antigos": [],
            "informacoes_proibidas": [],
            **a,
        },
    }


@pytest.mark.parametrize(
    "c,texto",
    [
        (caso("filhos", "quatro"), "Você tem agora quatro filhos."),
        (caso("filhos", "4"), "Tenho atualmente 4 filhos."),
        (caso("profissao", "bióloga"), "Você é uma bióloga."),
        (caso("profissao", "arquiteto"), "Eu sou um arquiteto."),
        (
            caso("profissao", "analista financeira"),
            "Seu trabalho atual é de analista financeira.",
        ),
        (
            caso("viagem", "Chile", "Para onde vou viajar em abril?"),
            "Você está planejando uma viagem para Chile em abril.",
        ),
        (
            caso("viagem", "Peru", "Para onde vou viajar em maio?"),
            "Em maio, estou planejando viagem para Peru.",
        ),
    ],
)
def test_variacoes_gramaticais_sem_mudar_o_fato(c, texto):
    j = julgar_resposta_p6(texto, c)
    assert j["versao"] == "p6-conteudo-v2"
    assert j["acerto_factual"]["status"] == "aprovado"
    assert j["formato_ok"]["valor"] is False


@pytest.mark.parametrize(
    "c,texto",
    [
        (
            caso("filhos", "quatro", valores_antigos=["dois"]),
            "Você tem agora dois filhos.",
        ),
        (caso("filhos", "quatro"), "Você tem agora quatro filhos ou cinco."),
        (caso("filhos", "quatro"), "Talvez você tem agora quatro filhos."),
        (caso("filhos", "quatro"), "Você não tem agora quatro filhos."),
        (caso("profissao", "bióloga"), "Você é uma enfermeira."),
        (caso("profissao", "bióloga"), "Você é uma bióloga e trabalha no hospital X."),
        (caso("profissao", "bióloga"), "Você não é uma bióloga."),
        (caso("profissao", "bióloga"), "Você era uma bióloga."),
        (
            caso("profissao", "arquiteto"),
            "Seu trabalho atual é de arquiteto, mas hoje é médico.",
        ),
        (
            caso("viagem", "Chile", "Para onde vou viajar em abril?"),
            "Você está planejando uma viagem para Chile em julho.",
        ),
        (
            caso("viagem", "Chile", "Para onde vou viajar?"),
            "Você está planejando uma viagem para Chile em abril.",
        ),
        (caso("viagem", "Chile"), "Você está planejando uma viagem para Argentina."),
        (
            caso("viagem", "Chile"),
            "Você está planejando uma viagem para Chile ou Peru.",
        ),
        (caso("viagem", "Chile"), "Você está planejando uma viagem para Chile?"),
    ],
)
def test_variacao_nao_aprova_negacao_detalhe_ou_valor_errado(c, texto):
    assert julgar_resposta_p6(texto, c)["passou"] is False


def test_desculpe_mas_so_e_aceito_em_recusa_completa_sem_alegacao():
    c = caso("carro", ["não sei"], tipo_resposta="abstencao")
    resposta = "Desculpe, mas não tenho informações sobre qual carro você dirige agora."
    j = julgar_resposta_p6(resposta, c)
    assert j["abstencao_correta"]["valor"] is True
    assert j["formato_ok"]["valor"] is False
    assert (
        julgar_resposta_p6(resposta, caso("carro", "Argo"))["acerto_factual"]["valor"]
        is False
    )
    for r in [
        resposta + " Talvez um Argo.",
        "Desculpe, mas não sei, mas você dirige um Argo.",
        "Desculpe, mas não tenho informações sobre qual carro você dirige agora, mas acho que um Argo.",
        "Desculpe, mas você dirige um Argo.",
        "Desculpe, mas talvez não tenho informações sobre seu carro.",
    ]:
        assert julgar_resposta_p6(r, c)["passou"] is False


def test_recusa_de_time_e_falha_quando_fato_era_esperado():
    c = caso("time", "Bahia")
    j = julgar_resposta_p6("Você não disse qual time você torce.", c)
    assert j["acerto_factual"]["valor"] is False
    assert j["acerto_factual"]["motivo"] == "abstencao_indevida_fato_esperado"


def test_inclusao_de_detalhe_e_genero_ambiguo_continuam_pendentes():
    j = julgar_resposta_p6(
        "Você é diretor(a) de arte.", caso("profissao", "diretora de arte")
    )
    assert j["acerto_factual"]["status"] == "nao_verificado"
    j = julgar_resposta_p6(
        "Você tem dois gatos: Mel e Sol.",
        caso("quantidade_pets", "dois", "Quantos gatos eu tenho?"),
    )
    assert j["acerto_factual"]["status"] == "nao_verificado"
