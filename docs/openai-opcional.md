# OpenAI no Cognitive Memory Agents: opção preparada

**Fora do escopo da entrega atual:** em 15/11/2026, o usuário confirmou Ollama como caminho sem assinatura/créditos para professor e avaliações. Este material permanece preservado; não é um pré-requisito nem uma etapa a executar para a entrega. Não houve ativação ou rodada real OpenAI.

Preparação de 15/11/2026, sem chamadas externas ou cobrança. A integração já existia em `src/modelos/openai_adapter.py` desde a arquitetura multprovedor; esta etapa conecta o Docker opcional ao chat atual e permite usar o wrapper isolado do comparativo com OpenAI. Não foi localizada referência chamada “QChat” nos arquivos atuais pesquisados; o modelo local é Qwen via Ollama.

## O que está pronto e o que depende de acesso

- Adaptador OpenAI por Chat Completions, seleção por catálogo e chave exclusivamente no servidor.
- Tokens reportados pela API: `prompt_tokens` → `tokens_entrada`, `completion_tokens` → `tokens_saida`. Ausência permanece desconhecida; não são tokens estimados do texto visível.
- Chat real da aplicação mantém API, regras, recuperação, SQLite e identidade. A interface apresenta o provedor/modelo escolhido e as contagens recebidas. OpenAI não é uma página externa de ChatGPT embutida.
- Ao escolher OpenAI, mensagem e contexto selecionado são enviados ao serviço externo; para avaliação use somente dados sintéticos e configuração explicitamente autorizada.
- Compose opcional inicia apenas preparo de acesso e API: não inicia Ollama nem baixa pesos locais. Credenciais de demonstração continuam em volume privado. Banco e identidades próprios no projeto `cma-openai`.
- Comparativo de desenvolvimento por comando permite `--provedor openai`. O botão de executar comparativo pela interface continua bloqueado para OpenAI; relatórios podem ser abertos no leitor. Nenhuma mudança de autenticação OAuth foi implementada.

**Decisão do grupo:** a entrega usa Ollama local e não depende de créditos ou faturamento OpenAI. ChatGPT Plus não é requisito para usar a API e não inclui seu uso. O login do ChatGPT não fornece automaticamente a chave de API deste adaptador. O caminho opcional não foi ativado nem avaliado com chamadas reais.

Fontes oficiais: [Chat Completions](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create), [contagem de tokens](https://developers.openai.com/api/docs/guides/token-counting), [uso de plano ChatGPT em apps](https://developers.openai.com/siwc/quickstart). Credenciais e disponibilidade do modelo precisam ser verificadas na conta antes de uma rodada real. O modelo do exemplo, `gpt-4.1-mini`, já constava no `.env.example`; não se presume acesso da conta.

## Ativar futuramente, com API e cobrança autorizadas

Não executar estes comandos esperando que o ChatGPT Free conceda acesso. Não enviar chaves no chat, colocá-las no código ou imprimir o Compose com ambiente resolvido. Não alterar o `.env` existente. O exemplo pede a chave sem exibi-la e a exporta somente no processo do PowerShell:

```powershell
cd D:\cognitive-memory-agents
$segredo = Read-Host 'Chave OpenAI da API' -AsSecureString
$credencial = New-Object System.Net.NetworkCredential('', $segredo)
$env:OPENAI_API_KEY = $credencial.Password
try {
    docker compose --env-file .env.example -p cma-openai -f docker-compose.yml -f docker-compose.openai.yml up --build -d
} finally {
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
    $credencial = $null
    $segredo.Dispose()
}
```

Esse terminal deve estar sem chave anterior configurada, para não remover uma variável de outro trabalho. Credenciais são repassadas ao servidor pelo ambiente do contêiner, conforme o contrato existente; não ficam no JavaScript. Abra **http://127.0.0.1:8003/**. Não inicia o navegador automaticamente. Compose 2.24.4 ou posterior é necessário pelo `!override`. O acesso inicial ao chat confirma somente prontidão da API e presença da configuração; a primeira conversa real verifica acesso efetivo ao provedor e pode gerar cobrança.

O modelo é selecionável por `$env:CMA_MODELO_OPENAI` e a porta por `$env:CMA_PORT_OPENAI` antes do comando. Registre o identificador e a configuração de cada rodada; não troque o modelo durante a comparação. Sem chave, o Compose recusa a inicialização antes de criar serviços. Para encerrar sem apagar dados, sem precisar repassar a chave:

```powershell
docker stop cma-openai-api-1
```

## Comparação de tokens depois de liberar a execução

Com a instância OpenAI preparada e autorização para consumo da API, o wrapper executa os sete casos conhecidos de desenvolvimento em banco temporário, separado do chat:

```powershell
docker exec cma-openai-api-1 python -B -m src.interface.comparativo --provedor openai --modelo gpt-4.1-mini --repeticoes 3 --saida /app/dados/avaliacoes-interface/openai-dev-01.json
```

São quatro cenários: sem memória/histórico, histórico completo, memória pré-carregada e memória automática. Use nomes novos para cada arquivo: o wrapper recusa sobrescrita. Mantenha o mesmo modelo em todos os cenários e compare ingestão, pergunta e sessão completa, acerto e cobertura. Para comparar provedores, execute rodadas separadas e identifique tokenizadores/modelos distintos; menor contagem bruta entre modelos não isola efeito da memória. Tokens de contexto não equivalem diretamente a preço, inclusive por diferenças de cache e cobrança.

Esse comando usa desenvolvimento, não libera P6/reservado nem substitui suas revisões. Preserve Ollama como instalação gratuita e independente de chave para o professor. A configuração local atual na porta 8002 não foi reiniciada nem modificada.

## Verificação desta preparação

Testes de contrato simulam SDK, tokens e falhas sem usar credencial real. O preparo `preparar-acesso` é testado para não chamar Ollama e preservar identidades. O wrapper é testado para propagar provedor/modelo, isolar banco e rejeitar OpenAI sem chave antes de iniciar processos. O Compose foi validado com chave fictícia somente por `config`, mostrando apenas serviços `preparar` e `api`; nenhuma conta foi consultada. Isso é validação de configuração/engenharia, não evidência real de respostas ou desempenho da OpenAI.

Suíte nesta preparação: **903 aprovados, 66 ignorados em 18,41 s**, 8 testes JavaScript, lint crítico e `git diff --check` aprovados. São seis casos de teste a mais que os 897 da etapa histórica de 14/11; seus logs e resultados não foram reescritos. Nenhuma execução real de OpenAI, P6 ou conjunto reservado nesta etapa.

## Escolha de provedor para a entrega

O grupo decidiu usar **Ollama com modelo local** para que professor e equipe executem o projeto sem contratar API externa nem depender de créditos de uso. Hardware, energia, armazenamento e download continuam tendo custo; “gratuito” aqui significa ausência de cobrança por uma API de geração no percurso da entrega.

**ChatGPT Plus não é requisito para usar a API da OpenAI nem inclui seu uso.** A API tem acesso e faturamento próprios; uma assinatura do ChatGPT não deve ser tratada como chave de API. A alternativa OpenAI permanece código opcional testado com clientes simulados, sem rodada real e fora do escopo de ativação desta entrega. A escolha não implica que a API esteja comprovadamente executada nem autoriza cobrança.

Fonte oficial: [ChatGPT Plus e separação do uso da API](https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus) e [faturamento separado](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform), conferidos em 20/11/2026. Não confundir ferramentas de IA usadas no desenvolvimento com o provedor integrado ao chatbot.
