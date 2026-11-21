# Checklist de entrega — versão candidata v3

Atualizado em 20/11/2026; evidências históricas conservam suas datas. O usuário autorizou publicação e confirmou MIT em nome do grupo. A composição de **três integrantes foi aceita pelo professor**, conforme confirmação explícita de Ezequiel. Instituição: **Faculdade UniAnchieta**, conforme informada. Cidade e professor foram omitidos por orientação do usuário.

| Item | Estado e evidência |
|---|---|
| Memória, atualização, esquecimento e contexto | Implementados; [relatório v3](acertos-tokens-contexto-v3.md) |
| P6: 20 sessões por cenário | Modelo real; 21/21 respostas da automática aprovadas; 19/19 checkpoints não vazios de persistência e 2/2 de exclusão |
| Acertos e tokens históricos de 18/11 | P6: 3.593 contra 22.228 tokens, redução de 83,84% em 20/20 pares. Validação: 48/48 aprovações; 84,88% em 47/48 pares. Baseline com julgamentos não verificados e um timeout; sem equivalência estatística demonstrada |
| Pesquisa PDF v3 de 18/11 (registro histórico) | [PDF](pesquisa-abnt.pdf): 25 páginas totais, 16 textuais, 11 referências; todas as páginas renderizadas e conferidas; metodologia atual, referências ordenadas e apêndice de reprodução |
| Documentação técnica | [Índice dos nove itens](README.md), [manual completo](manual-professor.md), [reprodução Docker](reproduzir-avaliacao-v3.md) e [cinco decisões](decisoes-arquitetura.md) consolidados |
| Contextos de IA | [Síntese disponível e modelo](registro-ia/README.md) preparados; cada colega ainda precisa fornecer/conferir seus registros |
| Dados acadêmicos | [Registro validado](dados-academicos.json); três autores |
| Licenças | [MIT](../LICENSE) autorizada; [NOTICE](../NOTICE) e [terceiros](licencas.md) separados |
| Tabelas, gráficos, JSON, logs e falhas | [Índice consolidado](../evidencias/entrega-v3-20261118/README.md), com fontes e denominadores |
| Testes | 960 Python aprovados, 66 ignorados; 8 JavaScript e lint crítico aprovados na v3; [CI da candidata aprovado](https://github.com/codezeck/cognitive-memory-agents/actions/runs/44435946851) |
| Instalação em cópia limpa | [Manual](manual-professor.md) validado em checkout limpo: novo volume de pesos, API pronta e 19 verificações HTTP aprovadas; [registro](../evidencias/entrega-v3-20261118/instalacao-resumo.json) |
| Vídeo de 3–5 minutos em tela inteira | Pendente; [roteiro atualizado](roteiro-demonstracao.md). Controle de tela encerrado por não confirmar URL no Windows |
| Publicação e revisão de PR | [PR #45 publicado](https://github.com/codezeck/cognitive-memory-agents/pull/45); CI aprovado; revisão solicitada a Paloma/Vinícius, ainda sem parecer |
| Fechamento e envio | Obter revisão humana, integrar versão aprovada, marcar `v1.0`, aguardar CI da tag e guardar link/captura. Conferir canal de envio com professor |

## O que significa o último passo

A tag `v1.0` é um marcador Git que identifica exatamente o código entregue. CI verde significa que os testes automáticos passaram **naquele código**. Link e captura permitem ao professor conferir. CI de PR comprova a candidata; o enunciado pede também CI na tag. A gravação demonstra a execução real; o CI não repete toda a avaliação do modelo.

Depois da revisão humana e da integração autorizada:

```powershell
git switch master
git pull --ff-only origin master
git tag -a v1.0 -m "Entrega acadêmica v1.0"
git push origin v1.0
```

Conferir antes que a tag não existe e que `master` contém a versão revisada. Não mover uma tag publicada. O workflow aceita `v1.0`. Guardar URL da execução, SHA do commit e PNG da tela verde no índice. Não declarar revisão, tag ou envio sem esses registros.

Documentos históricos de 14/11 e da v2 permanecem datados. Para o estado atual, usar este checklist e o relatório v3.

## Fechamento funcional informado em 20/11

Ezequiel validou a bateria oficial e o conjunto personalizado e autorizou passar à documentação. [Consolidação](consolidacao-testes-20261120.md): 84,80% no histórico oficial de versões, 84,91% na rodada oficial atual e 74,13% nas duas rodadas personalizadas. Última personalizada: 42/45 fatos e 15/15 abstenções na automática, contra 44/45 e 8/15 no histórico, com 60/60 pares medidos. Três reprovações factuais da automática e os inconclusivos dos controles permanecem registrados. A taxa separada de informação antiga foi incorporada em 21/11, com anotações, cobertura e limites gramaticais explícitos; ver [métrica](informacao-antiga-respostas.md). O aceite do usuário não substitui revisão humana, vídeo, CI da tag ou envio.

A pesquisa e seu PDF foram atualizados para esses métodos, médias, qualidade e limitações. A contagem atual de páginas e os hashes constam de `pesquisa-consolidacao-geracao.json`; a linha de 18/11 acima é histórica. Novas evidências: [índice de 20/11](../evidencias/consolidacao-interface-20261120/README.md). Não houve publicação ou operação de versionamento nesta atualização documental.


## Fechamento funcional aceito em 21/11

Ezequiel repetiu a P6 após as melhorias e declarou concluída esta etapa no escopo testado, autorizando a publicação. Cinco P6 completas somaram cem pares: redução consolidada de 85,62%, sem nova chamada ao modelo para calcular as médias. Última rodada: 25.747/3.576 tokens (86,11%); automática 16/17 fatos aprovados e um inconclusivo; histórico 9/17 aprovados, quatro reprovados e quatro inconclusivos na leitura adicional v2. Os erros e limites foram preservados, sem revisão humana fictícia. [Relatório por etapa](fechamento-avaliacao-20261121.md).

Concluídos localmente: apresentação de tokens da P6, atualização de cache, julgador adicional versionado v2, testes das entradas e documentação. Validação: 1.174 testes Python aprovados, 67 ignorados, 70 JavaScript, lint crítico, links e diferenças conferidos. Publicação, CI remoto desta revisão, parecer dos colegas, integração, clone novo, vídeo, tag/CI da tag e envio devem ser comprovados separadamente. A limpeza do Docker continua adiada até a instalação nova e a preservação dos relatórios necessários.
