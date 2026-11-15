import {projetarRelatorio,usoResposta} from "./relatorio.mjs";
const $=id=>document.getElementById(id);
const nf=new Intl.NumberFormat("pt-BR"), pf=new Intl.NumberFormat("pt-BR",{maximumFractionDigits:1});
let usuario=null,ocupado=false,modelos=[],soma=0,chamadas=0,incompleta=false,poll=null;
let demonstracao=false;
const numero=v=>Number.isSafeInteger(v)&&v>0;
const fmt=v=>typeof v==="number"&&Number.isFinite(v)?nf.format(v):"—";
function aviso(texto,erro=false){$("notice").textContent=texto;$("notice").classList.toggle("error",erro);$("notice").hidden=!texto;}
async function requisicao(rota,opcoes={}){
  const resposta=await fetch("/interface"+rota,{credentials:"same-origin",...opcoes,headers:{"Content-Type":"application/json",...opcoes.headers}});
  const dados=resposta.status===204?null:await resposta.json();
  if(!resposta.ok){
    if(resposta.status===401&&rota!=="/sessao")desconectar();
    throw new Error(dados?.mensagem||dados?.detail||"Não foi possível concluir a solicitação.");
  }
  return dados;
}
function travar(valor){
  ocupado=valor;
  for(const id of ["message","send","model","new-session","memory-query","memory-search","forget-all"])
    $(id).disabled=valor||!usuario;
  $("send").textContent=valor?"Aguardando…":"Enviar ↑";
}
function conectar(dados){
  usuario=dados.usuario_id;$("user-name").textContent=usuario;$("test-badge").hidden=!dados.modo_teste;
  $("logout").hidden=demonstracao;$("token").value="";$("login-error").textContent="";
  $("demo-profile").hidden=!demonstracao;$("demo-profile").value=dados.perfil||"a";
  if($("login").open)$("login").close();travar(false);servicos();
  const guardado=sessionStorage.getItem("cma-avaliacao");
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
    const dados=await requisicao("/disponibilidade");
    modelos=dados.modelos||[];const anterior=$("model").selectedOptions[0]?.textContent;
    $("model").replaceChildren();
    modelos.forEach((m,i)=>{const o=elemento("option",m.provedor+" · "+m.modelo);o.value=i;o.disabled=!m.configurado;o.selected=o.textContent===anterior||(!anterior?.includes(" · ")&&m.padrao);$("model").append(o);});
    $("service-status").textContent=dados.ollama==="disponivel"?"API disponível · Ollama acessível":"API disponível · Ollama indisponível";
    const m=selecao();const instalado=dados.modelos_instalados?.includes(m.modelo);
    if(m.provedor==="ollama"&&dados.ollama==="disponivel"&&!instalado)
      $("service-status").textContent="API disponível · modelo selecionado ausente no Ollama";
    if(m.provedor!=="ollama")$("service-status").textContent="API disponível · provedor configurado; disponibilidade não verificada";
    $("run-evaluation").disabled=!dados.comparativo_liberado||!usuario||m.provedor!=="ollama"||!instalado||!$("test-badge").hidden;
    if(!dados.comparativo_liberado)$("evaluation-status").textContent="Avaliações são executadas pelo protocolo revisado, após liberar os pré-requisitos. É possível abrir relatórios existentes.";
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
const nomesEtapa={sessao:"Sessão",pergunta_final:"Pergunta final",ingestao:"Ingestão"};
const nomesCanal={tokens_entrada:"entrada",tokens_saida:"saída",tokens_total:"total"};
function mostrarRelatorio(doc,origem){
  const r=projetarRelatorio(doc);$("report").hidden=false;$("report-empty").hidden=true;$("report-origin").textContent=origem;
  const data=r.geradoEm?new Date(r.geradoEm):null;
  $("report-date").textContent=(data&&!isNaN(data)?"Gerado em "+data.toLocaleString("pt-BR"):"Data não informada")+" · "+(r.modelos.join(", ")||"Modelo não informado")+" · medição separada da conversa";
  const p=r.principal;
  $("reduction").textContent=p.reducao===null?"Não medido":pf.format(Math.abs(p.reducao))+"% "+(p.reducao>=0?"de redução":"de aumento");
  $("reduction-caption").textContent="Total de tokens de geração da sessão, nos mesmos pares medidos.";
  $("baseline-value").textContent=fmt(p.base);$("memory-value").textContent=fmt(p.memoria);
  const max=Math.max(p.base||0,p.memoria||0,1);
  $("baseline-bar").style.width=(p.medido?100*p.base/max:0)+"%";$("memory-bar").style.width=(p.medido?100*p.memoria/max:0)+"%";
  $("pairs").textContent=p.pares+" par(es) medido(s) · "+fmt(p.ausentes)+" sem medição · "+fmt(p.duplicados)+" chave(s) duplicada(s) descartada(s).";
  $("quality").replaceChildren();
  for(const q of r.qualidade){
    const linha=elemento("div",undefined,"quality-row"),nome=q.cenario==="historico_completo"?"Histórico completo":"Memória automática";
    const valores=elemento("span",fmt(q.aprovados)+" / "+fmt(q.casos)+" aprovadas");
    valores.append(elemento("small",fmt(q.falhas)+" falha(s) de execução"));
    linha.append(elemento("span",nome),valores);$("quality").append(linha);
  }
  $("report-rows").replaceChildren();
  for(const l of r.linhas){
    const tr=elemento("tr");
    for(const texto of [nomesEtapa[l.etapa]+" / "+nomesCanal[l.canal],fmt(l.base),fmt(l.memoria),l.reducao===null?"Não medido":pf.format(l.reducao)+"%",String(l.pares)])
      tr.append(elemento("td",texto));
    $("report-rows").append(tr);
  }
}
$("report-file").addEventListener("change",async()=>{
  const file=$("report-file").files[0];if(!file)return;
  try{
    if(file.size>8*1024*1024)throw new Error("Escolha um relatório com até 8 MB.");
    mostrarRelatorio(JSON.parse(await file.text()),"ARQUIVO: "+file.name.slice(0,70));
    $("download-report").hidden=true;$("evaluation-status").textContent="Arquivo lido neste navegador. Não é uma medição da conversa atual.";
    aviso("");
  }catch(e){aviso(e.message,true);}finally{$("report-file").value="";}
});
async function acompanhar(id){
  if(poll){clearTimeout(poll);poll=null;}
  if(!usuario)return;
  try{
    const job=await requisicao("/avaliacoes/"+encodeURIComponent(id));
    if(job.estado==="executando"){
      $("run-evaluation").disabled=true;
      $("evaluation-status").textContent="Avaliação real em andamento. Os cenários fazem várias chamadas ao modelo; você pode continuar usando a conversa.";
      poll=setTimeout(()=>acompanhar(id),3000);return;
    }
    sessionStorage.removeItem("cma-avaliacao");
    if(job.estado==="falhou")throw new Error(job.mensagem);
    mostrarRelatorio(job.relatorio,"EXECUÇÃO REAL");
    $("evaluation-status").textContent="Avaliação concluída. Confira também falhas, qualidade e pares sem medição.";
    $("download-report").href="/interface/avaliacoes/"+encodeURIComponent(id)+"/relatorio";
    $("download-report").hidden=false;await servicos();
  }catch(e){$("evaluation-status").textContent=e.message;aviso(e.message,true);await servicos();}
}
$("run-evaluation").addEventListener("click",async()=>{
  $("run-evaluation").disabled=true;aviso("");
  try{
    const m=selecao();const job=await requisicao("/avaliacoes",{method:"POST",body:JSON.stringify({modelo:m.modelo,repeticoes:Number($("repetitions").value)})});
    sessionStorage.setItem("cma-avaliacao",JSON.stringify({id:job.id,usuario}));acompanhar(job.id);
  }catch(e){aviso(e.message,true);await servicos();}
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
