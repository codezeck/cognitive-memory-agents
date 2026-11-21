import assert from "node:assert/strict";
import {test} from "node:test";
import {instalarAparencia} from "../src/interface/static/aparencia.mjs";

function ambiente(valor=null){
  const listeners=new Set(),valores=new Map(valor===null?[]:[["cma-aparencia",valor]]);
  const seletor={atributos:{},setAttribute(nome,valor){this.atributos[nome]=valor;},addEventListener:(nome,fn)=>listeners.add(fn),removeEventListener:(nome,fn)=>listeners.delete(fn),
    mudar(){for(const fn of listeners)fn();}};
  const documento={documentElement:{dataset:{}},getElementById:id=>id==="appearance-theme"?seletor:null};
  const armazenamento={getItem:chave=>valores.get(chave)??null,setItem:(chave,texto)=>valores.set(chave,texto)};
  return {documento,seletor,armazenamento,valores,listeners};
}

test("Caderno inicia escuro e salva somente o tema no navegador",()=>{
  const a=ambiente();instalarAparencia(a.documento,a.armazenamento);
  assert.equal(a.documento.documentElement.dataset.tema,"escuro");assert.equal(a.seletor.atributos["aria-label"],"Ativar modo claro");assert.equal(a.seletor.atributos["aria-pressed"],"true");
  assert.deepEqual(JSON.parse(a.valores.get("cma-aparencia")),{tema:"escuro"});
});
test("recupera escuro no carregamento e persiste a troca para claro",()=>{
  const a=ambiente('{"tema":"escuro"}');instalarAparencia(a.documento,a.armazenamento);
  assert.equal(a.documento.documentElement.dataset.tema,"escuro");assert.equal(a.seletor.atributos["aria-label"],"Ativar modo claro");assert.equal(a.seletor.atributos["aria-pressed"],"true");
  a.seletor.mudar("claro");assert.equal(a.documento.documentElement.dataset.tema,"claro");
  assert.deepEqual(JSON.parse(a.valores.get("cma-aparencia")),{tema:"claro"});
  const b=ambiente(a.valores.get("cma-aparencia"));instalarAparencia(b.documento,b.armazenamento);
  assert.equal(b.documento.documentElement.dataset.tema,"claro");
});
test("migra a preferência antiga sem preservar acento ou outros campos",()=>{
  const a=ambiente('{"tema":"escuro","acento":"verde","extra":"ignorar"}');
  a.documento.documentElement.dataset.acento="verde";instalarAparencia(a.documento,a.armazenamento);
  assert.equal(a.documento.documentElement.dataset.tema,"escuro");
  assert.equal("acento" in a.documento.documentElement.dataset,false);
  assert.deepEqual(JSON.parse(a.valores.get("cma-aparencia")),{tema:"escuro"});
});
test("valores desconhecidos e JSON inválido voltam ao tema escuro",()=>{
  for(const valor of ['{invalido','null','[]','"claro"','42','{"tema":"outro"}','{"tema":{}}','{"acento":"ciano"}']){
    const a=ambiente(valor);instalarAparencia(a.documento,a.armazenamento);
    assert.equal(a.documento.documentElement.dataset.tema,"escuro");
    assert.deepEqual(JSON.parse(a.valores.get("cma-aparencia")),{tema:"escuro"});
  }
});
test("falha ao ler ou salvar não bloqueia a aparência nem o botão",()=>{
  const a=ambiente(),armazenamento={getItem(){throw Error("leitura indisponível");},setItem(){throw Error("gravação indisponível");}};
  assert.doesNotThrow(()=>instalarAparencia(a.documento,armazenamento));
  assert.equal(a.documento.documentElement.dataset.tema,"escuro");
  assert.doesNotThrow(()=>a.seletor.mudar("claro"));assert.equal(a.documento.documentElement.dataset.tema,"claro");
});
test("acesso negado à propriedade localStorage também é tolerado",()=>{
  const anterior=Object.getOwnPropertyDescriptor(globalThis,"localStorage");
  Object.defineProperty(globalThis,"localStorage",{configurable:true,get(){throw Error("acesso negado");}});
  try{
    const a=ambiente();assert.doesNotThrow(()=>instalarAparencia(a.documento));
    a.seletor.mudar("claro");assert.equal(a.documento.documentElement.dataset.tema,"claro");
  }finally{
    if(anterior)Object.defineProperty(globalThis,"localStorage",anterior);else delete globalThis.localStorage;
  }
});
test("botão de lua alterna com clique e mantém estado acessível",()=>{
  const a=ambiente();instalarAparencia(a.documento,a.armazenamento);
  a.seletor.mudar();assert.equal(a.documento.documentElement.dataset.tema,"claro");
  assert.equal(a.seletor.atributos["aria-pressed"],"false");assert.equal(a.seletor.atributos["aria-label"],"Ativar modo escuro");
  a.seletor.mudar();assert.equal(a.documento.documentElement.dataset.tema,"escuro");
  assert.equal(a.seletor.atributos["aria-pressed"],"true");assert.equal(a.seletor.atributos.title,"Ativar modo claro");
});

test("documento sem botão ainda aplica o tema e permite remover listeners",()=>{
  const a=ambiente('{"tema":"escuro"}');a.documento.getElementById=()=>null;
  const remover=instalarAparencia(a.documento,a.armazenamento);assert.equal(a.documento.documentElement.dataset.tema,"escuro");
  assert.doesNotThrow(remover);assert.doesNotThrow(()=>instalarAparencia(null,null));
  const b=ambiente();const parar=instalarAparencia(b.documento,b.armazenamento);
  assert.equal(b.listeners.size,1);parar();assert.equal(b.listeners.size,0);
});
