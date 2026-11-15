"""Captura configuração permitida e preservação; não imprime ambientes/segredos."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN='20261114-entrega-ae9eb113'
EVID=ROOT/'evidencias/entrega'/RUN


def docker(*args):return subprocess.check_output(['docker',*args],encoding='utf-8')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    anterior=json.loads((ROOT/f'.env.{RUN}-recursos.json').read_text(encoding='utf-8-sig'))
    preservacao=json.loads((ROOT/f'.env.{RUN}-preservacao.json').read_text(encoding='utf-8-sig'))
    servicos=[]
    for s in anterior['containers']:
        atual=json.loads(docker('inspect',s['id']))[0]
        servicos.append({'nome':s['nome'],'id':s['id'],'started_at_antes':s['iniciado_em'],
                         'started_at_depois':atual['State']['StartedAt'],'estado':atual['State']['Status'],
                         'preservado':atual['State']['StartedAt']==s['iniciado_em']})
    volumes=docker('volume','ls','--format','{{.Name}}').splitlines()
    fonte=Path('C:/Users/silva/.codex/worktrees/interface-instalacao/cognitive-memory-agents')
    worktree={p:sha(fonte/p)==h for p,h in preservacao['interface'].items()}
    historicos={p:sha(ROOT/p)==h for p,h in preservacao['root'].items() if p.startswith('evidencias/')}
    api=json.loads(docker('inspect','cma-entrega-ae9eb113-api-1'))[0]
    ollama=json.loads(docker('inspect','cma-entrega-ae9eb113-ollama-1'))[0]
    env=dict(x.split('=',1) for x in api['Config']['Env'])
    permitidos=['LLM_PROVIDER','LLM_MODEL','OLLAMA_HOST','USAR_FALSOS','MODO_DEMONSTRACAO','HABILITAR_OBSERVACAO_RAM','USUARIOS_AVALIACAO_RAM','MODELOS_PERMITIDOS','HABILITAR_COMPARATIVO_INTERFACE']
    codigo="import urllib.request,json; u='http://ollama:11434'; print(json.dumps({'tags':json.load(urllib.request.urlopen(u+'/api/tags')),'show':json.load(urllib.request.urlopen(urllib.request.Request(u+'/api/show',data=json.dumps({'model':'qwen2.5-coder:3b'}).encode(),headers={'Content-Type':'application/json'})))}))"
    modelo=json.loads(docker('exec',api['Id'],'python','-c',codigo))
    show=modelo['show'];modelo['show']={k:show[k] for k in ('details','parameters','model_info') if k in show}
    arquivos=[p for pasta in ('src','eval') for p in (ROOT/pasta).rglob('*') if p.is_file() and p.suffix in ('.py','.json','.mjs','.css','.html')]
    arquivos += [ROOT/p for p in ('Dockerfile','docker-compose.yml','requirements.txt','Iniciar.ps1')]
    config={'instante_utc':datetime.now(timezone.utc).isoformat(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
            'base':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'projeto':'cma-entrega-ae9eb113','porta':59059,
            'api':{'id':api['Id'],'imagem':api['Image'],'cmd':api['Config']['Cmd'],'started_at':api['State']['StartedAt'],'configuracao':{k:env.get(k) for k in permitidos}},
            'ollama':{'imagem':ollama['Image'],'referencia':ollama['Config']['Image']},'modelo':modelo,
            'parametros_requisicao':'Sem overrides de temperature/seed/num_ctx no adaptador; defaults efetivos do modelo/runtime. Modelo e versão não tornam geração determinística.',
            'p6_executada':False,'reservado_executado':False,'hashes_fontes':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in arquivos},
            'preservacao':{'servicos':servicos,'volumes_anteriores_presentes':all(v in volumes for v in anterior['volumes']),
                          'worktree_origem':worktree,'evidencias_anteriores':historicos}}
    destino=EVID/'configuracao-final.json'
    if destino.exists():destino=EVID/'configuracao-iniciador.json'
    with destino.open('x',encoding='utf-8') as f:f.write(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'servicos_preservados':all(s['preservado'] for s in servicos),'volumes_preservados':config['preservacao']['volumes_anteriores_presentes'],'worktree_preservado':all(worktree.values()),'evidencias_preservadas':all(historicos.values()),'imagem':api['Image'],'modelo':modelo['tags']},ensure_ascii=True))


if __name__=='__main__':main()
