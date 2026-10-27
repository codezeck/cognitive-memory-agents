
import pytest
import sqlite3

from src.armazenamento.repositorio import MemoriaSQLite


@pytest.fixture
def memoria(tmp_path):
    caminho = str(tmp_path / "teste.db")
    banco = MemoriaSQLite(caminho=caminho)
    yield banco
    banco.fechar()


def test_salvar_e_buscar(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")

    resultado = memoria.buscar("ana", "Ana mora em Osasco")

    assert len(resultado) == 1
    assert resultado[0]["texto"] == "Ana mora em Osasco"


def test_persistencia_apos_reabrir(tmp_path):
    caminho = str(tmp_path / "persistencia.db")

    banco = MemoriaSQLite(caminho=caminho)
    banco.salvar("ana", "Ana mora em Osasco")
    banco.fechar()

    banco = MemoriaSQLite(caminho=caminho)
    try:
        resultado = banco.buscar("ana", "Ana mora em Osasco")
        assert len(resultado) == 1
        assert resultado[0]["texto"] == "Ana mora em Osasco"
    finally:
        banco.fechar()


def test_isolamento_entre_usuarios(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")

    assert memoria.buscar("bia", "Ana mora em Osasco") == []


def test_mesma_chave_substitui_memoria_anterior(memoria):
    memoria.salvar("ana", "Ana mora em Osasco", chave="cidade")
    memoria.salvar("ana", "Ana mora em Campinas", chave="cidade")

    resultado = memoria.buscar("ana", "Ana mora")

    assert [item["texto"] for item in resultado] == [
        "Ana mora em Campinas"
    ]


def test_atualizar_memoria(memoria):
    memoria_id = memoria.salvar("ana", "Ana gosta de café")

    assert memoria.atualizar(
        "ana", memoria_id, "Ana gosta de chá"
    ) is True

    resultado = memoria.buscar("ana", "Ana gosta de chá")
    assert resultado[0]["texto"] == "Ana gosta de chá"


def test_esquecer_memoria(memoria):
    memoria_id = memoria.salvar("ana", "Ana mora em Osasco")

    assert memoria.esquecer("ana", memoria_id) is True
    assert memoria.esquecer("ana", memoria_id) is False


def test_esquecer_usuario(memoria):
    memoria.salvar("ana", "Ana mora em Osasco")
    memoria.salvar("ana", "Ana gosta de futebol")
    memoria.salvar("bia", "Bia gosta de música")

    assert memoria.esquecer_usuario("ana") == 2
    assert memoria.buscar("ana", "Ana") == []
    assert len(memoria.buscar("bia", "Bia gosta de música")) == 1


def test_usuario_invalido(memoria):
    with pytest.raises(ValueError):
        memoria.salvar("", "Texto de teste")


def test_texto_vazio(memoria):
    with pytest.raises(ValueError):
        memoria.salvar("ana", "   ")


def test_migracao_banco_antigo_preserva_memorias(tmp_path):
    caminho = str(tmp_path / "banco_antigo.db")

    # Simula a estrutura antiga, sem chave, metadados e vetor.
    con = sqlite3.connect(caminho)
    con.execute("""
        CREATE TABLE memorias (
            id TEXT PRIMARY KEY,
            usuario_id TEXT NOT NULL,
            texto TEXT NOT NULL,
            ativa INTEGER NOT NULL DEFAULT 1,
            criada_em TEXT NOT NULL,
            atualizada_em TEXT NOT NULL
        )
    """)
    con.execute("""
        INSERT INTO memorias
        (id, usuario_id, texto, ativa, criada_em, atualizada_em)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "memoria-antiga",
        "ana",
        "Ana mora em Osasco",
        1,
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00",
    ))
    con.commit()
    con.close()

    # Abrir o repositório deve executar a migração.
    banco = MemoriaSQLite(caminho=caminho)

    try:
        resultado = banco.buscar("ana", "Ana mora em Osasco")

        assert len(resultado) == 1
        assert resultado[0]["id"] == "memoria-antiga"
        assert resultado[0]["texto"] == "Ana mora em Osasco"

        con = sqlite3.connect(caminho)
        colunas = {
            linha[1]
            for linha in con.execute("PRAGMA table_info(memorias)")
        }
        con.close()

        assert {"chave", "metadados", "vetor"}.issubset(colunas)
    finally:
        banco.fechar()


@pytest.mark.parametrize("consulta", [None, 123, [], {}])
def test_buscar_rejeita_consulta_que_nao_e_texto(memoria, consulta):
    with pytest.raises(ValueError, match="consulta"):
        memoria.buscar("ana", consulta)