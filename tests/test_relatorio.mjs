import assert from "node:assert/strict";
import {test} from "node:test";
import {medida,projetarRelatorio,usoResposta,distribuicaoCriterio} from "../src/interface/static/relatorio.mjs";
import {bloqueioAvaliacao} from "../src/interface/static/avaliacao.mjs";

test("timeout mostra causa e soma parcelas de turnos sem declarar total completo",()=>{
  const bom=respostaTeste("A"),falho=respostaTeste("B","factual","nao_verificado");
  bom.tokens_por_etapa={sessao:{tokens_total:20,tokens_total_observados:20,metricas_completas:true,chamadas_modelo:1}};
  falho.repeticao=3;falho.erro="Erro no processo de histórico (ProvedorTimeout): O modelo demorou demais para responder.";
  falho.tokens_por_etapa={sessao:{tokens_total:null,tokens_total_observados:28,metricas_completas:false,chamadas_modelo:null,chamadas_previstas:3,chamadas_observadas:2}};
  const doc=documentoTeste([bom,falho]),antes=JSON.stringify(doc),r=projetarRelatorio(doc),t=r.tokensCenarios[0];
  assert.equal(t.medidos,1);assert.equal(t.previstos,2);assert.equal(t.total,null);assert.equal(t.subtotal,48);
  assert.equal(t.incompletos.length,1);assert.equal(t.incompletos[0].id,"B");assert.equal(t.incompletos[0].repeticao,3);
  assert.match(t.incompletos[0].motivo,/tempo limite/);assert.equal(t.incompletos[0].turnosObservados,2);
  assert.match(r.aviso,/falhas técnicas/);assert.equal(JSON.stringify(doc),antes);
});
test("ausência total de tokens mantém subtotal desconhecido em vez de zero",()=>{
  const q=respostaTeste("A");q.tokens_por_etapa={sessao:{tokens_total:null,tokens_total_observados:null,metricas_completas:false}};
  const t=projetarRelatorio(documentoTeste([q])).tokensCenarios[0];
  assert.equal(t.total,null);assert.equal(t.subtotal,null);
  assert.match(t.incompletos[0].motivo,/ausente ou inválida/);
});

test("controle direto e controle via API têm identificação distinta sem alterar julgamento",()=>{
  const q=respostaTeste("A");q.cenario="sem_memoria";q.via="ollama_direto";
  q.chamadas_modelo=1;q.tokens_por_etapa={sessao:{metricas_completas:true,tokens_total:25}};
  const doc=documentoTeste([q]),antes=JSON.stringify(doc),r=projetarRelatorio(doc);
  assert.equal(r.controleSemMemoria,"modelo_direto");
  assert.equal(r.qualidade[0].factual.aprovados,1);
  assert.equal(r.tokensCenarios[0].total,25);
  assert.equal(JSON.stringify(doc),antes);
  assert.notEqual(r.objetivos.find(o=>o.nome==="Sem memória · Recuperação factual").estado,"Não aplicável");
  q.via="api";
  assert.equal(projetarRelatorio(doc).controleSemMemoria,"api_local");
  delete q.via;
  assert.equal(projetarRelatorio(doc).controleSemMemoria,"nao_identificado");
});

test("falha do controle direto mantém consumo desconhecido e ocorrência técnica",()=>{
  const q=respostaTeste("A","factual","nao_verificado");q.cenario="sem_memoria";q.via="ollama_direto";
  q.erro="Tempo do provedor excedido";q.resposta=null;q.chamadas_modelo=null;
  q.tokens_por_etapa={sessao:{metricas_completas:false,tokens_total:null}};
  const r=projetarRelatorio(documentoTeste([q]));
  assert.equal(r.tokensCenarios[0].total,null);
  assert.equal(r.tokensCenarios[0].chamadas,null);
  assert.equal(r.qualidade[0].integrais,0);
  assert(r.ocorrencias[0].problemas.some(p=>p.tipo==="tecnica"));
});

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
  assert.equal(medida(null).reducao,null);assert.equal(medida(undefined).base,null);
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

test("bloqueio explica configuração, modelo ausente, modo falso e concorrência",()=>{
  const base={usuario:"demo",dados:{comparativo_liberado:true,ollama:"disponivel",modelos_instalados:["local"]},modelo:{provedor:"ollama",modelo:"local"}};
  assert.equal(bloqueioAvaliacao(base),null);
  assert.match(bloqueioAvaliacao({...base,executando:true}),/andamento/);
  assert.match(bloqueioAvaliacao({...base,simulado:true}),/simulado/);
  assert.match(bloqueioAvaliacao({...base,dados:{...base.dados,comparativo_liberado:false}}),/desativadas/);
  assert.match(bloqueioAvaliacao({...base,modelo:{provedor:"openai"}}),/pagas/);
  assert.match(bloqueioAvaliacao({...base,dados:{...base.dados,modelos_instalados:[]}}),/não está instalado/);
});

