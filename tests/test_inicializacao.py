import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from src import inicializacao
from src.api.main import app


@pytest.fixture
def credenciais(tmp_path, monkeypatch):
    caminho = tmp_path / 'segredos' / 'usuarios.json'
    monkeypatch.setenv('API_TOKENS_FILE', str(caminho))
    inicializacao.preparar_credenciais()
    usuarios = inicializacao.ler_credenciais()
    monkeypatch.setenv('API_TOKENS', ','.join(p['token']+':'+p['usuario_id'] for p in usuarios.values()))
    monkeypatch.setenv('MODO_DEMONSTRACAO', '1')
    return caminho, usuarios


def test_preparacao_preserva_identidade_e_nao_mostra_tokens(credenciais, capsys):
    caminho, usuarios = credenciais
    antes = caminho.read_bytes()
    inicializacao.preparar_credenciais()
    assert caminho.read_bytes() == antes
    assert usuarios['a']['token'] != usuarios['b']['token']
    saida = capsys.readouterr().out
    for perfil in usuarios.values():
        assert perfil['token'] not in saida


def test_arquivo_invalido_nao_e_substituido(credenciais):
    caminho, _ = credenciais
    caminho.write_text('{"usuarios": {}}')
    with pytest.raises(ValueError):
        inicializacao.preparar_credenciais()
    assert caminho.read_text() == '{"usuarios": {}}'


def test_demo_cookie_escopado_sem_token_no_corpo_e_api_ainda_bearer(credenciais):
    _, usuarios = credenciais
    with TestClient(app, base_url='http://127.0.0.1') as cliente:
        assert cliente.get('/interface/configuracao').json()['demonstracao_local']
        r = cliente.post('/interface/demonstracao', json={'perfil':'a'})
        assert r.status_code == 200
        assert r.json()['usuario_id'] == 'demo_professor'
        cookie = r.headers['set-cookie'].lower()
        assert 'httponly' in cookie and 'samesite=strict' in cookie and 'max-age=' in cookie
        assert usuarios['a']['token'] not in r.text
        assert cliente.get('/interface/sessao').json()['usuario_id'] == 'demo_professor'
        assert cliente.get('/usuarios/demo_professor/memorias?consulta=cidade').status_code == 401
        assert cliente.get('/usuarios/demo_visitante/memorias?consulta=cidade',
                           headers={'Authorization':'Bearer '+usuarios['a']['token']}).status_code == 403


def test_demo_recusa_origem_host_estrangeiros_e_modo_desligado(credenciais, monkeypatch):
    with TestClient(app, base_url='http://127.0.0.1') as cliente:
        assert cliente.post('/interface/demonstracao', json={}, headers={'Origin':'https://outro.example'}).status_code == 403
        assert cliente.post('/interface/demonstracao', json={}, headers={'Host':'outro.example'}).status_code == 403
        assert cliente.post('/interface/demonstracao', json={'perfil':'administrador'}).status_code == 422
        monkeypatch.setenv('MODO_DEMONSTRACAO','0')
        assert cliente.post('/interface/demonstracao', json={}).status_code == 404


def test_estaticos_nao_contem_credenciais_geradas(credenciais):
    _, usuarios = credenciais
    for arquivo in Path('src/interface/static').iterdir():
        for perfil in usuarios.values():
            assert perfil['token'] not in arquivo.read_text(encoding='utf-8')


def test_bootstrap_carrega_modelo_sem_prompt_de_usuario(monkeypatch):
    chamadas = []
    class Resposta:
        def __init__(self, dados): self.dados=json.dumps(dados).encode()
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return self.dados
        def __iter__(self): return iter([b'{"status":"success"}\n'])
    def ollama(rota, corpo=None, timeout=30):
        chamadas.append((rota,corpo))
        return Resposta({'done':True} if rota=='/api/generate' else {'models':[]})
    monkeypatch.setattr(inicializacao,'_ollama',ollama)
    monkeypatch.setenv('LLM_MODEL','qwen2.5-coder:3b')
    inicializacao.preparar_modelo()
    assert chamadas[-1]==('/api/generate',{'model':'qwen2.5-coder:3b','prompt':'','stream':False})


def test_preparo_acesso_openai_nao_consulta_ollama(monkeypatch, tmp_path):
    import sys
    monkeypatch.setenv('API_TOKENS_FILE',str(tmp_path/'usuarios.json'))
    monkeypatch.setattr(sys,'argv',['inicializacao','preparar-acesso'])
    def proibido():raise AssertionError('O preparo remoto nao pode carregar modelo local')
    monkeypatch.setattr(inicializacao,'preparar_modelo',proibido)
    assert inicializacao.main()==0
    antes=(tmp_path/'usuarios.json').read_bytes()
    assert inicializacao.main()==0
    assert (tmp_path/'usuarios.json').read_bytes()==antes
