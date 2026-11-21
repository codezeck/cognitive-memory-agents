import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def salvar_historico(base, codigo, usuario='demo', protocolo='comparativo_v3', saida=0):
    import json
    pasta = base / 'avaliacoes-interface' / codigo
    pasta.mkdir(parents=True)
    (pasta / 'dono.json').write_text(json.dumps({'usuario': usuario, 'protocolo': protocolo,
        'iniciada_em': '2026-11-20T01:00:00+00:00', 'credencial': 'nao-expor'}), encoding='utf-8')
    (pasta / 'relatorio.json').write_text(json.dumps({'interface': {'codigo_saida': saida,
        'modelo': 'modelo-local', 'repeticoes': 3, 'conjunto': 'oficial'}, 'resposta': 'nao-expor'}), encoding='utf-8')
    return pasta


def test_historico_isolado_paginado_e_recuperavel_sem_criar_processos(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'conversa.db'))
    monkeypatch.setattr(avaliacoes, '_jobs', {})
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', lambda *a, **k: pytest.fail('Listar não cria processo'))
    salvar_historico(tmp_path, '1' * 32)
    salvar_historico(tmp_path, '2' * 32, protocolo='p6', saida=1)
    salvar_historico(tmp_path, '3' * 32, usuario='outro')
    primeira = avaliacoes.listar('demo', limite=1)
    assert primeira['total'] == 2 and primeira['proximo_deslocamento'] == 1
    assert primeira['avaliacoes'][0]['id'] == '2' * 32
    assert primeira['avaliacoes'][0]['estado'] == 'falhou'
    assert primeira['avaliacoes'][0]['relatorio_disponivel'] is True
    segunda = avaliacoes.listar('demo', deslocamento=1, limite=1)
    assert segunda['avaliacoes'][0]['id'] == '1' * 32
    assert segunda['proximo_deslocamento'] is None
    assert 'nao-expor' not in json.dumps(primeira)
    assert str(tmp_path) not in json.dumps(primeira)
    assert avaliacoes.consultar('2' * 32, 'demo')[0]['estado'] == 'falhou'
    with pytest.raises(HTTPException): avaliacoes.consultar('2' * 32, 'outro')


def test_historico_corrupcao_tipos_metadados_legados_e_sem_relatorio(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'conversa.db'))
    monkeypatch.setattr(avaliacoes, '_jobs', {})
    p = salvar_historico(tmp_path, '1' * 32)
    (p / 'dono.json').write_text(json.dumps({'usuario': 'demo', 'protocolo': []}))
    (p / 'relatorio.json').write_text(json.dumps({'interface': {'modelo': [], 'repeticoes': True, 'conjunto': {}}}))
    q = salvar_historico(tmp_path, '2' * 32)
    (q / 'dono.json').write_text('[]')
    r = salvar_historico(tmp_path, '3' * 32)
    (r / 'relatorio.json').write_text('invalido')
    salvar_historico(tmp_path, 'nome-invalido')
    lista = avaliacoes.listar('demo')['avaliacoes']
    assert len(lista) == 2
    legado = next(i for i in lista if i['id'] == '1' * 32)
    assert legado['origem_data'] == 'arquivo_local'
    assert legado['modelo'] is legado['repeticoes'] is legado['conjunto'] is None
    assert next(i for i in lista if i['id'] == '3' * 32)['relatorio_disponivel'] is False


def test_estado_real_do_processo_tem_precedencia_sem_mutar_job(monkeypatch, tmp_path):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'conversa.db'))
    salvar_historico(tmp_path, '1' * 32)
    class Processo:
        returncode = 1
        def poll(self): return self.returncode
    processo = Processo()
    job = {'usuario': 'demo', 'processo': processo, 'prazo_excedido': True, 'trava': object()}
    monkeypatch.setattr(avaliacoes, '_jobs', {'1' * 32: job})
    antes = dict(job)
    assert avaliacoes.listar('demo')['avaliacoes'][0]['estado'] == 'falhou'
    processo.returncode = None
    assert avaliacoes.listar('demo')['avaliacoes'][0]['estado'] == 'executando'
    assert job == antes


