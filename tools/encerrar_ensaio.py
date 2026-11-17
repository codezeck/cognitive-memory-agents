"""Encerra somente o projeto fixo do ensaio, sem remover volumes."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PASTA=ROOT/'evidencias/entrega/20261114-entrega-ae9eb113'
PROJETO='cma-entrega-ae9eb113'


def docker(*args):return subprocess.check_output(['docker',*args],encoding='utf-8')


def main():
    snapshot=json.loads((ROOT/'.env.20261114-entrega-ae9eb113-recursos.json').read_text(encoding='utf-8-sig'))
    inicial=json.loads((ROOT/'.env.20261114-entrega-ae9eb113-preservacao.json').read_text(encoding='utf-8-sig'))
    ids=docker('ps','-aq','--filter',f'label=com.docker.compose.project={PROJETO}').split()
    for uid in ids:
        c=json.loads(docker('inspect',uid))[0]
        assert c['Config']['Labels']['com.docker.compose.project']==PROJETO
        servico=c['Config']['Labels']['com.docker.compose.service']
        assert servico in ('api','preparar','ollama')
        with (PASTA/f'final-{servico}.log').open('x',encoding='utf-8') as f:
            subprocess.run(['docker','logs','--timestamps',uid],stdout=f,stderr=subprocess.STDOUT,check=True)
    saida=subprocess.run(['docker','compose','--env-file','.env.example','-p',PROJETO,'down'],capture_output=True,text=True,encoding='utf-8',check=True)
    (PASTA/'encerramento-compose.log').write_text(saida.stdout+saida.stderr,encoding='utf-8')
    volumes=docker('volume','ls','--format','{{.Name}}').splitlines()
    servicos=[]
    for s in snapshot['containers']:
        atual=json.loads(docker('inspect',s['id']))[0]
        servicos.append({'id':s['id'],'nome':s['nome'],'estado':atual['State']['Status'],'started_at':atual['State']['StartedAt'],'preservado':atual['State']['StartedAt']==s['iniciado_em']})
    fonte=Path('C:/Users/silva/.codex/worktrees/interface-instalacao/cognitive-memory-agents')
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    worktree={p:sha(fonte/p)==h for p,h in inicial['interface'].items()}
    brutos={p:sha(ROOT/p)==h for p,h in inicial['root'].items() if p.startswith('evidencias/') and not p.endswith('.md')}
    historicos={p:sha(ROOT/p) for p in ('evidencias/comparativo_oficial_3rep.json','evidencias/agente/validacao-docker-20261114-07701ee5.jsonl','evidencias/agente/validacao-docker-20261114-07701ee5-api.log','evidencias/agente/validacao-docker-20261114-07701ee5-encerramento.json')}
    registro={'instante_utc':datetime.now(timezone.utc).isoformat(),'projeto_encerrado':PROJETO,'sem_remocao_volumes':True,
              'containers_ensaio_restantes':docker('ps','-aq','--filter',f'label=com.docker.compose.project={PROJETO}').split(),
              'servicos_anteriores':servicos,'volumes_anteriores_presentes':all(v in volumes for v in snapshot['volumes']),
              'volumes_ensaio_preservados':[v for v in volumes if v.startswith(PROJETO+'_')],
              'worktree_origem_preservado':all(worktree.values()),'arquivos_brutos_anteriores_preservados':all(brutos.values()),
              'hashes_brutos_anteriores':historicos,'indice_evidencias_atualizado_intencionalmente':True,'p6_executada':False,'reservado_executado':False}
    with (PASTA/'encerramento-final.json').open('x',encoding='utf-8') as f:json.dump(registro,f,ensure_ascii=False,indent=2)
    assert all(s['preservado'] for s in servicos) and registro['volumes_anteriores_presentes'] and all(worktree.values()) and all(brutos.values())
    print(json.dumps({k:v for k,v in registro.items() if k not in ('hashes_brutos_anteriores','servicos_anteriores')}))


if __name__=='__main__':main()
