import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.catalogo import Catalogo, SelecaoModelo
from src.api.config import Configuracao
from src.api.dependencias import get_agente, get_catalogo, get_memoria
from src.api.erros import (ModeloNaoPermitido, ProvedorIndisponivel,
                           ProvedorTimeout)
from src.api.falsos import AgenteFalso
from src.api.main import app
from src.memoria.store_mem import MemoriaEmRam

CONFIG = Configuracao(
    provedor_padrao="ollama",
    modelo_padrao="qwen2.5-coder:3b",
    modelos_permitidos=(("ollama", "qwen2.5-coder:3b"),
                        ("ollama", "outro-modelo:1b"),
                        ("hospedado", "modelo-x")),
)


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.delenv("HOSPEDADO_API_KEY", raising=False)
    monkeypatch.setenv("API_TOKENS", "tok-u1:u1,tok-u2:u2")



    agente, memoria = AgenteFalso(), MemoriaEmRam()
    app.dependency_overrides[get_agente] = lambda: agente
    app.dependency_overrides[get_memoria] = lambda: memoria
    app.dependency_overrides[get_catalogo] = lambda: Catalogo(CONFIG)
    yield TestClient(app, raise_server_exceptions=False,
                     headers={"Authorization": "Bearer tok-u1"}), agente, memoria


def conversa(client, **extra):
    corpo = {"usuario_id": "u1", "mensagem": "Oi", **extra}
    return client.post("/conversas", json=corpo)


def test_saude(ctx):
    assert ctx[0].get("/saude").json() == {"status": "ok"}


def test_provedores_mostra_o_padrao(ctx):
    lista = ctx[0].get("/provedores").json()
    assert any(p["padrao"] and p["modelo"] == "qwen2.5-coder:3b" for p in lista)


def test_conversa_usa_o_modelo_padrao(ctx):
    client, agente, _ = ctx
    r = conversa(client)
    assert r.status_code == 200
    assert r.json()["modelo"] == "qwen2.5-coder:3b"
    assert r.json()["latencia_ms"] >= 0
    assert r.json()["tokens_entrada"] == 10
    assert r.json()["tokens_saida"] == 5
    assert agente.chamadas[0]["selecao"].provedor == "ollama"


def test_escolhe_outro_modelo_permitido(ctx):
    assert conversa(ctx[0], modelo="outro-modelo:1b").json()["modelo"] == "outro-modelo:1b"


def test_modelo_nao_permitido_da_400(ctx):
    r = conversa(ctx[0], modelo="modelo-gigante")
    assert r.status_code == 400
    assert r.json()["codigo"] == "modelo_nao_permitido"


def test_provedor_hospedado_sem_chave_da_503(ctx):
    r = conversa(ctx[0], provedor="hospedado", modelo="modelo-x")
    assert r.status_code == 503
    assert r.json()["codigo"] == "provedor_nao_configurado"


def test_provedor_hospedado_com_chave_funciona(ctx, monkeypatch):
    monkeypatch.setenv("HOSPEDADO_API_KEY", "chave-de-teste")
    assert conversa(ctx[0], provedor="hospedado", modelo="modelo-x").status_code == 200


def test_conversa_recebe_as_memorias_do_usuario(ctx):
    client, agente, memoria = ctx
    memoria.salvar("u1", "O usuário mora em Campinas", "cidade")
    r = conversa(client, mensagem="O usuário mora em Campinas")
    assert r.json()["memorias_usadas"] == ["O usuário mora em Campinas"]
    assert agente.chamadas[0]["memorias"][0]["texto"] == "O usuário mora em Campinas"


def test_memorias_nao_vazam_entre_usuarios(ctx):
    client, _, memoria = ctx
    memoria.salvar("u1", "O usuário mora em Campinas", "cidade")
    r = client.post("/conversas",
                    json={"usuario_id": "u2", "mensagem": "O usuário mora em Campinas"},
                    headers={"Authorization": "Bearer tok-u2"})
    assert r.json()["memorias_usadas"] == []

def test_ollama_fora_do_ar_da_503(ctx):
    client, agente, _ = ctx
    agente.falhar_com = ProvedorIndisponivel("Ollama não respondeu.")
    r = conversa(client)
    assert r.status_code == 503
    assert r.json()["codigo"] == "provedor_indisponivel"


def test_erro_inesperado_nao_vaza_detalhes(ctx):
    client, agente, _ = ctx
    agente.falhar_com = RuntimeError("segredo-interno")
    r = conversa(client)
    assert r.status_code == 500
    assert "segredo-interno" not in r.text


def test_entrada_invalida_da_422(ctx):
    client = ctx[0]
    assert client.post("/conversas", json={"usuario_id": "u1", "mensagem": ""}).status_code == 422
    assert client.post("/conversas", json={"usuario_id": "../x", "mensagem": "oi"}).status_code == 422


