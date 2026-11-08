import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import httpx
import pytest

from eval import avaliar_comparativo as comparativo


def caso_valido():
    return {
        "id": "CLI", "categoria": "recuperacao",
        "mensagens": ["Moro em Osasco.", "Em que cidade moro?"],
        "esperado": "Osasco", "memorias": ["Moro em Osasco."],
        "estado_regras_esperado": {"cidade": "Osasco"},
        "avaliacao": {"tipo_resposta": "factual", "atributo": "cidade",
                      "informacoes_proibidas": []},
    }


def gravar_dataset(caminho, casos):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(casos), encoding="utf-8")
    return caminho


def chamada(resposta):
    return {"resposta": resposta, "tokens_entrada": 11, "tokens_saida": 3,
            "latencia_ms": 1, "memorias_usadas": []}


@pytest.fixture
def cli(monkeypatch, tmp_path):
    raiz = tmp_path / "projeto"
    padrao = gravar_dataset(raiz / "eval/dataset_comparativo.json", [caso_valido()])
    saida = tmp_path / "resultado.json"
    estado = {"memorias": [], "regras": {}}
    pedidos = []

    def responder(request):
        caminho = request.url.path
        pedidos.append((request.method, caminho))
        if caminho == "/saude":
            return httpx.Response(200, json={"status": "ok"})
        if caminho.endswith("/sessoes"):
            return httpx.Response(204)
        if caminho.endswith("/estado-regras"):
            return httpx.Response(200, json=estado["regras"])
        if caminho.endswith("/memorias"):
            if request.method == "DELETE":
                estado["memorias"] = []
                estado["regras"] = {}
                return httpx.Response(200, json={"removidas": 0})
            if request.method == "POST":
                estado["memorias"].append(json.loads(request.content)["texto"])
                return httpx.Response(201, json={"id": "memoria-simulada"})
            return httpx.Response(200, json=[])
        assert caminho == "/conversas"
        mensagem = json.loads(request.content)["mensagem"]
        if mensagem == "Moro em Osasco.":
            estado["memorias"] = [mensagem]
            estado["regras"] = {"cidade": "Osasco"}
        resposta = "Osasco" if estado["memorias"] else "DESCONHECIDO"
        return httpx.Response(200, json={
            **chamada(resposta), "memorias_usadas": list(estado["memorias"]),
        })

    cliente_real = httpx.Client
    fabrica = Mock(side_effect=lambda **kwargs: cliente_real(
        **kwargs, transport=httpx.MockTransport(responder),
    ))
    token = Mock(return_value="token-simulado")
    worker = Mock(return_value=[chamada("Registrado."), chamada("Osasco")])
    agente = Mock(side_effect=AssertionError("LLM real proibida"))
    monkeypatch.setattr(comparativo, "ROOT_DIR", raiz)
    monkeypatch.setattr(comparativo.httpx, "Client", fabrica)
    monkeypatch.setattr(comparativo, "carregar_token", token)
    monkeypatch.setattr(comparativo, "executar_historico_em_processo", worker)
    monkeypatch.setattr(comparativo, "AgenteLocal", agente)

    def executar(*argumentos):
        monkeypatch.setattr(comparativo.sys, "argv", [
            "avaliar_comparativo", "--saida", str(saida), *map(str, argumentos),
        ])
        return comparativo.main()

    def sem_chamadas():
        token.assert_not_called()
        fabrica.assert_not_called()
        worker.assert_not_called()
        agente.assert_not_called()
        assert not pedidos
        assert not saida.exists()

    return SimpleNamespace(raiz=raiz, padrao=padrao, saida=saida, executar=executar,
                           worker=worker, pedidos=pedidos, sem_chamadas=sem_chamadas)


@pytest.mark.parametrize("tipo", ["padrao", "relativo", "absoluto_interno", "absoluto_externo"])
def test_selecao_dataset_e_caminho_do_relatorio(cli, tmp_path, monkeypatch, tipo):
    caso = caso_valido()
    caso["id"] = "SELECIONADO"
    if tipo == "padrao":
        dataset = gravar_dataset(cli.padrao, [caso])
        argumentos = []
    elif tipo in {"relativo", "absoluto_interno"}:
        dataset = gravar_dataset(cli.raiz / "dados/casos teste.json", [caso])
        argumentos = ["--dataset", dataset.relative_to(cli.raiz) if tipo == "relativo" else dataset]
    else:
        dataset = gravar_dataset(tmp_path / "fora/casos teste.json", [caso])
        argumentos = ["--dataset", dataset]
    outro_diretorio = tmp_path / "outro_diretorio"
    outro_diretorio.mkdir()
    monkeypatch.chdir(outro_diretorio)
    assert cli.executar(*argumentos) == 0
    documento = json.loads(cli.saida.read_text(encoding="utf-8"))
    esperado = str(dataset.resolve()) if tipo == "absoluto_externo" else str(dataset.relative_to(cli.raiz))
    assert documento["dataset"] == esperado
    assert {r["id"] for r in documento["resultados"]} == {"SELECIONADO"}
    cli.worker.assert_called_once_with(caso, "ollama", "qwen2.5-coder:3b", timeout=None)


