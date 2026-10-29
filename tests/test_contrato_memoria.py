"""Contrato da memória de longo prazo, rodando nas duas implementações.

- MemoriaEmRamComChaves (src/memoria): usada em testes e CI.
- MemoriaSQLiteComChaves (src/memoria): a MemoriaSQLite da API (src/armazenamento)
  com `listar` e `esquecer_por_chave`.

Também prova que o baseline por regras (GerenciadorMemoria) se comporta igual
nas duas, inclusive depois de reiniciar o processo.
"""

import pytest

from src.memoria import MemoriaLongoPrazo
from src.memoria.avaliacao_regras import avaliar_conversas, carregar
from src.memoria.chaves import MemoriaComChaves, MemoriaEmRamComChaves
from src.memoria.gerenciador import GerenciadorMemoria
from src.memoria.sqlite_chaves import MemoriaSQLiteComChaves


@pytest.fixture(params=["ram", "sqlite"])
def memoria(request, tmp_path):
    if request.param == "ram":
        yield MemoriaEmRamComChaves()
        return
    banco = MemoriaSQLiteComChaves(str(tmp_path / "memoria.db"))
    yield banco
    banco.fechar()


def _textos(memoria, uid, consulta, k=10):
    return [m["texto"] for m in memoria.buscar(uid, consulta, k=k)]


# ---- contrato básico
def test_implementa_as_interfaces(memoria):
    assert isinstance(memoria, MemoriaLongoPrazo)
    assert isinstance(memoria, MemoriaComChaves)


