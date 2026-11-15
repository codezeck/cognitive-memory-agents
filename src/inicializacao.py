"""Preparacao idempotente da demonstracao local, sem imprimir credenciais."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import sys
import time
from urllib.request import Request, urlopen


def caminho_credenciais() -> Path:
    caminho = os.getenv("API_TOKENS_FILE", "")
    if not caminho:
        raise ValueError("Arquivo de credenciais da demonstracao nao configurado.")
    return Path(caminho)


def ler_credenciais() -> dict:
    dados = json.loads(caminho_credenciais().read_text(encoding="utf-8"))
    usuarios = dados["usuarios"]
    if set(usuarios) != {"a", "b"}:
        raise ValueError("Arquivo de credenciais incompleto; nao sera substituido.")
    tokens, ids = [], []
    for perfil in usuarios.values():
        token, uid = perfil["token"], perfil["usuario_id"]
        if not isinstance(token, str) or len(token) < 40 or any(c in token for c in ":,\n\r"):
            raise ValueError("Credencial local invalida; nao sera substituida.")
        if uid not in {"demo_professor", "demo_visitante"}:
            raise ValueError("Identidade local inesperada; nao sera substituida.")
        tokens.append(token)
        ids.append(uid)
    if len(set(tokens)) != 2 or len(set(ids)) != 2:
        raise ValueError("As duas identidades precisam ser distintas.")
    return usuarios


def preparar_credenciais() -> None:
    caminho = caminho_credenciais()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        ler_credenciais()
        print("Credenciais locais existentes preservadas.", flush=True)
        return
    usuarios = {perfil: {"usuario_id": uid, "token": secrets.token_urlsafe(40)}
                for perfil, uid in (("a", "demo_professor"), ("b", "demo_visitante"))}
    fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
        json.dump({"versao": 1, "usuarios": usuarios}, arquivo)
    print("Duas identidades sinteticas preparadas em volume privado.", flush=True)


def _ollama(caminho: str, corpo=None, timeout=30):
    base = os.getenv("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
    dados = json.dumps(corpo).encode() if corpo is not None else None
    request = Request(base + caminho, data=dados, headers={"Content-Type": "application/json"})
    return urlopen(request, timeout=timeout)


def preparar_modelo() -> None:
    modelo = os.getenv("LLM_MODEL", "qwen2.5-coder:3b")
    prazo = time.monotonic() + 120
    while True:
        try:
            with _ollama("/api/tags") as resposta:
                json.load(resposta)
            break
        except OSError:
            if time.monotonic() >= prazo:
                raise RuntimeError("Ollama nao ficou acessivel em 120 segundos.") from None
            time.sleep(1)
    print(f"Preparando modelo {modelo}. O primeiro download pode levar varios minutos.", flush=True)
    ultimo = None
    with _ollama("/api/pull", {"model": modelo, "stream": True}, timeout=1800) as resposta:
        for linha in resposta:
            evento = json.loads(linha)
            if evento.get("error"):
                raise RuntimeError("Ollama nao concluiu o download: " + str(evento["error"]))
            total, completo = evento.get("total", 0), evento.get("completed", 0)
            progresso = (int(100 * completo / total) // 10) * 10 if total else None
            chave = (evento.get("status"), progresso)
            if chave != ultimo:
                if total:
                    print(f"Modelo: {progresso}% — {completo} / {total} bytes", flush=True)
                else:
                    print("Modelo: " + str(evento.get("status", "preparando")), flush=True)
                ultimo = chave
    print("Conferindo carregamento real do modelo...", flush=True)
    with _ollama("/api/generate", {"model": modelo, "prompt": "", "stream": False}, timeout=900) as resposta:
        resultado = json.load(resposta)
        if resultado.get("error") or not resultado.get("done"):
            raise RuntimeError("Modelo instalado, mas o carregamento nao foi confirmado.")
    print("Modelo carregado e disponivel. A API pode iniciar.", flush=True)


def servir() -> None:
    if os.getenv("API_TOKENS_FILE"):
        usuarios = ler_credenciais()
        os.environ["API_TOKENS"] = ",".join(p["token"] + ":" + p["usuario_id"] for p in usuarios.values())
    import uvicorn
    print("Aplicacao local: http://127.0.0.1:" + os.getenv("CMA_PORT", "8001"), flush=True)
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, workers=1)


def main() -> int:
    try:
        if sys.argv[1:] == ["preparar"]:
            preparar_credenciais()
            preparar_modelo()
        elif sys.argv[1:] == ["preparar-acesso"]:
            preparar_credenciais()
        elif sys.argv[1:] == ["servir"]:
            servir()
        else:
            raise ValueError("Use preparar, preparar-acesso ou servir.")
    except Exception as erro:
        print("Falha na inicializacao: " + str(erro), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
