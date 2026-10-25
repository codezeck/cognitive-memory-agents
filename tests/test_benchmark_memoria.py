import pytest

from src.memoria import EmbedderHash, MemoriaEmRam
from src.memoria.benchmark import avaliar, carregar, estimar_tokens, normalizar


@pytest.fixture(scope="module")
def dados():
    return carregar()


@pytest.fixture(scope="module")
def resultado(dados):
    return avaliar(dados, lambda: MemoriaEmRam(EmbedderHash()), k=3)


def test_benchmark_tem_pelo_menos_20_sessoes(dados):
    sessoes = sum(len(u["sessoes"]) for u in dados["usuarios"])
    assert sessoes >= 20


def test_toda_pergunta_tem_os_campos_obrigatorios(dados):
    campos = {"apos_sessao", "pergunta", "esperado", "proibido", "tipo"}
    for usuario in dados["usuarios"]:
        for pergunta in usuario["perguntas"]:
            assert campos <= pergunta.keys()


def test_normalizar_ignora_acento_e_maiuscula():
    assert normalizar("Natação") == normalizar("NATACAO")


def test_estimar_tokens():
    assert estimar_tokens("") == 0
    assert estimar_tokens("abcd") == 1
    assert estimar_tokens("abcde") == 2


def test_nao_devolve_informacao_desatualizada(resultado):
    assert resultado["resumo"]["taxa_informacao_desatualizada"] == 0


def test_esquecimento_e_respeitado(resultado):
    assert resultado["resumo"]["taxa_esquecimento_correto"] == 1.0


def test_memoria_usa_menos_tokens_que_historico_completo(resultado):
    resumo = resultado["resumo"]
    assert resumo["tokens_medios_memoria"] < resumo["tokens_medios_historico_completo"]


def test_resumo_cobre_todas_as_perguntas(dados, resultado):
    total = sum(len(u["perguntas"]) for u in dados["usuarios"])
    assert resultado["resumo"]["perguntas"] == total
    assert len(resultado["detalhes"]) == total