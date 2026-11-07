"""Histórico completo isolado por caso, sem alterar o agente do produto."""

from __future__ import annotations

import math
import multiprocessing
import queue
import threading
import time


def _executar_historico_worker(conexao, caso, provedor, modelo):
    from eval.avaliar_comparativo import executar_historico
    from src import agent

    limite_original = agent.MAX_INTERACOES_HISTORICO
    try:
        agent.MAX_INTERACOES_HISTORICO = max(
            limite_original, len(caso["mensagens"])
        )
        chamadas = executar_historico(caso, provedor, modelo)
        conexao.send({"ok": True, "chamadas": chamadas})
    except Exception as erro:
        conexao.send({
            "ok": False, "tipo": type(erro).__name__, "mensagem": str(erro),
        })
    finally:
        agent.MAX_INTERACOES_HISTORICO = limite_original
        conexao.close()


def _receber_resultado(conexao, resultados):
    # A leitura também fica sob o prazo do pai, inclusive para respostas grandes.
    try:
        resultados.put((True, conexao.recv()))
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
    caso, provedor, modelo, timeout=None, *, _alvo=None,
):
    """Executa a P1 em spawn; `_alvo` permite simuladores explícitos nos testes.

    O prazo inclui inicialização, recebimento e saída do filho. O encerramento
    forçado pode acrescentar duas esperas de até dois segundos.
    """
    if timeout is None:
        timeout = 30.0 + 60.0 * max(1, len(caso["mensagens"]))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("O timeout do histórico deve ser positivo e finito.")

    contexto = multiprocessing.get_context("spawn")
    recepcao, envio = contexto.Pipe(duplex=False)
    processo = contexto.Process(
        target=_alvo or _executar_historico_worker,
        args=(envio, caso, provedor, modelo),
        name="historico_completo",
        daemon=True,
    )
    resultados = queue.Queue(maxsize=1)
    leitor = threading.Thread(
        target=_receber_resultado, args=(recepcao, resultados), daemon=True,
    )
    prazo = time.monotonic() + timeout
    try:
        processo.start()
        envio.close()
        leitor.start()
        try:
            recebido, resultado = resultados.get(
                timeout=max(0.0, prazo - time.monotonic())
            )
        except queue.Empty as erro:
            raise TimeoutError(
                f"O caso de histórico excedeu o prazo de {timeout:g}s."
            ) from erro

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
            raise RuntimeError(
                f"Erro no processo de histórico ({resultado.get('tipo')}): "
                f"{resultado.get('mensagem')}"
            )
        if not isinstance(resultado.get("chamadas"), list):
            raise RuntimeError("O processo de histórico não retornou as chamadas.")
        return resultado["chamadas"]
    finally:
        try:
            _encerrar_processo(processo)
        finally:
            envio.close()
            recepcao.close()
            if leitor.ident is not None:
                leitor.join(2)
