import assert from 'node:assert/strict';
import {test} from 'node:test';
import {projetarRelatorio} from '../src/interface/static/relatorio.mjs';

const criterio=(status,valor,motivo='teste')=>({status,valor,motivo});
function julgamento(aprovado){return {versao:'p6-conteudo-v1',tipo_resposta:'factual',
  acerto_factual:criterio(aprovado?'aprovado':'nao_verificado',aprovado?true:null),
  abstencao_correta:criterio('nao_aplicavel',null),sem_informacao_proibida:criterio('aprovado',true),
  formato_ok:criterio('reprovado',false),passou:aprovado,protocolo_ok:false,revisao_necessaria:!aprovado};}
function documento(){
  const original=julgamento(false);original.versao='p4-v3';
  const d={sessoes:[],comparacoes_tokens:{sessao:{tokens_total:{tokens_historico:200,tokens_automaticos:50,pares_medidos:20}}},
    perguntas_previstas_por_cenario:1,resultados:[
      {cenario:'historico_completo',evento:{id:'u1/s1/f1',tipo:'fato',texto:'Moro em Jundiaí.'}},
      ...['historico_completo','memoria_automatica'].map(cenario=>({cenario,estado:'concluido',trajetoria_integra:true,
        evento:{id:'u1/s2/p1',tipo:'pergunta',texto:'Onde eu moro?'},resultado:{resposta:'Hoje você mora em Jundiaí.'},julgamento:structuredClone(original)}))]};
  d.analise_tarefa={disponivel:true,versao:'tarefa-p6-conteudo-v1',resultados:d.resultados.slice(1).map((q,i)=>({
    indice:i+1,id:q.evento.id,cenario:q.cenario,repeticao:1,esperado:'Jundiaí',julgamento:julgamento(true)}))};
  return d;
}
test('P6 usa a análise versionada nos dois cenários e conserva originais e tokens',()=>{
  const d=documento(),antes=JSON.stringify(d),original=structuredClone(d);delete original.analise_tarefa;
  const r=projetarRelatorio(d);
  assert(r.tarefaComum);assert(r.qualidade.every(q=>q.factual.aprovados===1&&q.integrais===0));
  assert(r.perguntas.every(q=>q.julgamentoOriginal.versao==='p4-v3'&&q.julgamento.versao==='p6-conteudo-v1'));
  assert.deepEqual(r.principal,projetarRelatorio(original).principal);
  assert.deepEqual(r.tokensCenarios,projetarRelatorio(original).tokensCenarios);
  assert.equal(JSON.stringify(d),antes);
});
for(const mudanca of ['versao','id','cenario','indice','duplicado','ausente','criterio','trajetoria'])test('P6 rejeita análise incompatível: '+mudanca,()=>{
  const d=documento(),a=d.analise_tarefa;
  if(mudanca==='versao')a.versao='inexistente';
  if(mudanca==='id')a.resultados[0].id='outro';
  if(mudanca==='cenario')a.resultados[0].cenario='sem_memoria';
  if(mudanca==='indice')a.resultados[0].indice=0;
  if(mudanca==='duplicado')a.resultados[1]=structuredClone(a.resultados[0]);
  if(mudanca==='ausente')a.resultados.pop();
  if(mudanca==='criterio')a.resultados[0].julgamento.acerto_factual.valor=false;
  if(mudanca==='trajetoria')d.resultados[1].trajetoria_integra=false;
  const r=projetarRelatorio(d);assert.equal(r.tarefaComum,false);assert.equal(r.qualidade[0].factual.aprovados,0);
});

for(const versao of ['v1','v2'])test('P6 identifica a versão da leitura '+versao,()=>{
  const d=documento();d.analise_tarefa.versao='tarefa-p6-conteudo-'+versao;
  d.analise_tarefa.resultados.forEach(r=>r.julgamento.versao='p6-conteudo-'+versao);
  const r=projetarRelatorio(d);assert(r.tarefaComum);assert.equal(r.analiseConteudo,versao);
});
test('P6 não mistura versões do julgador na mesma análise',()=>{
  const d=documento();d.analise_tarefa.versao='tarefa-p6-conteudo-v2';
  assert.equal(projetarRelatorio(d).tarefaComum,false);
});
