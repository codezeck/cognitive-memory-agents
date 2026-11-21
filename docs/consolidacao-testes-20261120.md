# Consolidação dos comparativos locais — 20/11/2026

Ezequiel validou a bateria no escopo ensaiado e autorizou a transição para a documentação. Isso não substitui revisão humana de PR, vídeo, CI da versão final ou entrega institucional. A composição de três integrantes foi aceita pelo professor, conforme confirmação explícita de Ezequiel; não é pendência.

## Fontes e cálculo

Foram inventariados 14 relatórios do perfil Professor desta instalação: 12 comparativos sintéticos e duas P6. Os JSON originais foram copiados byte a byte, com SHA256, para o [pacote de evidências](../evidencias/consolidacao-interface-20261120/README.md). Este levantamento não abrange automaticamente outras instalações, perfis ou conversas privadas. Não houve novas chamadas ao modelo para consolidá-lo.

A redução consolidada é `100 × (1 − soma dos tokens automáticos / soma dos tokens do histórico)`, usando pares únicos de caso, repetição, provedor e modelo. A média de consumo é a soma de tokens dividida pelas tentativas medidas. Cada tentativa sintética compreende ingestão e pergunta final, podendo envolver várias chamadas. Não é uma média por chamada nem uma sessão P6.

Os consolidados principais exigem quatro cenários completamente medidos, pares completos e ausência de falha técnica. Respostas semanticamente reprovadas não são excluídas. Uma rodada com timeout ficou descrita à parte: 47/48 pares, redução de 85,08% somente nesses pares, custo total desconhecido. As P6 usam outra unidade e são apresentadas separadamente. Não transformar tokens ausentes em zero.

## Resultados por conjunto

| Conjunto e escopo | Rodadas completas | Tentativas por cenário | Redução consolidada |
|---|---:|---:|---:|
| Oficial, histórico de versões | 9 | 400 | 84,80% |
| Oficial, versão atual do comparativo | 1 | 48 | 84,91% |
| Personalizado, versão atual | 2 | 80 | 74,13% |

O histórico oficial é descritivo de desenvolvimento, não uma estimativa isolada da versão final. Não juntar oficial e personalizado numa média universal. A mudança de roteiro altera os fatos, o número de mensagens e as oportunidades de abstenção. A faixa observada não é intervalo de confiança, e repetições do mesmo roteiro não são amostras independentes.

## Consumo médio dos quatro cenários na versão atual

| Cenário | Oficial: tokens por tentativa, 48 tentativas | Personalizado: tokens por tentativa, 80 tentativas |
|---|---:|---:|
| Histórico completo | 857,79 | 773,44 |
| Memória automática | 129,42 | 200,09 |
| Sem memória | 76,79 | 78,25 |
| Memória pré-carregada | 129,42 | 143,25 |

O personalizado somou 61.875 tokens no histórico, 16.007 na automática, 6.260 sem memória e 11.460 na pré-carregada. Foram 20 tentativas por cenário na primeira rodada e 60 na segunda, com cobertura integral. A pré-carregada recebe estado-ouro e não inclui o custo de produzir esse estado. O controle sem memória atual envia somente a pergunta final ao Ollama; não recebeu os fatos pessoais anteriores. Regras, embeddings, armazenamento e infraestrutura não estão contabilizados em tokens de geração.

## Evolução do executor

As etapas abaixo identificam conjuntos de hashes do executor, não fases P1–P6 nem ensaios que isolem causalmente uma manutenção. O núcleo do agente tem hashes coincidentes nesses comparativos. São mantidos separados dataset, modelo, método do controle e versão do executor.

| Etapa registrada / conjunto | Rodadas completas | Redução consolidada |
|---|---:|---:|
| Etapa 1 / oficial | 2 | 84,44% |
| Etapa 2 / oficial | 4 | 84,86% |
| Etapa 3 / oficial | 2 | 84,87% |
| Etapa 4 / oficial | 1 | 84,91% |
| Etapa 4 / próprio | 2 | 74,13% |

