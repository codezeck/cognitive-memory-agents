import pytest

from src.memoria.avaliacao_regras import carregar
from src.memoria.regras import extrair, normalizar

CASOS = carregar("casos_dev.json")


def _tupla(acao, chave, valor):
    return [acao, chave, normalizar(valor) if valor else None]


def test_conjunto_de_desenvolvimento_tem_pelo_menos_100_casos():
    assert len(CASOS) >= 100


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_regra_extrai_as_decisoes_esperadas(caso):
    obtido = [_tupla(d.acao, d.chave, d.valor) for d in extrair(caso["frase"])]
    esperado = [_tupla(*x) for x in caso["esperado"]]
    assert obtido == esperado, caso["frase"]


def test_texto_canonico_e_o_valor_original_preservam_acentos():
    (decisao,) = extrair("Mudei para Florianópolis.")
    assert decisao.valor == "Florianópolis"
    assert decisao.texto == "Mora em Florianópolis."
