# PROMPTS.md: registro de uso de IA (Ezequiel)

Escopo: agente e avaliação (`src/agent.py`, `src/modelos/`, `eval/`).

## Ferramentas usadas

- Claude (chat).
- ChatGPT (versão gratuita).

Cada interação tem o prompt, o resumo da resposta e a decisão (aceito, corrigido ou descartado), com o motivo.

---

## Interações

### 1. Auditoria do escopo (Claude, 28/10/2026)

- **Prompt:** "quero corrigir o que foi feito fora do escopo e ajustar o código para funcionar corretamente, quero interação então me diga o que vai fazer antes de fazer e me faça apenas executar comandos".
- **Resposta:** clonou o repositório, listou os commits meus que mexeram em arquivos da Paloma (Docker, banco) e do Vinicius (regras de memória) e propôs não reverter nada.
- **Decisão:** aceito. Esses arquivos já estavam mesclados e os colegas trabalhavam em cima; reverter quebraria o trabalho deles.

### 2. Diagnóstico do estado local (Claude, 28/10/2026)

- **Prompt:** saída de `git status --short` e `git diff --stat`.
- **Resposta:** havia 33 arquivos não rastreados (backups `.bak`, resultados de tentativas e um script temporário) e nenhum arquivo do projeto alterado. Propôs mover tudo para `D:\backup-ezequiel`, sem apagar.
- **Decisão:** aceito e executado. A sugestão inicial de trocar de branch foi descartada pela própria IA ao ver as alterações pendentes no print, porque misturaria os arquivos.

### 3. Atualizar o master e rodar os testes (Claude, 28/10/2026)

- **Prompt:** saída de `git pull` e `python -m pytest -q`.
- **Resposta:** confirmou 308 testes passando e 1 ignorado. Conferiu as entregas do meu escopo e apontou `PROMPTS.md` vazio e `evidencias/` sem resultados.
- **Decisão:** aceito.

### 4. Validação do resultado "final" antigo (Claude, 28/10/2026)

- **Prompt:** saída do resumo de `results_comparativo_api_final.json`.
- **Resposta:** apontou que o resultado estava desatualizado em relação ao código, que o avaliador tinha sido ajustado várias vezes e que o cenário `memoria_persistente_api` é pré-carregado com o estado esperado (teto ideal, não medição).
- **Decisão:** aceito. Descartei esse resultado e refiz a avaliação com o avaliador congelado, como está no master.

### 5. Docker indisponível (Claude, 28/10/2026)

- **Prompt:** saída do erro do `docker compose up` e de `docker version`.
- **Resposta:** diagnosticou que o motor do Docker Desktop não iniciava (WSL estava ok) e deu uma alternativa: carregar o `.env` na sessão do PowerShell e rodar a API com `uvicorn`.
- **Decisão:** aceito; usei o `uvicorn` para a avaliação. O `docker compose up` continua sem validação na minha máquina.

### 6. Rodada oficial e análise de erros (Claude, 28/10/2026)

- **Prompt:** saída completa da avaliação com 3 repetições.
- **Resposta:** resumiu os resultados, concentrou os erros nos casos de esquecimento, notou o pico de 17.514 ms (carregamento do modelo) e encontrou acentos corrompidos nos prompts do dataset ("explica??es", "n?o").
- **Decisão:** aceito, depois de confirmar o problema no arquivo.

### 7. Correção do dataset e comparação antes e depois (Claude, 28/10/2026)

- **Prompt:** saída de `git diff --stat`, `pytest` e da nova rodada.
- **Resposta:** comando que substitui os 7 padrões corrompidos, testado antes no clone da IA (308 testes passando), e nova rodada com o resultado antigo renomeado para comparação.
- **Decisão:** aceito. O resultado "depois" é o oficial e o "antes" ficou como evidência da diferença. O dataset no master foi verificado: 7, 14 e 7 ocorrências com acento correto e nenhum resíduo de `?`.

### 8. Estrutura do PROMPTS.md (Claude, 28/10/2026)

- **Prompt:** "como consigo pegar esse histórico?" (sobre o histórico dos chats com IA).
- **Resposta:** formas de exportar o histórico e uma tabela de 3 linhas para o `PROMPTS.md`.
- **Decisão:** corrigido. A tabela não cumpria a regra de pelo menos 10 interações com prompt, resposta e decisão; foi substituída por este formato, com um bloco por interação.

### 9. Escopo completo e próximos passos (Claude, entre 28/10 e 04/11/2026)

- **Prompt:** "me de um escopo completto sobre o projeto, e quais serão os proxiimos passos" e "liste o que cada um tem que executar para concluir esse marco".
- **Resposta:** leu o enunciado e montou o escopo, o cronograma por marco e a lista por integrante para o Marco 2.
- **Decisão:** aceito, com a ressalva de que o quarto integrante (Produto e Interface) não está definido e precisa ser confirmado com o grupo.

### 10. Conflitos nos pull requests (Claude, 04/11/2026)

