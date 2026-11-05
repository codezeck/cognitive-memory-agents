# Índice de evidências

Cada afirmação do trabalho de pesquisa aponta para uma evidência desta pasta e para o comando que a reproduz. A coluna Status é atualizada a cada entrega.

- A parte de **memória de longo prazo** (Vinicius) tem índice próprio em [`memoria/README.md`](memoria/README.md).
- A parte do **agente e da avaliação** (Ezequiel) está neste arquivo.
- A parte de **API e infraestrutura** (Paloma) está listada abaixo como pendente.

## Agente e avaliação

| # | Afirmação | Evidência | Como conferir | Status |
|---|---|---|---|---|
| 1 | O agente com memória responde com menos tokens por pergunta que o histórico completo, e mantém o acerto. | `comparativo_oficial_3rep.json` | Ver "Reproduzir a avaliação oficial" abaixo | Disponível |
| 2 | Corrigir acentos corrompidos no dataset melhorou a avaliação (antes e depois). | `comparativo_antes_correcao_encoding.json` e `comparativo_oficial_3rep.json` | Comparar o campo `resumo` dos dois arquivos | Disponível |
| 3 | O modelo inventa informação quando não há memória, e os erros das estratégias de memória se concentram nos casos de esquecimento. | Campo `resultados` de `comparativo_oficial_3rep.json` (respostas por caso e cenário) e `PROMPTS.md` (análise de erros) | Filtrar `cenario` e `passou` no JSON | Disponível |
| 4 | O fluxo lembrar, atualizar, persistir, esquecer e apagar o usuário funciona pela API, com `401` sem token e `403` para outro usuário. | Testes de `tests/test_api.py` em `memoria/01_testes_pytest.txt`; log de execução manual | `python -m pytest tests/test_api.py -v` | Testes disponíveis; log manual a adicionar |
| 5 | Uso crítico da IA registrado (prompts, resposta, decisão e motivo). | `../PROMPTS.md` | Ler o arquivo | Pendente de mesclagem (PR `docs/prompts-md`) |
| 6 | A integração contínua passa. | Captura e link do run na tag `v1.0` | Página Actions do repositório | Pendente (tag `v1.0`) |
| 7 | O projeto sobe com `docker compose up`. | Vídeo da demonstração (3 a 5 minutos) | `docker compose up` do zero | Pendente (Docker não validado) |
| 8 | Resultados da avaliação final, congelada e reproduzível. | `comparativo_final_3rep.json` | Comando do `docs/guia-avaliacao.md` | Pendente (rodada final, até 21/11) |

### Reproduzir a avaliação oficial

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
| 9 | A API e o banco sobem do zero com `docker compose up` e as memórias persistem em volume. | Log da execução e vídeo | Pendente (responsável: Paloma) |
| 10 | Documentação da API e instruções de instalação. | `../README.md` e documentação dos endpoints | Verificar com a responsável |

## Capturas de tela e logs

| Item | Status |
|---|---|
| Captura do CI verde na tag `v1.0` | Pendente |
| Log de execução completa com data e hora (`agente/`) | Pendente |
| Pelo menos 5 capturas de tela do sistema funcionando | Pendente |
