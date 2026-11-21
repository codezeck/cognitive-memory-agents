import {projetarRelatorio,usoResposta,nomesCenario,distribuicaoCriterio} from "./relatorio.mjs?v=p6-conteudo-20261121-2";
import {bloqueioAvaliacao} from "./avaliacao.mjs";
import {instalarAparencia} from "./aparencia.mjs";
import {confirmarAvaliacao} from "./confirmacao.mjs";
const $=id=>document.getElementById(id);
const nf=new Intl.NumberFormat("pt-BR"), pf=new Intl.NumberFormat("pt-BR",{maximumFractionDigits:1});
let usuario=null,ocupado=false,modelos=[],soma=0,chamadas=0,incompleta=false,poll=null;
let demonstracao=false,dadosServicos=null,avaliacaoAtual=null,roteirosAtuais=[],casosProprios=null;
let historicoDeslocamento=null,historicoVersao=0,aberturaVersao=0,conexaoVersao=0;
instalarAparencia();
const numero=v=>Number.isSafeInteger(v)&&v>0;
const fmt=v=>typeof v==="number"&&Number.isFinite(v)?nf.format(v):"—";
function aviso(texto,erro=false){$("notice").textContent=texto;$("notice").classList.toggle("error",erro);$("notice").hidden=!texto;}
async function requisicao(rota,opcoes={}){
  const dono=usuario,geracao=conexaoVersao;
  const resposta=await fetch("/interface"+rota,{credentials:"same-origin",...opcoes,headers:{"Content-Type":"application/json",...opcoes.headers}});
  if(dono!==usuario||geracao!==conexaoVersao)throw new DOMException("Solicitação de conexão anterior descartada.","AbortError");
  const dados=resposta.status===204?null:await resposta.json();
  if(dono!==usuario||geracao!==conexaoVersao)throw new DOMException("Solicitação de conexão anterior descartada.","AbortError");
  if(!resposta.ok){
    if(resposta.status===401&&rota!=="/sessao")desconectar();
    throw new Error(dados?.mensagem||(Array.isArray(dados?.detail)?dados.detail.map(e=>e.loc?.join(".")+": "+e.msg).join("; "):dados?.detail)||"Não foi possível concluir a solicitação.");
  }
  return dados;
}
function travar(valor){
  ocupado=valor;
  for(const id of ["message","send","model","new-session","memory-query","memory-search","forget-all"])
    $(id).disabled=valor||!usuario;
  $("send").textContent=valor?"Aguardando…":"Enviar ↑";
}
function limparAvaliacao(){
  conexaoVersao++;
  if($("evaluation-confirmation").open)$("evaluation-confirmation").close("cancelar");
  if(poll){clearTimeout(poll);poll=null;}
  avaliacaoAtual=null;casosProprios=null;
  historicoVersao++;aberturaVersao++;historicoDeslocamento=null;
  $("history-list").replaceChildren();$("history-status").textContent="";$("evaluation-history").hidden=true;
  $("history-more").hidden=true;$("show-evaluation-history").setAttribute("aria-expanded","false");$("evaluation-form").hidden=false;
  $("report").hidden=true;$("report-explanation").hidden=true;$("report-empty").hidden=false;
  $("report-issues").replaceChildren();$("report-answers").replaceChildren();$("report-issue-filter").onchange=null;
  $("download-report").hidden=true;$("evaluation-progress").hidden=true;
  $("evaluation-status").textContent="Nenhuma avaliação iniciada neste perfil.";
  $("dataset-status").textContent="Nenhum conjunto próprio validado.";
}
function conectar(dados){
  if(usuario!==dados.usuario_id)limparAvaliacao();
  usuario=dados.usuario_id;$("user-name").textContent=usuario;$("test-badge").hidden=!dados.modo_teste;
  $("logout").hidden=demonstracao;$("token").value="";$("login-error").textContent="";
  $("demo-profile").hidden=!demonstracao;$("demo-profile").value=dados.perfil||"a";
  if($("login").open)$("login").close();travar(false);servicos();carregarRoteiros();carregarHistorico();
  const guardado=sessionStorage.getItem("cma-avaliacao:"+usuario);
  if(guardado){try{const j=JSON.parse(guardado);if(j.usuario===usuario)acompanhar(j.id);}catch{}}
}
function limparConversa(){
  for(const n of $("messages").querySelectorAll(".bubble"))n.remove();
  $("welcome").hidden=false;
  soma=0;chamadas=0;incompleta=false;
  for(const id of ["token-input","token-output","token-total","session-total"])$(id).textContent="—";
  $("memories").replaceChildren();$("memory-query").value="";
}
function desconectar(){
  limparAvaliacao();
  usuario=null;travar(false);limparConversa();$("user-name").textContent="Não conectado";
  $("logout").hidden=true;$("run-evaluation").disabled=true;$("test-badge").hidden=true;
  if(poll){clearTimeout(poll);poll=null;}
  $("report").hidden=true;$("report-empty").hidden=false;$("download-report").hidden=true;
  $("evaluation-status").textContent="Nenhuma avaliação iniciada nesta conexão.";
  $("login-form").hidden=demonstracao;$("reactivate-demo").hidden=!demonstracao;
  if(!$("login").open)$("login").showModal();
}
function elemento(tag,texto,classe){const e=document.createElement(tag);if(texto!==undefined)e.textContent=texto;if(classe)e.className=classe;return e;}
function bolha(papel,texto,memorias=[]){
  $("welcome").hidden=true;
  const e=elemento("div",undefined,"bubble "+(papel==="Você"?"user":"assistant"));
  e.append(elemento("small",papel.toUpperCase()),document.createTextNode(texto));
  if(memorias.length)e.append(elemento("div","Memórias usadas: "+memorias.join(" · "),"used-memories"));
  $("messages").append(e);$("messages").scrollTop=$("messages").scrollHeight;
}
function tokens(dados){
  const {local,entrada,saida,total}=usoResposta(dados);
  $("token-input").textContent=local?"0 local":fmt(entrada);$("token-output").textContent=local?"0 local":fmt(saida);$("token-total").textContent=local?"0 local":fmt(total);
  chamadas++;if(total===null)incompleta=true;else soma+=total;
  $("session-total").textContent=incompleta?"Medição incompleta":fmt(soma)+" · "+chamadas+" interação(ões)";
}
async function buscar(consulta){
  if(!consulta.trim()||!usuario)return;
  $("memory-query").value=consulta.slice(0,500);
  const dados=await requisicao("/memorias",{method:"POST",body:JSON.stringify({consulta:consulta.slice(0,500)})});
  $("memories").replaceChildren();
  if(!dados.length){$("memories").append(elemento("p","Nenhuma memória encontrada para este assunto.","muted"));return;}
  for(const m of dados){
    const e=elemento("div",undefined,"memory-item");
    e.append(elemento("p",m.texto),elemento("small","ID: "+m.id),elemento("small","Similaridade: "+pf.format(m.score)));
    const excluir=elemento("button","Excluir esta memória","text-button");
    excluir.type="button";
    excluir.addEventListener("click",async()=>{
      if(ocupado||!confirm("Excluir somente esta memória e reiniciar a conversa recente? Versões substituídas podem permanecer até a exclusão total."))return;
      travar(true);
      try{await requisicao("/memorias/"+encodeURIComponent(m.id),{method:"DELETE"});limparConversa();aviso("Memória selecionada excluída. A conversa recente foi reiniciada.");await buscar(consulta);}
      catch(erro){aviso(erro.message,true);}finally{travar(false);}
    });
    e.append(excluir);
    $("memories").append(e);
  }
}
function selecao(){const i=Number($("model").value);return modelos[i]||{};}
async function servicos(){
  try{
    const dono=usuario;const dados=await requisicao("/disponibilidade");if(usuario!==dono)return;dadosServicos=dados;
    modelos=dados.modelos||[];const anterior=$("model").selectedOptions[0]?.textContent;
    $("model").replaceChildren();
    modelos.forEach((m,i)=>{const o=elemento("option",m.provedor+" · "+m.modelo);o.value=i;o.disabled=!m.configurado;o.selected=o.textContent===anterior||(!anterior?.includes(" · ")&&m.padrao);$("model").append(o);});
    $("service-status").textContent=dados.ollama==="disponivel"?"API disponível · Ollama acessível":"API disponível · Ollama indisponível";
    const m=selecao();const instalado=dados.modelos_instalados?.includes(m.modelo);
    if(m.provedor==="ollama"&&dados.ollama==="disponivel"&&!instalado)
      $("service-status").textContent="API disponível · modelo selecionado ausente no Ollama";
    if(m.provedor!=="ollama")$("service-status").textContent="API disponível · provedor configurado; disponibilidade não verificada";
    atualizarBloqueio();
    if(dados.avaliacao_ativa?.id&&!avaliacaoAtual)acompanhar(dados.avaliacao_ativa.id);
  }catch(e){$("service-status").textContent="Não foi possível conferir os serviços";aviso(e.message,true);}
}
function mudarTab(nome){
  for(const n of document.querySelectorAll(".tab-page"))n.hidden=n.id!=="tab-"+nome;
  for(const n of document.querySelectorAll("[data-tab]")){const ativo=n.dataset.tab===nome;n.classList.toggle("active",ativo);if(ativo)n.setAttribute("aria-current","page");else n.removeAttribute("aria-current");}
}
for(const n of document.querySelectorAll("[data-tab]"))n.addEventListener("click",()=>mudarTab(n.dataset.tab));
for(const n of document.querySelectorAll("[data-prompt]"))n.addEventListener("click",()=>{$("message").value=n.dataset.prompt;$("message").focus();});
$("login").addEventListener("cancel",e=>e.preventDefault());
$("login-form").addEventListener("submit",async e=>{
  e.preventDefault();$("login-button").disabled=true;
  try{conectar(await requisicao("/sessao",{method:"POST",body:JSON.stringify({token:$("token").value.trim()})}));aviso("");}
  catch(erro){$("login-error").textContent=erro.message;$("token").value="";$("token").focus();}
  finally{$("login-button").disabled=false;}
});
$("logout").addEventListener("click",async()=>{try{await requisicao("/sessao",{method:"DELETE"});desconectar();}catch(e){aviso(e.message,true);}});
$("model").addEventListener("change",()=>servicos());
$("message").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();$("message-form").requestSubmit();}});
$("message-form").addEventListener("submit",async e=>{
  e.preventDefault();const mensagem=$("message").value.trim();if(!mensagem||ocupado||!usuario)return;
  const m=selecao();if(!m.provedor){aviso("Selecione um modelo configurado.",true);return;}
  travar(true);aviso("");bolha("Você",mensagem);$("message").value="";
  try{
    const dados=await requisicao("/conversas",{method:"POST",body:JSON.stringify({mensagem,provedor:m.provedor,modelo:m.modelo})});
    bolha("Agente",dados.resposta,dados.memorias_usadas||[]);tokens(dados);
  }catch(erro){incompleta=true;$("session-total").textContent="Medição incompleta";bolha("Sistema",erro.message);aviso("A resposta não foi concluída. Confira os serviços; uma memória pode ter sido registrada antes da falha.",true);if(usuario)await servicos();}
  finally{
    if(usuario){try{await buscar(mensagem);}catch(erro){aviso(erro.message,true);}}
    travar(false);if(usuario)$("message").focus();
  }
});
$("memory-form").addEventListener("submit",async e=>{e.preventDefault();try{await buscar($("memory-query").value);}catch(erro){aviso(erro.message,true);}});
$("forget-all").addEventListener("click",async()=>{
  if(ocupado||!usuario||!confirm("Apagar TODAS as memórias deste usuário, incluindo versões substituídas, e reiniciar a conversa recente?"))return;
  travar(true);
  try{const dados=await requisicao("/memorias",{method:"DELETE"});limparConversa();aviso("Exclusão total concluída: "+dados.removidas+" registro(s) removido(s). Outros usuários foram preservados.");}
  catch(erro){aviso(erro.message,true);}finally{travar(false);}
});
$("new-session").addEventListener("click",async()=>{
  if(ocupado||!usuario)return;travar(true);
  try{await requisicao("/nova-sessao",{method:"POST"});limparConversa();aviso("Nova sessão iniciada. As memórias persistentes foram preservadas.");}
  catch(erro){aviso(erro.message,true);}finally{travar(false);}
});
const nomesEtapa={sessao:"Sessão",pergunta_final:"Pergunta final",perguntas:"Perguntas",ingestao:"Ingestão"};
const nomesCanal={tokens_entrada:"entrada",tokens_saida:"saída",tokens_total:"total"};
function detalheResposta(q){
  const detalhe=elemento("details"),titulo=q.id+" · "+(nomesCenario[q.cenario]||q.cenario)+(q.repeticao!==null?" · repetição "+q.repeticao:"");
  detalhe.append(elemento("summary",titulo));
  if(q.informacaoAntiga)detalhe.append(elemento("p","Informação antiga: "+(q.informacaoAntiga.status==="nao_aplicavel"?"não aplicável":q.informacaoAntiga.retornou_antiga===true?"devolvida indevidamente":q.informacaoAntiga.retornou_antiga===false?"sem retorno indevido reconhecido":"inconclusivo")+" · "+q.informacaoAntiga.motivo,"fine-print"));
  if(q.notaAvaliacao)detalhe.append(elemento("p",q.notaAvaliacao,"notice"));
  for(const problema of q.problemas)detalhe.append(elemento("p",problema.rotulo+(problema.motivo?" · "+problema.motivo:""),"report-problem"));
  detalhe.append(elemento("p","Pergunta / evento: "+q.pergunta),elemento("p","Esperado neste cenário: "+q.esperado),elemento("p","Resposta: "+q.resposta));
  for(const [chave,rotulo] of [["acerto_factual","Acerto factual"],["abstencao_correta","Abstenção"],["sem_informacao_proibida","Informações proibidas"],["formato_ok","Formato"]]){
    const j=q.julgamento[chave];detalhe.append(elemento("p",rotulo+": "+(j?.status||"não verificado")+(j?.motivo?" · "+j.motivo:"")));
  }
  if(q.julgamentoOriginal){
    const original=elemento("details");original.append(elemento("summary","Julgamento original da execução (preservado)"));
    for(const chave of ["acerto_factual","abstencao_correta","sem_informacao_proibida","formato_ok"]){const j=q.julgamentoOriginal[chave];original.append(elemento("p",chave+": "+(j?.status||"não verificado")+(j?.motivo?" · "+j.motivo:"")));}
    detalhe.append(original);
  }
  return detalhe;
}
function mostrarOcorrencias(r){
  const filtro=$("report-issue-filter").value,selecionadas=r.ocorrencias.filter(q=>filtro==="todas"||q.problemas.some(p=>p.tipo===filtro));
  $("report-issue-count").textContent=selecionadas.length+" ocorrência(s) exibida(s) de "+r.ocorrencias.length+" com atenção necessária. Uma resposta pode ter mais de um motivo.";
  $("report-issues").replaceChildren();
  if(!selecionadas.length)$("report-issues").append(elemento("p","Nenhuma ocorrência registrada neste filtro. Isso não certifica ausência de erros fora dos critérios avaliados."));
  for(const q of selecionadas)$("report-issues").append(detalheResposta(q));
}
function circuloCriterio(rotulo,medida){
  const dados=distribuicaoCriterio(medida),figura=elemento("figure",undefined,"criterion-figure");
  const anel=elemento("div",undefined,"criterion-ring"),centro=elemento("div",undefined,"criterion-center");
  anel.setAttribute("role","img");centro.setAttribute("aria-hidden","true");
  if(dados.medido){
    anel.style.background=`conic-gradient(var(--chart-approved) 0% ${dados.fimAprovados}%,var(--chart-rejected) ${dados.fimAprovados}% ${dados.fimReprovados}%,var(--chart-pending) ${dados.fimReprovados}% 100%)`;
    anel.setAttribute("aria-label",`${rotulo}: ${dados.aprovados} aprovados, ${dados.reprovados} reprovados e ${dados.pendentes} inconclusivos, em ${dados.total} respostas classificadas.`);
    centro.append(elemento("strong",`${dados.aprovados} / ${dados.total}`),elemento("span","aprovados"));
  }else{
    anel.setAttribute("aria-label",rotulo+": "+dados.rotulo);
    centro.append(elemento("span",dados.rotulo));
  }
  anel.append(centro);figura.append(anel,elemento("figcaption",rotulo));
  if(dados.medido)figura.append(elemento("small",`${dados.reprovados} reprovados · ${dados.pendentes} inconclusivos`,"criterion-counts"));
  figura.append(elemento("small",rotulo==="Fatos corretos"?"Responder a informação pedida.":"Dizer que não sabe quando essa é a resposta esperada."));
  if(medida.desconhecidos>0)figura.append(elemento("small",medida.desconhecidos+" sem classificação de aplicabilidade"));
  return figura;
}
function painelTokensCenario(t,maior){
  const painel=elemento("section",undefined,"scenario-tokens");
  painel.append(elemento("h4","Tokens gastos"),elemento("strong",t.total===null?"Medição incompleta":fmt(t.total),"scenario-token-total"),elemento("p","Tokens de geração da sessão inteira neste cenário.","fine-print"));
  const trilho=elemento("div",undefined,"bar-track"),barra=elemento("div",undefined,"bar memory");
  barra.style.width=(t.total===null?0:100*t.total/maior)+"%";trilho.append(barra);
  trilho.setAttribute("role","img");trilho.setAttribute("aria-label",t.total===null?"Total de tokens desconhecido":fmt(t.total)+" tokens; barras dos cenários na mesma escala.");
  painel.append(trilho);
  const valores=elemento("dl",undefined,"quality-metrics");
  for(const [nome,valor] of [["Tokens de entrada",t.etapas.sessao.tokens_entrada],["Tokens de saída",t.etapas.sessao.tokens_saida],["Chamadas ao modelo",t.chamadas]])
    valores.append(elemento("dt",nome),elemento("dd",valor===null?"Não medido":fmt(valor)));
  painel.append(valores,elemento("p","Tokens medidos em "+t.medidos+" de "+fmt(t.previstos)+" "+(t.unidade||"registros")+"; isso não é contagem de acertos."+(t.total===null?t.subtotal===null?" Nenhuma parcela de tokens foi devolvida.":" Subtotal observado: "+fmt(t.subtotal)+"; inclui parcelas de turnos concluídos e não representa o total.":"")+(t.chamadas===0&&t.locais>0?" Respostas locais, sem chamada ao modelo nesta rodada.":""),"fine-print"));
  if(t.incompletos.length){
    const causas=elemento("div",undefined,"notice token-diagnostics");
    causas.append(elemento("strong","Por que a medição está incompleta?"));
    for(const falha of t.incompletos.slice(0,3)){
      const origem=falha.id+(falha.repeticao!==null?" · repetição "+falha.repeticao:"");
      causas.append(elemento("p",origem+": "+falha.motivo+(falha.turnosObservados!==null&&falha.turnosPrevistos!==null?
        " "+falha.turnosObservados+" de "+falha.turnosPrevistos+" turnos tiveram retorno registrado.":"")));
    }
    if(t.incompletos.length>3)causas.append(elemento("p","Mais "+(t.incompletos.length-3)+" teste(s) sem medição completa; veja Mostrar respostas nesta faixa."));
    causas.append(elemento("p","O subtotal contém apenas os tokens recebidos. Não há como recuperar a contagem que o modelo não devolveu; ela não é substituída por zero."));
    painel.append(causas);
  }
  const detalhe=elemento("details",undefined,"scenario-token-details");detalhe.append(elemento("summary","Ver medição por etapa"));
  const tabela=elemento("table"),cabeca=elemento("thead"),cabecalho=elemento("tr"),corpo=elemento("tbody");
  for(const nome of ["Etapa","Entrada","Saída","Total"])cabecalho.append(elemento("th",nome));cabeca.append(cabecalho);
  for(const [etapa,nome] of [["ingestao","Antes da pergunta"],["pergunta_final",t.p6?"Perguntas da sessão":"Pergunta final"],["sessao","Sessão inteira"]]){
    const linha=elemento("tr");linha.append(elemento("th",nome));
    for(const campo of ["tokens_entrada","tokens_saida","tokens_total"])linha.append(elemento("td",t.etapas[etapa][campo]===null?"Não medido":fmt(t.etapas[etapa][campo])));
    corpo.append(linha);
  }
  tabela.append(cabeca,corpo);const rolagem=elemento("div",undefined,"table-scroll");rolagem.append(tabela);detalhe.append(rolagem,elemento("p","Sessão inteira reúne as etapas anteriores. Preparação, regras e infraestrutura não têm seu custo total medido aqui.","fine-print"));painel.append(detalhe);
  return painel;
}
function mostrarRelatorio(doc,origem){
  const r=projetarRelatorio(doc);$("evaluation-form").hidden=true;$("report").hidden=false;$("report-empty").hidden=true;$("report-origin").textContent=doc.simulado===true?(origem.startsWith("ARQUIVO")?origem+" · ":"")+"SIMULAÇÃO DE TESTE":origem;
  const data=r.geradoEm?new Date(r.geradoEm):null;
  $("report-date").textContent=(data&&!isNaN(data)?"Gerado em "+data.toLocaleString("pt-BR"):"Data não informada")+" · "+(r.modelos.join(", ")||"Modelo não informado")+" · medição separada da conversa";
  const p=r.principal;
  $("reduction").textContent=p.reducao===null?"Não medido":pf.format(Math.abs(p.reducao))+"% "+(p.reducao>=0?"de redução":"de aumento");
  $("reduction-caption").textContent="Memória automática versus histórico completo: tokens de geração da sessão nos mesmos pares medidos.";
  $("baseline-value").textContent=fmt(p.base);$("memory-value").textContent=fmt(p.memoria);
  const max=Math.max(p.base||0,p.memoria||0,1);
  $("baseline-bar").style.width=(p.medido?100*p.base/max:0)+"%";$("memory-bar").style.width=(p.medido?100*p.memoria/max:0)+"%";
  $("pairs").textContent=p.pares+" par(es) medido(s) · "+fmt(p.ausentes)+" sem medição · "+fmt(p.duplicados)+" chave(s) duplicada(s) descartada(s).";
  $("paired-token-bars").hidden=!r.p6;$("all-scenario-tokens").replaceChildren();
  const maior=Math.max(...r.tokensCenarios.map(t=>t.total||0),1);
  $("all-scenario-tokens").hidden=true;
  $("quality-method").textContent=r.p6?(r.tarefaComum?"P6: análise de conteúdo "+r.analiseConteudo+" sobre as respostas salvas, com o mesmo gabarito nos dois cenários. Julgamentos originais preservados em Mostrar respostas; formato avaliado separadamente. São 21 perguntas em 20 sessões por cenário.":"P6: julgamentos originais de 21 perguntas por cenário, distribuídas em 20 sessões. Sem análise atualizada compatível; inconclusivo não é erro confirmado. Compare pergunta, fato esperado e resposta em Mostrar respostas."):r.tarefaComum?
    "As mesmas perguntas e respostas esperadas são usadas nos quatro cenários. As avaliações originais continuam disponíveis nos detalhes e no relatório baixado.":
    r.controleSemMemoria==="modelo_direto"?"Julgamentos originais do controle direto com o gabarito da tarefa. Fatos e abstenções são medidas distintas.":
    "Critérios originais da execução. Sem gabarito comum compatível: o controle sem memória pode medir apenas abstenção e não deve ser classificado como vencedor em recuperação.";
  if(r.controleSemMemoria==="modelo_direto")$("quality-method").textContent+=" Controle sem memória: Ollama direto (método novo); compare o método antes de confrontar rodadas antigas.";
  $("quality").replaceChildren();
  for(const q of r.qualidade){
    const linha=elemento("div",undefined,"quality-row"),nome=nomesCenario[q.cenario]||q.cenario;
    linha.append(elemento("h3",nome));
    const valores=elemento("dl",undefined,"quality-metrics");
    const circulos=elemento("div",undefined,"criterion-circles");
    circulos.append(circuloCriterio("Fatos corretos",q.factual),circuloCriterio("Abstenções corretas",q.abstencao));
    const legenda=elemento("ul",undefined,"criterion-legend");
    for(const [classe,texto] of [["approved","Aprovado"],["rejected","Reprovado"],["pending","Inconclusivo"]]){
      const item=elemento("li"),cor=elemento("span",undefined,"legend-dot "+classe);cor.setAttribute("aria-hidden","true");
      item.append(cor,document.createTextNode(texto));legenda.append(item);
    }
    const resultado=elemento("section",undefined,"scenario-result");
    resultado.append(circulos,legenda);
    for(const [rotulo,valor] of [["Conteúdo + formato",q.observados?fmt(q.integrais)+" / "+fmt(q.casos):"Sem registros para conferir"],
      ["Formato reprovado",q.formato.reprovados],["Julgamentos pendentes",q.pendentes],["Respostas ausentes",q.ausentes],["Falhas de execução",q.falhas]])
      valores.append(elemento("dt",rotulo),elemento("dd",typeof valor==="string"?valor:fmt(valor)));
    const antiga=q.informacaoAntiga;
    valores.append(elemento("dt","Informação antiga indevida"),elemento("dd",!antiga?"Sem análise compatível":
      antiga.tentativas_elegiveis===0&&antiga.aplicabilidade_desconhecida===0?"Não aplicável":
      antiga.denominador?fmt(antiga.numerador)+" / "+fmt(antiga.denominador)+" verificados · "+pf.format(antiga.taxa_pct)+"%":"Inconclusivo"));
    resultado.append(valores);
    resultado.append(elemento("p",antiga?"Valores antigos anotados: "+antiga.tentativas_elegiveis+" oportunidades; "+antiga.nao_verificados+" inconclusivas; "+antiga.aplicabilidade_desconhecida+" sem aplicabilidade definida. Cobertura: "+(antiga.cobertura_pct===null?"não aplicável":pf.format(antiga.cobertura_pct)+"%")+". Maior taxa é pior. Menção ambígua exige revisão; esquecimento e isolamento não entram nesta taxa.":"A taxa de informação antiga requer anotações originais compatíveis; ausência de análise não significa zero erros.","fine-print"));
    linha.append(elemento("p",q.cenario==="sem_memoria"?(r.controleSemMemoria==="modelo_direto"?"Ollama direto: somente a pergunta final, sem histórico, memórias ou abstenção local. ":r.controleSemMemoria==="api_local"?"Controle legado via API, sem fatos anteriores. A regra local pode responder sem chamar Ollama. ":"Método do controle sem memória não identificado nos registros. ")+(r.tarefaComum?"Não fornecer o fato solicitado conta como falha na tarefa factual; abstenção necessária é contada separadamente.":"As abstenções corretas não demonstram recuperação de memória."):
      q.factual.reprovados+" resposta(s) factual(is) reprovada(s), incluindo "+q.abstencoesIndevidas+" abstenção(ões) indevida(s); "+q.factual.pendentes+" julgamento(s) factual(is) pendente(s).","fine-print"));
    if(r.p6&&q.factual.pendentes>0)resultado.append(elemento("p",q.factual.pendentes+" resposta(s) factual(is) inconclusiva(s) não entram como acerto ou erro confirmado. Frases corretas e incorretas podem ficar fora da gramática do avaliador; abra Mostrar respostas para conferir.","fine-print"));
    const corpo=elemento("div",undefined,"scenario-body");corpo.append(resultado);
    const tokens=r.tokensCenarios.find(t=>t.cenario===q.cenario);
    if(tokens)corpo.append(painelTokensCenario(tokens,maior));
    linha.append(corpo);
    const perguntas=r.perguntas.filter(p=>p.cenario===q.cenario),respostas=elemento("details",undefined,"scenario-answers");
    respostas.append(elemento("summary","Mostrar respostas · "+perguntas.length));
    const lista=elemento("div",undefined,"scenario-answer-list");
    for(const pergunta of perguntas)lista.append(detalheResposta(pergunta));
    if(!perguntas.length)lista.append(elemento("p","Nenhuma resposta observada neste cenário."));
    respostas.append(lista);linha.append(respostas);
    $("quality").append(linha);
  }
  $("report-explanation").hidden=false;
  $("report-summary").textContent=r.protocolo+" · conjunto "+r.conjunto+". "+r.aviso;
  $("quality-chart").replaceChildren();
  $("quality-chart").append(elemento("p","Cada círculo considera as respostas classificadas daquele critério. Inconclusivo exige revisão; não é aprovação nem reprovação confirmada. Respostas ausentes e falhas de execução aparecem separadamente."));
  $("report-objectives").replaceChildren();
  for(const o of r.objetivos){
    const caixa=elemento("article",undefined,"objective");
    caixa.append(elemento("h3",o.nome),elemento("strong",o.estado),elemento("p",o.detalhe));$("report-objectives").append(caixa);
  }
  $("report-answers").replaceChildren();
  $("report-answers").append(elemento("p","Abra Mostrar respostas na faixa de cada cenário para conferir perguntas, respostas e julgamentos desta execução."));
  $("report-issue-filter").value="todas";$("report-issue-filter").onchange=()=>mostrarOcorrencias(r);mostrarOcorrencias(r);
  $("report-rows").replaceChildren();
  for(const l of r.linhas){
    const tr=elemento("tr");
    for(const texto of [nomesEtapa[l.etapa]+" / "+nomesCanal[l.canal],fmt(l.base),fmt(l.memoria),l.reducao===null?"Não medido":pf.format(l.reducao)+"%",String(l.pares)])
      tr.append(elemento("td",texto));
    $("report-rows").append(tr);
  }
  $("evaluation-history").hidden=true;$("show-evaluation-history").setAttribute("aria-expanded","false");
  if(!$("tab-avaliacao").hidden){$("report").focus({preventScroll:true});$("tab-avaliacao").scrollIntoView({behavior:"smooth",block:"start"});}
}
$("report-file").addEventListener("change",async()=>{
  const file=$("report-file").files[0];if(!file)return;
  const dono=usuario,versao=++aberturaVersao;
  try{
    if(file.size>8*1024*1024)throw new Error("Escolha um relatório com até 8 MB.");
    const doc=JSON.parse(await file.text());
    if(dono!==usuario||versao!==aberturaVersao)return;
    doc.analise_tarefa=await requisicao("/relatorios/analise",{method:"POST",body:JSON.stringify({documento:doc})});
    if(dono!==usuario||versao!==aberturaVersao)return;
    mostrarRelatorio(doc,"ARQUIVO: "+file.name.slice(0,70));
    $("download-report").hidden=true;$("evaluation-status").textContent="Arquivo lido neste navegador. Não é uma medição da conversa atual.";
    aviso("");
  }catch(e){if(dono===usuario&&versao===aberturaVersao)aviso(e.message,true);}
  finally{if(dono===usuario&&versao===aberturaVersao)$("report-file").value="";}
});
function atualizarBloqueio(){
  let motivo=bloqueioAvaliacao({usuario,dados:dadosServicos,modelo:selecao(),simulado:!$("test-badge").hidden,executando:!!avaliacaoAtual});
  if(!motivo&&$("evaluation-dataset").value==="proprio"&&!casosProprios)motivo="Importe e valide seu conjunto de casos antes de executar.";
  $("run-evaluation").disabled=!!motivo;$("evaluation-block").textContent=motivo||"Pronto para executar uma medição nova com Ollama local.";
  $("evaluation-protocol").disabled=!!avaliacaoAtual;
  $("evaluation-dataset").disabled=!!avaliacaoAtual||$("evaluation-protocol").value==="p6";
  $("repetitions").disabled=!!avaliacaoAtual||$("evaluation-protocol").value==="p6";
  $("new-evaluation").disabled=!usuario||!!avaliacaoAtual;$("show-evaluation-history").disabled=!usuario;
}

