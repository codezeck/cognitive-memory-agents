# Síntese disponível — Ezequiel, 18/11/2026

Origem: mensagens disponíveis nesta conversa e os artefatos identificados no repositório. Síntese assistida por Codex/ChatGPT, para conferência de Ezequiel; não é histórico integral nem aceite acadêmico dos colegas.

| Pedido/origem | Decisão e resultado registrado | Evidência/limite |
|---|---|---|
| Pedido literal: “precisamos melhorar os acertos e a quantia de tokens” | Avaliar contexto compacto, busca compartilhada e confirmações locais com contagem explícita | [Relatório v3](../acertos-tokens-contexto-v3.md); economia observada não é garantia universal |
| Resposta literal: “vamos corrigir da nossa maneira o prazo está curto” | Usuário autorizou resolver o protocolo local e executar avaliações isoladas | [Decisão](../revisao-experimental/decisao-contexto-v3-20261118.md); não equivale à aprovação de Vinícius/Paloma |
| Resposta literal: “Confirmo MIT e autorização do grupo” | Código/documentação próprios sob MIT, mantendo termos de terceiros | [LICENSE](../../LICENSE), [licenças](../licencas.md) |
| Correção literal: “Faculdade UniAnchieta” | Nome corrigido no README, dados e PDF; três integrantes já validados | [Dados acadêmicos](../dados-academicos.json); cidade e professor omitidos por instrução do usuário |
| Pedido de levantamento antes de novas alterações | Auditoria somente leitura distinguiu execução concluída, análise parcial e itens finais | P6 executada; baseline com 12 julgamentos não verificados; [tarefas restantes](../pendencias-equipe.md) |
| Pedido atual, resumido: atualizar README/GitHub preservando integrantes e texto do Tema 11/portfólio; reunir contextos e dividir pendências | Consolidação documental e prompt de continuidade, com publicação no PR existente após validação | [README](../../README.md), [prompt](../prompt-finalizacao.md), [registro de fechamento](../../evidencias/entrega-v3-20261118/README.md) |

## Correções e descartes relevantes

O primeiro ensaio da v3 foi interrompido quando a nova gramática poderia bloquear suporte válido no baseline; a correção e o log parcial foram preservados. O baseline permaneceu com histórico completo. A palavra “Quatro” não foi acrescentada retrospectivamente ao gabarito para aumentar aprovações. Não se transformaram tokens ausentes em zero nem respostas não verificadas em erros semânticos.

A tentativa de preparar gravação pela ferramenta de controle de tela foi encerrada por não confirmar a URL no Windows; nenhum vídeo ou captura de CI foi declarado produzido. O grupo ainda precisa gravar e revisar esses artefatos. Nenhuma aprovação humana, defesa oral ou entrega no AVA foi inventada.

## Material que depende do titular

Ezequiel deve conferir esta síntese, reunir trechos relevantes de seus outros chats caso existam e registrar a revisão. Paloma e Vinícius devem fornecer as próprias conversas ou sínteses revisadas pelo modelo de coleta. Não atribuir a um colega decisões que ele ainda não registrou.


Nesta consolidação foi encontrada uma diferença LF/CRLF nos hashes congelados da P6 entre Windows e Git/Linux. Foi acrescentado preparo de protocolo novo que aceita somente os finais de linha e rejeita alteração de conteúdo. Dados, anotações, protocolo e resultados históricos permanecem intactos; seis regressões e comandos Docker verificam esse contrato.


## Continuação em 21/11: P6, entradas e publicação autorizada

O usuário validou a nova apresentação da P6 e repetiu rodadas reais. A assistência de IA implementou tokens por cenário, revalidação dos módulos do navegador e análise P6 adicional versionada, com contraexemplos para negação, valores antigos, especulação, detalhes não anotados e trajetórias incompletas. As respostas, P4/P5, anotações e tokens originais não foram reescritos. O comparativo sintético e a conversa mantiveram seus critérios/código de produção. A conferência de entradas utilizou SQLite temporário e navegador simulado; nenhum teste com LLM real foi iniciado pela assistência nesta continuação.

Após mais uma rodada, Ezequiel declarou concluída a validação funcional no escopo testado, solicitou médias por etapa e autorizou publicar as alterações no GitHub. Não autorizou inferir parecer dos colegas, merge ou tag final. O plano de clone novo e limpeza permanece posterior à publicação e verificação; a limpeza não foi executada. Os MDs privados dos demais integrantes continuam dependendo deles. Referência: [fechamento de 21/11](../fechamento-avaliacao-20261121.md).