test("P6 mostra pares, não verificados e checkpoints sem inferir sucesso",()=>{
  const m={tokens_historico:200,tokens_automaticos:100,pares_medidos:2,pares_sem_medicao:1};
  const r=projetarRelatorio({sessoes:[],estado_orquestracao:"incompleta",comparacoes_tokens:{sessao:{tokens_total:m}},
    perguntas_previstas_por_cenario:21,resultados:[{cenario:"memoria_automatica",evento:{tipo:"pergunta",id:"u/s1/p",texto:"Onde moro?"},resultado:{resposta:"DESCONHECIDO"},julgamento:{passou:false,revisao_necessaria:true}}],
    metricas_checkpoints:{memoria_automatica:{checkpoint_exclusao:{denominador:1,numerador:0,nao_verificados:1,cobertura_pct:50}}}});
  assert.equal(r.principal.reducao,50);assert.equal(r.principal.ausentes,1);
  assert.equal(r.qualidade[1].pendentes,21);assert.match(r.aviso,/incompleta/);
  assert.equal(r.perguntas[0].pergunta,"Onde moro?");
  assert.equal(r.objetivos.find(o=>o.nome.includes("Persistência")).estado,"Inconclusivo");
  assert.equal(r.objetivos.find(o=>o.nome.includes("Exclusão no")).estado,"Falhou nos critérios medidos");
});

test("relatório próprio conserva origem e nunca declara persistência de casos",()=>{
  const doc={interface:{conjunto:"próprio",casos:[{id:"X",mensagens:["Fato","Pergunta?"]}]},resumo:{memoria_regras_api:{casos:1,falhas:1}},
    comparacoes_tokens:{memoria_regras_api:{sessao:{tokens_total:{tokens_historico:null,tokens_cenario:null,pares_medidos:0}}}},
    resultados:[{id:"X",cenario:"memoria_regras_api",resposta:"sem resultado",julgamento:{revisao_necessaria:true}}]};
  const r=projetarRelatorio(JSON.parse(JSON.stringify(doc)));
  assert.equal(r.conjunto,"próprio");assert.equal(r.principal.reducao,null);
  assert.equal(r.perguntas[0].pergunta,"Pergunta?");
  assert.equal(r.objetivos.find(o=>o.nome==="Persistência após reinício").estado,"Inconclusivo");
});

