"""Histórico completo isolado por caso, sem alterar o agente do produto."""

from __future__ import annotations

import math
import multiprocessing
import queue
import threading
import time
from contextlib import contextmanager
from functools import partial


def timeout_positivo(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
        raise ValueError('O timeout do modelo deve ser positivo e finito.')
    return float(valor)


@contextmanager
def limite_modelo_em_avaliacao(timeout):
    """Usar somente em processos dedicados; não configura o chat do produto."""
    if timeout is None:
        yield
        return
    timeout = timeout_positivo(timeout)
    from src.api import agente_local
    ollama_original, openai_original = agente_local.OllamaAdapter, agente_local.OpenAIAdapter
    try:
        agente_local.OllamaAdapter = partial(ollama_original, timeout=timeout)
        agente_local.OpenAIAdapter = partial(openai_original, timeout=timeout)
        yield
    finally:
        agente_local.OllamaAdapter, agente_local.OpenAIAdapter = ollama_original, openai_original


class FalhaProcessoHistorico(RuntimeError):
    """Preserva a cadeia de tipos sem copiar credenciais ou payloads do backend."""
    def __init__(self, mensagem, tipos):
        super().__init__(mensagem)
        self.tipos_causa = tipos


def tipos_causa(erro):
    tipos, vistos = [], set()
    while erro is not None and id(erro) not in vistos and len(tipos) < 6:
        vistos.add(id(erro))
        tipos.append(type(erro).__name__)
        erro = erro.__cause__
    return tipos


def _executar_historico_worker(conexao, caso, provedor, modelo, timeout_modelo=None):
    from eval.avaliar_comparativo import executar_historico
    from src import agent

    limite_original = agent.MAX_INTERACOES_HISTORICO
    try:
        agent.MAX_INTERACOES_HISTORICO = max(
            limite_original, len(caso["mensagens"])
        )
        def observar(chamada):
            conexao.send({'tipo': 'parcial', 'chamada': chamada})
        with limite_modelo_em_avaliacao(timeout_modelo):
            chamadas = executar_historico(caso, provedor, modelo, observador=observar)
        conexao.send({"ok": True, "chamadas": chamadas})
    except Exception as erro:
        conexao.send({
            "ok": False, "tipo": type(erro).__name__, "mensagem": str(erro),
            "tipos_causa": tipos_causa(erro),
        })
    finally:
        agent.MAX_INTERACOES_HISTORICO = limite_original
        conexao.close()


def _receber_resultado(conexao, resultados):
    # A leitura também fica sob o prazo do pai, inclusive para respostas grandes.
    try:
        while True:
            resultado = conexao.recv()
            resultados.put((True, resultado))
            if not isinstance(resultado, dict) or resultado.get('tipo') != 'parcial':
                return
    except (EOFError, OSError) as erro:
        resultados.put((False, type(erro).__name__))


def _encerrar_processo(processo):
    if processo.is_alive():
        processo.terminate()
        processo.join(2)
    if processo.is_alive():
        processo.kill()
        processo.join(2)
    if processo.is_alive():
        raise RuntimeError("Não foi possível encerrar o processo de histórico.")
    if processo.pid is not None:
        processo.join(0)
    processo.close()


def executar_historico_em_processo(
    caso, provedor, modelo, timeout=None, *, _alvo=None, timeout_modelo=None,
):
    """Executa a P1 em spawn; `_alvo` permite simuladores explícitos nos testes.

    O prazo inclui inicialização, recebimento e saída do filho. O encerramento
    forçado pode acrescentar duas esperas de até dois segundos.
    """
    if timeout_modelo is not None:
        timeout_modelo = timeout_positivo(timeout_modelo)
    if timeout is None:
        timeout = 30.0 + (timeout_modelo or 60.0) * max(1, len(caso["mensagens"]))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("O timeout do histórico deve ser positivo e finito.")

    contexto = multiprocessing.get_context("spawn")
    recepcao, envio = contexto.Pipe(duplex=False)
    processo = contexto.Process(
        target=_alvo or _executar_historico_worker,
        args=(envio, caso, provedor, modelo) + ((timeout_modelo,) if timeout_modelo is not None else ()),
        name="historico_completo",
        daemon=True,
    )
    resultados = queue.Queue()
    leitor = threading.Thread(
        target=_receber_resultado, args=(recepcao, resultados), daemon=True,
    )
    prazo = time.monotonic() + timeout
    chamadas_observadas = []
    try:
        processo.start()
        envio.close()
        leitor.start()
        while True:
            try:
                recebido, resultado = resultados.get(timeout=max(0.0, prazo - time.monotonic()))
            except queue.Empty as erro:
                raise TimeoutError(f"O caso de histórico excedeu o prazo de {timeout:g}s.") from erro
            if recebido and isinstance(resultado, dict) and resultado.get('tipo') == 'parcial':
                if (not isinstance(resultado.get('chamada'), dict)
                        or len(chamadas_observadas) >= len(caso['mensagens'])):
                    raise RuntimeError('O processo de histórico retornou uma medição parcial inválida.')
                chamadas_observadas.append(resultado['chamada'])
                continue
            break

        processo.join(max(0.0, prazo - time.monotonic()))
        if processo.is_alive():
            raise TimeoutError(
                f"O processo de histórico não encerrou no prazo de {timeout:g}s."
            )
        if not recebido or processo.exitcode != 0:
            raise RuntimeError(
                "O processo de histórico encerrou sem resultado válido "
                f"(código de saída: {processo.exitcode})."
            )
        if not isinstance(resultado, dict) or not isinstance(resultado.get("ok"), bool):
            raise RuntimeError("O processo de histórico retornou uma resposta inválida.")
        if not resultado["ok"]:
            tipos = resultado.get('tipos_causa')
            if not isinstance(tipos, list) or not all(isinstance(t, str) and t.isidentifier() for t in tipos):
                tipos = [str(resultado.get('tipo'))] if str(resultado.get('tipo')).isidentifier() else ['ErroNoFilho']
            raise FalhaProcessoHistorico(
                f"Erro no processo de histórico ({resultado.get('tipo')}): "
                f"{resultado.get('mensagem')}", tipos,
            )
        if not isinstance(resultado.get("chamadas"), list):
            raise RuntimeError("O processo de histórico não retornou as chamadas.")
        return resultado["chamadas"]
    except Exception as erro:
        erro.chamadas_observadas = chamadas_observadas
        raise
    finally:
        try:
            _encerrar_processo(processo)
        finally:
            envio.close()
            recepcao.close()
            if leitor.ident is not None:
                leitor.join(2)
