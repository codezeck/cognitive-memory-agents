from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

from src import agent
from src.api.main import app


@pytest.fixture
def cliente(monkeypatch):
    anteriores = deepcopy(agent.historicos_por_usuario)
    agent.historicos_por_usuario.clear()
    monkeypatch.setenv("API_TOKENS", "sintetico-a:u1,sintetico-b:u2")
    monkeypatch.setenv("HABILITAR_OBSERVACAO_RAM", "1")
    monkeypatch.setenv("USUARIOS_AVALIACAO_RAM", "u1")
    with TestClient(app) as c:
        yield c
    agent.historicos_por_usuario.clear()
    agent.historicos_por_usuario.update(anteriores)


def consultar(cliente, corpo=None, token="sintetico-a"):
    return cliente.post("/avaliacao/ram", json=corpo or {},
                        headers={"Authorization": "Bearer " + token})


def test_ler_inexistente_nao_cria_historico(cliente):
    antes = deepcopy(agent.historicos_por_usuario)
    r = consultar(cliente)
    assert r.status_code == 200
    assert r.json()["historico_existe"] is False
    assert r.json()["mensagens_total"] == 0
    assert agent.historicos_por_usuario == antes


def test_contagens_distinguem_sistema_alvos_e_outros_sem_expor_textos(cliente):
    agent.historicos_por_usuario["u1"] = [
        {"role":"system","content":"Prompt de sistema com Niteroi"},
        {"role":"user","content":"Moro em Niterói."},
        {"role":"assistant","content":"Você mora em Niteroi."},
        {"role":"user","content":"Quanto e 2 + 3?"},
    ]
    agent.historicos_por_usuario["u2"] = [{"role":"user","content":"segredo outro usuario"}]
    antes = deepcopy(agent.historicos_por_usuario)
    r = consultar(cliente, {"alvos":[{"rotulo":"cidade_antiga","termos":["Niteroi"]}]})
    d = r.json()
    assert d["mensagens_total"] == 4 and d["mensagens_sistema"] == 1
    assert d["mensagens_pessoais"] == 3 and d["alvos_no_historico"] == 2
    assert d["mensagens_pessoais_sem_alvo"] == 1
    assert d["ocorrencias_por_rotulo"] == {"cidade_antiga":2}
    assert all(t not in r.text for t in ["Niteroi","Niterói","segredo outro usuario","sintetico-a"])
    assert d["pid"] > 0 and d["instancia_id"]
    assert agent.historicos_por_usuario == antes
    assert r.headers["cache-control"] == "no-store"


def test_estado_apos_reset_diferente_de_total_de_mensagens(cliente):
    agent.limpar_historico("u1")
    r = consultar(cliente, {"alvos":[{"rotulo":"cidade","termos":["Vitoria"]}]})
    assert r.json()["mensagens_total"] == 1
    assert r.json()["mensagens_pessoais"] == r.json()["alvos_no_historico"] == 0


def test_autorizacao_e_modo_desligado(cliente, monkeypatch):
    assert cliente.post("/avaliacao/ram",json={}).status_code == 401
    assert consultar(cliente,token="sintetico-b").status_code == 403
    assert consultar(cliente,{"usuario_id":"u2"}).status_code == 422
    monkeypatch.setenv("HABILITAR_OBSERVACAO_RAM","0")
    assert consultar(cliente).status_code == 404
    assert "/avaliacao/ram" not in cliente.get("/openapi.json").json()["paths"]


def test_alvos_invalidos_e_rotulos_duplicados(cliente):
    assert consultar(cliente,{"alvos":[{"rotulo":"x","termos":[""]}]}).status_code == 422
    assert consultar(cliente,{"alvos":[{"rotulo":"x","termos":["a"]},{"rotulo":"x","termos":["b"]}]}).status_code == 422
