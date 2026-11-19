# Checklist de entrega — versão candidata v3

Estado de 18/11/2026. O usuário autorizou publicação e confirmou MIT em nome do grupo. A composição de **três integrantes está validada**. Instituição: **Faculdade União Chinita**, conforme informada. Cidade e professor foram omitidos por orientação do usuário.

| Item | Estado e evidência |
|---|---|
| Memória, atualização, esquecimento e contexto | Implementados; [relatório v3](acertos-tokens-contexto-v3.md) |
| P6: 20 sessões por cenário | Modelo real; 21/21 respostas da automática aprovadas; 19/19 checkpoints não vazios de persistência e 2/2 de exclusão |
| Acertos e tokens | P6: 3.593 contra 22.228 tokens, redução de 83,84% em 20/20 pares. Validação: 48/48 aprovações; 84,88% em 47/48 pares. Baseline com julgamentos não verificados e um timeout; sem equivalência estatística demonstrada |
| Pesquisa PDF v3 | [PDF](pesquisa-abnt.pdf): 24 páginas totais, 16 textuais, 11 referências; todas as páginas renderizadas e conferidas |
| Dados acadêmicos | [Registro validado](dados-academicos.json); três autores |
| Licenças | [MIT](../LICENSE) autorizada; [NOTICE](../NOTICE) e [terceiros](licencas.md) separados |
| Tabelas, gráficos, JSON, logs e falhas | [Índice consolidado](../evidencias/entrega-v3-20261118/README.md), com fontes e denominadores |
| Testes | 954 Python aprovados, 66 ignorados; 8 JavaScript e lint crítico aprovados na v3; [CI da candidata aprovado](https://github.com/codezeck/cognitive-memory-agents/actions/runs/44435946851) |
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
