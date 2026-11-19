# Pendências para fechar a entrega

Divisão proposta em 18/11/2026. As responsabilidades abaixo são sugestões de execução, não confirmações de aceite ou tarefas já realizadas pelos colegas. Instituição, composição de três integrantes e MIT estão resolvidas.

| Entrega restante | Responsável proposto | Como comprovar conclusão |
|---|---|---|
| Revisar regras, atualização, negação e respostas do baseline | Vinícius, com revisão de outro integrante | [Planilha de revisão](revisao-experimental/revisao-humana-baseline-v3.csv) preenchida com autor/data/parecer; análise complementar separada dos brutos |
| Conferir Docker, isolamento, persistência e exclusão no ambiente do professor | Paloma | Rodar [manual](manual-professor.md), registrar versão/ambiente e resultado; conferir logs e checkpoints já coletados |
| Revisar pesquisa e referências na fonte original | Os três, dividindo capítulos | Parecer com correções/aceite do texto, citações e fontes; não transformar checagem automática em revisão do grupo |
| Fornecer contextos das conversas de IA | Cada integrante; Paloma e Vinícius ainda precisam enviar os seus | [Modelo](registro-ia/modelo-contexto-colega.md) preenchido e conferido pelo autor; consolidar no `PROMPTS.md` |
| Gravar vídeo em tela inteira de 3–5 minutos | Ezequiel ou Paloma; revisão pelos outros | MP4 real, código identificado, Docker iniciando e fluxo principal; [roteiro](roteiro-demonstracao.md); ausência de segredos |
| Revisar PR #45 | Paloma ou Vinícius, sem autoaprovação do autor | Parecer humano no [PR](https://github.com/codezeck/cognitive-memory-agents/pull/45); revisão já solicitada |
| Integrar e congelar a versão revisada | Mantenedor do repositório, após revisão | `master` contém os commits aprovados; manual aponta para a versão publicada |
| Tag `v1.0` e CI verde nessa tag | Mantenedor; Paloma pode conferir | SHA, URL e captura PNG real do CI; não mover tag publicada |
| Índice final, demonstração e envio | Ezequiel com conferência do grupo | Vídeo/CI/revisões vinculados; cada um explica código sem IA; envio no canal definido pelo professor |

## O que já existe

Código v3, P6 real, validação sintética, testes, licença, pesquisa, gráficos, CSV/JSON, logs, análise de falhas e manual. O [índice](../evidencias/entrega-v3-20261118/README.md) distingue datas/versões. A atualização documental preserva os integrantes e a mensagem do Tema 11 no README. O [checklist](checklist-entrega.md) acompanha o fechamento.

## Limites de automação

As conversas privadas dos colegas dependem deles. Revisão humana, defesa oral e envio institucional não são substituídos por IA. O controle de tela encerrou a tentativa de vídeo/captura nesta sessão por não confirmar a URL no Windows; o roteiro está preparado para gravação pelo grupo. Não há vídeo oficial nem captura da tela do CI declarados concluídos.

## Próxima sessão

Usar o [prompt de continuidade](prompt-finalizacao.md), conferir PR/CI/revisões atuais e executar primeiro o que já estiver autorizado e independente de parecer humano. O enunciado disponível prevê Marco 4 em 21/11, demonstração em 28/11 e envio de 30/11 a 02/12; orientação posterior do professor prevalece.
