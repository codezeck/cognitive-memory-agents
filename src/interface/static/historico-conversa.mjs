// Histórico visual deste navegador; nunca é enviado como contexto ao modelo.
export function criarHistorico(armazenamento){
  const memoria=new Map(),chave=u=>"cma-conversa-v1:"+u;
  function ler(usuario){
    if(!usuario)return [];
    if(memoria.has(usuario))return memoria.get(usuario).map(x=>({...x,memorias:[...x.memorias]}));
    let itens=[];
    try{const dados=JSON.parse(armazenamento.getItem(chave(usuario))||"[]");
      if(Array.isArray(dados))itens=dados.filter(x=>x&&["Você","Agente","Sistema"].includes(x.papel)&&typeof x.texto==="string"&&x.texto.length<=100000&&Array.isArray(x.memorias)&&x.memorias.every(m=>typeof m==="string")).slice(-500);
    }catch{}
    memoria.set(usuario,itens);return ler(usuario);
  }
  function salvar(usuario,itens){
    if(!usuario)return;
    memoria.set(usuario,itens);
    try{armazenamento.setItem(chave(usuario),JSON.stringify(itens));}catch{}
  }
  return {ler,adicionar(usuario,papel,texto,memorias=[]){salvar(usuario,[...ler(usuario),{papel,texto,memorias:[...memorias]}].slice(-500));},
    limpar(usuario){if(!usuario)return;memoria.delete(usuario);try{armazenamento.removeItem(chave(usuario));}catch{};memoria.set(usuario,[]);}};
}
