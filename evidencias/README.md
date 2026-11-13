# Índice de evidências

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
| 4 | O fluxo lembrar, atualizar, persistir, esquecer e apagar o usuário funciona pela API, com `401` sem token e `403` para outro usuário. | Testes de `tests/test_api.py` em `memoria/01_testes_pytest.txt`; `agente/fluxo-memoria-docker-2026-11-05.txt` (execução real, API no Docker) | `python -m pytest tests/test_api.py -v` | Disponível |
| 5 | Uso crítico da IA registrado (prompts, resposta, decisão e motivo). | `../PROMPTS.md` | Ler o arquivo | Disponível (mesclado no PR #27; revisão posterior pedida) |
| 6 | A integração contínua passa. | Captura e link do run na tag `v1.0` | Página Actions do repositório | Pendente (tag `v1.0`) |
| 7 | O projeto sobe com `docker compose up`. | Log em `agente/fluxo-memoria-docker-2026-11-05.txt`; vídeo da demonstração (3 a 5 minutos), pendente | `docker compose up` do zero | Parcial: subida validada em 05/11; vídeo pendente |
| 8 | Resultados da avaliação final, congelada e reproduzível. | `comparativo_final_3rep.json` | Comando do `docs/guia-avaliacao.md` | Pendente (rodada final, até 21/11) |
| P4 | O julgador reconhece treze atributos, com regressão dos cinco antigos. | `../tests/test_julgamento_respostas.py` | Testes específicos no guia de avaliação | Validado por testes simulados; política `p4-v3` |
| P6 | As 21 anotações oficiais são estruturalmente compatíveis com o julgador. | `../eval/memoria/anotacoes_p6.json` e `../tests/test_sessoes_integradas.py` | Inspeção sem `--executar`, conforme guia | 21 compatíveis, 0 incompatíveis, 0 ausentes; revisão semântica dos gatos pendente |

As duas últimas linhas são evidências de engenharia, sem nova rodada de LLM. Não comprovam 21 respostas corretas nem execução real das 20 sessões. Contrato de esquecimento, observação da RAM e evidências operacionais continuam necessários. Os JSON históricos acima não foram alterados e não representam resultados da política P4-v3.

### Reproduzir a avaliação oficial

Material preparado para a pesquisa e apresentação: [tabelas e figuras](../docs/resultados-avaliacoes-agente.md), [texto acadêmico](../docs/contribuicao-academica-zeck.md), [roteiro do vídeo](../docs/roteiro-demonstracao.md) e [plano P6](../docs/plano-execucao-p6.md). Esses documentos não são novos resultados, vídeo gravado ou evidência de execução real P6. Os JSON existentes não possuem as etapas/julgamentos do protocolo P3/P4/P5 atual; as lacunas estão identificadas nas tabelas. A compatibilidade 21/21 pertence à PR #41 em revisão; a master desta preparação ainda usa P4-v2 (10/21).

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
| Log de execução com data e hora (`agente/`) | Parcial: fluxo de memória no Docker de 05/11; falta o log da avaliação final |
| Pelo menos 5 capturas de tela do sistema funcionando | Pendente |
