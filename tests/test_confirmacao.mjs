import assert from 'node:assert/strict';
import {test} from 'node:test';
import {confirmarAvaliacao} from '../src/interface/static/confirmacao.mjs';

function ambiente(){
  const elementos=Object.fromEntries(['evaluation-confirm-protocol','evaluation-confirm-quantity','evaluation-confirm-model'].map(id=>[id,{textContent:''}]));
  let foco=false;
  elementos['evaluation-confirm-cancel']={focus(){foco=true;}};
  const listeners=new Map();
  const dialogo={open:false,returnValue:'iniciar',
    addEventListener:(nome,fn)=>listeners.set(nome,fn),removeEventListener:nome=>listeners.delete(nome),
    showModal(){this.open=true;},
    fechar(valor){if(valor!==undefined)this.returnValue=valor;this.open=false;const fn=listeners.get('close');listeners.delete('close');fn?.();}};
  elementos['evaluation-confirmation']=dialogo;
  return {documento:{getElementById:id=>elementos[id]},elementos,dialogo,listeners,foco:()=>foco};
}
const rodada={protocolo:'Comparativo sintético v3',quantidade:'192 tentativas',modelo:'modelo-local'};

test('resumo é texto e cancelar recebe foco por padrão',async()=>{
  const a=ambiente(),p=confirmarAvaliacao(rodada,a.documento);
  assert.equal(a.dialogo.open,true);assert.equal(a.foco(),true);
  assert.equal(a.elementos['evaluation-confirm-quantity'].textContent,'192 tentativas');
  assert.equal(a.dialogo.returnValue,'cancelar');a.dialogo.fechar('cancelar');assert.equal(await p,false);
});
test('somente confirmação explícita autoriza o fluxo seguinte',async()=>{
  const a=ambiente(),p=confirmarAvaliacao(rodada,a.documento);a.dialogo.fechar('iniciar');assert.equal(await p,true);
  assert.equal(a.listeners.size,0);
});
test('Escape ou fechar sem valor não reutiliza uma confirmação anterior',async()=>{
  const a=ambiente();let p=confirmarAvaliacao(rodada,a.documento);a.dialogo.fechar('iniciar');assert.equal(await p,true);
  p=confirmarAvaliacao(rodada,a.documento);a.dialogo.fechar();assert.equal(await p,false);
});
test('segunda abertura não cria confirmação duplicada',async()=>{
  const a=ambiente(),p=confirmarAvaliacao(rodada,a.documento);
  assert.equal(await confirmarAvaliacao(rodada,a.documento),false);
  a.dialogo.fechar('cancelar');assert.equal(await p,false);
});
test('dialogo indisponível ou com erro não autoriza execução',async()=>{
  assert.equal(await confirmarAvaliacao(rodada,{getElementById:()=>null}),false);
  const a=ambiente();a.dialogo.showModal=()=>{throw Error('indisponível');};
  await assert.rejects(confirmarAvaliacao(rodada,a.documento),/indisponível/);assert.equal(a.listeners.size,0);
});