def test_dataset_e_timeout_juntos_preservam_p1_p4_e_campos_do_relatorio(cli, tmp_path):
    caso = caso_valido()
    dataset = gravar_dataset(tmp_path / "externo.json", [caso])
    assert cli.executar("--dataset", dataset, "--timeout-historico", 42,
                        "--modelo", "modelo-simulado", "--repeticoes", 2) == 0
    cli.worker.assert_has_calls([call(caso, "ollama", "modelo-simulado", timeout=42)] * 2)
    assert cli.worker.call_count == 2
    documento = json.loads(cli.saida.read_text(encoding="utf-8"))
    assert documento["versao_julgador"] == "p4-v2"
    assert documento["versao_metricas_resposta"] == "p5-v1"
    assert {"gerado_em", "dataset", "usuario_sintetico", "observacoes", "resumo",
            "comparacoes_tokens", "resultados"} <= documento.keys()
    assert len(documento["resultados"]) == 8
    for registro in documento["resultados"]:
        cenario = registro["cenario"]
        historico = cenario == "historico_completo"
        ingestao = 1 if cenario in {"historico_completo", "memoria_regras_api"} else 0
        assert registro["via"] == ("agente_local" if historico else "api")
        if historico:
            assert registro["memorias_usadas"] == []
        assert registro["passou"] is registro["protocolo_ok"] is True
        assert registro["julgamento"]["versao"] == "p4-v2"
        assert registro["vazamento_esquecidos"]["status"] == "nao_aplicavel"
        assert registro["provedor"] == "ollama"
        assert registro["modelo"] == "modelo-simulado"
        assert registro["repeticao"] in {1, 2}
        assert registro["tokens_por_etapa"]["ingestao"]["tokens_total"] == 14 * ingestao
        assert registro["tokens_por_etapa"]["pergunta_final"]["tokens_total"] == 14
        assert registro["tokens_por_etapa"]["sessao"]["tokens_total"] == 14 * (ingestao + 1)
        assert registro["tokens_entrada"] == 11 * (ingestao + 1)
        assert registro["tokens_saida"] == 3 * (ingestao + 1)
        assert registro["tokens_total"] == 14 * (ingestao + 1)
        assert registro["preparacao"]["custo_total_sistema_medido"] is False
        assert {"latencia_api_total_ms", "latencia_api_media_ms", "tempo_execucao_ms",
                "recuperacao_memoria_ok", "recuperacao_equivalente_ok",
                "estado_regras_esperado", "estado_regras_obtido", "estado_regras_ok"} <= registro.keys()
    pares = documento["comparacoes_tokens"]["memoria_regras_api"]["sessao"]["tokens_total"]
    assert pares["pares_medidos"] == 2
    assert pares["reducao_pct"] == 0
    assert all(r["aprovados"] == r["casos"] == 2 for r in documento["resumo"].values())
    for cenario, resumo in documento["resumo"].items():
        medidas = resumo["metricas_resposta"]
        factual = medidas["recuperacao_factual"]
        assert factual["tentativas_elegiveis"] == (0 if cenario == "sem_memoria" else 2)
        assert factual["taxa_pct"] == (None if cenario == "sem_memoria" else 100.0)
        assert medidas["abstencao_correta"]["tentativas_elegiveis"] == (2 if cenario == "sem_memoria" else 0)
        assert medidas["vazamento_esquecidos"]["nao_aplicaveis"] == 2
        assert medidas["vazamento_esquecidos"]["taxa_pct"] is None


