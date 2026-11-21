"""Verifica os derivados preservados sem rede, Docker ou geração de respostas."""
import hashlib
import json
from pathlib import Path
import sys

RAIZ=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(RAIZ))
from eval.informacao_antiga import analisar_informacao_antiga

def main():
    pasta=Path(__file__).resolve().parent
    fontes=json.loads((pasta/'fontes-originais.json').read_text(encoding='utf-8'))
    for codigo,h in fontes.items():
        raw=(RAIZ/'evidencias/consolidacao-interface-20261120/relatorios'/f'{codigo}.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest()==h,codigo
        obtido=analisar_informacao_antiga(json.loads(raw))
        esperado=json.loads((pasta/'analises'/f'{codigo}.json').read_text(encoding='utf-8'))
        assert obtido==esperado,codigo
    manifesto=pasta/'manifesto-sha256.json'
    if manifesto.exists():
        for n,h in json.loads(manifesto.read_text(encoding='utf-8')).items():
            assert hashlib.sha256((pasta/n).read_bytes()).hexdigest()==h,n
    print(f'{len(fontes)} análises adicionais e originais conferidos; nenhum modelo executado.')

if __name__=='__main__':main()
