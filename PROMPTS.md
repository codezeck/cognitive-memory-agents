# PROMPTS.md: registro de uso de IA (Ezequiel)

Escopo: agente e avaliação (`src/agent.py`, `src/modelos/`, `eval/`).

## 18/11/2026: contexto v3 — acertos e quantidade de tokens

- **Pedido:** “precisamos melhorar os acertos e a quantia de tokens”.
- **Aceito:** confirmação local de operações totalmente reconhecidas, sem atribuir texto local ao modelo; consultas pessoais com prompt breve e fatos atuais; resolução unívoca de negação por valor; limpeza de resíduos na RAM; reconhecimento de suporte também no baseline completo.
- **Correção crítica:** interrompida e preservada a primeira tentativa quando a checagem detectou que a nova gramática poderia bloquear fatos válidos no baseline. Foram acrescentados testes para filhos, profissão e viagem. A nova saída usa fontes identificadas separadamente.
- **Medições:** 48/48 aprovações P4 da memória automática em 16 casos sintéticos com três repetições; o baseline teve 36/48 e um timeout. Economia pareada de 84,88% em 47/48 pares. Na P6: 21/21 aprovações, zero julgamentos não verificados da automática, 3.593/22.228 tokens (83,84% menos) e checkpoints operacionais aprovados no escopo medido.
- **Limites aceitos:** as confirmações de armazenamento não geram tokens, mas têm custo de processamento/SQLite. Os conjuntos anteriores são agora desenvolvimento, não teste reservado. A bateria nova não é cega ou independente. O P4 pode rejeitar a palavra Quatro quando só o numeral 4 está anotado; não alteramos aliases ou resultados retrospectivamente. Equivalência estatística não foi demonstrada.
- **Evidências:** [relatório v3](docs/acertos-tokens-contexto-v3.md) e [decisão anterior à medição](docs/revisao-experimental/decisao-contexto-v3-20261118.md).

## 18/11/2026: confiabilidade, contexto e avaliação real