def test_salvar_e_buscar_devolve_id_texto_e_score(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    (item,) = memoria.buscar("ana", "Ana mora em Osasco")
    assert {"id", "texto", "score"} <= item.keys()
    assert item["texto"] == "Ana mora em Osasco"


def test_memorias_sao_isoladas_por_usuario(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    assert memoria.buscar("bia", "Ana mora em Osasco") == []


def test_chave_igual_substitui_e_o_antigo_nao_e_recuperado(memoria):
    memoria.salvar("ana", "Ana mora em Osasco", chave="cidade")
    memoria.salvar("ana", "Ana mora em Campinas", chave="cidade")
    textos = _textos(memoria, "ana", "Ana mora em Osasco Campinas")
    assert textos == ["Ana mora em Campinas"]


def test_atualizar_so_vale_para_o_dono(memoria):
    mid = memoria.salvar("ana", "Ana gosta de café")
    assert memoria.atualizar("bia", mid, "outro texto") is False
    assert memoria.atualizar("ana", mid, "Ana gosta de chá") is True
    assert _textos(memoria, "ana", "Ana gosta de chá") == ["Ana gosta de chá"]


def test_esquecer_remove_e_a_segunda_vez_devolve_false(memoria):
    mid = memoria.salvar("ana", "Ana mora em Osasco")
    assert memoria.esquecer("ana", mid) is True
    assert memoria.buscar("ana", "Ana mora em Osasco") == []
    assert memoria.esquecer("ana", mid) is False


def test_esquecer_apaga_tambem_uma_memoria_ja_substituida(memoria):
    antigo = memoria.salvar("ana", "Meu carro é um Gol", chave="carro")
    memoria.salvar("ana", "Meu carro é um Onix", chave="carro")
    assert memoria.esquecer("ana", antigo) is True


def test_esquecer_usuario_conta_tudo_e_nao_afeta_outros(memoria):
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


# ---- acesso por chave
def test_listar_devolve_so_as_ativas_com_chave_e_metadados(memoria):
    memoria.salvar("ana", "Ana mora em Osasco", chave="cidade", metadados={"valor": "Osasco"})
    memoria.salvar("ana", "Ana mora em Campinas", chave="cidade", metadados={"valor": "Campinas"})
    memoria.salvar("ana", "Ana gosta de futebol")
    itens = memoria.listar("ana")
    assert {i["texto"] for i in itens} == {"Ana mora em Campinas", "Ana gosta de futebol"}
    cidade = next(i for i in itens if i["chave"] == "cidade")
    assert {"id", "texto", "chave", "metadados"} <= cidade.keys()
    assert cidade["metadados"] == {"valor": "Campinas"}
    assert memoria.listar("bia") == []


def test_esquecer_por_chave_apaga_ativa_e_historico(memoria):
    memoria.salvar("ana", "Meu carro é um Gol", chave="carro")
    memoria.salvar("ana", "Meu carro é um Onix", chave="carro")
    memoria.salvar("ana", "Torço pelo Santos", chave="time")
    memoria.salvar("bia", "Meu carro é um Fusca", chave="carro")
    assert memoria.esquecer_por_chave("ana", "carro") == 2
    assert [i["chave"] for i in memoria.listar("ana")] == ["time"]
    assert memoria.esquecer_por_chave("ana", "carro") == 0
    assert len(memoria.listar("bia")) == 1


def test_esquecer_por_chave_com_prefixo(memoria):
    memoria.salvar("ana", "Pet: gato chamado Luna", chave="pet:gato:luna")
    memoria.salvar("ana", "Pet: gato chamado Simba", chave="pet:gato:simba")
    memoria.salvar("ana", "Pet: cachorro chamado Thor", chave="pet:cachorro:thor")
    assert memoria.esquecer_por_chave("ana", "pet:gato:") == 2
    assert [i["chave"] for i in memoria.listar("ana")] == ["pet:cachorro:thor"]


# ---- regras + memória: mesmo comportamento nas duas
def test_conversas_de_desenvolvimento_passam_em_qualquer_implementacao(memoria):
    resultado = avaliar_conversas(carregar("conversas_dev.json"), lambda: memoria)
    assert resultado["falhas"] == [], resultado["falhas"]


def test_regras_dao_o_mesmo_resultado_na_avaliacao_final_nas_duas(tmp_path):
    conversas = carregar("conversas_avaliacao.json")
    em_ram = avaliar_conversas(conversas, MemoriaEmRamComChaves)
    banco = MemoriaSQLiteComChaves(str(tmp_path / "comparacao.db"))
    try:
        no_banco = avaliar_conversas(conversas, lambda: banco)
    finally:
        banco.fechar()
    assert em_ram == no_banco


def test_fato_substituido_e_apagado_nao_voltam_pela_busca(memoria):
    g = GerenciadorMemoria(memoria)
    g.processar("u1", "Moro em Osasco.")
    g.processar("u1", "Mudei para Campinas.")
    assert not any("Osasco" in t for t in _textos(memoria, "u1", "Mora em Osasco Campinas"))
    g.processar("u1", "Esqueça meu endereço.")
    assert _textos(memoria, "u1", "Mora em Osasco Campinas") == []


def test_apagar_usuario_direto_na_memoria_e_salvar_de_novo_funciona(memoria):
    g = GerenciadorMemoria(memoria)
    g.processar("u1", "Moro em Osasco.")
    memoria.esquecer_usuario("u1")  # o que a API faz em DELETE /usuarios/{id}/memorias
    assert g.processar("u1", "Moro em Osasco.")[0].efeito == "salvo"
    assert _textos(memoria, "u1", "Mora em Osasco") == ["Mora em Osasco."]


# ---- persistência
def test_dados_sobrevivem_ao_reinicio_no_sqlite(tmp_path):
    caminho = str(tmp_path / "persistente.db")
    primeiro = MemoriaSQLiteComChaves(caminho)
    primeiro.salvar("ana", "Ana mora em Osasco")
    primeiro.fechar()

    segundo = MemoriaSQLiteComChaves(caminho)
    try:
        assert _textos(segundo, "ana", "Ana mora em Osasco") == ["Ana mora em Osasco"]
        segundo.esquecer_usuario("ana")
    finally:
        segundo.fechar()

    terceiro = MemoriaSQLiteComChaves(caminho)
    try:
        assert terceiro.buscar("ana", "Ana mora em Osasco") == []
    finally:
        terceiro.fechar()


def test_esquecer_por_topico_depois_de_reiniciar(tmp_path):
    caminho = str(tmp_path / "reinicio.db")
    banco = MemoriaSQLiteComChaves(caminho)
    GerenciadorMemoria(banco).processar("u1", "Meu carro é um Gol azul.")
    banco.fechar()

    banco = MemoriaSQLiteComChaves(caminho)  # processo reiniciado: gerenciador novo
    try:
        resultado = GerenciadorMemoria(banco).processar("u1", "Esqueça meu carro.")
        assert resultado[0].efeito == "esquecido"
        assert _textos(banco, "u1", "Carro Gol azul") == []
    finally:
        banco.fechar()
