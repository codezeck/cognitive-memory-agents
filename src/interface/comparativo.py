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

from src.interface.protocolos import RAIZ, gravar_progresso


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--saida", required=True)
    parser.add_argument("--provedor", choices=("ollama", "openai"), default="ollama")
    parser.add_argument("--modelo")
    parser.add_argument("--dataset", type=Path,
                        help="Conjunto anotado separado; validado antes de iniciar a API.")
    parser.add_argument("--repeticoes", type=int, default=1, choices=range(1, 4))
    parser.add_argument("--progresso", type=Path)
    parser.add_argument('--controle-sem-memoria', choices=('api_local', 'modelo_direto'), default='api_local',
                        help='api_local preserva o controle legado; modelo_direto chama Ollama sem agente.')
    parser.add_argument('--timeout-modelo', type=float, default=60,
                        help='Prazo por chamada nos quatro cenários (legado: 60 segundos).')
    args = parser.parse_args()
    from eval.historico_processo import timeout_positivo
    try:
        args.timeout_modelo = timeout_positivo(args.timeout_modelo)
    except ValueError as erro:
        parser.error(str(erro))
    if args.controle_sem_memoria == 'modelo_direto' and args.provedor != 'ollama':
        parser.error('O controle modelo_direto suporta somente Ollama.')
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
    casos = json.loads((args.dataset or RAIZ / 'eval/dataset_comparativo.json').read_text(encoding='utf-8'))
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
            "API_TOKENS_FILE": "", "MODO_DEMONSTRACAO": "0",
            "HABILITAR_COMPARATIVO_INTERFACE": "0", "HABILITAR_OBSERVACAO_RAM": "0",
            "USUARIOS_AVALIACAO_RAM": "",
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
                    [sys.executable, "-B", "-m", "src.interface.api_avaliacao",
                     "--port", str(porta), "--timeout-modelo", str(args.timeout_modelo)],
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
            token_original = avaliador.carregar_token
            avaliador.carregar_token = lambda: token
            argv_original = sys.argv
            sys.argv = [
                "avaliar_comparativo", "--base-url", base, "--provedor", args.provedor,
                "--modelo", args.modelo, "--repeticoes", str(args.repeticoes),
                "--saida", str(saida), "--timeout-api", str(max(120, args.timeout_modelo + 30)),
            ]
            if args.dataset:
                sys.argv.extend(['--dataset', str(args.dataset)])
            executar_original = avaliador.executar_cenario
            supervisor_original = avaliador.executar_historico_em_processo
            def supervisionar(caso, provedor, modelo, timeout=None):
                return supervisor_original(caso, provedor, modelo, timeout=timeout,
                                           timeout_modelo=args.timeout_modelo)
            concluidos = 0
            previstos = len(casos) * len(avaliador.CENARIOS) * args.repeticoes

            def executar_com_progresso(cliente, caso, cenario, *outros, **opcoes):
                nonlocal concluidos
                gravar_progresso(args.progresso, fase='Executando caso', concluidos=concluidos,
                                 previstos=previstos, unidade='tentativas', caso=caso['id'],
                                 cenario=cenario, pergunta=caso['mensagens'][-1])
                try:
                    if cenario == 'sem_memoria' and args.controle_sem_memoria == 'modelo_direto':
                        from src.interface.controle_modelo import executar_sem_memoria
                        return executar_sem_memoria(caso, args.provedor, args.modelo, timeout=args.timeout_modelo)
                    return executar_original(cliente, caso, cenario, *outros, **opcoes)
                finally:
                    concluidos += 1
                    gravar_progresso(args.progresso, fase='Tentativa encerrada; pode conter falha',
                                     concluidos=concluidos, previstos=previstos, unidade='tentativas',
                                     caso=caso['id'], cenario=cenario)

            avaliador.executar_cenario = executar_com_progresso
            avaliador.executar_historico_em_processo = supervisionar
            try:
                codigo = avaliador.main()
                if saida.is_file():
                    documento = json.loads(saida.read_text(encoding='utf-8'))
                    documento['limites_execucao'] = {
                        'versao': 'comparativo-limites-v1', 'timeout_modelo_s': args.timeout_modelo,
                        'timeout_api_s': max(120, args.timeout_modelo + 30),
                        'timeout_historico_base_s': 30, 'timeout_historico_por_turno_s': args.timeout_modelo,
                        'escopo': 'processos_isolados_do_comparativo', 'repeticao_automatica': False}
                    documento['falhas_execucao'] = sum(bool(r.get('erro')) for r in documento.get('resultados', []) if isinstance(r, dict))
                    if documento['falhas_execucao']:
                        codigo = codigo or 1
                    observacoes = documento.setdefault('observacoes', [])
                    observacoes[:] = [o for o in observacoes if not o.startswith('Timeout do histórico:')]
                    observacoes.extend([
                        f"Timeout por chamada de modelo nos quatro cenários: {args.timeout_modelo:g}s; API HTTP: {max(120, args.timeout_modelo + 30):g}s; histórico por caso: 30 + {args.timeout_modelo:g} segundos por turno.",
                        'Turnos concluídos do histórico são enviados ao processo pai imediatamente; chamadas sem retorno conservam consumo desconhecido, inclusive em timeout. Não há repetição automática.'
                    ])
                    saida.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                if args.controle_sem_memoria == 'modelo_direto' and saida.is_file():
                    from src.interface.controle_modelo import VERSAO
                    documento = json.loads(saida.read_text(encoding='utf-8'))
                    documento['versao_metodo_comparativo'] = VERSAO
                    documento['controle_sem_memoria'] = 'modelo_direto'
                    documento.setdefault('observacoes', []).extend([
                        'Nesta versão, sem_memoria envia somente a pergunta final diretamente ao Ollama, em um POST sem repetição, sem agente, histórico, memórias ou política local de abstenção.',
                        'O gabarito original P4 é aplicado ao controle direto. DESCONHECIDO não conta como acerto factual; abstenções exigidas pelo caso são avaliadas à parte.',
                        'O controle direto usa os padrões do modelo no Ollama. Contagens ausentes ou inválidas e falhas continuam desconhecidas; não há estimativa de tokens.',
                        'latencia_ollama_http_ms mede o percurso HTTP direto ao provedor; latencia_api_* não se aplica a esse controle.',
                        'Relatórios anteriores não são convertidos para este método. A limpeza de usuários e as regras da API descritas acima se aplicam somente aos cenários via API.'
                    ])
                    saida.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                return codigo
            finally:
                avaliador.executar_cenario = executar_original
                avaliador.executar_historico_em_processo = supervisor_original
                avaliador.carregar_token = token_original
                sys.argv = argv_original
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