const criterio=(status,valor)=>({status,valor,motivo:"fixture"});
function respostaTeste(id,tipo="factual",status="aprovado",resposta="Fortaleza"){
  const factual=tipo==="factual";
  const j={tipo_resposta:tipo,passou:status==="aprovado",protocolo_ok:status==="aprovado",revisao_necessaria:status==="nao_verificado",
    acerto_factual:criterio(factual?status:"nao_aplicavel",factual?(status==="aprovado"?true:status==="reprovado"?false:null):null),
    abstencao_correta:criterio(factual?"nao_aplicavel":status,factual?null:status==="aprovado"?true:status==="reprovado"?false:null),
    sem_informacao_proibida:criterio("aprovado",true),formato_ok:criterio("aprovado",true)};
  return {id,cenario:"historico_completo",categoria:"atualizacao",repeticao:2,resposta,julgamento:j};
}
function documentoTeste(resultados){
  return {interface:{casos:[{id:"A",mensagens:["Torço pelo Fortaleza.","Qual time?"],esperado:"Fortaleza"}]},
    comparacoes_tokens:{memoria_regras_api:{sessao:{tokens_total:{tokens_historico:100,tokens_cenario:40,pares_medidos:1}}}},
    resumo:Object.fromEntries([...new Set(resultados.map(r=>r.cenario))].map(c=>[c,{casos:resultados.filter(r=>r.cenario===c).length,falhas:0}])),resultados};
}
test("fatos, abstenções, erros e pendências têm denominadores separados",()=>{
  const doc=documentoTeste([respostaTeste("A"),respostaTeste("B","factual","reprovado","DESCONHECIDO"),
    respostaTeste("C","factual","reprovado","Outro"),respostaTeste("D","factual","nao_verificado","Fortaleza Estadual"),
    respostaTeste("E","abstencao","aprovado","DESCONHECIDO")]);
  const antes=JSON.stringify(doc),r=projetarRelatorio(doc),q=r.qualidade[0];
  assert.deepEqual([q.factual.aprovados,q.factual.total,q.factual.reprovados,q.factual.pendentes],[1,4,2,1]);
  assert.deepEqual([q.abstencao.aprovados,q.abstencao.total],[1,1]);
  assert.equal(q.abstencoesIndevidas,1);assert.equal(q.integrais,2);
  assert.equal(r.ocorrencias.length,3);assert.equal(r.perguntas[0].repeticao,2);assert.equal(r.perguntas[0].esperado,"Fortaleza");
  assert.match(r.ocorrencias[0].problemas[0].rotulo,/Abstenção indevida/);
  assert.equal(JSON.stringify(doc),antes);
});
test("conteúdo aprovado com formato reprovado não vira aprovação integral",()=>{
  const q=respostaTeste("A");q.resposta="Fortaleza.";q.julgamento.formato_ok=criterio("reprovado",false);q.julgamento.protocolo_ok=false;
  const r=projetarRelatorio(documentoTeste([q]));
  assert.equal(r.qualidade[0].factual.aprovados,1);assert.equal(r.qualidade[0].integrais,0);
  assert.equal(r.qualidade[0].formato.reprovados,1);assert.equal(r.ocorrencias[0].problemas[0].tipo,"formato");
});
test("controle sem memória não exibe nove não aplicáveis como pendências",()=>{
  const qs=Array.from({length:9},(_,i)=>({...respostaTeste(String(i),"abstencao","aprovado","DESCONHECIDO"),cenario:"sem_memoria"}));
  const r=projetarRelatorio(documentoTeste(qs)),q=r.qualidade[0];
  assert.equal(q.factual.total,0);assert.equal(q.factual.naoAplicaveis,9);assert.equal(q.factual.pendentes,0);
  assert.equal(q.abstencao.aprovados,9);assert.equal(q.integrais,9);
  const objetivo=r.objetivos.find(o=>o.nome.includes("Atualização"));
  assert.equal(objetivo.estado,"Não aplicável");assert.doesNotMatch(objetivo.detalhe,/não verificados/);
});
test("aprovação agregada não esconde um critério pendente ou ausente",()=>{
  const q=respostaTeste("A");q.julgamento.formato_ok=criterio("nao_verificado",null);
  const r=projetarRelatorio(documentoTeste([q]));
  assert.equal(r.qualidade[0].integrais,0);assert.equal(r.qualidade[0].formato.pendentes,1);
  assert.equal(r.ocorrencias[0].problemas[0].tipo,"pendente");
  delete q.julgamento.formato_ok;
  assert.equal(projetarRelatorio(documentoTeste([q])).qualidade[0].integrais,0);
});
test("dados ausentes não se tornam fatos corretos a partir do resumo",()=>{
  const doc=documentoTeste([respostaTeste("A")]);doc.resultados=[];doc.resumo.historico_completo.aprovados=1;
  const q=projetarRelatorio(doc).qualidade[0];
  assert.equal(q.observados,0);assert.equal(q.factual.aprovados,0);assert.equal(q.integrais,0);assert.equal(q.ausentes,1);
});
test("falhas operacionais P6 aparecem nas ocorrências sem inflar perguntas",()=>{
  const doc={sessoes:[],comparacoes_tokens:{sessao:{}},perguntas_previstas_por_cenario:21,
    resultados:[{cenario:"historico_completo",evento:{id:"u/s1/fato",tipo:"fato",texto:"Moro aqui"},estado:"erro",erro:{mensagem:"Timeout simulado"}}]};
  const r=projetarRelatorio(doc);
  assert.equal(r.perguntas.length,0);assert.equal(r.ocorrencias.length,1);
  assert.equal(r.ocorrencias[0].problemas[0].tipo,"tecnica");
  assert.equal(r.qualidade[0].falhas,1);assert.equal(r.qualidade[0].ausentes,21);
});

