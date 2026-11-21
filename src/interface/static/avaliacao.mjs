// Regras de bloqueio puras: usadas pela tela e pelos testes sem navegador.
export function bloqueioAvaliacao({usuario,dados,modelo,simulado,executando}){
  if(!usuario)return "Entre na interface para executar uma avaliação.";
  if(executando||dados?.avaliacao_ativa?.ocupada)return "Já existe uma avaliação em andamento. Aguarde a conclusão; não inicie outra bateria.";
  if(simulado)return "Modo simulado: os testes reais de tokens precisam do agente e Ollama reais.";
  if(!dados?.comparativo_liberado)return dados?.impedimento_avaliacao||"Avaliações desativadas nesta instalação. Atualize e reconstrua a demonstração local preservando os volumes.";
  if(modelo?.provedor!=="ollama")return "Selecione um modelo local Ollama na conversa. Esta tela não inicia chamadas pagas.";
  if(dados?.ollama!=="disponivel")return "Ollama indisponível. Retome o serviço e clique em Atualizar disponibilidade.";
  if(!dados?.modelos_instalados?.includes(modelo?.modelo))return "O modelo selecionado não está instalado no Ollama. Conclua o preparo e atualize a disponibilidade.";
  return null;
}