def test_cli_preserva_falhas_como_nao_verificadas_e_exibe_denominadores_p5(cli, tmp_path, monkeypatch, capsys):
    esquecimento = copy.deepcopy(caso_valido())
    esquecimento.update(id="ESQUECIMENTO", categoria="esquecimento", esperado=["não sei"],
                        informacoes_esquecidas=["Osasco"])
    esquecimento["avaliacao"]["tipo_resposta"] = "abstencao"
    dataset = gravar_dataset(tmp_path / "simulado.json", [caso_valido(), esquecimento])
    monkeypatch.setattr(comparativo, "executar_cenario", Mock(side_effect=TimeoutError("simulado")))
    assert cli.executar("--dataset", dataset, "--timeout-historico", 42) == 0
    documento = json.loads(cli.saida.read_text(encoding="utf-8"))
    for resumo in documento["resumo"].values():
        medida = resumo["metricas_resposta"]["vazamento_esquecidos"]
        assert medida["tentativas_elegiveis"] == medida["nao_verificados"] == 1
        assert medida["numerador"] == medida["denominador"] == 0
        assert medida["nao_aplicaveis"] == 1
        assert medida["cobertura_pct"] == 0.0
        assert medida["taxa_pct"] is None
        assert resumo["tokens_total"] is None
    terminal = capsys.readouterr().out
    assert "vazamento_esquecidos: 0/0 verificados (taxa=n/d) | elegíveis=1; cobertura=0/1 (0.0%); não verificados=1; não aplicáveis=1" in terminal
    assert "recuperacao_factual:" in terminal
    assert "abstencao_correta:" in terminal


@pytest.mark.parametrize("campo,valor", [
    ("avaliacao", None), ("avaliacao", {}),
    ("avaliacao.tipo_resposta", "palpite"), ("avaliacao.tipo_resposta", []),
    ("avaliacao.atributo", "profissao"), ("avaliacao.atributo", []),
    ("avaliacao.informacoes_proibidas", None), ("avaliacao.informacoes_proibidas", [""]),
    ("avaliacao.aliases_proibidos", []), ("avaliacao.aliases_proibidos", {"x": [False]}),
    ("avaliacao.aliases_aceitos", "alias"), ("avaliacao.valores_antigos", [None]),
    ("informacoes_esquecidas", None), ("esperado", ["alternativa"]),
])
def test_metadados_invalidos_sao_rejeitados_antes_de_api_ou_modelo(cli, tmp_path, capsys, campo, valor):
    caso = caso_valido()
    partes = campo.split(".")
    alvo = caso if len(partes) == 1 else caso["avaliacao"]
    alvo[partes[-1]] = valor
    dataset = gravar_dataset(tmp_path / "incompativel.json", [caso])
    with pytest.raises(SystemExit) as erro:
        cli.executar("--dataset", dataset)
    assert erro.value.code == 2
    mensagem = capsys.readouterr().err
    assert "Dataset incompatível com P4" in mensagem
    assert "CLI:" in mensagem
    cli.sem_chamadas()


def test_conjunto_sem_anotacoes_nao_recebe_metadados_automaticamente(cli, tmp_path, capsys):
    casos = []
    for indice in range(10):
        caso = caso_valido()
        caso["id"] = f"SEM-ANOTACAO-{indice}"
        del caso["avaliacao"]
        casos.append(caso)
    dataset = gravar_dataset(tmp_path / "sem_anotacoes.json", casos)
    antes = dataset.read_bytes()
    with pytest.raises(SystemExit) as erro:
        cli.executar("--dataset", dataset)
    assert erro.value.code == 2
    assert "SEM-ANOTACAO-9" in capsys.readouterr().err
    assert dataset.read_bytes() == antes
    cli.sem_chamadas()


@pytest.mark.parametrize("conteudo", ["{", "{}", "[]", "[1]"])
def test_dataset_invalido_nao_inicia_chamadas(cli, tmp_path, conteudo):
    dataset = tmp_path / "invalido.json"
    dataset.write_text(conteudo, encoding="utf-8")
    with pytest.raises(SystemExit) as erro:
        cli.executar("--dataset", dataset)
    assert erro.value.code == 2
    cli.sem_chamadas()


def test_dataset_ausente_nao_inicia_chamadas(cli, tmp_path):
    with pytest.raises(SystemExit) as erro:
        cli.executar("--dataset", tmp_path / "ausente.json")
    assert erro.value.code == 2
    cli.sem_chamadas()


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_timeout_invalido_e_rejeitado_com_dataset_explicito(cli, timeout):
    with pytest.raises(SystemExit) as erro:
        cli.executar("--dataset", cli.padrao, "--timeout-historico", timeout)
    assert erro.value.code == 2
    cli.sem_chamadas()


def test_metadados_de_abstencao_e_proibicoes_explicitas_sao_validos():
    caso = copy.deepcopy(caso_valido())
    caso["esperado"] = ["não sei"]
    caso["avaliacao"]["tipo_resposta"] = "abstencao"
    caso["informacoes_esquecidas"] = ["Osasco"]
    caso["avaliacao"]["aliases_proibidos"] = {"Osasco": ["alias anotado"]}
    comparativo.validar_dataset_p4([caso])
