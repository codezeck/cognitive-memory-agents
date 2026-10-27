import pytest

from src.memoria import MemoriaEmRam
from src.memoria.avaliacao_regras import avaliar_conversas, carregar
from src.memoria.gerenciador import GerenciadorMemoria
from src.memoria.regras import normalizar

CONVERSAS = carregar("conversas_dev.json")


@pytest.fixture
def g():
    return GerenciadorMemoria(MemoriaEmRam())


def _textos(g, uid, consulta, k=10):
    return [m["texto"] for m in g.memoria.buscar(uid, consulta, k=k)]


def test_ha_pelo_menos_5_conversas_sinteticas():
    assert len(CONVERSAS) >= 5


@pytest.mark.parametrize("conversa", CONVERSAS, ids=[c["id"] for c in CONVERSAS])
def test_conversa_de_desenvolvimento_chega_ao_estado_esperado(conversa):
    resultado = avaliar_conversas([conversa], MemoriaEmRam)
    assert resultado["falhas"] == [], resultado["falhas"]


# ---- conflitos e atualização
def test_fato_novo_substitui_o_antigo(g):
    g.processar("u1", "Moro em Osasco.")
    resultados = g.processar("u1", "Mudei para Campinas.")
    assert resultados[0].efeito == "atualizado"
    assert g.estado("u1")["cidade"] == "Campinas"


def test_fato_repetido_nao_duplica(g):
    g.processar("u1", "Moro em Osasco.")
    assert g.processar("u1", "Moro em Osasco.")[0].efeito == "duplicado"
    assert len(g.memoria._dados["u1"]) == 1


def test_repeticao_com_acento_ou_caixa_diferente_nao_duplica(g):
    g.processar("u1", "Mudei para São Paulo.")
    assert g.processar("u1", "moro em sao paulo.")[0].efeito == "duplicado"


def test_negacao_de_fato_antigo_nao_apaga_o_fato_novo(g):
    g.processar("u1", "Moro em Osasco.")
    g.processar("u1", "Mudei para Santos.")
    assert g.processar("u1", "Não moro mais em Osasco.")[0].efeito == "conflito_ignorado"
    assert g.estado("u1")["cidade"] == "Santos"


def test_negacao_do_fato_atual_apaga(g):
    g.processar("u1", "Moro em Osasco.")
    assert g.processar("u1", "Não moro mais em Osasco.")[0].efeito == "esquecido"
    assert "cidade" not in g.estado("u1")


def test_esquecer_algo_que_nao_existe_e_inofensivo(g):
    assert g.processar("u1", "Esqueça meu carro.")[0].efeito == "inexistente"


def test_ultima_afirmacao_da_mesma_mensagem_vence(g):
    g.processar("u1", "Moro em Osasco. Na verdade, moro em Campinas.")
    assert g.estado("u1")["cidade"] == "Campinas"


def test_usuarios_sao_independentes(g):
    g.processar("ana", "Moro em Osasco.")
    g.processar("bia", "Moro em Recife.")
    g.processar("ana", "Esqueça tudo sobre mim.")
    assert g.estado("ana") == {}
    assert g.estado("bia") == {"cidade": "Recife"}


def test_usuario_id_invalido(g):
    with pytest.raises(ValueError):
        g.processar("  ", "Moro em Osasco.")


# ---- evidências de recuperação (o que `buscar` devolve)
def test_fato_antigo_substituido_nao_e_recuperado(g):
    g.processar("u1", "Moro em Osasco.")
    g.processar("u1", "Mudei para Campinas.")
    textos = _textos(g, "u1", "Mora em Osasco Campinas")
    assert any("Campinas" in t for t in textos)
    assert not any("Osasco" in t for t in textos)


def test_fato_esquecido_deixa_de_ser_recuperado(g):
    g.processar("u1", "Meu carro é um Gol azul.")
    assert _textos(g, "u1", "Carro Gol")
    g.processar("u1", "Esqueça o que eu disse sobre o carro.")
    assert _textos(g, "u1", "Carro Gol") == []


def test_esquecer_apaga_tambem_o_historico_substituido(g):
    g.processar("u1", "Meu carro é um Gol azul.")
    g.processar("u1", "Agora meu carro é um Onix branco.")
    g.processar("u1", "Esqueça meu carro.")
    assert g.memoria._dados.get("u1", []) == []


def test_apagar_usuario_remove_tudo_e_nao_recupera(g):
    g.processar("u1", "Me chamo Lucas e moro em Porto Alegre.")
    g.processar("u1", "Esqueça tudo sobre mim.")
    assert _textos(g, "u1", "Chama-se Lucas Mora em Porto Alegre") == []
    assert g.memoria._dados.get("u1", []) == []


def test_apagar_um_usuario_nao_afeta_outro(g):
    g.processar("ana", "Moro em Osasco.")
    g.processar("bia", "Moro em Osasco.")
    g.processar("ana", "Apague todos os meus dados.")
    assert _textos(g, "bia", "Mora em Osasco")
