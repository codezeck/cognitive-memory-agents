# Resultados existentes do agente: tabelas, figuras e limites

Inventário documental de 12/11/2026, sobre `master` `fc759f3`. Apenas leitura dos arquivos e agregação descritiva dos registros existentes; não houve geração por LLM, novo julgamento de respostas, alteração de datasets ou sobrescrita de resultados.

Este arquivo concentra os números para a [contribuição acadêmica](contribuicao-academica-zeck.md). Fórmulas atuais, comandos e semântica dos indicadores permanecem no [guia de avaliação](guia-avaliacao.md). A política `p4-v3` e seus testes estão em revisão na [PR #41](https://github.com/codezeck/cognitive-memory-agents/pull/41); não foram trazidos para esta branch documental.

## 1. O que existe para P3/P4/P5

Foi inspecionado o conjunto de JSON rastreados pelo Git. Os arquivos experimentais encontrados não contêm `tokens_por_etapa`, objetos `julgamento`, `versao_julgador` ou `versao_metricas_resposta`. Os resultados de recuperação também têm outra unidade experimental. Portanto, **não há tabela de resultado real do protocolo P3/P4/P5 atual a preencher com números versionados**.

| Camada | Evidência utilizável agora | O que ainda falta para a tabela experimental final |
|---|---|---|
| P3: contabilização de tokens | Código `tokens_etapa`, testes de tokens e documentação; totais históricos com rótulo legado | Ingestão/pergunta final/sessão, entrada/saída, pares medidos e cobertura em uma nova rodada congelada |
| P4: julgamento | 26 respostas rotuladas de desenvolvimento e 20 de validação; testes como evidência de engenharia | Julgamentos de respostas realmente geradas com versão identificada e revisão dos rótulos |
| P5: métricas de resposta | Implementação `p5-v1`, testes de denominadores e aplicabilidade | Taxas e coberturas de factualidade, abstenção e vazamento na nova rodada |
| P6: sessões integradas | Dataset, 21 anotações, executor e relatório estrutural | Trajetórias e checkpoints reais; nenhuma taxa funcional disponível |

Não converter testes simulados em observações de modelo. Não reaplicar silenciosamente P4-v3 às respostas antigas: isso seria uma nova análise retrospectiva, exigiria política e proveniência próprias, e não é a rodada atual.

## 2. Inventário de artefatos

| Artefato | Conteúdo observado | Uso permitido e limite |
|---|---|---|
| [comparativo_oficial_3rep.json](../evidencias/comparativo_oficial_3rep.json) | 84 registros: 7 casos × 3 repetições × 4 cenários | Comparativo histórico; anterior às etapas/julgamentos atuais |
| [comparativo_antes_correcao_encoding.json](../evidencias/comparativo_antes_correcao_encoding.json) | Mesma quantidade de registros, rodada anterior | Comparação descritiva antes/depois; não isola causalidade da correção |
| [eval/results.json](../eval/results.json) | 18 registros: 6 casos × 1 repetição × 3 cenários | Ensaio legado cujo próprio cabeçalho declara memória externa simulada; não comprova integração real |
| [eval/results_anterior.json](../eval/results_anterior.json) | 75 registros, 25 por cenário, 5 repetições declaradas | Outro ensaio legado; não combinar com o dataset atual de seis casos ou com o comparativo de sete |
| [respostas_dev.json](../eval/julgamento/respostas_dev.json), [respostas_validacao.json](../eval/julgamento/respostas_validacao.json) | 26 e 20 respostas previamente rotuladas | Exemplos para explicar o julgador; não são novas respostas de uma rodada experimental |
| [resultados_recuperacao_hash.json](../evidencias/memoria/resultados_recuperacao_hash.json), [semântico](../evidencias/memoria/resultados_recuperacao_semantico.json) | Recuperação em 20 sessões, sem LLM gerador | Contexto complementar de Vinicius; tokens estimados por caracteres |
| [resultados_regras.json](../evidencias/memoria/resultados_regras.json) | Extração em desenvolvimento/avaliação e checkpoints de conversas | Evidência complementar de regras, sob revisão de Vinicius |
| [fluxo Docker de 05/11](../evidencias/agente/fluxo-memoria-docker-2026-11-05.txt) | Lembrar, atualizar, reiniciar contêiner, esquecer, apagar usuário e 401/403; commit `c7451fe` | Log histórico, sem prova completa de todos os resíduos em RAM nem substituição da gravação final |
| [revisão P6](../eval/memoria/relatorio_revisao_p6.md) | 21 anotações, 10 compatíveis/11 incompatíveis com P4-v2 | Compatibilidade estrutural da master; a PR #41 informa 21/21 em revisão |

O índice existente identifica a rodada oficial com o avaliador `0a847f8` e o modelo `qwen2.5-coder:3b`. O JSON não grava esses campos de versão/provedor/modelo por registro. Essa proveniência vem da documentação e deve ser descrita como tal; não acrescentar campos ao arquivo histórico.

## 3. Tabela pronta — comparativo histórico oficial

Fonte: `evidencias/comparativo_oficial_3rep.json`, objeto `resumo`. `gerado_em` é `2026-10-29T00:27:35.880206+00:00`, equivalente a **28/10/2026 21:27:35 no fuso de São Paulo**. São 21 tentativas por cenário, sete casos repetidos três vezes, todas com execução registrada. A aprovação é a da política antiga.

| Cenário histórico | Aprovados/tentados | Aprovação legada | Tokens totais registrados | Média de latência por caso registrada (ms) |
|---|---:|---:|---:|---:|
| Sem memória | 7/21 | 33,33% | 6.437 | 137,48 |
| Histórico completo | 18/21 | 85,71% | 18.710 | 584,19 |
| Memória pré-carregada pela API | 16/21 | 76,19% | 7.733 | 127,38 |
| Memória por regras, percurso antigo | 17/21 | 80,95% | 7.738 | 92,38 |

Legenda sugerida: “Comparativo preliminar histórico de sete casos sintéticos com três repetições por cenário; julgador e contabilização anteriores ao protocolo P3/P4/P5 atual. Fonte: artefato do projeto, rodada de 28/10/2026.”

Os contextos esperados dos dois cenários de memória foram recuperados exatamente em **15/15** tentativas com memória esperada. Nas **6/6** tentativas sem memória esperada, o registro indica ausência de memórias usadas. Esses denominadores são subconjuntos das 21 tentativas, não casos independentes adicionais. Não converter os 15/15 em taxa de resposta correta nem os 6/6 em prova de remoção de registros inativos ou de RAM.

### Variação observada por repetição

Fonte: agrupamento somente de `resultados` por `cenario` e `repeticao`; o numerador soma o booleano histórico `passou`. Nenhuma resposta foi rejulgada.

| Cenário | Repetição 1 | Repetição 2 | Repetição 3 | Soma |
|---|---:|---:|---:|---:|
| Sem memória | 1/7 | 3/7 | 3/7 | 7/21 |
| Histórico completo | 7/7 | 5/7 | 6/7 | 18/21 |
| Memória pré-carregada | 5/7 | 5/7 | 6/7 | 16/21 |
| Memória por regras, percurso antigo | 6/7 | 5/7 | 6/7 | 17/21 |

O histórico teve mais aprovações que as duas condições de memória. É adequado dizer que os totais registrados foram menores nas condições de memória; não dizer que o acerto foi mantido, que se mediu todo o custo do sistema ou que o experimento comprova economia P3 por etapa.

### Antes e depois do encoding

Fonte: objetos `resumo` das duas rodadas. A anterior tem `gerado_em: 2026-10-29T00:23:02.879767+00:00` (28/10 às 21:23:02 em São Paulo).

| Cenário | Aprovados antes | Aprovados depois | Tokens antes | Tokens depois |
|---|---:|---:|---:|---:|
| Sem memória | 6/21 | 7/21 | 6.804 | 6.437 |
| Histórico completo | 16/21 | 18/21 | 19.786 | 18.710 |
| Memória pré-carregada | 15/21 | 16/21 | 8.122 | 7.733 |
| Memória por regras, percurso antigo | 18/21 | 17/21 | 8.116 | 7.738 |

A aprovação caiu no último cenário. O modelo varia entre execuções; não chamar o quadro de “melhora em todos os cenários” nem atribuir toda diferença ao encoding. Usá-lo como registro de correção dos dados e da necessidade de repetir medições, sem testes de significância ou intervalos inventados.

## 4. Tabela complementar — recuperação e regras

Reutilizar com revisão de Vinicius e referência ao [índice próprio](../evidencias/memoria/README.md). Esses experimentos não são P6 real.

| Recuperação, 21 perguntas, k=3 | Hash lexical | Semântico |
|---|---:|---:|
| Acerto geral registrado | 71,43% | 100% |
| Lembranças corretas entre perguntas com alvo | 64,71% | 100% |
| Informação desatualizada anotada, sobre todas as perguntas | 0% | 0% |
| Esquecimento correto segundo ausência de termos proibidos | 100% | 100% |
| Tokens médios estimados de contexto recuperado | 10,3 | 17,9 |
| Tokens médios estimados do histórico de fatos | 40,6 | 40,6 |
| Redução de contexto estimada registrada | 74,5% | 55,9% |

`src/memoria/benchmark.py` não chama LLM e estima tokens por `ceil(caracteres/4)`. O seu indicador de esquecimento considera ausência dos termos proibidos anotados, não inspeção de toda a persistência ou prova de busca totalmente vazia. Separar esses números dos tokens reportados pelo gerador e das respostas do chatbot. A API usa hash por padrão.

No conjunto final de regras, o artefato registra **31/50 frases exatas (62%)**, precisão **89,29%**, revocação **58,14%**, F1 **70,42%** e **9/13 checkpoints corretos (69,23%)**; usar as casas dos campos armazenados, sem interpretar arredondamento como maior precisão experimental. Desenvolvimento e avaliação têm distribuições diferentes e autoria compartilhada com as regras. Análise detalhada já existe em [falhas das regras](falhas-conhecidas-regras.md).

## 5. Figuras e tabelas que podem ser usadas

Estas são especificações de figuras, com dados já tabulados; não são imagens nem resultados novos. Ao exportar uma figura para o PDF, manter título, unidade, denominadores, política, fonte e data. Não juntar escalas em eixo duplo.

| Identificador e figura | Dados/eixos | Uso e ressalva obrigatória |
|---|---|---|
| F1 — Aprovação legada por cenário | Barras de 0–100%; numeradores 7, 18, 16, 17 e denominador 21 | Gráfico histórico do agente; sete casos × três repetições; sem inferência sobre P4-v3 |
| F2 — Tokens totais históricos | Barras com 6.437, 18.710, 7.733, 7.738; eixo “tokens registrados na rodada” | Mostrar separado de F1; não rotular como custo completo ou ingestão P3 |
| F3 — Variação entre repetições | Pontos de aprovações/7 da tabela por repetição | Expor variabilidade observada; não desenhar intervalo de confiança sem método/dados suficientes |
| F4 — Recuperação hash versus semântica | Barras de acerto e lembranças corretas, em painéis separados | Resultado de busca, sem chatbot; atribuir a Vinicius |
| T1 — Comparativo histórico | Tabela da seção 3 | Pode entrar em resultados preliminares com todos os limites |
| T2 — Antes/depois | Quadro da seção 3 | Apêndice de integridade dos dados; não prova causalidade |
| T3 — Taxonomia de falhas | Referenciar três casos de `casos-de-falha.md` e seu artefato de origem | Não criar novos exemplos como se tivessem sido observados |
| F5 — Fluxo de contexto | Diagrama da contribuição acadêmica | Figura de arquitetura, sem significado de medição |

### Estruturas reservadas para os resultados finais

| Tabela futura | Colunas necessárias | Situação |
|---|---|---|
| P3 | Cenário, etapa, canal, tokens conhecidos, pares identificados/medidos, cobertura, redução pareada | Sem valores experimentais atuais |
| P4/P5 | Critério/métrica, elegíveis, verificados, aprovados ou vazamentos, não verificados, não aplicáveis, taxa e cobertura | Sem valores experimentais atuais |
| P6 | Execução, usuário/sessão/cenário, tokens por etapa, falhas, configuração comparável, checkpoints e proveniência | Aguardando execução real |

Usar “não medido” ou “não verificado” nessas lacunas; nunca preencher com zero. Gráficos finais devem preservar o conjunto de pares de cada canal e indicar a versão do julgador. O teste final de dez casos continua reservado até receber metadados revisados.

## 6. Proveniência e preservação

SHA-256 dos bytes inspecionados no checkout desta máquina (outro checkout pode converter CRLF/LF):

| Arquivo | SHA-256 |
|---|---|
| `evidencias/comparativo_oficial_3rep.json` | `f247abd524075477f74b5f43511dc80313c67d7ec183d13f199e5962727bb5af` |
| `evidencias/comparativo_antes_correcao_encoding.json` | `ebe1529cc3b8e0a711f309546d0f22c65b5dc05821e77d068c93cb8901e0eca4` |
| `eval/results.json` | `ec3d50dd91810198016700d1c32ee16c108bdaf7dd16a51f3ceff127a562a7d4` |
| `eval/results_anterior.json` | `370196a9590d70609fc18664d8b20f1b76618b7c912c6d9c72bd17468a2104e8` |

Reprodução dos experimentos segue o guia, sempre com saída nova, ambiente dedicado e versão identificada. Os scripts de memória/regras e `evaluate.py` podem sobrescrever resultados; os comparativos também executam operações sobre usuários. Não executar esses comandos apenas para desenhar gráficos: as tabelas acima podem ser conferidas lendo os JSON existentes. Não foi gerado novo artefato experimental nesta preparação.
