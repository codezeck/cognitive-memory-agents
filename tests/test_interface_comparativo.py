import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from src.interface import avaliacoes, comparativo


@pytest.fixture(autouse=True)
def liberar_somente_testes_simulados(monkeypatch):
    monkeypatch.setenv("HABILITAR_COMPARATIVO_INTERFACE", "1")


@pytest.mark.parametrize('provedor',['ollama','openai'])
def test_execucao_isola_banco_e_credencial_sem_editar_avaliador(monkeypatch, tmp_path, provedor):
    from eval import avaliar_comparativo as avaliador
    original = Path(avaliador.__file__).read_bytes()
    for nome in ("API_TOKENS", "DB_PATH", "LLM_PROVIDER", "LLM_MODEL", "MODELOS_PERMITIDOS"):
        monkeypatch.setenv(nome, "configuracao-original-sintetica")
    monkeypatch.delenv("USAR_FALSOS", raising=False)
    monkeypatch.setenv('OPENAI_API_KEY','chave-simulada-nao-real')
    monkeypatch.setattr(sys, "argv", ["comparativo", "--saida", str(tmp_path / "resultado.json"),'--provedor',provedor])
    monkeypatch.setattr(comparativo.signal, "signal", lambda *args: None)
    observacao = {}
    class Processo:
        returncode = None
        def __init__(self, args, **kwargs):
            observacao["args"] = args
            observacao["banco"] = os.environ["DB_PATH"]
            observacao["token"] = os.environ["API_TOKENS"]
        def poll(self): return self.returncode
        def terminate(self): self.returncode = 0
        def wait(self, **kwargs): return self.returncode
    class Saude:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(comparativo.subprocess, "Popen", Processo)
    monkeypatch.setattr(comparativo, "urlopen", lambda *args, **kwargs: Saude())
    def avaliar():
        token = avaliador.carregar_token()
        assert os.environ["API_TOKENS"] == token + ":eval_comparativo"
        assert token not in " ".join(observacao["args"])
        assert os.environ["DB_PATH"] != "configuracao-original-sintetica"
        assert "cma-comparativo-" in os.environ["DB_PATH"]
        assert "--base-url" in sys.argv
        assert os.environ['LLM_PROVIDER']==provedor
        assert sys.argv[sys.argv.index('--provedor')+1]==provedor
        assert os.environ['MODELOS_PERMITIDOS']==provedor+':'+os.environ['LLM_MODEL']
        return 0
    monkeypatch.setattr(avaliador, "carregar_token", lambda: "original")
    monkeypatch.setattr(avaliador, "main", avaliar)
    assert comparativo.main() == 0
    assert Path(avaliador.__file__).read_bytes() == original
    assert not Path(observacao["banco"]).parent.exists()


def test_wrapper_openai_sem_chave_nao_cria_processo(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('USAR_FALSOS',raising=False)
    monkeypatch.setattr(sys,'argv',['comparativo','--provedor','openai','--saida',str(tmp_path/'resultado.json')])
    def proibido(*args,**kwargs):raise AssertionError('Nao pode iniciar sem credencial')
    monkeypatch.setattr(comparativo.subprocess,'Popen',proibido)
    with pytest.raises(SystemExit):comparativo.main()
    assert 'ChatGPT Free' in capsys.readouterr().err
    assert not (tmp_path/'resultado.json').exists()


def test_wrapper_nao_sobrescreve_relatorio(monkeypatch, tmp_path):
    caminho = tmp_path / "existente.json"
    caminho.write_text("original", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["comparativo", "--saida", str(caminho)])
    with pytest.raises(SystemExit):
        comparativo.main()
    assert caminho.read_text(encoding="utf-8") == "original"


def test_somente_uma_execucao_e_resultados_por_usuario(monkeypatch, tmp_path):
    monkeypatch.delenv("USAR_FALSOS", raising=False)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "conversa.db"))
    monkeypatch.setattr(avaliacoes, "_jobs", {})
    class Processo:
        def __init__(self, args, **kwargs): self.returncode = None
        def poll(self): return self.returncode
    monkeypatch.setattr(avaliacoes.subprocess, "Popen", Processo)
    inicio = avaliacoes.iniciar("demo", "qwen2.5-coder:3b", 1)
    assert inicio["estado"] == "executando"
    with pytest.raises(HTTPException) as erro:
        avaliacoes.iniciar("outro", "qwen2.5-coder:3b", 1)
    assert erro.value.status_code == 409
    with pytest.raises(HTTPException) as erro:
        avaliacoes.consultar(inicio["id"], "outro")
    assert erro.value.status_code == 404
    assert avaliacoes.consultar(inicio["id"], "demo")[0]["estado"] == "executando"
    assert not (tmp_path / "conversa.db").exists()
    avaliacoes._jobs[inicio["id"]]["timer"].cancel()


def test_limite_independe_de_poll_do_navegador(monkeypatch, tmp_path):
    monkeypatch.delenv("USAR_FALSOS", raising=False)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "conversa.db"))
    monkeypatch.setattr(avaliacoes, "_jobs", {})
    timers = []
    class Processo:
        returncode = None
        def __init__(self, *args, **kwargs): pass
        def poll(self): return self.returncode
    class Timer:
        def __init__(self, prazo, callback, args):
            self.callback, self.args = callback, args
            self.cancelado = False
            timers.append(self)
        def start(self): pass
        def cancel(self): self.cancelado = True
    monkeypatch.setattr(avaliacoes.subprocess, "Popen", Processo)
    monkeypatch.setattr(avaliacoes.threading, "Timer", Timer)
    monkeypatch.setattr(avaliacoes, "_encerrar", lambda p: setattr(p, "returncode", -1))
    inicio = avaliacoes.iniciar("demo", "qwen2.5-coder:3b", 1)
    timers[0].callback(*timers[0].args)
    estado, _ = avaliacoes.consultar(inicio["id"], "demo")
    assert estado["estado"] == "falhou"
    assert "prazo" in estado["mensagem"]
    assert timers[0].cancelado