def test_historico_ignora_links_externos(monkeypatch, tmp_path):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'dados' / 'conversa.db'))
    monkeypatch.setattr(avaliacoes, '_jobs', {})
    fora = salvar_historico(tmp_path / 'fora', '1' * 32)
    raiz = tmp_path / 'dados' / 'avaliacoes-interface'
    raiz.mkdir(parents=True)
    try:
        (raiz / ('2' * 32)).symlink_to(fora, target_is_directory=True)
    except OSError:
        pytest.skip('Criação de links indisponível neste ambiente')
    assert avaliacoes.listar('demo')['total'] == 0
    with pytest.raises(HTTPException): avaliacoes.consultar('2' * 32, 'demo')
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


def test_dataset_invalido_e_recusado_antes_de_iniciar_api(monkeypatch, tmp_path):
    dataset = tmp_path / 'invalido.json'
    dataset.write_text('[{"id":"sem-anotacoes"}]', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['comparativo', '--dataset', str(dataset),
                                    '--saida', str(tmp_path / 'resultado.json')])
    def proibido(*args, **kwargs):
        raise AssertionError('Não iniciar API nem modelo com dataset inválido')
    monkeypatch.setattr(comparativo.subprocess, 'Popen', proibido)
    with pytest.raises(SystemExit):
        comparativo.main()
    assert not (tmp_path / 'resultado.json').exists()


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


@pytest.fixture
def processos_simulados(monkeypatch, tmp_path):
    monkeypatch.setenv('HABILITAR_COMPARATIVO_INTERFACE', '1')
    monkeypatch.setenv('USAR_FALSOS', '0')
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'conversa.db'))
    monkeypatch.setenv('API_TOKENS', 'segredo-do-chat')
    monkeypatch.setenv('API_TOKENS_FILE', 'arquivo-privado-chat')
    monkeypatch.setenv('OPENAI_API_KEY', 'segredo-remoto')
    monkeypatch.setattr(avaliacoes, '_jobs', {})
    processos = []
    class Processo:
        def __init__(self, args, **kwargs):
            self.args, self.kwargs, self.returncode = args, kwargs, None
            processos.append(self)
        def poll(self): return self.returncode
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', Processo)
    monkeypatch.setattr(avaliacoes, '_encerrar', lambda p: setattr(p, 'returncode', -1))
    yield processos
    avaliacoes.encerrar_avaliacoes()


@pytest.mark.parametrize('protocolo', ['comparativo_v3', 'p6'])
def test_comando_isolado_dos_dados_credenciais_e_protocolo(processos_simulados, protocolo, tmp_path):
    inicio = avaliacoes.iniciar('demo', 'qwen2.5-coder:3b', 1, protocolo)
    p = processos_simulados[0]
    assert p.args[p.args.index('--protocolo') + 1] == protocolo
    assert 'src.interface.executar_avaliacao' in p.args
    ambiente = p.kwargs['env']
    for campo in ('API_TOKENS', 'API_TOKENS_FILE', 'OPENAI_API_KEY'):
        assert ambiente[campo] == ''
    assert ambiente['MODO_DEMONSTRACAO'] == ambiente['HABILITAR_OBSERVACAO_RAM'] == '0'
    assert ambiente['DB_PATH'] != str(tmp_path / 'conversa.db')
    assert not (tmp_path / 'conversa.db').exists()
    assert avaliacoes.ativa('outro') == {'ocupada': True, 'id': None}
    assert avaliacoes.ativa('demo')['id'] == inicio['id']


def test_conjunto_proprio_validado_salvo_no_job_sem_caminho_do_cliente(processos_simulados):
    from src.interface.protocolos import fonte_v3
    import json
    casos = fonte_v3()[:1]
    inicio = avaliacoes.iniciar('demo', 'qwen2.5-coder:3b', 3, casos=casos)
    p = processos_simulados[0]
    caminho = Path(p.args[p.args.index('--dataset-proprio') + 1])
    assert caminho.parent.name == inicio['id']
    assert json.loads(caminho.read_text(encoding='utf-8')) == casos
    assert 'segredo' not in ' '.join(p.args)


