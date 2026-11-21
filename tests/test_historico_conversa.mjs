import {test} from 'node:test';
import assert from 'node:assert/strict';
import {criarHistorico} from '../src/interface/static/historico-conversa.mjs';
import {confirmarExclusao} from '../src/interface/static/confirmacao.mjs';
const storage=()=>{const dados=new Map();return {getItem:k=>dados.get(k),setItem:(k,v)=>dados.set(k,v),removeItem:k=>dados.delete(k)};};
test('mensagens são separadas por perfil e sobrevivem ao recarregamento',()=>{
 const s=storage(),h=criarHistorico(s);h.adicionar('a','Você','Moro em Pernambuco');h.adicionar('a','Agente','Registrado',['cidade']);
 assert.deepEqual(h.ler('b'),[]);h.adicionar('b','Você','Outra conversa');
 const novo=criarHistorico(s);assert.equal(novo.ler('a')[0].texto,'Moro em Pernambuco');assert.equal(novo.ler('b')[0].texto,'Outra conversa');
 novo.limpar('a');assert.deepEqual(criarHistorico(s).ler('a'),[]);assert.equal(criarHistorico(s).ler('b').length,1);
});
test('armazenamento bloqueado usa memória temporária sem interromper a conversa',()=>{
 const h=criarHistorico({getItem(){throw Error();},setItem(){throw Error();},removeItem(){throw Error();}});
 h.adicionar('a','Você','oi');assert.equal(h.ler('a').length,1);h.limpar('a');assert.deepEqual(h.ler('a'),[]);
});
test('dados inválidos são ignorados e o histórico tem limite',()=>{
 const s=storage();s.setItem('cma-conversa-v1:a','{');const h=criarHistorico(s);assert.deepEqual(h.ler('a'),[]);
 for(let i=0;i<505;i++)h.adicionar('a','Você',String(i));assert.equal(h.ler('a').length,500);assert.equal(h.ler('a')[0].texto,'5');
 const copia=h.ler('a');copia[0].texto='alterado';assert.equal(h.ler('a')[0].texto,'5');
});
test('conteúdo parecido com código é preservado como texto',()=>{
 const h=criarHistorico(storage()),texto='<script>alert(1)</script> SELECT * FROM memorias';h.adicionar('a','Você',texto);assert.equal(h.ler('a')[0].texto,texto);
});
function modal(){const eventos=new Map(),campos={};let focou=false;
 const d={open:false,returnValue:'apagar',addEventListener:(n,f)=>eventos.set(n,f),removeEventListener:n=>eventos.delete(n),showModal(){this.open=true;},close(v){if(v!==undefined)this.returnValue=v;this.open=false;const f=eventos.get('close');eventos.delete('close');f?.();}};
 campos['delete-confirmation']=d;campos['delete-confirm-title']={};campos['delete-confirm-description']={};campos['delete-confirm-cancel']={focus(){focou=true;}};
 return {d,doc:{getElementById:id=>campos[id]},focou:()=>focou,eventos};}
test('exclusão só é autorizada após confirmação explícita; Escape cancela',async()=>{
 const a=modal(),dados={titulo:'Apagar?',descricao:'Somente este perfil'};let p=confirmarExclusao(dados,a.doc);assert.equal(a.focou(),true);a.d.close();assert.equal(await p,false);
 p=confirmarExclusao(dados,a.doc);assert.equal(await confirmarExclusao(dados,a.doc),false);a.d.close('apagar');assert.equal(await p,true);assert.equal(a.eventos.size,0);
 p=confirmarExclusao(dados,a.doc);a.d.close('cancelar');assert.equal(await p,false);
});
test('ausência ou falha do modal nunca autoriza exclusão',async()=>{
 assert.equal(await confirmarExclusao({}, {getElementById:()=>null}),false);const a=modal();a.d.showModal=()=>{throw Error('falha');};await assert.rejects(confirmarExclusao({},a.doc));assert.equal(a.eventos.size,0);
});