- **Prompt:** "preciso reavaliar o como o projeto está muitas mudanças foram realizadas e temos esses problemas preciso resolver e ver o que mudou para finalizarmos", com dois prints de conflito.
- **Resposta:** simulou o merge de todas as branches no master atual. Só a `feature/memoria-regras` (Vinicius) conflita, porque ela e o master resolveram o mesmo problema do índice de memória de formas diferentes. Recomendou que o Vinicius resolva.
- **Decisão:** aceito. O conflito está em `src/memoria/`, que é escopo dele. Desfecho: o PR foi fechado, pois o Vinicius já havia corrigido o problema em outro PR (#24). A mensagem ao Vinicius ainda não foi enviada.

### 11. Reescrita do avaliador (ChatGPT, 28/10/2026)

- **Prompt:** Texto original não recuperado (histórico do chat truncado). Pedido: melhorar a avaliação de respostas "desconhecido" e evitar vazamento de fatos que deveriam ser esquecidos.
- **Resposta:** reescreveu `avaliar_resposta_comparativo` (normalização, rejeição de fatos esquecidos, expressões de desconhecimento aceitas).
- **Decisão:** aceito na época, descartado como evidência. O avaliador foi ajustado várias vezes e os resultados dessa fase (0/21 sem memória, 13/21 histórico, 14/21 persistente, 0/21 regras, estado das regras em 0/0) foram substituídos pela avaliação oficial com avaliador congelado.

### 12. Métrica de recuperação equivalente (ChatGPT, 28/10/2026)

- **Prompt:** Texto original não recuperado (histórico truncado). Pedido reconstruído pelo contexto: criar a métrica de recuperação equivalente de memórias, com testes.
- **Resposta:** script que adiciona `avaliar_recuperacao_equivalente`, campos no resumo e testes.
- **Decisão:** corrigido. O script gravou `\n` literal no final do arquivo de testes (erro de sintaxe) e o padrão do carro falhou no teste; ambos foram refeitos com novos scripts. A métrica ficou como complementar, pois só reconhece formatos previstos no código; não faz parte da avaliação oficial.

### 13. Métrica de esquecimento efetivo (ChatGPT, 28/10/2026)

- **Prompt:** Texto original não recuperado (histórico truncado). Pedido reconstruído pelo contexto: criar a métrica de esquecimento efetivo, em que fatos esquecidos não podem aparecer na resposta.
- **Resposta:** propôs `avaliar_esquecimento` e deixar de calcular a recuperação exata quando não há memória esperada.
- **Decisão:** descartado. O script foi cancelado porque um trecho não foi encontrado (os acentos se perdem quando o texto vai pelo PowerShell para `python -`). A proposta de ignorar listas vazias foi rejeitada: "casos sem resíduos" (6/6) é uma verificação válida de que nada sobrou após o esquecimento.

---

### 14. Preparação acadêmica e apresentação (Codex, 12/11/2026)

- **Pedido:** consultar o enunciado, preparar a contribuição de agente/provedores/avaliação para a pesquisa, organizar evidências históricas, elaborar roteiro de 3–5 minutos e plano das 20 sessões P6, somente com documentação, sem execução real, commit ou publicação.
- **Resposta produzida:** quatro documentos em `docs/`, com texto acadêmico, oito fontes primárias verificadas, tabelas derivadas dos arquivos existentes, especificações de figuras, roteiro de 4min30s e plano P6 com pré-requisitos/checkpoints. O guia e o índice de avaliações receberam referências aos materiais. Os números foram mantidos com política/data/origem, distinguindo resultados históricos, simulação e entregas da PR #41 em revisão.
- **Revisão necessária:** Zeck e a equipe ainda precisam aceitar/corrigir o texto, conferir as referências para o PDF coletivo e aprovar contratos/gabaritos. Não foi registrada aprovação humana antecipada. A ausência de resultado atual P3/P4/P5, os metadados finais e o checkpoint de persistência após banco vazio foram explicitados, sem preencher valores ou alterar dados para obter sucesso.

## Evidências

- `evidencias/comparativo_oficial_3rep.json`: avaliação oficial.
- `evidencias/comparativo_antes_correcao_encoding.json`: execução anterior à correção dos acentos.

Resultado oficial (7 casos x 3 repetições = 21 por cenário, modelo `qwen2.5-coder:3b`):

| Cenário | Acertos | Tokens | Latência média por caso |
|---|---|---|---|
| sem_memoria | 7/21 (33,3%) | 6.437 | 137 ms |
| historico_completo | 18/21 (85,7%) | 18.710 | 584 ms |
| memoria_persistente_api | 16/21 (76,2%) | 7.733 | 127 ms |
| memoria_regras_api | 17/21 (81,0%) | 7.738 | 92 ms |

## Análise de erros

- A camada de memória acertou tudo: estado das regras 21/21, recuperação exata 15/15 e 6/6 sem resíduos.
- Todas as falhas das duas estratégias de memória estão nos casos de esquecimento (CMP003 e CMP004): sem memória no contexto, o modelo inventa uma cidade ou time, ou deforma a palavra DESCONHECIDO.
- Sem memória, o modelo inventa respostas em quase todos os casos em que deveria dizer DESCONHECIDO.
- No histórico completo houve palavra deformada, erro de formato ("Pratico yoga.") e uma resposta errada ("Pratico natação.").
- O prompt corrompido causava falhas extras: no CMP006 persistente, 2 falhas em 3 antes da correção e nenhuma depois.

## Limitações

- Apenas 7 casos; diferenças de 1 ou 2 respostas são ruído (o modelo não é determinístico).
- `memoria_persistente_api` é pré-carregada com o estado esperado, então representa um teto, não uma medição.
- O avaliador compara texto exato, o que penaliza respostas corretas com formato diferente.
