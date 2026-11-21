import copy

import pytest
from fastapi.testclient import TestClient

from src.api.catalogo import Catalogo
from src.api.config import Configuracao
from src.api.dependencias import get_agente, get_catalogo, get_gerenciador, get_memoria
from src.api.falsos import AgenteFalso
from src.api.main import app
from src.armazenamento.repositorio import MemoriaSQLite
from src.interface.protocolos import fonte_v3
from src.memoria.gerenciador import GerenciadorMemoria


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("API_TOKENS", "teste-entrada-u1:u1,teste-entrada-u2:u2")
    memoria = MemoriaSQLite(str(tmp_path / "isolado.db"))
    agente = AgenteFalso()
    gerente = GerenciadorMemoria(memoria)
    config = Configuracao("ollama", "modelo-teste", (("ollama", "modelo-teste"),))
    anteriores = dict(app.dependency_overrides)
    app.dependency_overrides.update(
        {
            get_memoria: lambda: memoria,
            get_agente: lambda: agente,
            get_catalogo: lambda: Catalogo(config),
            get_gerenciador: lambda: gerente,
        }
    )
    with TestClient(app, base_url="http://127.0.0.1") as cliente:
        assert (
            cliente.post(
                "/interface/sessao", json={"token": "teste-entrada-u1"}
            ).status_code
            == 200
        )
        yield cliente, memoria, agente
    app.dependency_overrides.clear()
    app.dependency_overrides.update(anteriores)
    memoria.fechar()


@pytest.mark.parametrize(
    "texto",
    [
        "'; DROP TABLE memorias; --",
        "' OR 1=1 --",
        "<script>window.__entradaExecutada=1</script>",
    ],
)
def test_conversa_trata_payload_como_texto_e_preserva_outro_usuario(ambiente, texto):
    cliente, banco, agente = ambiente
    segredo = "Fato sintético exclusivo do perfil dois"
    banco.salvar("u2", segredo)
    r = cliente.post("/interface/conversas", json={"mensagem": texto})
    assert r.status_code == 200
    assert agente.chamadas[-1]["mensagem"] == texto
    assert segredo not in r.text
    assert banco.listar_por_usuario("u2")[0]["texto"] == segredo
    assert (
        cliente.post("/interface/memorias", json={"consulta": texto}).status_code == 200
    )
    assert banco.listar_por_usuario("u1") == []


def test_sql_em_usuario_chave_texto_e_id_nao_altera_escopo_do_banco(ambiente):
    _, banco, _ = ambiente
    outro = banco.salvar("u2", "Segredo sintético do outro perfil", "cidade")
    payload = "u1' OR 1=1 --"
    assert banco.listar_por_usuario(payload) == []
    assert banco.esquecer_usuario(payload) == 0
    assert not banco.atualizar("u1", outro + "' OR 1=1 --", "Novo")
    assert not banco.esquecer("u1", outro + "' OR 1=1 --")
    ident = banco.salvar("u1", "'; DROP TABLE memorias; --", payload)
    assert banco.listar_por_usuario("u1")[0]["id"] == ident
    assert banco.listar_por_usuario("u1")[0]["chave"] == payload
    assert banco.listar_por_usuario("u2")[0]["id"] == outro


@pytest.mark.parametrize(
    "extra",
    [
        {"usuario_id": "u2"},
        {"sql": "SELECT * FROM memorias"},
        {"comando": "qualquer-comando"},
    ],
)
def test_campo_extra_na_conversa_nao_e_um_canal_de_execucao(ambiente, extra):
    cliente, _, agente = ambiente
    assert (
        cliente.post(
            "/interface/conversas", json={"mensagem": "Olá", **extra}
        ).status_code
        == 422
    )
    assert agente.chamadas == []


@pytest.mark.parametrize("campo", ["sql", "comando", "caminho", "url"])
def test_importacao_rejeita_canais_extras_sem_executar_processos(
    ambiente, monkeypatch, campo
):
    import subprocess

    cliente, _, _ = ambiente
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("Validação não executa processo"),
    )
    caso = copy.deepcopy(fonte_v3()[0])
    caso[campo] = "conteúdo sintético"
    assert (
        cliente.post("/interface/conjuntos/validar", json={"casos": [caso]}).status_code
        == 422
    )


def test_json_com_texto_de_codigo_e_dado_nao_programa(ambiente, monkeypatch):
    import subprocess

    cliente, _, _ = ambiente
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("Importação não executa processo"),
    )
    caso = copy.deepcopy(fonte_v3()[0])
    caso["descricao"] = '<img src=x onerror="window.__entradaExecutada=1">'
    r = cliente.post("/interface/conjuntos/validar", json={"casos": [caso]})
    assert r.status_code == 200
    assert r.json()["casos"][0]["descricao"] == caso["descricao"]
    assert (
        cliente.post(
            "/interface/conjuntos/validar", content='__import__("os")'
        ).status_code
        == 422
    )
