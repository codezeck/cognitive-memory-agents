const canais = ["tokens_entrada", "tokens_saida", "tokens_total"];
const etapas = ["sessao", "pergunta_final", "ingestao"];
const inteiro = v => Number.isSafeInteger(v) && v >= 0;
export function usoResposta(dados) {
  const local=dados?.origem_uso==="politica_local"&&dados?.chamadas_modelo_observadas===0
    &&[dados.tokens_entrada,dados.tokens_saida].every(v=>v===null||v===0);
  const entrada=local?0:(inteiro(dados?.tokens_entrada)&&dados.tokens_entrada>0?dados.tokens_entrada:null);
  const saida=local?0:(inteiro(dados?.tokens_saida)&&dados.tokens_saida>0?dados.tokens_saida:null);
  return {local,entrada,saida,total:entrada!==null&&saida!==null?entrada+saida:null};
}
export function medida(valor) {
  if (!valor || typeof valor !== "object") return {medido:false};
  const {tokens_historico:base,tokens_cenario:memoria,pares_medidos:pares}=valor;
  const medido=inteiro(base)&&inteiro(memoria)&&inteiro(pares)&&pares>0;
  return {medido,base:medido?base:null,memoria:medido?memoria:null,
    pares:inteiro(pares)?pares:0,identificados:inteiro(valor.pares_identificados)?valor.pares_identificados:null,
    ausentes:inteiro(valor.pares_sem_medicao)?valor.pares_sem_medicao:null,
    duplicados:inteiro(valor.chaves_duplicadas_descartadas)?valor.chaves_duplicadas_descartadas:null,
    reducao:medido&&base>0?100*(1-memoria/base):null};
}
export function projetarRelatorio(doc) {
  if(!doc || typeof doc!=="object" || !doc.comparacoes_tokens?.memoria_regras_api || !doc.resumo)
    throw new Error("Este arquivo não contém as comparações pareadas do avaliador atual. Gere um relatório novo; resultados antigos não são convertidos em medições.");
  const comparacao=doc.comparacoes_tokens.memoria_regras_api;
  const linhas=etapas.flatMap(etapa=>canais.map(canal=>({etapa,canal,...medida(comparacao[etapa]?.[canal])})));
  const qualidade=["historico_completo","memoria_regras_api"].map(cenario=>{
    const r=doc.resumo[cenario]||{};
    return {cenario,aprovados:inteiro(r.aprovados)?r.aprovados:null,
      casos:inteiro(r.casos)?r.casos:null,falhas:inteiro(r.falhas)?r.falhas:null};
  });
  const modelos=[...new Set((Array.isArray(doc.resultados)?doc.resultados:[])
    .map(r=>r?.modelo).filter(v=>typeof v==="string"))];
  return {principal:medida(comparacao.sessao?.tokens_total),linhas,qualidade,
    geradoEm:typeof doc.gerado_em==="string"?doc.gerado_em:null,modelos};
}
