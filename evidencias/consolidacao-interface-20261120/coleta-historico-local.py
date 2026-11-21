import collections
import hashlib
import json
from pathlib import Path
import subprocess

codigo = r'''
import collections,hashlib,json,pathlib
raiz=pathlib.Path('/app/dados/avaliacoes-interface')
saida=[]
def digest(obj):
 return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
for p in sorted(raiz.glob('*/relatorio.json')):
 try:
  if json.loads(p.with_name('dono.json').read_text()).get('usuario')!='demo_professor':continue
  raw=p.read_bytes();d=json.loads(raw);i=d.get('interface',{});rs=d.get('resultados',[])
  fontes=i.get('fontes_sha256',{})
  if i.get('protocolo')=='p6':
   saida.append({'pasta':p.parent.name,'arquivo_sha256':hashlib.sha256(raw).hexdigest(),'gerado_em':d.get('gerado_em'),'protocolo':'p6','codigo_saida':i.get('codigo_saida'),'situacao':'protocolo_separado','comparacoes_tokens':d.get('comparacoes_tokens',{}),'sessoes':len(d.get('sessoes',[]))})
   continue
  nucleo={k:v for k,v in fontes.items() if k.startswith(('src/api/','src/memoria/','src/modelos/')) or k in ('src/agent.py','src/contexto.py','src/evidencias_pessoais.py')}
  executor={k:v for k,v in fontes.items() if k in ('eval/avaliar_comparativo.py','eval/historico_processo.py','src/interface/comparativo.py','src/interface/controle_modelo.py','src/interface/api_avaliacao.py')}
  if not isinstance(rs,list):
   saida.append({'pasta':p.parent.name,'arquivo_sha256':hashlib.sha256(raw).hexdigest(),'gerado_em':d.get('gerado_em'),'protocolo':i.get('protocolo'),'situacao':'protocolo_separado','chaves':list(d),'resumo':d.get('resumo')})
   continue
  casos=i.get('casos',[]) or []
  item={'pasta':p.parent.name,'arquivo_sha256':hashlib.sha256(raw).hexdigest(),'gerado_em':d.get('gerado_em'),'protocolo':i.get('protocolo'),'conjunto':i.get('conjunto'),'repeticoes':i.get('repeticoes'),'casos':len(casos),'dataset':i.get('dataset_sha256') or digest(casos),'modelo':i.get('modelo'),'nucleo':digest(nucleo),'executor':digest(executor),'fontes_presentes':bool(fontes),'limites':i.get('limites_execucao',d.get('limites_execucao')),'controle':i.get('controle_sem_memoria',d.get('controle_sem_memoria')),'codigo_saida':i.get('codigo_saida'),'cenarios':{},'pareados':{}}
  por={}
  for q in rs:
   if not isinstance(q,dict):continue
   c=q.get('cenario');por.setdefault(c,[]).append(q)
  for c,qs in por.items():
   medidos=[q for q in qs if isinstance(q.get('tokens_total'),(int,float)) and not isinstance(q.get('tokens_total'),bool) and q.get('metricas_completas') is True and not q.get('erro')]
   item['cenarios'][c]={'tentativas':len(qs),'medidos':len(medidos),'falhas':sum(bool(q.get('erro')) for q in qs),'tokens_completos':sum(q['tokens_total'] for q in medidos) if len(medidos)==len(qs) else None,'subtotal_medido':sum(q['tokens_total'] for q in medidos),'fatos':dict(collections.Counter(q.get('julgamento',{}).get('acerto_factual',{}).get('status') for q in qs)),'vias':dict(collections.Counter(q.get('via','ausente') for q in qs))}
  def chave(q):return (q.get('id'),q.get('repeticao'),q.get('provedor'),q.get('modelo'))
  h=por.get('historico_completo',[]);a=por.get('memoria_regras_api',[])
  hc=collections.Counter(chave(q) for q in h);ac=collections.Counter(chave(q) for q in a)
  hm={chave(q):q for q in h if hc[chave(q)]==1};am={chave(q):q for q in a if ac[chave(q)]==1}
  pares=[]
  for k in hm.keys() & am.keys():
   x,y=hm[k],am[k]
   if all(q.get('metricas_completas') is True and isinstance(q.get('tokens_total'),(int,float)) and not isinstance(q.get('tokens_total'),bool) and not q.get('erro') for q in (x,y)):pares.append((x['tokens_total'],y['tokens_total']))
  ht=sum(x for x,y in pares);at=sum(y for x,y in pares)
  item['pareados']={'pares':len(pares),'historico':ht,'automatica':at,'reducao_pct':100*(1-at/ht) if ht else None,'historico_previsto':len(h),'automatica_prevista':len(a)}
  saida.append(item)
 except Exception as e:saida.append({'pasta':p.parent.name,'erro_leitura':type(e).__name__,'detalhe':str(e)[:180]})
print(json.dumps(saida,ensure_ascii=False))
'''
r = subprocess.run(['docker','exec','cma-validacao-api-1','python','-c',codigo],capture_output=True,check=True)
dados=json.loads(r.stdout)
destino=Path(__file__).parent/'medias-tokens-historico'
destino.mkdir(exist_ok=True)
(destino/'inventario.json').write_text(json.dumps(dados,ensure_ascii=False,indent=2),encoding='utf-8')
for d in sorted(dados,key=lambda x:x.get('gerado_em') or ''):
 print(json.dumps({k:v for k,v in d.items() if k not in ('arquivo_sha256','cenarios','limites')},ensure_ascii=False))
 print('  totais:',{k:(v['tokens_completos'],v['medidos'],v['tentativas']) for k,v in d.get('cenarios',{}).items()})