As etapas 1 e 2 usavam controle local de abstenção: seus zeros não medem Ollama nativo. Na etapa 3 o controle passou a consultar Ollama diretamente. Na etapa 4 o comparativo passou a usar 180 segundos por chamada e 210 segundos no percurso da API, com preservação de parcelas observadas em falha. Os padrões da conversa normal e da P6 foram preservados. Se o provedor não devolver uso, a medição permanece desconhecida. O supervisor do histórico permite `30 + 180 × turnos` segundos, sem repetir chamadas enquanto espera.

## Qualidade na última rodada personalizada

Vinte casos, três repetições: 60 tentativas por cenário, 240 no total, com 45 oportunidades factuais e 15 de abstenção por cenário. Não são 60 casos distintos.

| Cenário | Fatos aprovados / oportunidades | Fatos não verificados | Abstenções aprovadas / oportunidades | Abstenções não verificadas | Conteúdo + formato / tentativas | Tokens completos |
|---|---:|---:|---:|---:|---:|---:|
| Histórico completo | 44/45 | 0 | 8/15 | 0 | 48/60 | 46.282 |
| Memória automática | 42/45 | 0 | 15/15 | 0 | 50/60 | 11.989 |
| Sem memória | 1/45 | 7 | 7/15 | 2 | 5/60 | 4.697 |
| Pré-carregada | 40/45 | 5 | 15/15 | 0 | 54/60 | 8.597 |

A automática teve 93,33% de aprovações factuais sobre todas as 45 oportunidades e o histórico 97,78%: diferença de −4,44 pontos percentuais. Houve três reprovações factuais na automática, que continuam negativas; não foram ajustados gabarito, aliases ou respostas. As abstenções corretas foram 15/15 e 8/15, respectivamente. Aprovação de conteúdo não dispensa formato: a automática teve 50/60 aprovações estritas. Não verificados permanecem inconclusivos, não são transformados em erros nem acertos. A redução dessa rodada foi 74,10%, com 11.989 contra 46.282 tokens. O relatório salvo registra 46.282, corrigindo a leitura oral de 46.288.

O arquivo personalizado foi proposto com auxílio de IA e reduzido de 40 para 20 casos compatíveis; cinco anotações foram classificadas como abstenção antes das execuções. O conjunto tem 15 perguntas factuais e cinco de abstenção, e não é teste cego independente. O original e a seleção foram preservados. Conhecimento geral do modelo não garante fatos pessoais que ele não recebeu; qualquer acerto real do controle sem memória continua contado pelo mesmo gabarito.

## P6 e alcance da conclusão

Uma P6 deste histórico teve 20/20 pares completos: 3.556 tokens automáticos contra 21.739 no histórico, redução de 83,64%. A outra teve 15/20 pares e falha técnica; os 83,16% se referem só ao subconjunto medido. A P6 de 18/11 continua preservada com 83,84% em 20/20 pares. Não misturar sessões P6 com tentativas sintéticas para produzir uma média geral.

O usuário encerrou a validação funcional desta bateria e passou à documentação. A economia foi observada no escopo descrito, com erros e incertezas explícitos; não é promessa de redução fixa nem prova de equivalência estatística. A [métrica adicional de informação antiga](informacao-antiga-respostas.md), incorporada em 21/11, distingue valores substituídos de esquecidos e outros usuários, com cobertura gramatical limitada; a validação do usuário não equivale a declarar todos os requisitos de entrega concluídos.

## Reprodução do levantamento

Os relatórios preservados, inventário, grupos, qualidade, tabela CSV, script de recálculo e manifesto ficam no pacote de evidências. Executar `python evidencias/consolidacao-interface-20261120/recalcular.py` apenas lê os JSON e verifica as médias; não inicia Docker, API ou modelos. O cálculo não exige dados privados da instalação.

## Fechamento da leitura de avaliação em 21/11

As médias de tokens acima não mudaram. A [análise de informação antiga](informacao-antiga-respostas.md) foi acrescentada, preservando respostas e P4/P5. Os 14 derivados e seus originais estão identificados no [índice](../evidencias/informacao-antiga-20261121/README.md). Na última personalizada, automática: 0/15; histórico: 0/15; pré-carregada: 0/13 verificadas e duas inconclusivas. Zero nesse indicador não significa acerto factual. A validação funcional pelo usuário está encerrada no escopo ensaiado.
