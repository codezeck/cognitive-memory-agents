"""Testes de spawn real com adaptadores simulados instalados no filho."""

import multiprocessing
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest

from eval import avaliar_comparativo as comparativo
from eval import historico_processo as processos
from src import agent


def _worker_simulado(conexao, caso, provedor, modelo):
    from src.api import agente_local

    contextos = []
    selecoes = []
    limite_original = agent.MAX_INTERACOES_HISTORICO
    responder_original = agente_local.AgenteLocal.responder

    class AdaptadorSimulado:
        def gerar_com_detalhes(self, mensagens):
            contextos.append([dict(m) for m in mensagens])
            if len(contextos) == 1 and "barreira" in caso:
                caso["barreira"].wait(timeout=10)
            if len(contextos) == caso.get("falhar_na_chamada"):
                raise ValueError("falha simulada no turno")
            return {
                "resposta": f"Resposta simulada {len(contextos)}",
                "tokens_entrada": 11, "tokens_saida": 3,
            }

    def fabrica(nome):
        def criar(modelo, api_key=None):
            selecoes.append((nome, modelo, api_key))
            return AdaptadorSimulado()
        return criar

    def conferir_memorias(self, usuario_id, mensagem, memorias, selecao):
        assert memorias == []
        return responder_original(self, usuario_id, mensagem, memorias, selecao)

    class ConexaoObservada:
        def send(self, resultado):
            assert agent.obter_historico(comparativo.USUARIO_HISTORICO) == [
                {"role": "system", "content": agent.SYSTEM_PROMPT},
            ]
            if resultado["ok"]:
                for chamada, contexto in zip(resultado["chamadas"], contextos):
                    chamada["contexto_teste"] = contexto
                    chamada["pid_teste"] = os.getpid()
                    chamada["limite_teste"] = agent.MAX_INTERACOES_HISTORICO
                    chamada["selecoes_teste"] = selecoes
                    chamada["inicio_teste"] = multiprocessing.get_start_method()
            conexao.send(resultado)

        def close(self):
            conexao.close()

    with (
        patch.object(agente_local, "OllamaAdapter", fabrica("ollama")),
        patch.object(agente_local, "OpenAIAdapter", fabrica("openai")),
        patch.object(agente_local.AgenteLocal, "responder", conferir_memorias),
        patch("httpx.Client.request", side_effect=AssertionError("HTTP proibido")),
        patch("src.armazenamento.repositorio.MemoriaSQLite.__init__",
              side_effect=AssertionError("Armazenamento proibido")),
        patch("src.memoria.gerenciador.GerenciadorMemoria.processar",
              side_effect=AssertionError("Memória automática proibida")),
    ):
        processos._executar_historico_worker(
            ConexaoObservada(), caso, provedor, modelo,
        )
    assert agent.MAX_INTERACOES_HISTORICO == limite_original


def _worker_travado(conexao, caso, provedor, modelo):
    threading.Event().wait(30)


def _worker_responde_e_trava(conexao, caso, provedor, modelo):
    conexao.send({"ok": True, "chamadas": []})
    threading.Event().wait(30)


def _worker_encerra_sem_resposta(conexao, caso, provedor, modelo):
    os._exit(7)


def _worker_resposta_grande(conexao, caso, provedor, modelo):
    conexao.send({"ok": True, "chamadas": [{"resposta": "x" * 2_000_000}]})
    conexao.close()


def _caso(prefixo="A", turnos=15):
    return {"mensagens": [f"Fato {prefixo}-{i}" for i in range(turnos)]}


@pytest.mark.parametrize("provedor", ["ollama", "openai"])
def test_spawn_preserva_historico_longo_modelo_prompt_e_estado_do_pai(
    monkeypatch, provedor,
):
    caso = _caso()
    monkeypatch.setenv("OPENAI_API_KEY", "chave-simulada")
    historicos_pai = {
        comparativo.USUARIO_HISTORICO: [{"role": "user", "content": "Só no pai"}],
    }
    monkeypatch.setattr(agent, "historicos_por_usuario", historicos_pai)
    limite_pai = agent.MAX_INTERACOES_HISTORICO

    chamadas = processos.executar_historico_em_processo(
        caso, provedor, "modelo-simulado", timeout=20, _alvo=_worker_simulado,
    )

    assert len(chamadas) == 15
    for indice, chamada in enumerate(chamadas):
        contexto = chamada["contexto_teste"]
        assert contexto[0] == {"role": "system", "content": agent.SYSTEM_PROMPT}
        assert [m["content"] for m in contexto if m["role"] == "user"] == (
            caso["mensagens"][:indice + 1]
        )
        assert [m["content"] for m in contexto if m["role"] == "assistant"] == [
            f"Resposta simulada {n}" for n in range(1, indice + 1)
        ]
        assert len(contexto) == 2 * (indice + 1)
        assert chamada["memorias_usadas"] == []
        assert chamada["limite_teste"] == 15
        assert chamada["pid_teste"] != os.getpid()
        assert chamada["inicio_teste"] == "spawn"
        assert chamada["selecoes_teste"] == [
            (provedor, "modelo-simulado",
             "chave-simulada" if provedor == "openai" else None),
        ]
    assert agent.MAX_INTERACOES_HISTORICO == limite_pai == 10
    assert agent.historicos_por_usuario is historicos_pai
    assert historicos_pai == {
        comparativo.USUARIO_HISTORICO: [{"role": "user", "content": "Só no pai"}],
    }
    assert multiprocessing.active_children() == []


