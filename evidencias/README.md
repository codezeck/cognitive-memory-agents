# Índice de evidências

## Estado atual — 22/11/2026

[Pacote de fechamento](fechamento-entrega-20261122/README.md): vídeo de 4min59,75s, versão exibida e edição documentadas, instalação isolada com 19 verificações aprovadas e correção da reprodução offline da P6. Os relatórios de 20/11 e as análises de informação antiga também foram reconferidos sem modelo. Os [históricos da equipe](../docs/registro-ia/README.md) estão reunidos na PR #46. A PR #45 já foi integrada; revisão do fechamento, tag, CI/captura da tag e envio seguem pendentes. As seções datadas abaixo são históricas e não sobrepõem este estado.

**21/11:** [análise adicional de informação antiga, derivados e testes](informacao-antiga-20261121/README.md); os originais e os números de tokens anteriores foram preservados.

**Consolidação de 20/11:** [14 relatórios locais preservados, médias e recálculo](consolidacao-interface-20261120/README.md). Oficial e personalizado separados, P6 em unidade própria, qualidade e falhas mantidas.

**Candidata v3 de 18/11:** [índice consolidado](entrega-v3-20261118/README.md), PDF, gráficos, CSV e fontes brutas; ver pendências atuais nesse índice.

## Contexto v3 — acertos e tokens

[Relatório atual](../docs/acertos-tokens-contexto-v3.md), [validação de 16 casos/3 repetições](contexto-v3-20261118/validacao-nova-r02-3rep.json), [P6 original](contexto-v3-20261118/p6-r01/eventos.jsonl) e [resumo P6](contexto-v3-20261118/p6-r01/resumo.json). A memória automática teve 48/48 aprovações na validação e 21/21 na P6; economia de 83,84% nos 20 pares P6. A comparação curta tem 47/48 pares medidos por um timeout do baseline. A tentativa inicial interrompida tem log separado; resultados da v2 permanecem preservados. Há [manifestos e testes](contexto-v3-20261118/); não é avaliação cega nem garantia de generalização.

## Rodadas reais de 18/11/2026

- [Relatório de melhorias e avaliação](../docs/melhorias-avaliacao-20261118.md): implementação, números, cobertura, análise de falhas e reprodução.
- [Comparativo de desenvolvimento](melhorias-20261118/comparativo-r01.json): 84 tentativas; memória automática 20/21, histórico 16/21.
- [P6 original JSONL](melhorias-20261118/p6-r02/eventos.jsonl), [resumo](melhorias-20261118/p6-r02/resumo.json) e [configuração/hash das fontes](melhorias-20261118/p6-r02/configuracao.json): 20 sessões por cenário, 42 respostas e observações de SQLite/RAM/reinício.
- [Evidências operacionais por evento](melhorias-20261118/p6-r02/evidencias-operacionais.json) e [respostas CSV](melhorias-20261118/respostas-p6.csv): a coleta é automática e não declara aprovação humana da equipe.
- [Análise textual complementar assistida por IA](melhorias-20261118/revisao-textual-ia.json): separada dos julgamentos automáticos preservados.
- [Bateria separada de teste](melhorias-20261118/teste-separado-r01.json): 120 tentativas; memória automática 21/30 contra histórico 24/30. Resultado negativo preservado, sem ajustes do produto por essas respostas.
- [Figura P6](melhorias-20261118/p6-resultados.png) e [pesquisa atualizada](../docs/pesquisa-abnt.pdf): rascunho para revisão coletiva, sem alegação de versão final.

`melhorias-20261118/p6-r01` preserva a preparação que falhou antes de gerar sessões; `p6-r02` é uma execução nova. Nenhuma evidência de 14/11 foi sobrescrita. Os nomes e fatos da avaliação são sintéticos. A publicação/tag, o vídeo oficial e a revisão humana permanecem pendentes.

## 15/11/2026: preparação opcional OpenAI

