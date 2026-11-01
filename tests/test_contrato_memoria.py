"""Contrato da memória de longo prazo, rodando nas duas implementações.

- MemoriaEmRam (src/memoria): usada em testes e CI.
- MemoriaSQLite (src/armazenamento): a que a API usa.

Também prova que o baseline por regras (GerenciadorMemoria) se comporta igual
nas duas e continua correto quando a API mexe na memória por outros caminhos
(POST, DELETE de uma memória, DELETE do usuário) ou quando o processo reinicia.
"""

import pytest

from src.armazenamento.repositorio import MemoriaSQLite
from src.memoria import MemoriaEmRam, MemoriaLongoPrazo
from src.memoria.avaliacao_regras import avaliar_conversas, carregar
from src.memoria.gerenciador import GerenciadorMemoria


@pytest.fixture(params=["ram", "sqlite"])
def memoria(request, tmp_path):
    if request.param == "ram":
        yield MemoriaEmRam()
        return
    banco = MemoriaSQLite(str(tmp_path / "memoria.db"))
    yield banco
    banco.fechar()


def _textos(memoria, uid, consulta, k=10):
    return [m["texto"] for m in memoria.buscar(uid, consulta, k=k)]


def _quantas_linhas(memoria, uid):
    return len(memoria.listar_por_usuario(uid))


# ---- contrato básico
def test_implementa_a_interface(memoria):
    assert isinstance(memoria, MemoriaLongoPrazo)


