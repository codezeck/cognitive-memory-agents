"""Preserva textos de licença e metadados das dependências Python fixadas."""
import hashlib
import json
import re
from importlib.metadata import distributions
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def canonico(nome):
    return re.sub(r'[-_.]+', '-', nome).lower()


def main():
    requisitos = {}
    for arquivo in ('requirements.txt', 'requirements-dev.txt'):
        for linha in (RAIZ / arquivo).read_text(encoding='utf-8-sig').splitlines():
            if '==' in linha and not linha.startswith('#'):
                nome, versao = linha.strip().split('==')
                requisitos[canonico(nome)] = versao
    itens = []
    vistas = set()
    for d in distributions(path=[str(RAIZ/'.venv/Lib/site-packages'),
                                 str(RAIZ/'.env.ferramentas-entrega/Lib/site-packages')]):
        nome = canonico(d.metadata['Name'])
        if nome not in requisitos or nome in vistas:
            continue
        vistas.add(nome)
        textos = []
        for f in d.files or []:
            if '.dist-info/licenses/' not in str(f).replace('\\', '/'):
                continue
            origem = Path(d.locate_file(f))
            if not origem.is_file():
                continue
            destino = RAIZ / 'third_party/licenses/python' / nome / origem.name
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(origem.read_bytes())
            textos.append({'arquivo':destino.relative_to(RAIZ).as_posix(),
                           'sha256':hashlib.sha256(destino.read_bytes()).hexdigest()})
        itens.append({'nome':d.metadata['Name'], 'versao_instalada':d.version,
                      'versao_fixada':requisitos[nome],
                      'licenca_declarada':d.metadata.get('License-Expression') or d.metadata.get('License') or
                          '; '.join(x for x in d.metadata.get_all('Classifier', []) if x.startswith('License ::')),
                      'textos_incluidos':textos})
    ausentes = sorted(set(requisitos) - {canonico(x['nome']) for x in itens})
    if ausentes:
        raise ValueError('Distribuições não inventariadas: ' + ', '.join(ausentes))
    destino = RAIZ / 'third_party/licenses/inventario-python.json'
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(itens,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'distribuicoes':len(itens), 'sem_texto':[x['nome'] for x in itens if not x['textos_incluidos']]}))


if __name__ == '__main__':
    main()
