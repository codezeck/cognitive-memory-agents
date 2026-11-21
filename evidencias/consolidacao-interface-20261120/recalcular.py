"""Confere evidências sintéticas e médias locais, sem rede ou modelos."""
import collections
import hashlib
import json
from math import isclose
from pathlib import Path

RAIZ=Path(__file__).resolve().parent
def hash_obj(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def main():
    inventario=json.loads((RAIZ/'inventario.json').read_text(encoding='utf-8'))
    consolidado=json.loads((RAIZ/'consolidado.json').read_text(encoding='utf-8'))
    totais={}
    for item in inventario:
        raw=(RAIZ/'relatorios'/f"{item['pasta']}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['arquivo_sha256']
        d=json.loads(raw)
        if item['protocolo']=='p6':
            assert d['comparacoes_tokens']==item['comparacoes_tokens']
            continue
        i=d['interface'];fontes=i['fontes_sha256']
        execs={k:v for k,v in fontes.items() if k in ('eval/avaliar_comparativo.py','eval/historico_processo.py','src/interface/comparativo.py','src/interface/controle_modelo.py','src/interface/api_avaliacao.py')}
        assert hash_obj(execs)==item['executor']
        assert i['dataset_sha256']==item['dataset'] and i['modelo']==item['modelo']
        agrupados=collections.defaultdict(list)
        for q in d['resultados']:agrupados[q['cenario']].append(q)
        totais[item['pasta']]={}
        for c,qs in agrupados.items():
            medidos=[q for q in qs if isinstance(q.get('tokens_total'),(int,float)) and not isinstance(q['tokens_total'],bool) and q.get('metricas_completas') is True and not q.get('erro')]
            s=item['cenarios'][c]
            assert s['tentativas']==len(qs) and s['medidos']==len(medidos)
            assert s['subtotal_medido']==sum(q['tokens_total'] for q in medidos)
            assert s['tokens_completos']==(s['subtotal_medido'] if len(medidos)==len(qs) else None)
            totais[item['pasta']][c]=(s['tokens_completos'],len(qs))
    nomes={'Histórico completo':'historico_completo','Memória automática':'memoria_regras_api','Sem memória':'sem_memoria','Memória pré-carregada':'memoria_persistente_api'}
    for g in consolidado['grupos']:
        for nome,c in nomes.items():
            valores=[totais[k][c] for k in g['execucoes']]
            assert all(t is not None for t,n in valores)
            t=sum(t for t,n in valores);n=sum(n for t,n in valores)
            assert t==g['cenarios'][nome]['tokens'] and n==g['tentativas_por_cenario']
            assert isclose(t/n,g['cenarios'][nome]['media_tokens_por_tentativa'],abs_tol=1e-10)
        h=g['cenarios']['Histórico completo']['tokens'];a=g['cenarios']['Memória automática']['tokens']
        assert isclose(100*(1-a/h),g['reducao_consolidada_pct'],abs_tol=1e-10)
        print(f"{g['etapa']} / {g['conjunto']}: {g['execucoes_completas']} rodadas, {g['tentativas_por_cenario']} tentativas/cenário, redução {g['reducao_consolidada_pct']:.4f}%")
    for q in json.loads((RAIZ/'qualidade-atual.json').read_text(encoding='utf-8')):
        d=json.loads((RAIZ/'relatorios'/f"{q['execucao']}.json").read_bytes())
        rs=[r for r in d['resultados'] if r['cenario']==q['cenario']]
        assert sum(r['julgamento']['protocolo_ok'] is True for r in rs)==q['conteudo_formato_aprovados']
        for chave,metrica in [('fatos','acerto_factual'),('abstencoes','abstencao_correta')]:
            estados=[r['julgamento'][metrica]['status'] for r in rs]
            assert sum(e!='nao_aplicavel' for e in estados)==q[chave]['oportunidades']
            for nome,estado in [('aprovados','aprovado'),('reprovados','reprovado'),('nao_verificados','nao_verificado')]:assert estados.count(estado)==q[chave][nome]
    manifesto=RAIZ/'manifesto-sha256.json'
    if manifesto.exists():
        for n,h in json.loads(manifesto.read_text(encoding='utf-8')).items():assert hashlib.sha256((RAIZ/n).read_bytes()).hexdigest()==h
    print('14 relatórios, consumos, qualidade e médias conferidos; nenhuma avaliação executada.')
if __name__=='__main__':main()