def test_json_quebrado_da_mensagem_clara(ctx):
    r = ctx[0].post("/conversas", content='{"usuario_id": "u1",}',
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert "JSON" in r.json()["mensagem"]


def test_esquecer_usuario_remove_tudo(ctx):
    client, agente, memoria = ctx
    memoria.salvar("u1", "O usuário mora em Campinas", "cidade")
    memoria.salvar("u1", "O usuário gosta de xadrez", "hobby")
    memoria.salvar("u2", "O usuário gosta de corrida", "hobby")
    assert client.delete("/usuarios/u1/memorias").json() == {"removidas": 2}
    assert client.get("/usuarios/u1/memorias",
                      params={"consulta": "O usuário mora em Campinas"}).json() == []
    assert memoria.buscar("u2", "O usuário gosta de corrida")  # o outro usuário continua
    assert agente.sessoes_novas == ["u1"]


def test_esquecer_uma_memoria(ctx):
    client, _, memoria = ctx
    mid = memoria.salvar("u1", "O usuário mora em Campinas", "cidade")
    assert client.delete(f"/usuarios/u1/memorias/{mid}").status_code == 204
    r = client.delete(f"/usuarios/u1/memorias/{mid}")
    assert r.status_code == 404
    assert r.json()["codigo"] == "memoria_nao_encontrada"


# ---------- o adaptador do agente (não precisa do Ollama) ----------
def test_agente_local_traduz_ollama_desligado(monkeypatch):
    from src import agent as agente_mod
    from src.api.agente_local import AgenteLocal

    def quebrado(mensagem, usuario_id, memorias=None):
        raise ConnectionError("sem conexão")

    monkeypatch.setattr(agente_mod, "responder", quebrado)
    with pytest.raises(ProvedorIndisponivel):
        AgenteLocal().responder("u1", "oi", [], SelecaoModelo("ollama", agente_mod.MODEL))


def test_agente_local_traduz_timeout(monkeypatch):
    from src import agent as agente_mod
    from src.api.agente_local import AgenteLocal

    def lento(mensagem, usuario_id, memorias=None):
        raise httpx.ReadTimeout("demorou")

    monkeypatch.setattr(agente_mod, "responder", lento)
    with pytest.raises(ProvedorTimeout):
        AgenteLocal().responder("u1", "oi", [], SelecaoModelo("ollama", agente_mod.MODEL))


def test_agente_local_recusa_modelo_diferente_se_agente_nao_aceita(monkeypatch):
    from src import agent as agente_mod
    from src.api.agente_local import AgenteLocal

    def simples(mensagem, usuario_id, memorias=None):
        return "ok"

    monkeypatch.setattr(agente_mod, "responder", simples)
    with pytest.raises(ModeloNaoPermitido):
        AgenteLocal().responder("u1", "oi", [], SelecaoModelo("ollama", "outro-modelo:1b"))

def test_sem_token_da_401(ctx):
    sem_token = TestClient(app, raise_server_exceptions=False)
    r = sem_token.get("/usuarios/u1/memorias", params={"consulta": "x"})
    assert r.status_code == 401
    assert r.json()["codigo"] == "nao_autenticado"


def test_token_invalido_da_401(ctx):
    r = ctx[0].get("/usuarios/u1/memorias", params={"consulta": "x"},
                   headers={"Authorization": "Bearer errado"})
    assert r.status_code == 401


def test_usuario_nao_acessa_memorias_de_outro(ctx):
    client, _, memoria = ctx   # o cliente está autenticado como u1
    memoria.salvar("u2", "O usuário gosta de xadrez", "hobby")
    r = client.get("/usuarios/u2/memorias",
                   params={"consulta": "O usuário gosta de xadrez"})
    assert r.status_code == 403 and r.json()["codigo"] == "acesso_negado"
    r = client.post("/conversas", json={"usuario_id": "u2", "mensagem": "oi"})
    assert r.status_code == 403
    assert client.delete("/usuarios/u2/memorias").status_code == 403
    assert memoria.buscar("u2", "O usuário gosta de xadrez")  # nada foi apagado


def test_saude_e_provedores_sao_publicos(ctx):
    sem_token = TestClient(app, raise_server_exceptions=False)
    assert sem_token.get("/saude").status_code == 200
    assert sem_token.get("/provedores").status_code == 200

def test_nova_sessao_limpa_apenas_a_conversa(ctx):
    client, agente, memoria = ctx
    memoria.salvar("u1", "O usuário mora em Campinas", "cidade")
    r = client.post("/usuarios/u1/sessoes")
    assert r.status_code == 204
    assert agente.sessoes_novas == ["u1"]
    assert memoria.buscar("u1", "O usuário mora em Campinas")  # a memória continua    

def test_atualizar_memoria(ctx):
    client, _, memoria = ctx
    mid = memoria.salvar("u1", "O usuário mora em Campinas", "cidade")
    r = client.patch(f"/usuarios/u1/memorias/{mid}",
                     json={"texto": "O usuário mora em Santos"})
    assert r.status_code == 204
    achadas = client.get("/usuarios/u1/memorias",
                         params={"consulta": "O usuário mora em Santos"}).json()
    assert achadas and achadas[0]["texto"] == "O usuário mora em Santos"


def test_atualizar_memoria_inexistente_da_404(ctx):
    r = ctx[0].patch("/usuarios/u1/memorias/nao-existe", json={"texto": "x"})
    assert r.status_code == 404
    assert r.json()["codigo"] == "memoria_nao_encontrada"


def test_atualizar_memoria_de_outro_usuario_da_403(ctx):
    client, _, memoria = ctx   # o cliente está autenticado como u1
    mid = memoria.salvar("u2", "O usuário gosta de xadrez", "hobby")
    r = client.patch(f"/usuarios/u2/memorias/{mid}", json={"texto": "invadido"})
    assert r.status_code == 403
    assert memoria.buscar("u2", "O usuário gosta de xadrez")[0]["texto"] == \
        "O usuário gosta de xadrez"


def test_atualizar_memoria_com_texto_invalido_da_422(ctx):
    client, _, memoria = ctx
    mid = memoria.salvar("u1", "O usuário mora em Campinas", "cidade")
    r = client.patch(f"/usuarios/u1/memorias/{mid}", json={"texto": ""})
    assert r.status_code == 422
    r = client.patch(f"/usuarios/u1/memorias/{mid}", json={"texto": "   "})
    assert r.status_code == 422