def test_trava_entre_workers_e_falha_de_spawn_nao_prendem_fila(processos_simulados, monkeypatch, tmp_path):
    inicio = avaliacoes.iniciar('demo', 'qwen2.5-coder:3b', 1)
    jobs = avaliacoes._jobs
    monkeypatch.setattr(avaliacoes, '_jobs', {})  # simula outro worker, mesmo diretório
    with pytest.raises(HTTPException) as erro:
        avaliacoes.iniciar('outro', 'qwen2.5-coder:3b', 1, 'p6')
    assert erro.value.status_code == 409
    monkeypatch.setattr(avaliacoes, '_jobs', jobs)
    processos_simulados[0].returncode = 0
    avaliacoes.consultar(inicio['id'], 'demo')
    def falhar(*args, **kwargs): raise OSError('falha de spawn simulada')
    popen = avaliacoes.subprocess.Popen
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', falhar)
    with pytest.raises(HTTPException) as erro: avaliacoes.iniciar('demo', 'qwen2.5-coder:3b', 1)
    assert erro.value.status_code == 503
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', popen)
    assert avaliacoes.iniciar('demo', 'qwen2.5-coder:3b', 1)['estado'] == 'executando'


def test_relatorio_parcial_disponivel_e_recuperacao_pos_reinicio(processos_simulados, monkeypatch):
    import json
    inicio = avaliacoes.iniciar('demo', 'qwen2.5-coder:3b', 1)
    job = avaliacoes._jobs[inicio['id']]
    documento = {'interface': {'codigo_saida': 1}, 'estado_orquestracao': 'incompleta'}
    job['saida'].write_text(json.dumps(documento), encoding='utf-8')
    processos_simulados[0].returncode = 1
    estado, caminho = avaliacoes.consultar(inicio['id'], 'demo')
    assert estado['estado'] == 'falhou' and caminho == job['saida']
    assert estado['relatorio']['estado_orquestracao'] == 'incompleta'
    monkeypatch.setattr(avaliacoes, '_jobs', {})
    with pytest.raises(HTTPException): avaliacoes.consultar(inicio['id'], 'outro')
    assert avaliacoes.consultar(inicio['id'], 'demo')[0]['relatorio'] == documento
    with pytest.raises(HTTPException): avaliacoes.consultar('../../dados', 'demo')


def test_runner_comparativo_proprio_reutiliza_execucao_e_exporta_origem(tmp_path, monkeypatch):
    import json
    from src.interface import executar_avaliacao as runner
    from src.interface.protocolos import fonte_v3
    monkeypatch.setattr(runner, 'preparar_modelo', lambda *a, **kw: {'tipo': 'simulado'})
    dataset = tmp_path / 'proprio.json'
    dataset.write_text(json.dumps(fonte_v3()[:1]), encoding='utf-8')
    def executar():
        assert '--dataset' in sys.argv and sys.argv[sys.argv.index('--dataset')+1] == str(dataset)
        assert sys.argv[sys.argv.index('--controle-sem-memoria')+1] == 'modelo_direto'
        assert float(sys.argv[sys.argv.index('--timeout-modelo')+1]) == 180
        saida = Path(sys.argv[sys.argv.index('--saida')+1])
        saida.write_text(json.dumps({'resultados': [], 'resumo': {}, 'comparacoes_tokens': {}}))
        return 0
    monkeypatch.setattr(comparativo, 'main', executar)
    monkeypatch.setenv('CMA_COMMIT_BASE', 'commit-simulado')
    saida = tmp_path / 'relatorio.json'
    assert runner.main(['--protocolo', 'comparativo_v3', '--modelo', 'simulado', '--dataset-proprio', str(dataset),
                        '--saida', str(saida), '--progresso', str(tmp_path/'progresso.json')]) == 0
    doc = json.loads(saida.read_text(encoding='utf-8'))
    assert doc['interface']['conjunto'] == 'próprio'
    assert doc['interface']['controle_sem_memoria'] == 'modelo_direto'
    assert doc['interface']['versao_metodo_comparativo'] == 'comparativo-v3-ollama-direto-v1'
    assert doc['interface']['casos'] == fonte_v3()[:1]
    assert len(doc['interface']['dataset_sha256']) == 64
    assert doc['interface']['revisao_humana'].startswith('não realizada')


