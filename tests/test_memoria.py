import pytest

from src.memoria import MemoriaEmRam, MemoriaLongoPrazo


@pytest.fixture
def memoria():
    return MemoriaEmRam()


def test_implementa_a_interface(memoria):
    assert isinstance(memoria, MemoriaLongoPrazo)


def test_salvar_e_buscar_devolve_formato_do_agente(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    resultado = memoria.buscar("ana", "onde Ana mora")
    assert len(resultado) == 1
    assert resultado[0]["texto"] == "Ana mora em Osasco"
    assert {"id", "texto", "score"} <= resultado[0].keys()


def test_busca_ordena_pela_relevancia(memoria):
    memoria.salvar("ana", "Ana gosta de futebol")
    memoria.salvar("ana", "Ana mora em Osasco")
    resultado = memoria.buscar("ana", "cidade onde Ana mora em Osasco", k=2)
    assert resultado[0]["texto"] == "Ana mora em Osasco"


def test_busca_sem_relacao_nao_devolve_nada(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    assert memoria.buscar("ana", "xyzzy") == []


def test_memorias_sao_isoladas_por_usuario(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    assert memoria.buscar("bia", "Ana mora em Osasco") == []


def test_fato_com_mesma_chave_substitui_o_antigo(memoria):
    memoria.salvar("ana", "Ana mora em Osasco", chave="cidade")
    memoria.salvar("ana", "Ana mora em Campinas", chave="cidade")
    textos = [m["texto"] for m in memoria.buscar("ana", "onde Ana mora")]
    assert textos == ["Ana mora em Campinas"]


def test_atualizar_altera_o_texto(memoria):
    mid = memoria.salvar("ana", "Ana gosta de café")
    assert memoria.atualizar("ana", mid, "Ana gosta de chá") is True
    assert memoria.buscar("ana", "Ana gosta de chá")[0]["texto"] == "Ana gosta de chá"


def test_atualizar_de_outro_usuario_falha(memoria):
    mid = memoria.salvar("ana", "Ana gosta de café")
    assert memoria.atualizar("bia", mid, "texto novo") is False


def test_esquecer_remove_a_memoria(memoria):
    mid = memoria.salvar("ana", "Ana mora em Osasco")
    assert memoria.esquecer("ana", mid) is True
    assert memoria.buscar("ana", "Ana mora em Osasco") == []
    assert memoria.esquecer("ana", mid) is False


def test_apagar_usuario_remove_todas_as_memorias_dele(memoria):
    memoria.salvar("ana", "Ana mora em Osasco", chave="cidade")
    memoria.salvar("ana", "Ana mora em Campinas", chave="cidade")
    memoria.salvar("ana", "Ana gosta de futebol")
    memoria.salvar("bia", "Bia gosta de futebol")

    assert memoria.esquecer_usuario("ana") == 3
    assert memoria.buscar("ana", "Ana mora Osasco Campinas futebol") == []
    assert len(memoria.buscar("bia", "Bia futebol")) == 1


@pytest.mark.parametrize("uid", ["", "   ", None])
def test_usuario_id_invalido(memoria, uid):
    with pytest.raises(ValueError):
        memoria.salvar(uid, "texto")


def test_texto_vazio_e_rejeitado(memoria):
    with pytest.raises(ValueError):
        memoria.salvar("ana", "   ")