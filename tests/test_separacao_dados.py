from src.memoria.avaliacao_regras import carregar
from src.memoria.regras import normalizar


def _frases(casos, conversas):
    frases = {normalizar(c["frase"]) for c in casos}
    for conversa in conversas:
        frases |= {normalizar(t) for t in conversa["turnos"]}
    return frases


def test_avaliacao_final_nao_repete_frases_do_desenvolvimento():
    dev = _frases(carregar("casos_dev.json"), carregar("conversas_dev.json"))
    final = _frases(carregar("casos_avaliacao.json"), carregar("conversas_avaliacao.json"))
    assert not (dev & final), sorted(dev & final)


def test_conjunto_de_avaliacao_tem_tamanho_minimo():
    assert len(carregar("casos_avaliacao.json")) >= 40
    assert len(carregar("conversas_avaliacao.json")) >= 3


def test_casos_tem_ids_unicos_em_cada_conjunto():
    for nome in ("casos_dev.json", "casos_avaliacao.json"):
        ids = [c["id"] for c in carregar(nome)]
        assert len(ids) == len(set(ids)), nome
