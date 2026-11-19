"""Hashes dos artefatos publicados, cujos bytes são preservados no Git."""
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / 'evidencias/entrega-v3-20261118'
DESTINO = PASTA / 'manifesto-sha256.json'


def main():
    arquivos = {RAIZ/'docs/pesquisa-abnt.pdf'}
    for pasta in (PASTA, RAIZ/'evidencias/contexto-v3-20261118',
                  RAIZ/'evidencias/melhorias-20261118', RAIZ/'third_party/licenses'):
        arquivos.update(p for p in pasta.rglob('*') if p.is_file()
                        and '__pycache__' not in p.parts)
    arquivos.discard(DESTINO)
    resultado = {'algoritmo': 'SHA256', 'escopo': 'Bytes dos artefatos; manifesto não inclui a si mesmo.',
                 'arquivos': {p.relative_to(RAIZ).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(arquivos)}}
    DESTINO.write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({'arquivos': len(arquivos)}))


if __name__ == '__main__':
    main()
