"""Execuções explícitas do comparativo em processos e bancos isolados."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import HTTPException

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
PRAZO_SEGUNDOS = 3600


def _encerrar(processo):
    if processo.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(processo.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW, check=False,
        )
    else:
        try:
            os.killpg(processo.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(processo.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        processo.wait(timeout=5)
    except subprocess.TimeoutExpired:
        processo.kill()


def _expirar(codigo):
    with _lock:
        job = _jobs.get(codigo)
        if job and job["processo"].poll() is None:
            job["prazo_excedido"] = True
            _encerrar(job["processo"])


def encerrar_avaliacoes():
    with _lock:
        for job in _jobs.values():
            if job.get("timer"):
                job["timer"].cancel()
            _encerrar(job["processo"])


def iniciar(usuario: str, modelo: str, repeticoes: int) -> dict:
    if os.getenv("HABILITAR_COMPARATIVO_INTERFACE") != "1":
        raise HTTPException(409, "Comparativo indisponível nesta demonstração. Use o protocolo revisado de avaliação.")
    if os.getenv("USAR_FALSOS") == "1":
        raise HTTPException(409, "A avaliação real está desativada no modo de testes.")
    with _lock:
        for job in _jobs.values():
            if job["processo"].poll() is None:
                raise HTTPException(409, "Já existe uma avaliação em andamento. Aguarde sua conclusão.")
        # Resultados sintéticos separados do banco conversacional.
        pasta = Path(os.getenv("DB_PATH", "dados/memorias.db")).resolve().parent / "avaliacoes-interface"
        pasta.mkdir(parents=True, exist_ok=True)
        codigo = uuid.uuid4().hex
        saida = pasta / f"{codigo}.json"
        log = pasta / f"{codigo}.log"
        opcoes = (
            {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
            if os.name == "nt" else {"start_new_session": True}
        )
        with log.open("wb") as arquivo:
            processo = subprocess.Popen(
                [sys.executable, "-B", "-m", "src.interface.comparativo",
                 "--saida", str(saida), "--modelo", modelo,
                 "--repeticoes", str(repeticoes)],
                stdout=arquivo, stderr=subprocess.STDOUT, **opcoes,
            )
        _jobs[codigo] = {
            "processo": processo, "usuario": usuario, "saida": saida,
            "inicio": time.monotonic(),
        }
        timer = threading.Timer(PRAZO_SEGUNDOS, _expirar, args=(codigo,))
        timer.daemon = True
        _jobs[codigo]["timer"] = timer
        timer.start()
        return {"id": codigo, "estado": "executando"}


def consultar(codigo: str, usuario: str) -> tuple[dict, Path | None]:
    with _lock:
        job = _jobs.get(codigo)
        if not job or job["usuario"] != usuario:
            raise HTTPException(404, "Avaliação não encontrada para este usuário.")
        processo = job["processo"]
        if processo.poll() is None and time.monotonic() - job["inicio"] > PRAZO_SEGUNDOS:
            _encerrar(processo)
            job["prazo_excedido"] = True
        if processo.poll() is None:
            return {"id": codigo, "estado": "executando"}, None
        if job.get("timer"):
            job["timer"].cancel()
        if processo.returncode != 0 or not job["saida"].is_file():
            return {
                "id": codigo, "estado": "falhou",
                "mensagem": (
                    "A avaliação excedeu o prazo. Nenhum resultado foi presumido."
                    if job.get("prazo_excedido") else
                    "A avaliação não terminou. Confira o Ollama e o log local da execução."
                ),
            }, None
        try:
            documento = json.loads(job["saida"].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise HTTPException(500, "Não foi possível ler o relatório da avaliação.")
        return {"id": codigo, "estado": "concluido", "relatorio": documento}, job["saida"]
