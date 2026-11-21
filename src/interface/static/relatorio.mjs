const canais = ["tokens_entrada", "tokens_saida", "tokens_total"];
const etapas = ["sessao", "pergunta_final", "ingestao"];
export const nomesCenario={sem_memoria:"Sem memória",historico_completo:"Histórico completo",
  memoria_persistente_api:"Memória pré-carregada",memoria_regras_api:"Memória automática",memoria_automatica:"Memória automática"};
const lista=v=>Array.isArray(v)?v:[];
const inteiro = v => Number.isSafeInteger(v) && v >= 0;
function registrosDaTarefa(doc,p6){
  const originais=lista(doc.resultados),analise=doc.analise_tarefa;
  if(p6){
    if(analise?.disponivel!==true||!(["tarefa-p6-conteudo-v1","tarefa-p6-conteudo-v2"].includes(analise.versao))||!Array.isArray(analise.resultados))return {registros:originais,comum:false};
    const perguntas=originais.map((q,i)=>[q,i]).filter(([q])=>q?.evento?.tipo==="pergunta"),porIndice=new Map();
    if(!perguntas.length||analise.resultados.length!==perguntas.length)return {registros:originais,comum:false};
    for(const a of analise.resultados){
      const q=originais[a?.indice];
      if(!inteiro(a?.indice)||porIndice.has(a.indice)||q?.evento?.tipo!=="pergunta"||a.id!==q.evento.id||a.cenario!==q.cenario||a.repeticao!==1||typeof a.esperado!=="string"||a.julgamento?.versao!==analise.versao.replace("tarefa-",""))return {registros:originais,comum:false};
      if(["acerto_factual","abstencao_correta","sem_informacao_proibida","formato_ok"].some(k=>{
        const c=a.julgamento[k];return !c||!(["aprovado","reprovado","nao_verificado","nao_aplicavel"].includes(c.status))||c.valor!==({aprovado:true,reprovado:false,nao_verificado:null,nao_aplicavel:null}[c.status]);
      }))return {registros:originais,comum:false};
      if((q.estado!=="concluido"||q.trajetoria_integra!==true||q.erro)&&a.julgamento.passou===true)return {registros:originais,comum:false};
      porIndice.set(a.indice,a);
    }
    return {comum:true,registros:originais.map((q,i)=>porIndice.has(i)?{...q,julgamento_original:q.julgamento,julgamento:porIndice.get(i).julgamento,esperado:porIndice.get(i).esperado}:q)};
  }
  if(analise?.disponivel!==true||analise.versao!=="tarefa-comum-p4-v1"||!Array.isArray(analise.resultados)||analise.resultados.length!==originais.length)
    return {registros:originais,comum:false};
  const validos=analise.resultados.every((a,i)=>a.indice===i&&a.id===originais[i]?.id&&a.cenario===originais[i]?.cenario&&a.repeticao===originais[i]?.repeticao&&a.julgamento&&typeof a.esperado==="string");
  if(!validos)return {registros:originais,comum:false};
  return {comum:true,registros:originais.map((q,i)=>({...q,julgamento_original:q.julgamento,julgamento:analise.resultados[i].julgamento,esperado:analise.resultados[i].esperado}))};
}
function tokensCenario(registros,cenario,previstos,opcoes={}){
  const etapaVazia=s=>opcoes.etapasVazias===true&&s.chamadas_modelo===0&&s.chamadas_previstas===0&&s.chamadas_observadas===0;
  const grupo=registros.filter(q=>q.cenario===cenario),medidos=grupo.filter(q=>{
    const s=q.tokens_por_etapa?.sessao??q;
    return s.metricas_completas===true&&inteiro(s.tokens_total)&&(s.tokens_total>0||(s.chamadas_modelo===0&&inteiro(s.respostas_locais_confirmadas)&&s.respostas_locais_confirmadas>0)||etapaVazia(s));
  });
  const completo=grupo.length>0&&grupo.length===previstos&&medidos.length===grupo.length;
  const detalhes=Object.fromEntries(etapas.map(etapa=>[etapa,Object.fromEntries(canais.map(campo=>{
    const medidas=grupo.map(q=>q.tokens_por_etapa?.[etapa]??(etapa==="sessao"?q:{}));
    const conhecidos=medidas.filter(s=>inteiro(s[campo])&&(campo!=="tokens_total"||s.metricas_completas===true)
      &&(s[campo]>0||(s.chamadas_modelo===0&&(etapa==="ingestao"||s.respostas_locais_confirmadas>0||etapaVazia(s)))));
    return [campo,grupo.length>0&&grupo.length===previstos&&conhecidos.length===grupo.length?conhecidos.reduce((a,s)=>a+s[campo],0):null];
  }))]));
  const parcelas=grupo.map(q=>{
    const s=q.tokens_por_etapa?.sessao??q,v=s.tokens_total_observados;
    if(inteiro(v)&&(v>0||(s.chamadas_modelo===0&&inteiro(s.respostas_locais_confirmadas)&&s.respostas_locais_confirmadas>0)||etapaVazia(s)))return v;
    return medidos.includes(q)?s.tokens_total:null;
  }).filter(inteiro);
  const incompletos=grupo.filter(q=>!medidos.includes(q)).map(q=>{
    const s=q.tokens_por_etapa?.sessao??q;
    const mensagem=typeof q.erro==="string"?q.erro:typeof q.erro?.mensagem==="string"?q.erro.mensagem:"";
    return {id:typeof q.id==="string"?q.id:"Teste sem identificador",repeticao:inteiro(q.repeticao)?q.repeticao:null,
      motivo:/timeout|prazo|demorou|tempo limite/iu.test(mensagem)?"O modelo não devolveu a resposta dentro do tempo limite.":
        mensagem?"A execução deste teste falhou; confira o erro nas respostas.":"A contagem de tokens está ausente ou inválida.",
      turnosObservados:inteiro(s.chamadas_observadas)?s.chamadas_observadas:null,
      turnosPrevistos:inteiro(s.chamadas_previstas)?s.chamadas_previstas:null};
  });
  return {cenario,unidade:opcoes.unidade||"registros",p6:opcoes.etapasVazias===true,etapas:detalhes,incompletos,medidos:medidos.length,previstos,total:completo?medidos.reduce((a,q)=>a+(q.tokens_por_etapa?.sessao??q).tokens_total,0):null,
    subtotal:parcelas.length?parcelas.reduce((a,v)=>a+v,0):null,
    chamadas:grupo.length&&grupo.every(q=>inteiro(q.chamadas_modelo))?grupo.reduce((a,q)=>a+q.chamadas_modelo,0):null,
    locais:grupo.length&&grupo.every(q=>inteiro(q.respostas_locais_confirmadas))?grupo.reduce((a,q)=>a+q.respostas_locais_confirmadas,0):null};
}
function tokensP6(doc,cenario){
  const fontes=lista(doc.sessoes).filter(s=>s?.cenario===cenario);
  const identificavel=s=>typeof s.usuario_id==="string"&&s.usuario_id.trim().length>0&&inteiro(s.sessao)&&s.sessao>0;
  const chave=s=>JSON.stringify([s.usuario_id,s.sessao]),contagens=new Map();
  for(const s of fontes)if(identificavel(s))contagens.set(chave(s),(contagens.get(chave(s))||0)+1);
  const unicas=fontes.filter(s=>identificavel(s)&&contagens.get(chave(s))===1);
  const registros=unicas.map(s=>({cenario,id:`${s.usuario_id}/s${s.sessao}`,estado:s.estado,
    tokens_por_etapa:{ingestao:s.tokens?.ingestao,pergunta_final:s.tokens?.perguntas,sessao:s.tokens?.sessao},
    chamadas_modelo:s.tokens?.sessao?.chamadas_modelo,respostas_locais_confirmadas:s.tokens?.sessao?.respostas_locais_confirmadas}));
  const declarados=doc.comparacoes_tokens?.sessao?.tokens_total?.pares_previstos;
  const previstos=inteiro(declarados)&&declarados>0?declarados:20;
  const medida=tokensCenario(registros,cenario,previstos,{etapasVazias:true,unidade:"sessões"});
  const rejeitadas=fontes.length-unicas.length;
  if(rejeitadas){
    medida.total=null;medida.chamadas=null;
    for(const etapa of Object.values(medida.etapas))for(const campo of canais)etapa[campo]=null;
    medida.incompletos.push({id:"Identificação das sessões",repeticao:null,
      motivo:`${rejeitadas} registro(s) duplicado(s) ou sem identificação confiável foram excluídos da soma.`});
  }
  if(unicas.length!==previstos)medida.incompletos.push({id:"Cobertura das sessões",repeticao:null,
    motivo:`${unicas.length} sessões únicas registradas para ${previstos} previstas. O total permanece desconhecido.`});
  if(rejeitadas){medida.total=null;medida.chamadas=null;}
  return medida;
}
function pendente(q){
  const j=q.julgamento;
  return j?.revisao_necessaria!==false||["acerto_factual","abstencao_correta","sem_informacao_proibida","formato_ok"]
    .some(k=>!["aprovado","reprovado","nao_aplicavel"].includes(j?.[k]?.status));
}
function integral(q){
  const j=q.julgamento;
  return j?.passou===true&&j.protocolo_ok===true&&j.revisao_necessaria===false&&q.estado!=="erro"&&!q.erro
    &&["acerto_factual","abstencao_correta","sem_informacao_proibida","formato_ok"].every(k=>
      j[k]?.status==="nao_aplicavel"||(j[k]?.status==="aprovado"&&j[k].valor===true));
}
function contarCriterio(grupo,chave){
  const tipo=chave==="acerto_factual"?"factual":chave==="abstencao_correta"?"abstencao":null;
  const r={total:0,aprovados:0,reprovados:0,pendentes:0,naoAplicaveis:0,desconhecidos:0};
  for(const q of grupo){
    const j=q.julgamento?.[chave],modo=q.julgamento?.tipo_resposta;
    if(j?.status==="nao_aplicavel"||(tipo&&modo&&modo!==tipo)){r.naoAplicaveis++;continue;}
    if(!j?.status&&!(tipo&&modo===tipo)){r.desconhecidos++;continue;}
    r.total++;
    if(j?.status==="aprovado"&&j.valor===true)r.aprovados++;
    else if(j?.status==="reprovado"&&j.valor===false)r.reprovados++;
    else r.pendentes++;
  }
  return r;
}
const respostaDe=q=>q.resultado?.resposta??q.resposta;
function abstencaoIndevida(q){
  const texto=respostaDe(q);
  return q.julgamento?.tipo_resposta==="factual"&&q.julgamento?.acerto_factual?.status==="reprovado"
    &&typeof texto==="string"&&(q.julgamento.acerto_factual.motivo==="abstencao_indevida_fato_esperado"||/^(desconhecido|n[aã]o sei)[.!]?$/iu.test(texto.trim()));
}
function problemasDe(q){
  const j=q.julgamento||{},problemas=[];
  if(q.estado==="erro"||q.erro)problemas.push({tipo:"tecnica",rotulo:"Falha técnica",motivo:q.erro?.mensagem||String(q.erro||"Evento encerrado com erro.")});
  if(j.acerto_factual?.status==="reprovado")problemas.push({tipo:"conteudo",rotulo:abstencaoIndevida(q)?"Abstenção indevida: o fato era esperado":"Resposta factual incorreta",motivo:j.acerto_factual.motivo});
  if(j.abstencao_correta?.status==="reprovado")problemas.push({tipo:"conteudo",rotulo:"Não respeitou a ausência ou o esquecimento do fato",motivo:j.abstencao_correta.motivo});
  if(j.sem_informacao_proibida?.status==="reprovado")problemas.push({tipo:"conteudo",rotulo:"Informação proibida na resposta",motivo:j.sem_informacao_proibida.motivo});
  if(j.formato_ok?.status==="reprovado")problemas.push({tipo:"formato",rotulo:"Formato exigido não atendido",motivo:j.formato_ok.motivo});
  if((!q.evento||q.evento.tipo==="pergunta")&&pendente(q))problemas.push({tipo:"pendente",rotulo:"Julgamento pendente: sem aprovação integral",motivo:"Confira os critérios não verificados abaixo."});
  return problemas;
}
export function distribuicaoCriterio(m){
  const campos=[m?.total,m?.aprovados,m?.reprovados,m?.pendentes];
  if(!campos.every(inteiro)||!m.total||m.aprovados+m.reprovados+m.pendentes!==m.total)
    return {medido:false,rotulo:m?.naoAplicaveis>0&&!m?.desconhecidos?"Não aplicável":"Sem classificação",total:null};
  return {medido:true,total:m.total,aprovados:m.aprovados,reprovados:m.reprovados,pendentes:m.pendentes,
    fimAprovados:100*m.aprovados/m.total,fimReprovados:100*(m.aprovados+m.reprovados)/m.total};
}
export function usoResposta(dados) {
  const local=dados?.origem_uso==="politica_local"&&dados?.chamadas_modelo_observadas===0
    &&[dados.tokens_entrada,dados.tokens_saida].every(v=>v===null||v===0);
  const entrada=local?0:(inteiro(dados?.tokens_entrada)&&dados.tokens_entrada>0?dados.tokens_entrada:null);
  const saida=local?0:(inteiro(dados?.tokens_saida)&&dados.tokens_saida>0?dados.tokens_saida:null);
  return {local,entrada,saida,total:entrada!==null&&saida!==null?entrada+saida:null};
}
export function medida(valor) {
  if (!valor || typeof valor !== "object") return {medido:false,base:null,memoria:null,pares:0,identificados:null,ausentes:null,duplicados:null,reducao:null};
  const {tokens_historico:base,tokens_cenario:memoria,pares_medidos:pares}=valor;
  const medido=inteiro(base)&&inteiro(memoria)&&inteiro(pares)&&pares>0;
  return {medido,base:medido?base:null,memoria:medido?memoria:null,
    pares:inteiro(pares)?pares:0,identificados:inteiro(valor.pares_identificados)?valor.pares_identificados:null,
    ausentes:inteiro(valor.pares_sem_medicao)?valor.pares_sem_medicao:null,
    duplicados:inteiro(valor.chaves_duplicadas_descartadas)?valor.chaves_duplicadas_descartadas:null,
    reducao:medido&&base>0?100*(1-memoria/base):null};
}
function informacaoAntiga(doc){
  const a=doc.analise_tarefa?.informacao_antiga??doc.analise_informacao_antiga;
  if(a?.versao!=="informacao-antiga-v1"||a.disponivel!==true||!Array.isArray(a.resultados)||!a.cenarios||typeof a.cenarios!=="object")return null;
  const originais=lista(doc.resultados),p6=Array.isArray(doc.sessoes),vistos=new Set();
  for(const r of a.resultados){
    if(!r||typeof r.id!=="string"||typeof r.cenario!=="string"||!inteiro(r.repeticao)||r.repeticao<1||r.repeticao>3||!r.medida)return null;
    const chave=JSON.stringify([r.cenario,r.id,r.repeticao]);if(vistos.has(chave))return null;vistos.add(chave);
    if(r.indice!==null){
      if(!inteiro(r.indice))return null;const q=originais[r.indice];
      if(!q||r.id!==(p6?q.evento?.id:q.id)||r.cenario!==q.cenario||r.repeticao!==(p6?1:q.repeticao))return null;
    }
    const m=r.medida;
    if(![true,false,null].includes(m.aplicavel)||!["verificado","nao_verificado","nao_aplicavel"].includes(m.status))return null;
    if(m.status==="verificado"&&(m.aplicavel!==true||typeof m.retornou_antiga!=="boolean"))return null;
  }
  const cenarios={};
  for(const c of new Set(a.resultados.map(r=>r.cenario))){
    const rs=a.resultados.filter(r=>r.cenario===c),e=rs.filter(r=>r.medida.aplicavel===true),v=e.filter(r=>r.medida.status==="verificado");
    cenarios[c]={tentativas_elegiveis:e.length,numerador:v.filter(r=>r.medida.retornou_antiga===true).length,denominador:v.length,
      nao_verificados:e.length-v.length,nao_aplicaveis:rs.filter(r=>r.medida.aplicavel===false).length,
      aplicabilidade_desconhecida:rs.filter(r=>r.medida.aplicavel===null).length,
      cobertura_pct:e.length?100*v.length/e.length:null,taxa_pct:v.length?100*v.filter(r=>r.medida.retornou_antiga===true).length/v.length:null};
  }
  return {...a,cenarios};
}
export function projetarRelatorio(doc) {
  const p6=!!doc?.comparacoes_tokens?.sessao&&Array.isArray(doc?.sessoes);
  if(!doc || typeof doc!=="object" || (!p6&&(!doc.comparacoes_tokens?.memoria_regras_api || !doc.resumo)))
    throw new Error("Este arquivo não contém as comparações pareadas do avaliador atual. Gere um relatório novo; resultados antigos não são convertidos em medições.");
  const antiga=informacaoAntiga(doc);
  const comparacao=p6?doc.comparacoes_tokens:doc.comparacoes_tokens.memoria_regras_api;
  const converter=v=>medida(p6?{...v,tokens_cenario:v?.tokens_automaticos}:v);
  const linhas=(p6?["sessao","perguntas","ingestao"]:etapas).flatMap(etapa=>canais.map(canal=>({etapa,canal,...converter(comparacao[etapa]?.[canal])})));
  const leitura=registrosDaTarefa(doc,p6),direto=lista(doc.resultados).filter(q=>q.cenario==="sem_memoria").some(q=>q.via==="ollama_direto"),registros=leitura.registros, questoes=registros.filter(r=>!p6||r?.evento?.tipo==="pergunta");
  const cenarios=p6?["historico_completo","memoria_automatica"]:
    ["historico_completo","memoria_regras_api","sem_memoria","memoria_persistente_api"].filter(c=>doc.resumo[c]);
  const qualidade=cenarios.map(cenario=>{
    const grupo=questoes.filter(q=>q.cenario===cenario);
    const detalhes={factual:contarCriterio(grupo,"acerto_factual"),abstencao:contarCriterio(grupo,"abstencao_correta"),
      formato:contarCriterio(grupo,"formato_ok"),observados:grupo.length,
      integrais:grupo.filter(integral).length,
      abstencoesIndevidas:grupo.filter(abstencaoIndevida).length,informacaoAntiga:antiga?.cenarios?.[cenario]??null};
    if(p6){
      const grupo=questoes.filter(r=>r.cenario===cenario), q=grupo.map(r=>r.julgamento);
      return {cenario,casos:doc.perguntas_previstas_por_cenario??21,
        aprovados:q.filter(j=>j?.passou===true).length,
        reprovados:q.filter(j=>[j?.acerto_factual,j?.abstencao_correta,j?.sem_informacao_proibida].some(c=>c?.status==="reprovado")).length,
        pendentes:(doc.perguntas_previstas_por_cenario??21)-grupo.filter(q=>!pendente(q)).length,
        falhas:registros.filter(r=>r.cenario===cenario&&r.estado==="erro").length,...detalhes,
        ausentes:Math.max(0,(doc.perguntas_previstas_por_cenario??21)-grupo.length)};
    }
    const r=doc.resumo[cenario]||{};
    return {cenario,aprovados:leitura.comum?grupo.filter(q=>q.julgamento?.passou===true).length:inteiro(r.aprovados)?r.aprovados:null,
      casos:inteiro(r.casos)?r.casos:null,falhas:inteiro(r.falhas)?r.falhas:null,
      pendentes:grupo.length?grupo.filter(pendente).length:null,...detalhes,
      ausentes:inteiro(r.casos)?Math.max(0,r.casos-grupo.length):null};
  });
  const modelos=[...new Set((Array.isArray(doc.resultados)?doc.resultados:[])
    .map(r=>r?.modelo).filter(v=>typeof v==="string"))];
  if(doc.interface?.modelo&&!modelos.includes(doc.interface.modelo))modelos.push(doc.interface.modelo);
  const objetivos=[];
  const objetivo=(nome,m,inverter=false)=>{
    const d=m?.denominador,n=m?.numerador;
    const ruim=Number.isInteger(d)&&Number.isInteger(n)&&(inverter?n>0:n<d);
    const completo=d>0&&m?.nao_verificados===0&&(m?.aplicabilidade_desconhecida??0)===0;
    objetivos.push({nome,estado:ruim?"Falhou nos critérios medidos":completo?"Demonstrado nos critérios medidos":"Inconclusivo",
      detalhe:Number.isInteger(d)?`${inverter?d-n:n} / ${d} julgamentos favoráveis; ${m?.nao_verificados??"?"} não verificados; cobertura ${m?.cobertura_pct??"não medida"}%.`:"Sem medição independente neste protocolo."});
  };
  for(const c of cenarios){
    const metricas=p6?doc.metricas_resposta?.[c]:doc.resumo[c]?.metricas_resposta;
    for(const [chave,nome,inverter] of [["recuperacao_factual","Recuperação factual",false],["abstencao_correta","Abstenção",false],["vazamento_esquecidos","Ausência de vazamento dos alvos anotados",true]]){
      if(leitura.comum&&["recuperacao_factual","abstencao_correta"].includes(chave)){
        const m=contarCriterio(questoes.filter(q=>q.cenario===c),chave==="recuperacao_factual"?"acerto_factual":"abstencao_correta"),n=m.aprovados+m.reprovados;
        if(!m.total&&m.naoAplicaveis>0)objetivos.push({nome:`${nomesCenario[c]} · ${nome}`,estado:"Não aplicável",detalhe:"Não há tarefas deste tipo nos registros."});
        else objetivo(`${nomesCenario[c]} · ${nome}`,{numerador:m.aprovados,denominador:n,nao_verificados:m.pendentes,aplicabilidade_desconhecida:m.desconhecidos,cobertura_pct:m.total?100*n/m.total:0});
      }else if(c==="sem_memoria"&&!direto&&chave==="recuperacao_factual")objetivos.push({nome:`${nomesCenario[c]} · ${nome}`,estado:"Não aplicável",detalhe:"Controle sem fatos anteriores: abstenção correta não demonstra recuperação de memória."});
      else objetivo(`${nomesCenario[c]} · ${nome}`,metricas?.[chave],inverter);
    }
    const antigaCenario=antiga?.cenarios?.[c];
    if(antigaCenario?.tentativas_elegiveis===0&&antigaCenario.aplicabilidade_desconhecida===0)
      objetivos.push({nome:`${nomesCenario[c]} · Ausência de informação antiga indevida`,estado:"Não aplicável",detalhe:"Sem oportunidades factuais com valores antigos anotados. Esquecimento e isolamento são avaliados separadamente."});
    else objetivo(`${nomesCenario[c]} · Ausência de informação antiga indevida`,antigaCenario,true);
    const atualizacoes=questoes.filter(q=>q.cenario===c&&(q.categoria||doc.interface?.anotacoes?.[q.evento?.id]?.categoria)==="atualizacao");
    const contagem=contarCriterio(atualizacoes,"acerto_factual"),verificados=contagem.aprovados+contagem.reprovados;
    if((c==="sem_memoria"&&!leitura.comum&&!direto)||(atualizacoes.length&&contagem.naoAplicaveis===atualizacoes.length))
      objetivos.push({nome:`${nomesCenario[c]} · Atualização nas respostas anotadas`,estado:"Não aplicável",detalhe:`${contagem.naoAplicaveis} ocorrência(s) não aplicável(is). Este cenário não mede atualização factual; consulte a abstenção.`});
    else objetivo(`${nomesCenario[c]} · Atualização nas respostas anotadas`,atualizacoes.length?{
      denominador:verificados,numerador:contagem.aprovados,aplicabilidade_desconhecida:contagem.desconhecidos,
      nao_verificados:contagem.pendentes,cobertura_pct:contagem.total?100*verificados/contagem.total:0}:null);
  }
  if(p6){
    for(const [chave,nome] of [["checkpoint_persistencia","Persistência após reinício"],["checkpoint_exclusao","Exclusão no SQLite e RAM"]])
      objetivo(nome,doc.metricas_checkpoints?.memoria_automatica?.[chave]);
  }else for(const nome of ["Persistência após reinício","Exclusão física no SQLite/RAM"])
    objetivos.push({nome,estado:"Inconclusivo",detalhe:"Não medido pelo comparativo de casos. Use P6 para esses checkpoints."});
  const sem=lista(doc.resultados).filter(q=>q.cenario==="sem_memoria");
  const controleSemMemoria=!p6&&sem.length&&sem.every(q=>q.via==="ollama_direto")?"modelo_direto":
    !p6&&sem.length&&sem.every(q=>q.via==="api")?"api_local":"nao_identificado";
  const p=converter(comparacao.sessao?.tokens_total);
  objetivos.unshift({nome:"Economia de tokens pareados",estado:p.reducao===null?"Inconclusivo":p.reducao>0?"Demonstrado nos pares medidos":"Não houve redução nos pares medidos",
    detalhe:`${p.pares} pares medidos. A economia não inclui pares sem medição nem comprova qualidade ou custo total do sistema.`});
  const perguntas=questoes.map(q=>{
    const fonte=lista(doc.interface?.casos).find(c=>c.id===q.id);
    const anotacao=p6?doc.interface?.anotacoes?.[q.evento?.id]:fonte;
    const esperado=q.esperado??(q.julgamento?.tipo_resposta==="abstencao"?"DESCONHECIDO":anotacao?.esperado);
    const antigaResposta=antiga?.resultados.find(r=>r.indice!==null&&r.id===(q.id||q.evento?.id)&&r.cenario===q.cenario&&r.repeticao===(p6?1:q.repeticao))?.medida;
    const problemas=problemasDe(q);
    if(antigaResposta?.retornou_antiga===true)problemas.push({tipo:"conteudo",rotulo:"Informação antiga devolvida como resposta",motivo:antigaResposta.motivo});
    else if(antigaResposta?.aplicavel===true&&antigaResposta.status==="nao_verificado")problemas.push({tipo:"pendente",rotulo:"Informação antiga: análise inconclusiva",motivo:antigaResposta.motivo});
    const notaAvaliacao=p6&&q.julgamento?.acerto_factual?.status==="nao_verificado"&&q.julgamento.acerto_factual.motivo==="parafrase_nao_reconhecida"?
      "O avaliador automático não reconheceu esta forma da frase. O conteúdo fica inconclusivo: compare a resposta com o fato esperado; isso não confirma acerto nem erro.":null;
    return {notaAvaliacao,informacaoAntiga:antigaResposta,id:q.id||q.evento?.id,cenario:q.cenario,repeticao:inteiro(q.repeticao)?q.repeticao:null,
      esperado:typeof esperado==="string"?esperado:Array.isArray(esperado)?esperado.join(" / "):"Não incorporado neste relatório; consulte as anotações.",
      problemas,pergunta:p6?q.evento.texto:fonte?.mensagens?.at(-1)||q.pergunta||"Pergunta não incorporada neste relatório; consulte o roteiro original.",
      resposta:(p6?q.resultado?.resposta:q.resposta)??"Sem resposta observada",julgamento:q.julgamento||{},julgamentoOriginal:q.julgamento_original||null,
      erro:q.erro,checkpoint:q.checkpoint};
  });
  const errosOperacionais=p6?registros.filter(q=>q.evento?.tipo!=="pergunta"&&(q.estado==="erro"||q.erro)).map(q=>({
    id:q.evento?.id||"Evento sem identificador",cenario:q.cenario,repeticao:null,
    pergunta:q.evento?.texto||q.evento?.tipo||"Evento operacional",esperado:"Conclusão do evento operacional; não é uma pergunta factual.",
    resposta:q.resultado?.resposta??"Sem resposta observada",julgamento:q.julgamento||{},problemas:problemasDe(q)})):[];
  return {principal:p,linhas,qualidade,objetivos,perguntas,p6,tarefaComum:leitura.comum,controleSemMemoria,
    analiseConteudo:p6&&leitura.comum?doc.analise_tarefa.versao.replace("tarefa-p6-conteudo-",""):null,
    tokensCenarios:p6?cenarios.map(c=>tokensP6(doc,c)):cenarios.map(c=>tokensCenario(lista(doc.resultados),c,doc.resumo[c]?.casos)),
    ocorrencias:[...perguntas.filter(q=>q.problemas.length),...errosOperacionais],
    protocolo:p6?"P6 · 20 sessões por cenário":"Comparativo de casos",
    conjunto:doc.interface?.conjunto||"origem não declarada",
    aviso:doc.estado_orquestracao==="incompleta"?"Orquestração incompleta; resultados parciais.":registros.some(q=>q.erro||q.estado==="erro")?"A execução terminou com falhas técnicas; resultados e medições parciais preservados.":
      "Critérios automáticos limitados. Revisão humana adicional não foi realizada por esta execução.",
    geradoEm:typeof doc.gerado_em==="string"?doc.gerado_em:null,modelos};
}