[preparacao-openai-20261115](agente/preparacao-openai-20261115/): resumo com hashes/configuração, log de 903 testes aprovados/66 ignorados, lint/diff-check e links. Override remoto validado somente com `docker compose config` e chave fictícia; nenhum serviço OpenAI iniciado nem chamada externa. Tokens novos foram testados por SDK simulado, não medidos num modelo real. Usuário possui ChatGPT Free: chave/créditos necessários ainda são bloqueio. [Procedimento e limites](../docs/openai-opcional.md). Ollama/porta 8002 e resultados históricos preservados; P6/reservado não executados.

## Integração local de entrega: 14/11/2026

Pasta nova [entrega/20261114-entrega-ae9eb113](entrega/20261114-entrega-ae9eb113/):

- `iniciador-real-r03.log`: comando único real concluído após corrigir tratamento de `stderr` e passagem de argumentos no PowerShell 5; duas tentativas anteriores preservadas. `configuracao-iniciador.json` registra a configuração padrão, com observador RAM desligado. Nesse snapshot o único hash anterior diferente é `evidencias/README.md`, atualizado intencionalmente; arquivos brutos continuam intactos.
- `r05-iniciador-padrao.png` e `r05-interrupcao.json`: erro real 2 + 3 = 4; JSON HTTP não coletado antes do assert. `r06-iniciador-padrao.json`/PNG: cinco repetições corretas e uma pergunta geral correta; cookie HttpOnly e nenhum token gerado localizado nos candidatos à publicação. Não apaga a falha anterior.

- `primeira-inicializacao.json` e `inicial-*.log`: volume inicialmente vazio, download e preparo reais. `build-frio-final.log`: build sem cache Python; sistema/base Docker preexistentes.
- `configuracao-final.json`: modelo/digest/quantização, imagens, fontes/configuração sem segredos e preservação dos dois serviços anteriores, oito volumes e worktree de origem.
- `r04-interface.jsonl` e nove capturas `r04-*.png`: 80 verificações aprovadas, API/modelo reais, origem de uso, SQLite somente leitura, RAM no processo, nova sessão versus reinício, identidade e isolamento.
- `r02-interface.jsonl`: primeiro percurso completo, 51 aprovadas. `r01-interface.jsonl`: tentativa interrompida pela espera de visibilidade de uma opção; preservada. `r03-conexao-api.json`/PNG: falha da API própria, recuperação e identidade conservada.
- `testes-finais-r02.log`: 897 aprovados/66 ignorados, aviso de cache; `testes-finais.log`: 212 erros de preparação por temporário sem acesso. `testes-javascript.log`: 8 aprovados; `lint.log`: aprovado.
- `comparativo-desenvolvimento.json` e `.log`: 84 tentativas reais, P3/P4/P5 atuais, sete casos conhecidos × três repetições × quatro cenários, sem P6/reservado. `falhas-desenvolvimento.csv`: todas as 22 falhas de conteúdo. Figuras derivadas em `figuras/`, sem alterar arquivos históricos.
- `pesquisa-geracao.json`: proveniência do rascunho PDF e contagem de 14 páginas textuais/22 totais. Todas as páginas foram renderizadas para conferência; metadados institucionais/revisão coletiva pendentes.

Síntese: [matriz](../docs/andamento-entrega.md), [manual](../docs/manual-professor.md), [ensaio](../docs/ensaio-desenvolvimento-20261114.md) e [checklist](../docs/checklist-entrega.md). Automática aumentou tokens completos 6,72%; meta global não atingida. Sem vídeo oficial, P6 real, publicação/tag ou CI remoto desta versão. Evidências anteriores abaixo são históricas.

Cada afirmação do trabalho de pesquisa aponta para uma evidência desta pasta e para o comando que a reproduz. A coluna Status é atualizada a cada entrega.

- A parte de **memória de longo prazo** (Vinicius) tem índice próprio em [`memoria/README.md`](memoria/README.md).
- A parte do **agente e da avaliação** (Ezequiel) está neste arquivo.
- A parte de **API e infraestrutura** (Paloma) está listada abaixo como pendente.

## Agente e avaliação