test("leitura comum separa julgamento da tarefa e julgamento original sem mutar dados",()=>{
  const q={...respostaTeste("A","abstencao","aprovado","DESCONHECIDO"),cenario:"sem_memoria"};
  const doc=documentoTeste([q]),j=respostaTeste("A","factual","reprovado","DESCONHECIDO").julgamento;
  doc.analise_tarefa={disponivel:true,versao:"tarefa-comum-p4-v1",resultados:[{indice:0,id:"A",cenario:"sem_memoria",repeticao:2,esperado:"Fortaleza",julgamento:j}]};
  const antes=JSON.stringify(doc),r=projetarRelatorio(doc);
  assert.equal(r.tarefaComum,true);assert.equal(r.qualidade[0].factual.total,1);assert.equal(r.qualidade[0].factual.aprovados,0);
  assert.equal(r.qualidade[0].integrais,0);assert.equal(r.perguntas[0].julgamentoOriginal.passou,true);
  assert.equal(r.perguntas[0].esperado,"Fortaleza");assert.equal(JSON.stringify(doc),antes);
  assert.equal(r.objetivos.find(o=>o.nome.includes("Atualização")).estado,"Falhou nos critérios medidos");
});
test("análise desalinhada ou versão desconhecida não substitui critérios",()=>{
  const doc=documentoTeste([respostaTeste("A")]);
  for(const analise of [{disponivel:true,versao:"outra",resultados:[]},{disponivel:true,versao:"tarefa-comum-p4-v1",resultados:[{indice:0,id:"OUTRO"}]}]){
    doc.analise_tarefa=analise;assert.equal(projetarRelatorio(doc).tarefaComum,false);
  }
});
test("tokens de todos os cenários exigem medição completa e origem de zero",()=>{
  const nomes=["historico_completo","memoria_regras_api","sem_memoria","memoria_persistente_api"];
  const qs=nomes.map((cenario,i)=>({...respostaTeste("A"),cenario,tokens_total:i===2?0:100-i,metricas_completas:true,
    chamadas_modelo:i===2?0:1,respostas_locais_confirmadas:i===2?1:0}));
  const doc=documentoTeste(qs),r=projetarRelatorio(doc);
  assert.equal(r.tokensCenarios.length,4);
  assert.equal(r.tokensCenarios.find(t=>t.cenario==="sem_memoria").total,0);
  assert.equal(r.tokensCenarios.find(t=>t.cenario==="memoria_persistente_api").total,97);
  qs[2].respostas_locais_confirmadas=0;
  assert.equal(projetarRelatorio(doc).tokensCenarios.find(t=>t.cenario==="sem_memoria").total,null);
  qs[2].respostas_locais_confirmadas="1";
  assert.equal(projetarRelatorio(doc).tokensCenarios.find(t=>t.cenario==="sem_memoria").total,null);
  qs[1].metricas_completas=false;
  assert.equal(projetarRelatorio(doc).tokensCenarios.find(t=>t.cenario==="memoria_regras_api").total,null);
});

test("tokens por etapa conservam parcelas conhecidas sem transformar ausência em zero",()=>{
  const q=respostaTeste("A");q.chamadas_modelo=1;q.tokens_por_etapa={
    sessao:{tokens_entrada:20,tokens_saida:null,tokens_total:null,metricas_completas:false,chamadas_modelo:1},
    ingestao:{tokens_entrada:0,tokens_saida:0,tokens_total:0,metricas_completas:true,chamadas_modelo:0}};
  const r=projetarRelatorio(documentoTeste([q])).tokensCenarios[0];
  assert.equal(r.etapas.sessao.tokens_entrada,20);assert.equal(r.etapas.sessao.tokens_saida,null);
  assert.equal(r.etapas.ingestao.tokens_total,0);assert.equal(r.etapas.pergunta_final.tokens_total,null);
});
test("círculo mantém trinta erros e três inconclusivos separados",()=>{
  const m={total:33,aprovados:0,reprovados:30,pendentes:3};const antes=JSON.stringify(m),d=distribuicaoCriterio(m);
  assert.equal(d.aprovados,0);assert.equal(d.reprovados,30);assert.equal(d.pendentes,3);
  assert(d.fimReprovados<100);assert.equal(JSON.stringify(m),antes);
});
test("círculo aprovado integralmente fecha em cem por cento",()=>{
  const d=distribuicaoCriterio({total:33,aprovados:33,reprovados:0,pendentes:0});
  assert.equal(d.medido,true);assert.equal(d.fimAprovados,100);assert.equal(d.fimReprovados,100);
});
test("sem dados e não aplicável não viram reprovação ou aprovação",()=>{
  assert.equal(distribuicaoCriterio({total:0,aprovados:0,reprovados:0,pendentes:0}).rotulo,"Sem classificação");
  assert.equal(distribuicaoCriterio({total:0,aprovados:0,reprovados:0,pendentes:0,naoAplicaveis:48}).rotulo,"Não aplicável");
});
test("contagens incompatíveis não desenham percentuais artificiais",()=>{
  assert.equal(distribuicaoCriterio({total:33,aprovados:33,reprovados:1,pendentes:0}).medido,false);
  assert.equal(distribuicaoCriterio({total:33,aprovados:true,reprovados:32,pendentes:0}).medido,false);
});