def test_runner_p6_preserva_falha_e_eventos_no_relatorio(tmp_path, monkeypatch):
    import json
    from src.interface import executar_avaliacao as runner
    from tools import reproduzir_p6
    monkeypatch.setattr(runner, 'preparar_modelo', lambda *a, **kw: {'tipo': 'simulado'})
    def executar(args):
        pasta = Path(args[args.index('--saida-dir')+1]);pasta.mkdir()
        (pasta/'resumo.json').write_text(json.dumps({'sessoes': [], 'estado_orquestracao': 'incompleta', 'comparacoes_tokens': {}}))
        (pasta/'eventos.jsonl').write_text(json.dumps({'tipo':'resultado', 'cenario':'memoria_automatica',
            'evento':{'tipo':'pergunta','id':'u01/s2/pergunta1'}, 'estado':'erro'})+'\n')
        assert '--progresso' in args
        return 1
    monkeypatch.setattr(reproduzir_p6, 'main', executar)
    monkeypatch.setenv('CMA_COMMIT_BASE', 'commit-simulado')
    saida = tmp_path/'relatorio.json'
    assert runner.main(['--protocolo','p6','--modelo','simulado','--saida',str(saida),
                        '--progresso',str(tmp_path/'progresso.json')]) == 1
    doc = json.loads(saida.read_text(encoding='utf-8'))
    assert doc['estado_orquestracao'] == 'incompleta'
    assert doc['resultados'][0]['estado'] == 'erro'
    assert doc['interface']['protocolo'] == 'p6'


def test_ambiente_desabilitado_da_motivo_antes_de_criar_processos(monkeypatch, tmp_path):
    monkeypatch.setenv('HABILITAR_COMPARATIVO_INTERFACE', '0')
    def proibido(*args, **kwargs): pytest.fail('Não iniciar avaliação desabilitada')
    monkeypatch.setattr(avaliacoes.subprocess, 'Popen', proibido)
    with pytest.raises(HTTPException) as erro: avaliacoes.iniciar('demo', 'modelo', 1)
    assert 'preservando volumes' in erro.value.detail


def test_diagnostico_de_preparo_aparece_sem_relatorio(processos_simulados, monkeypatch):
    import json
    inicio = avaliacoes.iniciar('demo', 'qwen2.5-coder:3b', 1, 'p6')
    job = avaliacoes._jobs[inicio['id']]
    job['saida'].with_name('falha-preparo.json').write_text(json.dumps({
        'etapa': 'preparo_modelo', 'mensagem': 'O modelo não carregou; nenhuma tentativa iniciada.'}), encoding='utf-8')
    processos_simulados[0].returncode = 1
    estado, caminho = avaliacoes.consultar(inicio['id'], 'demo')
    assert estado['estado'] == 'falhou'
    assert estado['mensagem'] == 'O modelo não carregou; nenhuma tentativa iniciada.'
    assert caminho is None
    monkeypatch.setattr(avaliacoes, '_jobs', {})
    recuperado, caminho = avaliacoes.consultar(inicio['id'], 'demo')
    assert recuperado['mensagem'] == estado['mensagem']
    assert recuperado['estado'] == 'falhou' and caminho is None


def test_progresso_comparativo_conta_tentativa_com_falha_sem_repetir(monkeypatch, tmp_path):
    import json
    from eval import avaliar_comparativo as avaliador
    from src.interface.protocolos import fonte_v3
    fonte = tmp_path/'casos.json'
    fonte.write_text(json.dumps(fonte_v3()[:1]),encoding='utf-8')
    progresso=tmp_path/'progresso.json'
    monkeypatch.setenv('USAR_FALSOS','0')
    monkeypatch.setattr(sys,'argv',['comparativo','--dataset',str(fonte),'--saida',str(tmp_path/'resultado.json'),
                                  '--progresso',str(progresso)])
    monkeypatch.setattr(comparativo.signal,'signal',lambda *args:None)
    class Processo:
        returncode=None
        def __init__(self,*args,**kwargs):pass
        def poll(self):return self.returncode
        def terminate(self):self.returncode=0
        def wait(self,**kwargs):return self.returncode
    class Saude:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setattr(comparativo.subprocess,'Popen',Processo)
    monkeypatch.setattr(comparativo,'urlopen',lambda *args,**kwargs:Saude())
    chamadas=[]
    def cenario(*args,**kwargs):
        chamadas.append(args[1]['id'])
        raise TimeoutError('falha simulada')
    monkeypatch.setattr(avaliador,'executar_cenario',cenario)
    token_original=avaliador.carregar_token
    def main_simulado():
        with pytest.raises(TimeoutError):
            avaliador.executar_cenario(None,fonte_v3()[0],'historico_completo','ollama','simulado')
        return 0
    monkeypatch.setattr(avaliador,'main',main_simulado)
    assert comparativo.main()==0
    assert chamadas==[fonte_v3()[0]['id']]
    assert json.loads(progresso.read_text(encoding='utf-8'))['concluidos']==1
    assert avaliador.executar_cenario is cenario
    assert avaliador.carregar_token is token_original
