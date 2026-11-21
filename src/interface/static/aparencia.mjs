// Preferência visual deste navegador. Não interfere no agente nem nas avaliações.
const CHAVE="cma-aparencia";
const temaValido=valor=>valor==="escuro"?"escuro":"claro";

export function instalarAparencia(documento=globalThis.document,armazenamento){
  if(!documento?.documentElement)return ()=>{};
  if(armazenamento===undefined){
    try{armazenamento=globalThis.localStorage;}catch{armazenamento=null;}
  }
  let tema="claro";
  try{
    const salvo=JSON.parse(armazenamento?.getItem(CHAVE)??"null");
    if(salvo&&typeof salvo==="object"&&!Array.isArray(salvo))tema=temaValido(salvo.tema);
  }catch{}
  const botao=documento.getElementById("appearance-theme");
  function aplicar(){
    documento.documentElement.dataset.tema=tema;
    // Preferências antigas de acento não definem a identidade do Caderno.
    delete documento.documentElement.dataset.acento;
    if(botao){
      const rotulo=tema==="escuro"?"Ativar modo claro":"Ativar modo escuro";
      botao.setAttribute("aria-pressed",String(tema==="escuro"));
      botao.setAttribute("aria-label",rotulo);botao.setAttribute("title",rotulo);
    }
    try{armazenamento?.setItem(CHAVE,JSON.stringify({tema}));}catch{}
  }
  const mudar=()=>{tema=tema==="escuro"?"claro":"escuro";aplicar();};
  aplicar();
  botao?.addEventListener("click",mudar);
  return ()=>botao?.removeEventListener("click",mudar);
}