def test_salvar_e_buscar_devolve_id_texto_e_score(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    (item,) = memoria.buscar("ana", "Ana mora em Osasco")
    assert {"id", "texto", "score"} <= item.keys()
    assert item["texto"] == "Ana mora em Osasco"


def test_memorias_sao_isoladas_por_usuario(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    assert memoria.buscar("bia", "Ana mora em Osasco") == []
    assert memoria.listar_por_usuario("bia") == []


def test_chave_igual_substitui_e_o_antigo_nao_e_recuperado(memoria):
    memoria.salvar("ana", "Ana mora em Osasco", chave="cidade")
    memoria.salvar("ana", "Ana mora em Campinas", chave="cidade")
    assert _textos(memoria, "ana", "Ana mora em Osasco Campinas") == ["Ana mora em Campinas"]


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


def test_listar_por_usuario_inclui_ativas_e_substituidas(memoria):
    memoria.salvar("ana", "Ana mora em Osasco", chave="cidade", metadados={"valor": "Osasco"})
    memoria.salvar("ana", "Ana mora em Campinas", chave="cidade", metadados={"valor": "Campinas"})
    itens = memoria.listar_por_usuario("ana")
    assert [(i["chave"], i["ativa"]) for i in itens] == [("cidade", False), ("cidade", True)]
    assert {"id", "texto", "chave", "metadados", "ativa"} <= itens[0].keys()
    assert itens[1]["metadados"] == {"valor": "Campinas"}


# ---- regras + memória: mesmo comportamento nas duas
def test_conversas_de_desenvolvimento_passam_em_qualquer_implementacao(memoria):
    resultado = avaliar_conversas(carregar("conversas_dev.json"), lambda: memoria)
    assert resultado["falhas"] == [], resultado["falhas"]


def test_regras_dao_o_mesmo_resultado_na_avaliacao_final_nas_duas(tmp_path):
    conversas = carregar("conversas_avaliacao.json")
    em_ram = avaliar_conversas(conversas, MemoriaEmRam)
    banco = MemoriaSQLite(str(tmp_path / "comparacao.db"))
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


# ---- a API mexe na memória por outros caminhos: o gerenciador não pode ficar com estado velho
def test_apagar_o_usuario_direto_na_memoria_e_salvar_de_novo_funciona(memoria):
    g = GerenciadorMemoria(memoria)
    g.processar("u1", "Moro em Osasco.")
    memoria.esquecer_usuario("u1")  # DELETE /usuarios/{id}/memorias sem passar pelo gerenciador
    g.processar("u1", "Moro em Osasco.")
    assert _textos(memoria, "u1", "Mora em Osasco") == ["Mora em Osasco."]


def test_apagar_uma_memoria_pela_api_e_repetir_o_fato_funciona(memoria):
    g = GerenciadorMemoria(memoria)
    g.processar("u1", "Moro em Osasco.")
    (ativa,) = [i for i in memoria.listar_por_usuario("u1") if i["ativa"]]
    memoria.esquecer("u1", ativa["id"])  # DELETE /usuarios/{id}/memorias/{id}
    g.processar("u1", "Moro em Osasco.")
    assert _textos(memoria, "u1", "Mora em Osasco") == ["Mora em Osasco."]


def test_memoria_criada_a_mao_com_chave_e_esquecida_pelo_chat(memoria):
    g = GerenciadorMemoria(memoria)
    memoria.salvar("u1", "Mora em Osasco.", chave="cidade")  # POST /usuarios/{id}/memorias
    g.processar("u1", "Esqueça meu endereço.")
    assert _textos(memoria, "u1", "Mora em Osasco") == []
    assert _quantas_linhas(memoria, "u1") == 0


def test_memoria_criada_a_mao_com_chave_e_substituida_pelas_regras(memoria):
    g = GerenciadorMemoria(memoria)
    memoria.salvar("u1", "Mora em Osasco.", chave="cidade")
    g.processar("u1", "Mudei para Campinas.")
    textos = _textos(memoria, "u1", "Mora em Osasco Campinas")
    assert any("Campinas" in t for t in textos)
    assert not any("Osasco" in t for t in textos)


def test_esquecer_apaga_o_historico_escondido_depois_que_a_api_apagou_so_a_ativa(memoria):
    g = GerenciadorMemoria(memoria)
    g.processar("u1", "Meu carro é um Gol azul.")
    g.processar("u1", "Agora meu carro é um Onix branco.")
    (ativa,) = [i for i in memoria.listar_por_usuario("u1") if i["ativa"]]
    memoria.esquecer("u1", ativa["id"])  # sobra a linha substituída (Gol)
    assert _quantas_linhas(memoria, "u1") == 1
    g.processar("u1", "Esqueça meu carro.")
    assert _quantas_linhas(memoria, "u1") == 0


def test_estado_nao_mostra_chave_sem_memoria_ativa(memoria):
    g = GerenciadorMemoria(memoria)
    g.processar("u1", "Meu carro é um Gol azul.")
    g.processar("u1", "Agora meu carro é um Onix branco.")
    (ativa,) = [i for i in memoria.listar_por_usuario("u1") if i["ativa"]]
    memoria.esquecer("u1", ativa["id"])
    assert "carro" not in g.estado("u1")


# ---- persistência
def test_dados_sobrevivem_ao_reinicio_no_sqlite(tmp_path):
    caminho = str(tmp_path / "persistente.db")
    primeiro = MemoriaSQLite(caminho)
    primeiro.salvar("ana", "Ana mora em Osasco")
    primeiro.fechar()

    segundo = MemoriaSQLite(caminho)
    try:
        assert _textos(segundo, "ana", "Ana mora em Osasco") == ["Ana mora em Osasco"]
        segundo.esquecer_usuario("ana")
    finally:
        segundo.fechar()

    terceiro = MemoriaSQLite(caminho)
    try:
        assert terceiro.buscar("ana", "Ana mora em Osasco") == []
    finally:
        terceiro.fechar()


def test_esquecer_por_topico_depois_de_reiniciar(tmp_path):
    caminho = str(tmp_path / "reinicio.db")
    banco = MemoriaSQLite(caminho)
    GerenciadorMemoria(banco).processar("u1", "Meu carro é um Gol azul.")
    banco.fechar()

    banco = MemoriaSQLite(caminho)  # processo reiniciado: gerenciador novo
    try:
        resultado = GerenciadorMemoria(banco).processar("u1", "Esqueça meu carro.")
        assert resultado[0].efeito == "esquecido"
        assert _textos(banco, "u1", "Carro Gol azul") == []
    finally:
        banco.fechar()
