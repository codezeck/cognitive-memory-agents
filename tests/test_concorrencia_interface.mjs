import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const fonte=readFileSync(new URL('../src/interface/static/app.mjs',import.meta.url),'utf8');
const pedido=fonte.slice(fonte.indexOf('async function requisicao('),fonte.indexOf('function travar('));
const importar=fonte.slice(fonte.indexOf('$("report-file").addEventListener("change",async()=>{'),fonte.indexOf('function atualizarBloqueio('));
const adiar=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};

test('401 antigo não desconecta perfil novo nem sessão posterior do mesmo perfil',async()=>{
  for(const usuarioNovo of ['perfil-b','perfil-a']){
    const resposta=adiar();let desconexoes=0,leituras=0;
    const contexto=vm.createContext({usuario:'perfil-a',conexaoVersao:1,DOMException,
      fetch:()=>resposta.promise,desconectar:()=>desconexoes++});
    vm.runInContext(pedido,contexto);const p=contexto.requisicao('/avaliacoes');
    contexto.usuario=usuarioNovo;contexto.conexaoVersao=2;
    resposta.resolve({status:401,ok:false,json:async()=>{leituras++;return {mensagem:'Acesso anterior'};}});
    await assert.rejects(p,e=>e.name==='AbortError');assert.equal(desconexoes,0);assert.equal(leituras,0);
  }
});

test('401 da conexão atual ainda exige novo acesso',async()=>{
  let desconexoes=0;
  const contexto=vm.createContext({usuario:'a',conexaoVersao:1,DOMException,
    fetch:async()=>({status:401,ok:false,json:async()=>({mensagem:'Entre novamente'})}),desconectar:()=>desconexoes++});
  vm.runInContext(pedido,contexto);
  await assert.rejects(contexto.requisicao('/avaliacoes'),/Entre novamente/);assert.equal(desconexoes,1);
});

function contextoImportacao(){
  const elementos={'report-file':{files:[],value:'arquivo'},'download-report':{},'evaluation-status':{}};
  let handler;const avisos=[],mostrados=[],postagens=[];
  elementos['report-file'].addEventListener=(_,fn)=>handler=fn;
  const ctx=vm.createContext({usuario:'a',aberturaVersao:0,$:id=>elementos[id],
    requisicao:async(...args)=>{postagens.push(args);return {disponivel:false};},
    mostrarRelatorio:doc=>mostrados.push(doc),aviso:t=>avisos.push(t)});
  vm.runInContext(importar,ctx);
  return {ctx,elementos,avisos,mostrados,postagens,abrir:()=>handler()};
}

test('leitura de arquivo anterior ao perfil atual não envia análise nem mostra resultado',async()=>{
  const x=contextoImportacao(),leitura=adiar();
  x.elementos['report-file'].files=[{name:'anterior.json',size:10,text:()=>leitura.promise}];
  const p=x.abrir();x.ctx.usuario='b';x.ctx.aberturaVersao++;
  leitura.resolve('{}');await p;
  assert.equal(x.postagens.length,0);assert.equal(x.mostrados.length,0);assert.equal(x.avisos.length,0);
});

test('falha de importação antiga não substitui aviso ou entrada da mais recente',async()=>{
  const x=contextoImportacao(),leitura=adiar();
  x.elementos['report-file'].files=[{name:'antigo.json',size:10,text:()=>leitura.promise}];
  const p=x.abrir();
  x.elementos['report-file'].files=[{name:'novo.json',size:10,text:async()=>'{}'}];
  await x.abrir();x.elementos['report-file'].value='seleção posterior';
  leitura.reject(Error('Erro do arquivo antigo'));await p;
  assert.equal(x.mostrados.length,1);assert.deepEqual(x.avisos,['']);
  assert.equal(x.elementos['report-file'].value,'seleção posterior');
});