- **Pedido:** melhorar o que já funciona e concluir a avaliação conforme o escopo do professor. Ao consultar as revisões pendentes, o usuário determinou: “vamos corrigir da nossa maneira o prazo está curto”.
- **Aceito:** corrigir reconhecimento de consultas pessoais, busca por chave e montagem de contexto; manter o baseline completo; testar em ambiente próprio; resolver explicitamente contrato de esquecimento e checkpoint vazio; executar desenvolvimento, P6 e teste separado com Ollama real.
- **Correções da implementação assistida:** os primeiros testes reproduziram dez falhas de suporte. A suíte completa detectou que a opção compacta também atingia o baseline; a construção do agente do baseline foi corrigida e testes de histórico longo passaram. O primeiro preparo P6 tentou observar SQLite antes da criação sob demanda; foi corrigido e recebeu teste de processo real sem LLM. A tentativa inicial foi preservada.
- **Resultados aceitos como evidência:** desenvolvimento 20/21 contra 16/21, P6 com 42 respostas e zero falhas técnicas, persistência/exclusão verificadas no escopo medido e redução de 25,27% dos tokens completos. A bateria separada teve 21/30 contra 24/30 e apenas 2,40% de economia; as metas adicionais foram reprovadas.
- **Descartado:** afirmar sucesso global com base só no desenvolvimento, tratar não verificados como acertos, modificar gabaritos para acompanhar o modelo ou atribuir aprovação aos colegas. A análise textual assistida por IA permanece separada do P4 original e do requisito de revisão humana.
- **Limites:** paráfrases, negação de carro não reconhecida e detalhes inventados ainda falham. O PDF foi atualizado como rascunho com resultados negativos visíveis. Sem publicação, merge, tag, vídeo oficial, licença definida ou envio acadêmico nesta etapa.
- **Referências:** [relatório](docs/melhorias-avaliacao-20261118.md), [decisão](docs/revisao-experimental/decisao-20261118.md), [evidências](evidencias/README.md#rodadas-reais-de-18112026).

## 15/11/2026: autorização de publicação para revisão

O usuário solicitou publicar a última atualização em PR para aprovação e continuar em outro dia. Essa autorização substitui a proibição anterior de commit/push/PR somente para esta publicação; não autoriza merge, tag, envio final ou avaliações bloqueadas. Conferidos branch/base remota, alterações e candidatos novos, padrões de credenciais, datasets oficiais inalterados e testes. PR deve explicitar as falhas/limites, o caminho Ollama e a revisão de Paloma/Vinicius, sem declarar a entrega pronta. Evidências brutas preservadas e sem normalização de fins de linha nesta publicação.

## 15/11/2026: confirmação do caminho gratuito

Após conferir o bloqueio de acesso pelo ChatGPT Free, o usuário determinou manter Ollama para cumprir o requisito de execução sem assinatura/créditos. Registrado o escopo em arquitetura/README e marcada a preparação OpenAI como material preservado fora da entrega atual. Nenhum modelo, serviço, configuração Docker ou dado experimental foi alterado nesta confirmação. CPU deve continuar sendo caminho funcional para hardware desconhecido; GPU é opcional. Eventual troca de modelo exige ensaio de desenvolvimento e configuração identificada, mantendo o mesmo modelo nos cenários do comparativo. P6 e reservado continuam sujeitos às revisões pendentes.

## 15/11/2026: opção OpenAI para chat e tokens

Usuário pediu reaproveitar integração antiga para conversar e comparar tokens com modelos OpenAI; informou possuir somente ChatGPT Free. Identificada base existente no adaptador, catálogo e avaliador. Preparados override Docker opcional sem Ollama/pesos, modo de preparo somente de acesso e parâmetro de provedor no wrapper isolado. Login ChatGPT/OAuth não foi implementado; a chave/créditos exigidos pelo caminho de API continuam indisponíveis. Não foi solicitada chave no chat nem feita chamada externa OpenAI.

Validação: Compose somente `config` com chave fictícia, 903 testes Python aprovados/66 ignorados, 8 JavaScript, lint e diff-check. Novas regressões conferem uso reportado/desconhecido, preparo sem Ollama, isolamento e recusa de OpenAI sem chave. São testes de engenharia; não representam respostas ou tokens reais da OpenAI. Serviço Ollama da porta 8002 preservado. [Caminho e bloqueio](docs/openai-opcional.md). Sem commit/push/PR/tag nem P6/reservado.

## Continuação de 14/11/2026: entrega local revisável

Solicitação: reaproveitar interface existente, automatizar Docker/modelo/autenticação, comprovar fluxo real e RAM, preparar revisões experimentais e artefatos acadêmicos. Base `2be5d51`, branch `fix/validacao-entrega-docker`; sem publicação. Uso de IA para conciliação de código, regressões, análise de logs, documentação e rascunho PDF; não representa revisão humana nem autoria exclusiva do chat reutilizado.

Decisões do usuário: ≥30% de redução de tokens completos, perda ≤5 p.p., nenhum novo vazamento/desatualização; extensão opcional `origem_uso`/`chamadas_modelo_observadas` autorizada preservando resultados antigos. Usuário informou revisão de Vinicius/Paloma, mas ainda sem referência/escopo verificáveis; não liberar P6 automaticamente. Instituição/cidade/docente e composição 3×4 aguardam confirmação.

Verificação: 897 testes Python aprovados/66 ignorados, 8 JavaScript e lint; 80 verificações de navegador com Docker/Ollama reais. Tentativa inicial da suíte teve erro de acesso a temporários; repetição com pasta própria passou. Tentativas intermediárias preservadas. Comparativo real de desenvolvimento: 84 tentativas, 22 falhas de conteúdo; automática 17/21 e 17.094 tokens, histórico 12/21 e 16.017. Aumento de 6,72%: meta global não atingida. Falhas fora da gramática pessoal e abstenção indevida continuam registradas. Nenhuma P6 nem conjunto reservado executados. Dados reservados lidos apenas para proposta estrutural de metadados, sem ajuste posterior de regras/prompts/modelo/gabaritos por seus resultados.

Artefatos e limites: [matriz](docs/andamento-entrega.md), [evidências](evidencias/README.md), [revisão experimental](docs/revisao-experimental/README.md), [checklist](docs/checklist-entrega.md). Rascunho PDF, gráficos e roteiro preparados; vídeo oficial, CI remoto/tag, licença e revisão coletiva continuam pendentes. Não foram enviados avisos a terceiros nem feitos commits/push/PR/merge/tag/envio.

## Ferramentas usadas

Assistência desta etapa: Codex/ChatGPT para auditoria, integração e consolidação documental; sem presumir plano de assinatura ou revisão humana. Contextos disponíveis e coleta dos colegas: [registro de IA](docs/registro-ia/README.md).

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

### 15. Validação real da entrega Docker (Codex, 14/11/2026)

- **Pedido:** conferir a implementação integrada, o enunciado original e o percurso do professor; testar Ollama real em ambiente isolado, corrigir lacunas dentro do escopo e documentar limites, sem publicar ou executar a P6 final.
- **Resposta produzida:** enunciado local lido; PRs #41/#42/#43 confirmadas integradas; Swagger identificado como interface atual e chat de outro worktree identificado como não integrado. Override opcional com volume/porta/tokens próprios, manual e matriz produzidos. A conversa real armazenou, recuperou, atualizou e persistiu fatos; SQLite confirmou exclusão total, e 401/403 e isolamento foram observados. Após excluir, o modelo inventou duas cidades com contexto vazio; as falhas constam no JSONL/log, sem alteração dos resultados históricos. A suíte passou com 827 aprovados e 1 ignorado; inspeção P6 sem execução retornou 21/21 compatíveis.
- **Decisão/revisão necessária:** não há aprovação humana antecipada. A equipe precisa decidir a política de abstenção para fatos pessoais sem evidência antes de uma mudança arquitetural ou de contrato. Não se adotou bloqueio genérico, troca de modelo, fallback nem ajuste seletivo de prompt. Observação direta da RAM, contratos/gabaritos P6, QA visual, vídeo e avaliação final continuam pendentes. Código, regras, datasets e artefatos históricos não foram alterados; nada foi publicado.
- **Evidências:** [relatório e matriz](docs/validacao-entrega-docker.md), [JSONL real](evidencias/agente/validacao-docker-20261114-07701ee5.jsonl) e [log da API](evidencias/agente/validacao-docker-20261114-07701ee5-api.log).

### 16. Correção da abstenção e repetição do ensaio (Codex, 14/11/2026)

- **Pedido:** investigar regras, recuperação, contexto, histórico e geração; corrigir a falha sem bloquear conversa comum; criar regressões e ensaiar Docker/Ollama reais com repetições, preservando dados/serviços e sem P6/publicação.
- **Investigação e decisão técnica:** rastreado o percurso e registrado o contexto efetivamente encaminhado ao SDK. Reset/exclusão já existiam; o gerador ainda inventava sem suporte. A tentativa só com instruções explícitas falhou e foi rejeitada. Implementada checagem local de suporte para consultas pessoais diretas, sem alterar armazenamento, aquisição de memória, contratos HTTP ou adaptadores. Fatos apoiados e perguntas gerais seguem no LLM; parte pessoal desconhecida de pergunta mista é separada. A gramática é conservadora e não universal.
- **Evidências/resultados:** base reexecutada com 827 aprovados e 1 ignorado; suíte final com 855 aprovados e 66 ignorados (1 semântico e 65 reais opt-in). Bateria real separada: 65 aprovados, 115 chamadas efetivas a `qwen2.5-coder:3b` e 30 abstenções locais, sem atribuí-las ao modelo. Rodadas anteriores registram alucinações, abstenções indevidas do candidato de prompt e duas falhas de formato do candidato v2; nada foi sobrescrito. [Relatório](docs/validacao-entrega-docker.md) e [resumo bruto de todas as rodadas](evidencias/agente/20261114-abstencao-c4468914-resumo.json).
- **Revisão/limites:** implementação feita dentro do pedido, sem registrar aprovação humana antecipada dos artefatos. Equipe ainda deve revisar a política e suas limitações; RAM direta, P6 e comparativo global não foram executados. Nenhum commit, push, PR, publicação ou merge.

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


## Fechamento da candidata v3 — 18/11/2026

A assistência de IA ajudou a implementar busca por chave e contexto compacto, confirmações locais com proveniência explícita, tratamento limitado de negação, testes e executores de avaliação. Também consolidou o relatório v3, PDF, gráficos/CSV derivados dos brutos, checklist e inventário de licenças. O usuário confirmou a instituição conforme transcrita, composição de três integrantes e MIT com autorização do grupo, e autorizou a publicação. Resultados negativos e desconhecidos foram preservados. Revisão humana não foi atribuída à IA nem aos colegas. A tentativa de preparar vídeo pela ferramenta de controle de tela foi encerrada por falha na confirmação da URL; roteiro atualizado, sem vídeo fictício. Evidências e estado atual: `evidencias/entrega-v3-20261118/README.md`.


## 18/11/2026 — Consolidação para validação e registro das conversas

- **Pedido, resumido:** atualizar README/GitHub e documentos necessários, preservar nomes/RA e a mensagem do Tema 11 como primeiro dos 16 temas do portfólio, preparar prompt de continuidade e listar tarefas para os colegas; reunir o contexto disponível das conversas.
- **Esclarecimento do usuário:** a prioridade citada como “font” era conferir e atualizar o README online.
- **Decisão:** preservar integralmente o cabeçalho e a mensagem do portfólio; consolidar documentação corrente, cinco decisões de arquitetura, manual do GitHub até o chat e comandos Docker para avaliação isolada. Contextos dos colegas dependem de envio por eles.
- **Correções e limites:** separar histórico da v3, manter as 12 respostas do baseline sem parecer até revisão humana e não converter a síntese desta conversa em transcrição integral ou aprovação dos colegas. Vídeo, captura real de CI, revisão humana e fechamento da tag continuam com critérios próprios.
- **Artefatos:** [documentação técnica](docs/README.md), [prompt](docs/prompt-finalizacao.md), [contextos e modelo](docs/registro-ia/README.md), [pendências](docs/pendencias-equipe.md). Validação efetiva e publicação são registradas no índice de evidências depois da execução.

Retomada em 19/11/2026: conferidos 960 testes Python aprovados/66 ignorados, oito JavaScript, lint e links locais; o comando Docker P6 completou 40 registros de sessão e 42 respostas sem falhas técnicas. Acrescentado preparo de protocolo que aceita apenas LF/CRLF, com seis regressões. A conferência operacional é separada dos resultados originais da pesquisa. Evidências em `evidencias/entrega-v3-20261118/verificacao-documentacao/`.
