import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.catalogo import Catalogo
from src.api.config import Configuracao
from src.api.dependencias import get_agente, get_catalogo, get_memoria, get_gerenciador
from src.api.falsos import AgenteFalso
from src.api.main import app
from src.memoria.gerenciador import GerenciadorMemoria
from src.memoria.store_mem import MemoriaEmRam
from src.interface import avaliacoes

TOKEN = "credencial-sintetica-do-teste-u1"
OUTRO = "credencial-sintetica-do-teste-u2"


def test_listagem_historico_autenticada_sem_cache_e_com_limites(ctx, monkeypatch):
    cliente, _, _ = ctx
    chamadas = []
    monkeypatch.setattr(avaliacoes, 'listar', lambda *args: chamadas.append(args) or {'avaliacoes': [], 'total': 0, 'proximo_deslocamento': None})
    assert cliente.get('/interface/avaliacoes').status_code == 401
    entrar(cliente)
    r = cliente.get('/interface/avaliacoes?limite=10&deslocamento=2')
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    assert chamadas == [('u1', 2, 10)]
    assert cliente.get('/interface/avaliacoes?limite=51').status_code == 422
    assert cliente.get('/interface/avaliacoes?deslocamento=-1').status_code == 422
    assert cliente.get('/interface/avaliacoes', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403


def test_analise_importada_autenticada_nao_persiste_nem_cria_processos(ctx, monkeypatch):
    from src.interface.protocolos import fonte_v3
    cliente, _, _ = ctx
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', lambda *a, **k: pytest.fail('Análise não cria processo'))
    caso = fonte_v3()[0]
    doc = {'interface': {'casos': [caso]}, 'resultados': [{'id': caso['id'], 'cenario': 'sem_memoria', 'repeticao': 1, 'resposta': 'DESCONHECIDO'}]}
    assert cliente.post('/interface/relatorios/analise', json={'documento': doc}).status_code == 401
    entrar(cliente)
    r = cliente.post('/interface/relatorios/analise', json={'documento': doc})
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    assert r.json()['resultados'][0]['julgamento']['passou'] is False
    assert cliente.post('/interface/relatorios/analise', json={'documento': []}).status_code == 422


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setenv("HABILITAR_COMPARATIVO_INTERFACE", "1")
    monkeypatch.setenv("API_TOKENS", TOKEN + ":u1," + OUTRO + ":u2")
    memoria, agente = MemoriaEmRam(), AgenteFalso()
    gerente = GerenciadorMemoria(memoria)
    config = Configuracao("ollama", "qwen2.5-coder:3b", (("ollama", "qwen2.5-coder:3b"),))
    anteriores = dict(app.dependency_overrides)
    app.dependency_overrides.update({
        get_memoria: lambda: memoria, get_agente: lambda: agente,
        get_catalogo: lambda: Catalogo(config), get_gerenciador: lambda: gerente,
    })
    with TestClient(app, base_url='http://127.0.0.1', raise_server_exceptions=False) as cliente:
        yield cliente, memoria, agente
    app.dependency_overrides.clear()
    app.dependency_overrides.update(anteriores)


def entrar(cliente, token=TOKEN):
    resposta = cliente.post("/interface/sessao", json={"token": token})
    assert resposta.status_code == 200
    return resposta


def test_pagina_publica_sem_credenciais_e_swagger_preservado(ctx):
    cliente, _, _ = ctx
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert TOKEN not in resposta.text
    assert "frame-ancestors 'none'" in resposta.headers["content-security-policy"]
    assert cliente.get("/interface/arquivos/app.mjs").status_code == 200
    spec = cliente.get("/openapi.json").json()
    assert "/conversas" in spec["paths"]
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


def test_login_identifica_dono_sem_devolver_token(ctx):
    cliente, _, _ = ctx
    assert cliente.get("/interface/sessao").status_code == 401
    assert cliente.post("/interface/sessao", json={"token": "invalido"}).status_code == 401
    resposta = entrar(cliente)
    assert resposta.json()["usuario_id"] == "u1"
    assert TOKEN not in resposta.text
    cookie = resposta.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/interface" in cookie
    assert resposta.headers["cache-control"] == "no-store"
    assert cliente.get("/interface/sessao").json()["usuario_id"] == "u1"


def test_cookie_nao_substitui_bearer_na_api_publica(ctx):
    cliente, _, _ = ctx
    entrar(cliente)
    assert cliente.get("/usuarios/u1/memorias", params={"consulta": "Campinas"}).status_code == 401


def test_credencial_revogada_deixa_de_funcionar(ctx, monkeypatch):
    cliente, _, _ = ctx
    entrar(cliente)
    monkeypatch.setenv("API_TOKENS", OUTRO + ":u2")
    assert cliente.get("/interface/sessao").status_code == 401
    assert cliente.post("/interface/conversas", json={"mensagem": "oi"}).status_code == 401


def test_origem_externa_recusada_no_login_e_na_sessao(ctx):
    cliente, _, agente = ctx
    assert cliente.post("/interface/sessao", json={"token": TOKEN}, headers={"Origin": "https://outro.example"}).status_code == 403
    entrar(cliente)
    assert cliente.post("/interface/conversas", json={"mensagem": "oi"}, headers={"Origin": "http://testserver:9001"}).status_code == 403
    assert cliente.post("/interface/nova-sessao", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert agente.chamadas == []


def test_usuario_injetado_pelo_servidor_e_tentativa_de_troca_recusada(ctx):
    cliente, _, agente = ctx
    entrar(cliente)
    forjado = cliente.post("/interface/conversas", json={"usuario_id": "u2", "mensagem": "oi"})
    assert forjado.status_code == 422
    r = cliente.post("/interface/conversas", json={"mensagem": "Moro em Campinas."})
    assert r.status_code == 200
    assert agente.chamadas[-1]["usuario_id"] == "u1"
    assert r.json()["tokens_entrada"] == 10


def test_memoria_sessao_e_isolamento(ctx):
    cliente, memoria, agente = ctx
    memoria.salvar("u2", "Mora em Curitiba.", "cidade")
    entrar(cliente)
    assert cliente.post("/interface/conversas", json={"mensagem": "Moro em Campinas."}).status_code == 200
    resultado = cliente.post("/interface/memorias", json={"consulta": "Campinas"}).json()
    assert resultado and "Campinas" in resultado[0]["texto"]
    assert cliente.post("/interface/nova-sessao").status_code == 204
    assert agente.sessoes_novas == ["u1"]
    assert memoria.buscar("u1", "Campinas")
    entrar(cliente, OUTRO)
    assert all("Campinas" not in m["texto"] for m in cliente.post("/interface/memorias", json={"consulta": "Campinas"}).json())


def test_logout_encerra_acesso(ctx):
    cliente, _, _ = ctx
    entrar(cliente)
    assert cliente.delete("/interface/sessao").status_code == 204
    assert cliente.get("/interface/sessao").status_code == 401


def test_avaliacao_exige_login_e_modelo_permitido(ctx, monkeypatch):
    cliente, _, _ = ctx
    chamadas = []
    monkeypatch.setattr(avaliacoes, "iniciar", lambda *args: chamadas.append(args) or {"id": "sintetico", "estado": "executando"})
    assert cliente.post("/interface/avaliacoes", json={"modelo": "qwen2.5-coder:3b"}).status_code == 401
    entrar(cliente)
    assert cliente.post("/interface/avaliacoes", json={"modelo": "nao-permitido"}).status_code == 400
    assert cliente.post("/interface/avaliacoes", json={"modelo": "qwen2.5-coder:3b", "repeticoes": 0}).status_code == 422
    assert cliente.post("/interface/avaliacoes", json={"modelo": "qwen2.5-coder:3b"}).status_code == 202
    assert chamadas == [("u1", "qwen2.5-coder:3b", 1, 'comparativo_v3', None)]


def test_job_de_outro_usuario_nao_pode_ser_consultado(ctx, monkeypatch, tmp_path):
    cliente, _, _ = ctx
    class Processo:
        returncode = 0
        def poll(self): return 0
    saida = tmp_path / "relatorio.json"
    saida.write_text(json.dumps({"resultados": []}), encoding="utf-8")
    monkeypatch.setattr(avaliacoes, "_jobs", {"sintetico": {
        "processo": Processo(), "usuario": "u1", "saida": saida, "inicio": 0,
    }})
    entrar(cliente, OUTRO)
    assert cliente.get("/interface/avaliacoes/sintetico").status_code == 404
    assert cliente.get("/interface/avaliacoes/sintetico/relatorio").status_code == 404
    entrar(cliente)
    assert cliente.get("/interface/avaliacoes/sintetico").json()["estado"] == "concluido"
    assert cliente.get("/interface/avaliacoes/sintetico/relatorio").status_code == 200


def test_comparativo_recusado_com_agente_falso(ctx, monkeypatch):
    cliente, _, _ = ctx
    monkeypatch.setenv("USAR_FALSOS", "1")
    entrar(cliente)
    r = cliente.post("/interface/avaliacoes", json={"modelo": "qwen2.5-coder:3b"})
    assert r.status_code == 409


def test_modelos_nao_sao_marcados_disponiveis_so_por_configuracao(ctx, monkeypatch):
    cliente, _, _ = ctx
    import httpx
    class Offline:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, *args): raise httpx.ConnectError("offline")
    monkeypatch.setattr("src.interface.rotas.httpx.AsyncClient", Offline)
    entrar(cliente)
    r = cliente.get("/interface/disponibilidade")
    assert r.status_code == 200
    assert r.json()["ollama"] == "indisponivel"
    assert r.json()["modelos"][0]["configurado"] is True


def test_assunto_da_busca_nao_aparece_nos_logs(ctx, caplog):
    import logging
    cliente, _, _ = ctx
    assunto = "assunto_sintetico_privado_nao_registrado"
    entrar(cliente)
    caplog.clear()
    with caplog.at_level(logging.INFO):
        assert cliente.post("/interface/memorias", json={"consulta": assunto}).status_code == 200
    assert assunto not in caplog.text
    assert "HTTP Request" in caplog.text


def test_roteiros_e_exemplos_autenticados_sem_modelo(ctx, monkeypatch):
    cliente, _, _ = ctx
    def proibido(*args, **kwargs):
        pytest.fail('Consultar arquivos não deve criar processo de avaliação')
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', proibido)
    assert cliente.get('/interface/roteiros').status_code == 401
    assert cliente.get('/interface/conjuntos/oficial').status_code == 401
    entrar(cliente)
    roteiros = cliente.get('/interface/roteiros').json()['protocolos']
    assert len(roteiros[0]['questoes']) == 16
    assert len(roteiros[1]['sessoes']) == 20
    assert len(roteiros[1]['questoes']) == 21
    modelo = cliente.get('/interface/conjuntos/exemplo')
    assert 'attachment' in modelo.headers['content-disposition']
    assert len(modelo.json()) == 1
    assert len(cliente.get('/interface/conjuntos/oficial').json()) == 16
    assert cliente.post('/interface/conjuntos/validar', json={'casos': modelo.json()}).json()['valido']


@pytest.mark.parametrize('alteracao', ['duplicado', 'sem_anotacao', 'tipo', 'mensagem_longa', 'muitos', 'caminho', 'estado'])
def test_upload_invalido_nao_inicia_modelo(ctx, monkeypatch, alteracao):
    import copy
    from src.interface.protocolos import fonte_v3
    cliente, _, _ = ctx
    entrar(cliente)
    casos = copy.deepcopy(fonte_v3()[:1])
    if alteracao == 'duplicado': casos *= 2
    elif alteracao == 'sem_anotacao': casos[0].pop('avaliacao')
    elif alteracao == 'tipo': casos[0]['mensagens'] = 'texto'
    elif alteracao == 'mensagem_longa': casos[0]['mensagens'][0] = 'x' * 2001
    elif alteracao == 'muitos': casos *= 21
    elif alteracao == 'caminho': casos[0]['dataset'] = '../../dados/memorias.db'
    elif alteracao == 'estado': casos[0]['estado_regras_esperado'] = {'cidade': {'objeto': 'não é texto'}}
    def proibido(*args, **kwargs): pytest.fail('Não executar arquivo inválido')
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', proibido)
    assert cliente.post('/interface/conjuntos/validar', json={'casos': casos}).status_code == 422
    assert cliente.post('/interface/avaliacoes', json={'modelo': 'qwen2.5-coder:3b', 'casos': casos}).status_code == 422


def test_limite_corpo_inclusive_sem_content_length(ctx, monkeypatch):
    cliente, _, _ = ctx
    entrar(cliente)
    def proibido(*args, **kwargs): pytest.fail('Não executar corpo excessivo')
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', proibido)
    r = cliente.post('/interface/conjuntos/validar', content=iter([b' ' * 100000, b' ' * 100000]),
                     headers={'Content-Type': 'application/json'})
    assert r.status_code == 413


def test_p6_nao_aceita_conjunto_generico_nem_repeticoes(ctx, monkeypatch):
    from src.interface.protocolos import fonte_v3
    cliente, _, _ = ctx
    entrar(cliente)
    def proibido(*args, **kwargs): pytest.fail('Não iniciar P6 incompatível')
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', proibido)
    for extra in ({'casos': fonte_v3()[:1]}, {'repeticoes': 3}):
        assert cliente.post('/interface/avaliacoes', json={'modelo': 'qwen2.5-coder:3b', 'protocolo': 'p6', **extra}).status_code == 422


def test_avaliacao_recusa_host_externo_e_origem_cruzada(ctx, monkeypatch):
    cliente, _, _ = ctx
    entrar(cliente)
    def proibido(*args, **kwargs): pytest.fail('Não executar origem externa')
    monkeypatch.setattr(avaliacoes, 'iniciar', proibido)
    corpo = {'modelo': 'qwen2.5-coder:3b'}
    assert cliente.post('/interface/avaliacoes', json=corpo, headers={'Host': 'outro.example'}).status_code == 403
    assert cliente.post('/interface/avaliacoes', json=corpo, headers={'Origin': 'https://outro.example'}).status_code == 403
