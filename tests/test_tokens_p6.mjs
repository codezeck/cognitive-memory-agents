import assert from 'node:assert/strict';
import {test} from 'node:test';
import {projetarRelatorio} from '../src/interface/static/relatorio.mjs';

function medida(entrada,saida,chamadas=1,locais=0){
  return {tokens_entrada:entrada,tokens_saida:saida,tokens_total:entrada+saida,tokens_total_observados:entrada+saida,
    metricas_completas:true,chamadas_modelo:chamadas,respostas_locais_confirmadas:locais,
    chamadas_previstas:chamadas+locais,chamadas_observadas:chamadas+locais};
}
function documento(){
  const sessoes=[];
  for(const cenario of ['historico_completo','memoria_automatica'])for(let usuario=1;usuario<=4;usuario++)for(let sessao=1;sessao<=5;sessao++){
    const automatico=cenario==='memoria_automatica';
    const ingestao=automatico?medida(0,0,0,2):medida(30,10,2);
    const perguntas=sessao===1?medida(0,0,0,0):medida(10,5);
    const total=medida(ingestao.tokens_entrada+perguntas.tokens_entrada,ingestao.tokens_saida+perguntas.tokens_saida,
      ingestao.chamadas_modelo+perguntas.chamadas_modelo,ingestao.respostas_locais_confirmadas);
    sessoes.push({cenario,usuario_id:'u0'+usuario,sessao,tokens:{ingestao,perguntas,sessao:total}});
  }
  return {sessoes,resultados:[],interface:{protocolo:'p6'},
    comparacoes_tokens:{sessao:{tokens_total:{tokens_historico:1040,tokens_automaticos:240,pares_medidos:20,pares_previstos:20}}}};
}
test('P6 usa as 20 sessões de cada cenário para mostrar custo ao lado da qualidade',()=>{
  const d=documento(),antes=JSON.stringify(d),r=projetarRelatorio(d);
  assert.equal(r.tokensCenarios.length,2);assert.equal(r.qualidade.length,2);
  const [h,a]=r.tokensCenarios;
  assert.equal(h.cenario,'historico_completo');assert.equal(h.total,1040);assert.equal(h.chamadas,56);
  assert.equal(a.cenario,'memoria_automatica');assert.equal(a.total,240);assert.equal(a.chamadas,16);
  assert.equal(a.medidos,20);assert.equal(a.previstos,20);assert.equal(a.unidade,'sessões');
  assert.equal(a.etapas.ingestao.tokens_total,0);assert.equal(a.etapas.pergunta_final.tokens_total,240);
  assert.equal(JSON.stringify(d),antes);
});
test('etapa P6 sem perguntas tem zero comprovado sem inventar operação local',()=>{
  const d=documento();d.sessoes.filter(s=>s.cenario==='memoria_automatica').forEach(s=>{
    s.tokens.ingestao=medida(0,0,0,0);s.tokens.perguntas=medida(0,0,0,0);s.tokens.sessao=medida(0,0,0,0);
  });
  const a=projetarRelatorio(d).tokensCenarios[1];assert.equal(a.total,0);assert.equal(a.medidos,20);
  assert.equal(a.locais,0);assert.equal(a.etapas.pergunta_final.tokens_total,0);
});
test('token ausente na P6 preserva subtotal e impede total completo',()=>{
  const d=documento();const s=d.sessoes[2];s.tokens.sessao={...s.tokens.sessao,metricas_completas:false,tokens_total:null,
    tokens_entrada:null,tokens_saida:null,tokens_total_observados:12};
  const h=projetarRelatorio(d).tokensCenarios[0];assert.equal(h.total,null);assert.equal(h.medidos,19);
  assert.equal(h.subtotal,1040-55+12);assert.equal(h.incompletos.length,1);
  assert.equal(h.incompletos[0].id,'u01/s3');
});
test('sessão P6 ausente não é substituída por soma pareada nem zero',()=>{
  const d=documento();d.sessoes.splice(0,1);
  const r=projetarRelatorio(d),h=r.tokensCenarios[0];assert.equal(h.total,null);assert.equal(h.previstos,20);
  assert.equal(h.medidos,19);assert.equal(h.subtotal,1000);
  assert.equal(r.principal.base,1040);
});
test('sessão duplicada não duplica consumo e mantém diagnóstico visível',()=>{
  const d=documento();d.sessoes.push(structuredClone(d.sessoes[0]));
  const h=projetarRelatorio(d).tokensCenarios[0];assert.equal(h.total,null);assert.equal(h.medidos,19);
  assert.equal(h.subtotal,1000);assert.equal(h.etapas.sessao.tokens_total,null);
  assert(h.incompletos.some(x=>/duplicado/.test(x.motivo)));
});
test('contagem zero sem prova da origem não é medição completa na P6',()=>{
  const d=documento();d.sessoes[0].tokens.sessao={metricas_completas:true,tokens_total:0,tokens_total_observados:0,chamadas_modelo:1};
  const h=projetarRelatorio(d).tokensCenarios[0];assert.equal(h.total,null);assert.equal(h.medidos,19);
});
test('frase P6 inconclusiva recebe explicação sem nova nota',()=>{
  const d=documento();const julgamento={tipo_resposta:'factual',passou:false,revisao_necessaria:true,
    acerto_factual:{status:'nao_verificado',valor:null,motivo:'parafrase_nao_reconhecida'}};
  d.resultados=[{cenario:'historico_completo',evento:{tipo:'pergunta',id:'u01/s2/pergunta1',texto:'Onde moro?'},
    resultado:{resposta:'Sua memória registra que você mora em Osasco.'},julgamento}];
  const antes=JSON.stringify(d),r=projetarRelatorio(d);
  assert.match(r.perguntas[0].notaAvaliacao,/não confirma acerto nem erro/);
  assert.equal(r.qualidade[0].factual.pendentes,1);assert.equal(r.qualidade[0].factual.aprovados,0);
  assert.equal(r.perguntas[0].julgamento,julgamento);assert.equal(JSON.stringify(d),antes);
});
