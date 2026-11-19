"""Reutiliza o avaliador oficial com uma API e um SQLite temporários."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--saida", required=True)
    parser.add_argument("--provedor", choices=("ollama", "openai"), default="ollama")
    parser.add_argument("--modelo")
    parser.add_argument("--dataset", type=Path,
                        help="Conjunto anotado separado; validado antes de iniciar a API.")
    parser.add_argument("--repeticoes", type=int, default=1, choices=range(1, 4))
    args = parser.parse_args()
    if os.getenv("USAR_FALSOS") == "1":
        parser.error("Use o modelo real para medir tokens.")
    if args.provedor == "openai" and not os.getenv("OPENAI_API_KEY"):
        parser.error("OpenAI exige OPENAI_API_KEY no ambiente e creditos de API; login ChatGPT Free nao substitui a chave.")
    args.modelo = args.modelo or ("gpt-4.1-mini" if args.provedor == "openai" else "qwen2.5-coder:3b")
    saida = Path(args.saida).resolve()
    if saida.exists():
        parser.error("O relatório já existe; escolha outro caminho.")
    if args.dataset:
        from eval.avaliar_comparativo import validar_dataset_p4
        args.dataset = args.dataset.resolve()
        try:
            validar_dataset_p4(json.loads(args.dataset.read_text(encoding='utf-8')))
        except (OSError, ValueError) as erro:
            parser.error(str(erro))
    token = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="cma-comparativo-") as temporario:
        with socket.socket() as porta_livre:
            porta_livre.bind(("127.0.0.1", 0))
            porta = porta_livre.getsockname()[1]
        os.environ.update({
            "API_TOKENS": token + ":eval_comparativo",
            "DB_PATH": str(Path(temporario) / "comparativo.db"),
            "LLM_PROVIDER": args.provedor, "LLM_MODEL": args.modelo,
            "MODELOS_PERMITIDOS": args.provedor + ":" + args.modelo,
        })
        os.environ.pop("USAR_FALSOS", None)
        log_path = Path(temporario) / "api.log"
        api = None
        def interromper(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, interromper)
        try:
            with log_path.open("wb") as log:
                api = subprocess.Popen(
                    [sys.executable, "-B", "-m", "uvicorn", "src.api.main:app",
                     "--host", "127.0.0.1", "--port", str(porta)],
                    stdout=log, stderr=subprocess.STDOUT,
                    **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
                )
            base = f"http://127.0.0.1:{porta}"
            for tentativa in range(150):
                if api.poll() is not None:
                    raise RuntimeError("A API isolada não iniciou.")
                try:
                    with urlopen(base + "/saude", timeout=0.5) as resposta:
                        if resposta.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("A API isolada não ficou disponível.")
            from eval import avaliar_comparativo as avaliador
            # Só este processo recebe a credencial efêmera. O avaliador original
            # e os arquivos de configuração da aplicação não são modificados.
            avaliador.carregar_token = lambda: token
            sys.argv = [
                "avaliar_comparativo", "--base-url", base, "--provedor", args.provedor,
                "--modelo", args.modelo, "--repeticoes", str(args.repeticoes),
                "--saida", str(saida),
            ]
            if args.dataset:
                sys.argv.extend(['--dataset', str(args.dataset)])
            return avaliador.main()
        finally:
            if api is not None and api.poll() is None:
                api.terminate()
                try:
                    api.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    api.kill()
                    api.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
