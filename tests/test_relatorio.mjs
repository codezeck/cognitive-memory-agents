import assert from "node:assert/strict";
import {test} from "node:test";
import {medida,projetarRelatorio,usoResposta} from "../src/interface/static/relatorio.mjs";

test("zero local exige origem e contagem explicitas",()=>{
  assert.deepEqual(usoResposta({tokens_entrada:null,tokens_saida:null,origem_uso:"politica_local",chamadas_modelo_observadas:0}),
    {local:true,entrada:0,saida:0,total:0});
  assert.equal(usoResposta({tokens_entrada:null,tokens_saida:null}).total,null);
  assert.equal(usoResposta({tokens_entrada:0,tokens_saida:0,origem_uso:"provedor",chamadas_modelo_observadas:1}).total,null);
});

test("texto DESCONHECIDO do provedor nao altera sua contagem",()=>{
  const r=usoResposta({resposta:"DESCONHECIDO",tokens_entrada:20,tokens_saida:3,origem_uso:"provedor",chamadas_modelo_observadas:1});
  assert.equal(r.local,false);assert.equal(r.total,23);
});

test("ausência de contagem não vira zero nem economia",()=>{
  const m=medida({tokens_historico:100,tokens_cenario:null,pares_medidos:1});
  assert.equal(m.medido,false);assert.equal(m.reducao,null);
});
test("redução é recalculada das somas, sem confiar em porcentagem fornecida",()=>{
  const m=medida({tokens_historico:100,tokens_cenario:150,pares_medidos:2,reducao_pct:99});
  assert.equal(m.reducao,-50);assert.equal(m.memoria,150);
});
test("sem pares ou denominador não há porcentagem",()=>{
  assert.equal(medida({tokens_historico:100,tokens_cenario:50,pares_medidos:0}).reducao,null);
  assert.equal(medida({tokens_historico:0,tokens_cenario:0,pares_medidos:1}).reducao,null);
});
test("relatórios legados não produzem comparações inventadas",()=>{
  assert.throws(()=>projetarRelatorio({resumo:{historico_completo:{tokens_total:100}}}));
});
test("sessão é indicador principal, cobertura e qualidade preservadas",()=>{
  const r=projetarRelatorio({comparacoes_tokens:{memoria_regras_api:{
    sessao:{tokens_total:{tokens_historico:200,tokens_cenario:120,pares_medidos:2,pares_sem_medicao:1,chaves_duplicadas_descartadas:0}},
    pergunta_final:{tokens_total:{tokens_historico:100,tokens_cenario:20,pares_medidos:3}}
  }},resumo:{historico_completo:{aprovados:1,casos:3,falhas:1},memoria_regras_api:{aprovados:2,casos:3,falhas:0}}});
  assert.equal(r.principal.reducao,40);assert.equal(r.principal.ausentes,1);
  assert.equal(r.qualidade[0].casos,3);assert.equal(r.qualidade[0].falhas,1);
  assert.equal(r.linhas.length,9);
});
test("contagens não finitas ou negativas são desconhecidas",()=>{
  for(const base of [Infinity,NaN,-2,"100"])
    assert.equal(medida({tokens_historico:base,tokens_cenario:1,pares_medidos:1}).medido,false);
});
