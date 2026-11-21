import assert from 'node:assert/strict';
import {test} from 'node:test';
import {projetarRelatorio} from '../src/interface/static/relatorio.mjs';

function documento(){
  const criterio={status:'aprovado',valor:true};
  const resultados=['Osasco','Campinas','Não é Osasco'].map((resposta,i)=>({id:String(i),cenario:'historico_completo',repeticao:1,resposta,
    julgamento:{tipo_resposta:'factual',passou:true,protocolo_ok:true,revisao_necessaria:false,acerto_factual:criterio,
      abstencao_correta:{status:'nao_aplicavel',valor:null},sem_informacao_proibida:criterio,formato_ok:criterio}}));
  return {resultados,resumo:{historico_completo:{casos:3,falhas:0}},
    comparacoes_tokens:{memoria_regras_api:{sessao:{tokens_total:{tokens_historico:100,tokens_cenario:20,pares_medidos:1}}}},
    analise_informacao_antiga:{versao:'informacao-antiga-v1',disponivel:true,cenarios:{historico_completo:{numerador:999}},
      resultados:resultados.map((q,i)=>({indice:i,id:q.id,cenario:q.cenario,repeticao:1,
        medida:{aplicavel:true,status:i===2?'nao_verificado':'verificado',retornou_antiga:i===2?null:i===0,motivo:'fixture'}}))}};
}
test('taxa de informação antiga é separada e recalculada com cobertura',()=>{
  const d=documento(),antes=JSON.stringify(d),r=projetarRelatorio(d),m=r.qualidade[0].informacaoAntiga;
  assert.equal(m.numerador,1);assert.equal(m.denominador,2);assert.equal(m.taxa_pct,50);
  assert.equal(m.tentativas_elegiveis,3);assert.equal(m.nao_verificados,1);
  assert.equal(r.qualidade[0].integrais,3);assert.equal(r.principal.memoria,20);
  assert.equal(JSON.stringify(d),antes);
  assert(r.perguntas[0].problemas.some(p=>/antiga devolvida/.test(p.rotulo)));
  assert(r.perguntas[2].problemas.some(p=>/antiga: análise inconclusiva/.test(p.rotulo)));
  assert.equal(r.objetivos.find(o=>o.nome.includes('Ausência de informação antiga')).estado,'Falhou nos critérios medidos');
});
test('sem anotação antiga não transforma não aplicável em zero por cento',()=>{
  const d=documento();d.analise_informacao_antiga.resultados.forEach(r=>r.medida={aplicavel:false,status:'nao_aplicavel',retornou_antiga:null});
  const r=projetarRelatorio(d);assert.equal(r.qualidade[0].informacaoAntiga.taxa_pct,null);
  assert.equal(r.objetivos.find(o=>o.nome.includes('Ausência de informação antiga')).estado,'Não aplicável');
});
test('análise ausente ou incompatível permanece inconclusiva',()=>{
  for(const alterar of [d=>delete d.analise_informacao_antiga,d=>d.analise_informacao_antiga.resultados[0].id='outro',d=>d.analise_informacao_antiga.resultados.push(d.analise_informacao_antiga.resultados[0])]){
    const d=documento();alterar(d);const r=projetarRelatorio(d);assert.equal(r.qualidade[0].informacaoAntiga,null);
    assert.equal(r.objetivos.find(o=>o.nome.includes('Ausência de informação antiga')).estado,'Inconclusivo');
  }
});
test('tentativa ausente com anotação conta na cobertura e não inventa resposta',()=>{
  const d=documento();d.analise_informacao_antiga.resultados.push({indice:null,id:'ausente',cenario:'historico_completo',repeticao:1,medida:{aplicavel:true,status:'nao_verificado',retornou_antiga:null}});
  const r=projetarRelatorio(d);assert.equal(r.qualidade[0].informacaoAntiga.tentativas_elegiveis,4);
  assert.equal(r.qualidade[0].informacaoAntiga.cobertura_pct,50);assert.equal(r.perguntas.length,3);
});
test('análise da API tem precedência e P6 mantém seus julgamentos',()=>{
  const d=documento();d.analise_tarefa={informacao_antiga:d.analise_informacao_antiga};delete d.analise_informacao_antiga;
  assert.equal(projetarRelatorio(d).qualidade[0].informacaoAntiga.numerador,1);
  d.sessoes=[];d.comparacoes_tokens={sessao:{}};
  d.resultados=d.resultados.map(q=>({...q,evento:{id:q.id,tipo:'pergunta',texto:'Qual cidade?'},resultado:{resposta:q.resposta}}));
  assert.equal(projetarRelatorio(d).qualidade[0].informacaoAntiga.numerador,1);
});