def test_casos_concorrentes_usam_processos_e_historicos_independentes():
    barreira = multiprocessing.get_context("spawn").Barrier(2)
    casos = [_caso("A"), _caso("B")]
    for caso in casos:
        caso["barreira"] = barreira
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(
            processos.executar_historico_em_processo,
            caso, "ollama", "modelo-simulado", timeout=20, _alvo=_worker_simulado,
        ) for caso in casos]
        resultados = [futuro.result(timeout=25) for futuro in futuros]

    assert len({resultado[-1]["pid_teste"] for resultado in resultados}) == 2
    for caso, resultado in zip(casos, resultados):
        assert [m["content"] for m in resultado[-1]["contexto_teste"]
                if m["role"] == "user"] == caso["mensagens"]
    assert multiprocessing.active_children() == []


def test_erro_do_filho_e_reportado_e_processo_recolhido():
    caso = _caso()
    caso["falhar_na_chamada"] = 3
    with pytest.raises(RuntimeError, match="ValueError.*falha simulada no turno"):
        processos.executar_historico_em_processo(
            caso, "ollama", "modelo-simulado", timeout=20, _alvo=_worker_simulado,
        )
    assert multiprocessing.active_children() == []


@pytest.mark.parametrize("alvo", [_worker_travado, _worker_responde_e_trava])
def test_timeout_encerra_filho_inclusive_apos_receber_resultado(alvo):
    with pytest.raises(TimeoutError, match="prazo"):
        processos.executar_historico_em_processo(
            _caso(), "ollama", "modelo-simulado", timeout=2, _alvo=alvo,
        )
    assert multiprocessing.active_children() == []


def test_saida_abrupta_do_filho_nao_trava_o_pai():
    with pytest.raises(RuntimeError, match="código de saída: 7"):
        processos.executar_historico_em_processo(
            _caso(), "ollama", "modelo-simulado", timeout=20,
            _alvo=_worker_encerra_sem_resposta,
        )
    assert multiprocessing.active_children() == []


def test_resposta_grande_e_lida_antes_de_aguardar_saida_do_filho():
    chamadas = processos.executar_historico_em_processo(
        _caso(), "ollama", "modelo-simulado", timeout=20,
        _alvo=_worker_resposta_grande,
    )
    assert len(chamadas[0]["resposta"]) == 2_000_000
    assert multiprocessing.active_children() == []


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_timeout_invalido_e_rejeitado_antes_de_criar_processo(monkeypatch, timeout):
    criar_contexto = Mock()
    monkeypatch.setattr(processos.multiprocessing, "get_context", criar_contexto)
    with pytest.raises(ValueError, match="positivo e finito"):
        processos.executar_historico_em_processo(
            _caso(), "ollama", "modelo-simulado", timeout=timeout,
        )
    criar_contexto.assert_not_called()


def test_falha_ao_iniciar_fecha_processo_e_conexoes(monkeypatch):
    recepcao, envio, processo = Mock(), Mock(), Mock()
    processo.start.side_effect = OSError("falha ao iniciar")
    processo.is_alive.return_value = False
    processo.pid = None
    contexto = Mock()
    contexto.Pipe.return_value = (recepcao, envio)
    contexto.Process.return_value = processo
    monkeypatch.setattr(processos.multiprocessing, "get_context", lambda modo: contexto)

    with pytest.raises(OSError, match="falha ao iniciar"):
        processos.executar_historico_em_processo(_caso(), "ollama", "modelo-simulado")

    processo.close.assert_called_once()
    recepcao.close.assert_called_once()
    envio.close.assert_called_once()


def test_cenario_historico_despacha_para_supervisor_sem_http(monkeypatch):
    caso = {
        "id": "P2", "categoria": "recuperacao", "mensagens": ["Onde moro?"],
        "memorias": [], "esperado": "Osasco",
        "avaliacao": {"tipo_resposta": "factual", "atributo": "cidade", "informacoes_proibidas": []},
    }
    supervisor = Mock(return_value=[{
        "resposta": "Osasco", "memorias_usadas": [],
        "tokens_entrada": 11, "tokens_saida": 3, "latencia_ms": 1,
    }])
    monkeypatch.setattr(comparativo, "executar_historico_em_processo", supervisor)
    cliente = Mock()
    resultado = comparativo.executar_cenario(
        cliente, caso, "historico_completo", "ollama", "modelo-simulado",
        timeout_historico=42,
    )
    supervisor.assert_called_once_with(caso, "ollama", "modelo-simulado", timeout=42)
    assert resultado["passou"] is True
    assert cliente.mock_calls == []
