# Pendências para fechar a entrega

Atualizado em 22/11/2026; responsabilidades propostas, sujeitas à distribuição do grupo. As responsabilidades abaixo são sugestões de execução, não confirmações de aceite ou tarefas já realizadas pelos colegas. Instituição, composição de três integrantes e MIT estão resolvidas.

| Entrega restante | Responsável proposto | Como comprovar conclusão |
|---|---|---|
| Revisar regras, atualização, negação e respostas do baseline | Vinícius, com revisão de outro integrante | [Planilha de revisão](revisao-experimental/revisao-humana-baseline-v3.csv) preenchida com autor/data/parecer; análise complementar separada dos brutos |
| Conferir Docker, isolamento, persistência e exclusão no ambiente do professor | Paloma | Rodar [manual](manual-professor.md), registrar versão/ambiente e resultado; conferir logs e checkpoints já coletados |
| Revisar pesquisa e referências na fonte original | Os três, dividindo capítulos | Parecer com correções/aceite do texto, citações e fontes; não transformar checagem automática em revisão do grupo |
| Conferir os históricos de IA já reunidos | Cada integrante | [Três históricos e PROMPTS](registro-ia/README.md) revisados contra as fontes; registrar correções/aceite |
| Revisar o vídeo publicado | Os três | [MP4 de 4min59,75s](../evidencias/fechamento-entrega-20261122/demonstracao.mp4), origem/edição registradas; conferir versão, conteúdo e ausência de segredos antes do envio |
| Revisar PR #47 | Paloma ou Vinícius, sem autoaprovação do autor | Parecer humano no [PR](https://github.com/codezeck/cognitive-memory-agents/pull/47); PRs #45 e #46 já integradas. O merge da #46 foi feito por Vinicius000011; a consulta não retornou parecer formal, que não foi presumido |
| Integrar e congelar a versão revisada | Mantenedor do repositório, após revisão | `master` contém os commits aprovados; manual aponta para a versão publicada |
| Tag `v1.0` e CI verde nessa tag | Mantenedor; Paloma pode conferir | SHA, URL e captura PNG real do CI; não mover tag publicada |
| Índice final, demonstração e envio | Ezequiel com conferência do grupo | Vídeo/CI/revisões vinculados; cada um explica código sem IA; envio no canal definido pelo professor |

## O que já existe

Código v3, P6 real, validação sintética, testes, licença, pesquisa, gráficos, CSV/JSON, logs, análise de falhas e manual. O [índice](../evidencias/entrega-v3-20261118/README.md) distingue datas/versões. A atualização documental preserva os integrantes e a mensagem do Tema 11 no README. O [checklist](checklist-entrega.md) acompanha o fechamento.

## Limites de automação

Os históricos fornecidos já foram reunidos; complementos privados dependem dos autores. O usuário gravou e escolheu o vídeo definitivo, agora publicado com cortes de pausas e duração conferida. A instalação isolada de 22/11 passou em 19 verificações. Revisão humana, defesa oral e envio institucional não são substituídos por IA. Captura e link do CI da tag ainda dependem da criação da versão aprovada.

## Próxima sessão

Usar o [prompt de continuidade](prompt-finalizacao.md), conferir PR/CI/revisões atuais e executar primeiro o que já estiver autorizado e independente de parecer humano. O enunciado disponível prevê Marco 4 em 21/11, demonstração em 28/11 e envio de 30/11 a 02/12; orientação posterior do professor prevalece.

## Atualização de 20/11

Ezequiel confirmou o aceite do professor para três integrantes e encerrou a validação funcional da bateria ensaiada. A [consolidação](consolidacao-testes-20261120.md) e o PDF atualizado passam à revisão documental coletiva, com médias por roteiro e qualidade separada. Não marcar essa atualização como revisão humana já realizada. Seguem os itens de fechamento acima, os registros dos colegas e a revisão dos limites da [métrica separada de informações antigas](informacao-antiga-respostas.md), já implementada.