async function carregarHistorico(mais=false){
  if(!usuario)return;
  const dono=usuario,versao=++historicoVersao,deslocamento=mais?historicoDeslocamento:0;
  if(mais&&deslocamento===null)return;
  $("history-status").textContent="Consultando avaliações salvas deste perfil…";
  try{
    const dados=await requisicao("/avaliacoes?deslocamento="+deslocamento+"&limite=20");
    if(usuario!==dono||versao!==historicoVersao)return;
    if(!mais)$("history-list").replaceChildren();
    for(const item of dados.avaliacoes){
      const linha=elemento("article",undefined,"history-row"),texto=elemento("div"),data=new Date(item.data);
      texto.append(elemento("h3",item.protocolo==="p6"?"P6 · 20 sessões por cenário":item.protocolo==="comparativo_v3"?"Comparativo sintético v3":"Protocolo não identificado"));
      const estado=item.estado==="executando"?"Em execução":item.estado==="concluido"?"Execução concluída":"Encerrada com falhas ou interrupção";
      texto.append(elemento("p",estado+(item.repeticoes?" · "+item.repeticoes+" repetição(ões)":"")+(item.conjunto?" · conjunto "+item.conjunto:"")));
      if(item.protocolo==="comparativo_v3")texto.append(elemento("p",item.controle_sem_memoria==="modelo_direto"?"Controle sem memória: Ollama direto":"Controle sem memória: método anterior ou não informado"));
      texto.append(elemento("small",(isNaN(data)?"Data não informada":data.toLocaleString("pt-BR"))+(item.origem_data==="arquivo_local"?" · data do arquivo local":"")+(item.modelo?" · "+item.modelo:"")));
      const abrir=elemento("button",item.estado==="executando"?"Acompanhar":item.relatorio_disponivel?"Abrir resultado":"Ver situação","secondary");
      abrir.type="button";abrir.onclick=()=>{if(usuario===dono)abrirAvaliacaoSalva(item.id);};linha.append(texto,abrir);$("history-list").append(linha);
    }
    historicoDeslocamento=dados.proximo_deslocamento;$("history-more").hidden=historicoDeslocamento===null;
    $("history-status").textContent=dados.total?dados.total+" avaliação(ões) salva(s) neste perfil.":"Nenhuma avaliação salva neste perfil. Você pode iniciar uma nova ou importar um JSON.";
  }catch(e){if(usuario===dono&&versao===historicoVersao)$("history-status").textContent="Não foi possível consultar o histórico: "+e.message;}
}
async function abrirAvaliacaoSalva(id){
  const dono=usuario,versao=++aberturaVersao;
  try{
    const job=await requisicao("/avaliacoes/"+encodeURIComponent(id));if(dono!==usuario||versao!==aberturaVersao)return;
    if(job.estado==="executando"){acompanhar(id);return;}
    $("download-report").hidden=true;
    if(job.relatorio){mostrarRelatorio(job.relatorio,"HISTÓRICO · "+(job.estado==="falhou"?"RESULTADO PARCIAL":"EXECUÇÃO CONCLUÍDA"));$("download-report").href="/interface/avaliacoes/"+encodeURIComponent(id)+"/relatorio";$("download-report").hidden=false;}
    else{$("report").hidden=true;$("report-explanation").hidden=true;$("report-empty").hidden=false;}
    if(!avaliacaoAtual)$("evaluation-status").textContent=job.mensagem||"Resultado salvo reaberto. Nenhum teste foi executado novamente.";
  }catch(e){if(dono===usuario&&versao===aberturaVersao)aviso(e.message,true);}
}
$("show-evaluation-history").addEventListener("click",()=>{const aberto=$("evaluation-history").hidden;$("evaluation-history").hidden=!aberto;$("show-evaluation-history").setAttribute("aria-expanded",String(aberto));if(aberto)carregarHistorico();});
$("history-more").addEventListener("click",()=>carregarHistorico(true));
$("new-evaluation").addEventListener("click",()=>{
  if(avaliacaoAtual)return;aberturaVersao++;$("evaluation-form").hidden=false;$("report").hidden=true;$("report-explanation").hidden=true;$("report-empty").hidden=true;$("download-report").hidden=true;
  $("evaluation-status").textContent="Prepare o roteiro e confirme para iniciar uma nova avaliação. Os resultados anteriores continuam no histórico.";
  $("evaluation-form").focus({preventScroll:true});$("evaluation-form").scrollIntoView({behavior:"smooth",block:"start"});
});
async function carregarRoteiros(){
  const dono=usuario;
  try{const dados=await requisicao("/roteiros");if(dono!==usuario)return;roteirosAtuais=dados.protocolos;mostrarRoteiro();}
  catch(e){aviso("Não foi possível ler os roteiros: "+e.message,true);}
}
function mostrarRoteiro(){
  const p6=$("evaluation-protocol").value==="p6",proprio=!p6&&$("evaluation-dataset").value==="proprio";
  $("evaluation-dataset").disabled=p6||!!avaliacaoAtual;
  if(p6)$("evaluation-dataset").value="oficial";
  $("repetitions").disabled=p6||!!avaliacaoAtual;if(p6)$("repetitions").value="1";
  $("repetitions").options[0].textContent=p6?"1 · rodada integral P6":"1 · conferência inicial";
  $("custom-dataset").hidden=!proprio;
  const roteiro=roteirosAtuais.find(r=>r.id===$("evaluation-protocol").value);
  $("protocol-description").replaceChildren();$("protocol-questions").replaceChildren();
  if(!roteiro){atualizarBloqueio();return;}
  const quantidade=proprio?(casosProprios?.length??0):16;
  $("protocol-description").append(elemento("h3",roteiro.nome),elemento("p",proprio?
    "Conjunto próprio: "+quantidade+" casos × "+$("repetitions").value+" repetição(ões) × quatro cenários. Não é a bateria oficial.":roteiro.descricao),
    elemento("p",p6?roteiro.completa:proprio?"Uma ou três repetições reutilizam o mesmo arquivo. Veja as questões validadas abaixo.":$("repetitions").value==="3"?roteiro.completa:roteiro.conferencia),elemento("p",roteiro.limites));
  const ul=elemento("ul");for(const o of roteiro.objetivos)ul.append(elemento("li",o));$("protocol-description").append(ul);
  const questoes=proprio?(casosProprios||[]).map(c=>({id:c.id,pergunta:c.mensagens.at(-1),mensagens:c.mensagens})):roteiro.questoes;
  for(const q of questoes){
    const d=elemento("details");d.append(elemento("summary",q.id+" · "+q.pergunta));
    for(const m of q.mensagens||[])d.append(elemento("p",m));$("protocol-questions").append(d);
  }
  if(p6)for(const sessao of roteiro.sessoes||[]){
    const d=elemento("details");d.append(elemento("summary",sessao.usuario+" · sessão "+sessao.sessao));
    for(const f of sessao.fatos||[])d.append(elemento("p",f.texto));
    if(sessao.apagar_usuario)d.append(elemento("p","Ação: apagar o usuário sintético desta rodada."));
    if(sessao.esquecer_chaves?.length)d.append(elemento("p","Ação: esquecer as chaves "+sessao.esquecer_chaves.join(", ")));
    $("protocol-questions").append(d);
  }
  atualizarBloqueio();
}
for(const id of ["evaluation-protocol","evaluation-dataset","repetitions"])$(id).addEventListener("change",mostrarRoteiro);
$("refresh-services").addEventListener("click",servicos);
$("dataset-file").addEventListener("change",async()=>{
  const arquivo=$("dataset-file").files[0];if(!arquivo)return;
  casosProprios=null;const dono=usuario;
  try{
    if(arquivo.size>128*1024)throw new Error("O conjunto deve ter até 128 KB.");
    const casos=JSON.parse(await arquivo.text());
    const r=await requisicao("/conjuntos/validar",{method:"POST",body:JSON.stringify({casos})});
    if(dono!==usuario)return;casosProprios=r.casos;
    $("dataset-status").textContent=r.quantidade+" caso(s) validado(s). Confira as questões antes de executar. Nenhuma chamada de modelo foi feita na validação.";
  }catch(e){if(dono!==usuario)return;$("dataset-status").textContent="Arquivo recusado: "+e.message;}
  finally{$("dataset-file").value="";mostrarRoteiro();}
});
async function acompanhar(id){
  if(poll){clearTimeout(poll);poll=null;}if(!usuario)return;
  const dono=usuario;avaliacaoAtual=id;atualizarBloqueio();
  try{
    const job=await requisicao("/avaliacoes/"+encodeURIComponent(id));if(usuario!==dono||avaliacaoAtual!==id)return;
    const p=job.progresso;
    if(job.estado==="executando"){
      $("evaluation-progress").hidden=false;$("evaluation-progress").max=p?.previstos||1;$("evaluation-progress").value=p?.concluidos||0;
      $("evaluation-status").textContent=(p?p.fase+": "+p.concluidos+" / "+p.previstos+" "+p.unidade+" encerradas (não significa aprovadas). ":"Preparando execução isolada. ")+
        (p?.cenario?(nomesCenario[p.cenario]||p.cenario)+". ":"")+(p?.respostas!==undefined?p.respostas+" / "+p.respostas_previstas+" perguntas tentadas. ":"")+
        (p?.pergunta?"Pergunta atual: "+p.pergunta+". ":"")+"O chat pode ficar mais lento enquanto compartilha o modelo.";
      poll=setTimeout(()=>acompanhar(id),2500);return;
    }
    aberturaVersao++;avaliacaoAtual=null;sessionStorage.removeItem("cma-avaliacao:"+dono);$("evaluation-progress").hidden=true;
    if(job.relatorio){
      $("download-report").href="/interface/avaliacoes/"+encodeURIComponent(id)+"/relatorio";$("download-report").hidden=false;
      mostrarRelatorio(job.relatorio,job.estado==="falhou"?"EXECUÇÃO PARCIAL":"NOVA EXECUÇÃO REAL");
    }
    $("evaluation-status").textContent=job.estado==="falhou"?job.mensagem:"Execução encerrada. Consulte gráficos, qualidade, cobertura e objetivos; testes reprovados ou inconclusivos permanecem visíveis.";
    if(job.estado==="falhou")aviso(job.mensagem,true);
    carregarHistorico();
  }catch(e){if(usuario!==dono)return;avaliacaoAtual=null;$("evaluation-status").textContent=e.message;aviso(e.message,true);sessionStorage.removeItem("cma-avaliacao:"+dono);}
  finally{if(!avaliacaoAtual&&usuario===dono)await servicos();}
}
$("run-evaluation").addEventListener("click",async()=>{
  if(avaliacaoAtual||$("run-evaluation").disabled)return;
  const protocolo=$("evaluation-protocol").value,proprio=$("evaluation-dataset").value==="proprio";
  const quantidade=protocolo==="p6"?"P6 integral: 40 sessões e 42 respostas previstas":(proprio?casosProprios.length:16)*4*Number($("repetitions").value)+" tentativas";
  const dono=usuario,geracao=conexaoVersao,m=selecao();
  const corpo={modelo:m.modelo,protocolo,repeticoes:Number($("repetitions").value),...(proprio?{casos:casosProprios}:{})};
  try{
    const confirmou=await confirmarAvaliacao({protocolo:roteirosAtuais.find(r=>r.id===protocolo)?.nome||protocolo,quantidade,modelo:m.modelo});
    if(!confirmou||dono!==usuario||geracao!==conexaoVersao||avaliacaoAtual)return;
  }catch{aviso("Não foi possível abrir a confirmação da avaliação. Recarregue a página e tente novamente.",true);return;}
  avaliacaoAtual="iniciando";atualizarBloqueio();aviso("");
  try{
    const job=await requisicao("/avaliacoes",{method:"POST",body:JSON.stringify(corpo)});
    if(usuario!==dono)return;aberturaVersao++;sessionStorage.setItem("cma-avaliacao:"+usuario,JSON.stringify({id:job.id,usuario}));
    $("report").hidden=true;$("report-explanation").hidden=true;$("download-report").hidden=true;
    acompanhar(job.id);
  }catch(e){if(usuario!==dono)return;avaliacaoAtual=null;aviso(e.message,true);$("evaluation-status").textContent=e.message;await servicos();}
});
$("demo-profile").addEventListener("change",async()=>{
  if(ocupado)return;
  try{const dados=await requisicao("/demonstracao",{method:"POST",body:JSON.stringify({perfil:$("demo-profile").value})});limparConversa();conectar(dados);aviso("Perfil sintético alterado. Os fatos de cada perfil permanecem separados.");}
  catch(erro){aviso(erro.message,true);}
});
$("reactivate-demo").addEventListener("click",async()=>{
  try{conectar(await requisicao("/demonstracao",{method:"POST",body:JSON.stringify({perfil:$("demo-profile").value||"a"})}));aviso("Acesso local retomado; envie novamente sua mensagem se desejar.");}
  catch(erro){aviso(erro.message,true);}
});
try{
  demonstracao=(await requisicao("/configuracao")).demonstracao_local;
  try{conectar(await requisicao("/sessao"));}
  catch{
    if(demonstracao)conectar(await requisicao("/demonstracao",{method:"POST",body:JSON.stringify({perfil:"a"})}));
    else desconectar();
  }
}catch(erro){aviso("A preparação do acesso local falhou. "+erro.message,true);desconectar();}
