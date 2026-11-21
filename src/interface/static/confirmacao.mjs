// Apenas confirmação visual. A chamada de avaliação continua no fluxo autenticado.
export function confirmarAvaliacao({protocolo,quantidade,modelo},documento=globalThis.document){
  const dialogo=documento?.getElementById("evaluation-confirmation");
  if(!dialogo||dialogo.open)return Promise.resolve(false);
  documento.getElementById("evaluation-confirm-protocol").textContent=protocolo;
  documento.getElementById("evaluation-confirm-quantity").textContent=quantidade;
  documento.getElementById("evaluation-confirm-model").textContent=modelo;
  dialogo.returnValue="cancelar";
  return new Promise((resolve,reject)=>{
    const fechar=()=>resolve(dialogo.returnValue==="iniciar");
    dialogo.addEventListener("close",fechar,{once:true});
    try{
      dialogo.showModal();
      documento.getElementById("evaluation-confirm-cancel").focus();
    }catch(erro){dialogo.removeEventListener("close",fechar);reject(erro);}
  });
}

export function confirmarExclusao({titulo,descricao},documento=globalThis.document){
  const dialogo=documento?.getElementById("delete-confirmation");
  if(!dialogo||dialogo.open)return Promise.resolve(false);
  documento.getElementById("delete-confirm-title").textContent=titulo;
  documento.getElementById("delete-confirm-description").textContent=descricao;
  dialogo.returnValue="cancelar";
  return new Promise((resolve,reject)=>{
    const fechar=()=>resolve(dialogo.returnValue==="apagar");
    dialogo.addEventListener("close",fechar,{once:true});
    try{dialogo.showModal();documento.getElementById("delete-confirm-cancel").focus();}
    catch(erro){dialogo.removeEventListener("close",fechar);reject(erro);}
  });
}