| # | Afirmação | Evidência | Como conferir | Status |
|---|---|---|---|---|
| 1 | O comparativo histórico registra tokens e aprovação de quatro estratégias; os cenários de memória têm menor total registrado e também menos aprovações que o histórico completo. | `comparativo_oficial_3rep.json` | Ver "Reproduzir a avaliação oficial" abaixo e as tabelas em `../docs/resultados-avaliacoes-agente.md` | Disponível, com política/percurso históricos; não demonstra manutenção do acerto |
| 2 | Há rodadas registradas antes e depois da correção de encoding, com variação entre cenários. | `comparativo_antes_correcao_encoding.json` e `comparativo_oficial_3rep.json` | Comparar `resumo`; tabela e ressalvas no inventário | Disponível; não isola o efeito causal do encoding nem mostra melhora universal |
| 3 | O modelo inventa informação quando não há memória, e os erros das estratégias de memória se concentram nos casos de esquecimento. | Campo `resultados` de `comparativo_oficial_3rep.json` (respostas por caso e cenário) e `PROMPTS.md` (análise de erros) | Filtrar `cenario` e `passou` no JSON | Disponível |
| 4 | O fluxo histórico de memória e segurança foi exercitado em 05/11; isso não garante qualidade das respostas pós-exclusão na versão atual. | Testes de `tests/test_api.py` em `memoria/01_testes_pytest.txt`; `agente/fluxo-memoria-docker-2026-11-05.txt` | `python -m pytest tests/test_api.py -v` | Histórico disponível; ver sondagem atual abaixo |
| 5 | Uso crítico da IA registrado (prompts, resposta, decisão e motivo). | `../PROMPTS.md` | Ler o arquivo | Disponível (mesclado no PR #27; revisão posterior pedida) |
| 6 | A integração contínua passa. | Captura e link do run na tag `v1.0` | Página Actions do repositório | Pendente (tag `v1.0`) |
| 7 | O projeto sobe com `docker compose up`. | Log em `agente/fluxo-memoria-docker-2026-11-05.txt`; vídeo da demonstração (3 a 5 minutos), pendente | `docker compose up` do zero | Parcial: subida validada em 05/11; vídeo pendente |
| 8 | Resultados da avaliação final, congelada e reproduzível. | `comparativo_final_3rep.json` | Comando do `docs/guia-avaliacao.md` | Pendente (rodada final, até 21/11) |
| P4 | O julgador reconhece treze atributos, com regressão dos cinco antigos. | `../tests/test_julgamento_respostas.py` | Testes específicos no guia de avaliação | Validado por testes simulados; política `p4-v3` |
| P6 | As 21 anotações oficiais são estruturalmente compatíveis com o julgador. | `../eval/memoria/anotacoes_p6.json` e `../tests/test_sessoes_integradas.py` | Inspeção sem `--executar`, conforme guia | 21 compatíveis, 0 incompatíveis, 0 ausentes; revisão semântica dos gatos pendente |

As duas últimas linhas são evidências de engenharia, sem nova rodada de LLM. Não comprovam 21 respostas corretas nem execução real das 20 sessões. Contrato de esquecimento, observação da RAM e evidências operacionais continuam necessários. Os JSON históricos acima não foram alterados e não representam resultados da política P4-v3.

### Conferência real Docker/Ollama — 14/11/2026

[Manual do professor](../docs/manual-professor.md) e [relatório com matriz de requisitos](../docs/validacao-entrega-docker.md). Base `2be5d51`, PRs #41/#42/#43 integradas; ambiente, volume e usuários exclusivos, agente real com `qwen2.5-coder:3b`.

| Afirmação observada | Evidência nova | Limite |
|---|---|---|
| Fato extraído pela conversa, recuperado em nova sessão, atualizado e preservado após reinício real; isolamento e 401/403 | [JSONL](agente/validacao-docker-20261114-07701ee5.jsonl), [log da API](agente/validacao-docker-20261114-07701ee5-api.log) | Uma sondagem sintética, sem baseline; build com camadas/modelo em cache |
| Exclusão total removeu linhas ativas e inativas de A no SQLite e preservou B | Snapshots somente leitura no JSONL | Não observa diretamente histórico em RAM |
| Modelo inventou Belo Horizonte após DELETE individual e São Paulo após DELETE total, com `memorias_usadas=[]` | Respostas originais e duas verificações negativas no JSONL | Falhas de abstenção; não são as cidades apagadas nem prova de vazamento delas |

O resumo tem 49 verificações auxiliares positivas e 2 negativas, sem representar 51 casos independentes ou uma taxa de qualidade. Não é P6 nem resultado final P3/P4/P5. Swagger/OpenAPI foram verificados por HTTP; faltam QA visual/capturas desta rodada.

[Encerramento registrado](agente/validacao-docker-20261114-07701ee5-encerramento.json): somente o contêiner/rede de teste removidos, sem `-v`; volume dedicado e recursos anteriores preservados, serviço original sem reinício.

**Continuação da correção de abstenção:** [relatório completo](../docs/validacao-entrega-docker.md#continuação--correção-da-abstenção-14112026), [HTTP final](agente/20261114-abstencao-c4468914-correcao-final-http.jsonl), [traço real do modelo](agente/20261114-abstencao-c4468914-correcao-final-modelo.jsonl) e [todas as rodadas/falhas](agente/20261114-abstencao-c4468914-resumo.json). Resultado final: 65 verificações aprovadas (13 situações × 5 repetições), 115 chamadas reais ao Ollama e 30 abstenções locais sem chamada ao modelo. A guarda não é agente falso; é uma política do produto, com gramática limitada, e suas respostas não são atribuídas ao LLM. Não comprova a meta de economia/equivalência ao histórico completo nem substitui P6 ou snapshot da RAM.

### Reproduzir a avaliação oficial

Material preparado para a pesquisa e apresentação: [tabelas e figuras](../docs/resultados-avaliacoes-agente.md), [texto acadêmico](../docs/contribuicao-academica-zeck.md), [roteiro do vídeo](../docs/roteiro-demonstracao.md) e [plano P6](../docs/plano-execucao-p6.md). Esses documentos não são novos resultados, vídeo gravado ou evidência de execução real P6. Os JSON históricos não possuem as etapas/julgamentos do protocolo P3/P4/P5 atual; as lacunas estão identificadas nas tabelas. Em 14/11, a base integrada P4-v3 confirmou 21/21; os 10/21 de P4-v2 pertencem ao relatório histórico de 12/11.

A avaliação oficial (`comparativo_oficial_3rep.json`, gerada em 28/10/2026 com `qwen2.5-coder:3b`, 3 repetições) foi executada com o avaliador do commit `0a847f8`, anterior ao PR #20, que depois mudou o cenário `memoria_regras_api` (passou a enviar as mensagens anteriores pela API real). Para reproduzir exatamente esses números:

```powershell
git checkout 0a847f8
# subir a API e rodar, conforme docs/guia-avaliacao.md:
python eval/avaliar_comparativo.py --repeticoes 3 --saida evidencias/conferencia_oficial.json
git checkout master
```

Com o avaliador atual do `master`, os números do cenário `memoria_regras_api` (tokens, latência e recuperação exata) são diferentes. A rodada final, congelada, substituirá esta evidência.

## Memória de longo prazo

Ver [`memoria/README.md`](memoria/README.md): testes, recuperação em 20 sessões simuladas (palavras e semântica), regras com conjunto de avaliação separado, contrato da memória antes e depois do ajuste, histórico do git e ambiente.

## API e infraestrutura

| # | Afirmação | Evidência | Status |
|---|---|---|---|
| 9 | A API e o banco sobem do zero com `docker compose up` e as memórias persistem em volume. | Log da execução e vídeo | Parcial: subida e persistência no volume validadas em 05/11 (item 7); vídeo pendente |
| 10 | Documentação da API e instruções de instalação. | `../README.md` e documentação dos endpoints | Verificar com a responsável |

## Capturas de tela e logs

| Item | Status |
|---|---|
| Captura do CI verde na tag `v1.0` | Pendente |
| Log de execução com data e hora (`agente/`) | Fluxos Docker de 05/11 e 14/11 disponíveis; falta o log da avaliação final |
| Pelo menos 5 capturas de tela do sistema funcionando | Pendente |
