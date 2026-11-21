"""API do comparativo com limites próprios, isolada da conversa do produto."""
import argparse

from eval.historico_processo import limite_modelo_em_avaliacao, timeout_positivo


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--timeout-modelo', type=float, required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('Porta inválida.')
    try:
        timeout = timeout_positivo(args.timeout_modelo)
    except ValueError as erro:
        parser.error(str(erro))
    import uvicorn
    with limite_modelo_em_avaliacao(timeout):
        uvicorn.run('src.api.main:app', host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
