"""Reproduz P6 com protocolo novo, aceitando somente a diferença LF/CRLF.

Não altera dados, anotações ou protocolo históricos. Cada fonte ainda precisa
corresponder byte a byte ao congelamento, ressalvados os finais de linha.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

RAIZ = Path(__file__).resolve().parents[1]
PROTOCOLO = Path('docs/revisao-experimental/protocolo-contexto-v3-20261118.json')
FONTES = {'dataset_sha256': Path('eval/memoria/sessoes.json'),
          'anotacoes_sha256': Path('eval/memoria/anotacoes_p6.json')}


def conferir_fonte(dados: bytes, esperado: str) -> str:
    """Valida bytes exatos ou o mesmo texto com finais de linha LF/CRLF."""
    atual = hashlib.sha256(dados).hexdigest()
    lf = dados.replace(b'\r\n', b'\n')
    variantes = {atual, hashlib.sha256(lf).hexdigest(),
                 hashlib.sha256(lf.replace(b'\n', b'\r\n')).hexdigest()}
    if esperado not in variantes:
        raise ValueError('Fonte difere do congelamento além dos finais de linha.')
    return atual


def preparar_protocolo(destino: Path) -> dict:
    if destino.exists():
        raise FileExistsError('Protocolo de reprodução já existe; escolha outra saída.')
    original = json.loads((RAIZ/PROTOCOLO).read_text(encoding='utf-8'))
    if original.get('execucao_autorizada') is not True:
        raise ValueError('Protocolo original não autoriza a execução local.')
    hashes_atuais = {campo: conferir_fonte((RAIZ/caminho).read_bytes(), original[campo])
                     for campo, caminho in FONTES.items()}
    novo = {**original, **hashes_atuais,
            'referencia': original['referencia'] + ' / reprodução com bytes deste checkout',
            'reproducao': {'protocolo_original': PROTOCOLO.as_posix(),
                          'hashes_originais': {campo: original[campo] for campo in FONTES},
                          'diferenca_permitida': 'somente LF/CRLF; conteúdo não pode mudar',
                          'revisao_humana_adicional': False}}
    # O modo x impede sobrescrita inclusive se outro processo criar o arquivo.
    with destino.open('x', encoding='utf-8', newline='\n') as arquivo:
        json.dump(novo, arquivo, ensure_ascii=False, indent=2)
        arquivo.write('\n')
    return novo


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida-dir', required=True, type=Path)
    parser.add_argument('--commit-base', required=True)
    parser.add_argument('--modelo', default='qwen2.5-coder:3b')
    parser.add_argument('--progresso', type=Path)
    parser.add_argument('--somente-preparar', action='store_true',
                        help='Valida fontes e grava protocolo, sem chamar API/modelo.')
    args = parser.parse_args(argv)
    saida = args.saida_dir.resolve()
    if saida.exists():
        parser.error('Diretório de rodada já existe; escolha outra saída.')
    protocolo = saida.with_name(saida.name+'.protocolo.json')
    try:
        preparar_protocolo(protocolo)
    except (OSError, ValueError, KeyError) as erro:
        parser.error(str(erro))
    if args.somente_preparar:
        print(json.dumps({'fontes_conferidas': len(FONTES), 'modelo_executado': False,
                          'protocolo': str(protocolo)}, ensure_ascii=False))
        return 0
    return subprocess.run(
        [sys.executable, '-B', '-m', 'tools.executar_p6_local',
         '--saida-dir', str(saida), '--commit-base', args.commit_base,
         '--protocolo', str(protocolo), '--modelo', args.modelo,
         *(['--progresso', str(args.progresso)] if args.progresso else [])], cwd=RAIZ,
        check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
