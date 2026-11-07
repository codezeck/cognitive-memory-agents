# Guia de avaliação

Como reproduzir as avaliações do projeto e como ler as métricas. Comandos para Windows (PowerShell), na raiz do repositório.

## O que é avaliado

| Avaliação | Pergunta que responde | Script | Responsável |
|---|---|---|---|
| Comparativo do agente | A memória melhora as respostas do chatbot e reduz tokens em relação ao histórico completo? | `eval/avaliar_comparativo.py` | Ezequiel |
| Recuperação de memórias | Em 20 sessões simuladas, o sistema lembra, atualiza e esquece corretamente? | `eval/avaliar_memoria.py` | Vinicius |
| Regras de memória | As regras extraem, atualizam e esquecem fatos em frases novas? | `eval/avaliar_regras.py` | Vinicius |

## Pré-requisitos

1. Ambiente Python:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para o embedder semântico (`avaliar_memoria.py --embedder semantico`): `pip install -r requirements-memoria.txt`.

2. Ollama aberto, com o modelo padrão (`ollama list` deve mostrar `qwen2.5-coder:3b`).
3. Arquivo `.env` na raiz, com um token para o usuário sintético do benchmark. As demais variáveis estão em `.env.example`. O `.env` nunca vai para o repositório.

```
API_TOKENS=troque-por-um-token-longo:eval_comparativo
```

## Avaliação comparativa do agente (um comando)

1. Subir a API (terminal 1; deixe aberto):

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=]+)=(.*)$') { Set-Item "env:$($matches[1].Trim())" $matches[2].Trim() } }
uvicorn src.api.main:app --port 8000
```

A API também pode subir por `docker compose up` (ver o README; subida validada em 05/11, ver `evidencias/agente/`).

2. Rodar a avaliação (terminal 2, com o `.venv` ativo):

```powershell
python eval/avaliar_comparativo.py --repeticoes 3 --saida evidencias/comparativo_NOME.json
```

Parâmetros: `--base-url` (padrão `http://127.0.0.1:8000`), `--provedor` (padrão `ollama`), `--modelo` (padrão `qwen2.5-coder:3b`), `--repeticoes` e `--saida`. O script não sobrescreve um arquivo de saída existente. Ao final ele imprime o bloco `===== RESUMO =====` e grava os resultados completos em JSON.

### Cenários

| Cenário | O que faz |
|---|---|
| `sem_memoria` | Envia só a pergunta final. Mostra o que o modelo inventa sem contexto. |
| `historico_completo` | Envia todas as mensagens do caso na mesma conversa (baseline). |
| `memoria_persistente_api` | Grava o estado esperado como memórias e envia só a pergunta final. É um teto ideal, pois o estado é inserido à mão. |
| `memoria_regras_api` | Envia as mensagens anteriores pela API, deixando as regras extraírem os fatos; reinicia a sessão e faz a pergunta final sem histórico. |

Os casos estão em `eval/dataset_comparativo.json` (CMP001 a CMP007: recuperação, atualização, esquecimento e variações).

### Métricas

| Métrica | Como é calculada |
|---|---|
| Acertos (`taxa_aprovacao_pct`) | Resposta final aceita pelo avaliador. Casos de esquecimento esperam "não sei" ou equivalente. |
| Recuperação exata | Conjunto de memórias usadas igual ao esperado, texto por texto. |
| Recuperação equivalente | Igual à exata, mas reconhecendo variantes conhecidas de redação (por exemplo "Moro em X" e "Mora em X"). Complementar: cobre só os formatos previstos no código (cidade, esporte, carro, nome). |
| Estado das regras | Estado estruturado obtido pela API comparado ao esperado (`estado_regras_esperado`). |
| Sem resíduos | Em casos sem memória esperada, nenhuma memória foi usada. |
| Tokens | `tokens_total` do caso: soma das chamadas ao modelo (entrada e saída). |
| Latência | Soma das latências das chamadas à API no caso. |

### Como ler os tokens

O `tokens_total` soma todas as chamadas do caso. No `historico_completo` e no `memoria_regras_api` isso inclui o envio das mensagens anteriores. No `memoria_persistente_api` mede apenas a pergunta final. Por isso, a comparação de custo por pergunta em sessão nova deve usar `memoria_persistente_api` contra `historico_completo`, e o `memoria_regras_api` deve ser lido como custo total do fluxo.

## Outras avaliações

```powershell
python eval/avaliar_memoria.py --embedder hash --saida evidencias/memoria/resultados_recuperacao_hash.json
python eval/avaliar_memoria.py --embedder semantico --saida evidencias/memoria/resultados_recuperacao_semantico.json
python eval/avaliar_regras.py --conjunto ambos --mostrar-falhas
```

O benchmark de recuperação usa `eval/memoria/sessoes.json` (4 usuários fictícios, 5 sessões cada, 20 sessões). As regras são avaliadas em dois conjuntos separados: desenvolvimento (149 frases) e avaliação final (50 frases), que não deve ser usado para ajustar as regras. Os resultados e a análise estão em `evidencias/memoria/`.

## Conjuntos de desenvolvimento e teste

| Conjunto | Arquivo | Casos | Uso |
|---|---|---|---|
| Desenvolvimento | `eval/dataset_comparativo.json` | CMP001 a CMP007 | Pode ser usado para ajustar regras e prompts. |
| Teste | `eval/dataset_teste.json` | TST001 a TST010 | Não é usado para ajustar nada. Roda uma vez, na versão final, com 3 repetições. |

Comando do conjunto de teste (API e Ollama abertos, como na avaliação comparativa):

```powershell
python eval/avaliar_comparativo.py --dataset eval/dataset_teste.json --repeticoes 3 --saida evidencias/comparativo_teste_3rep.json
```

O baseline é o cenário `historico_completo`. Os casos de teste usam nomes fictícios e redações que as regras podem não cobrir, então falhas neles são resultado e não defeito. Para as regras de memória, os conjuntos de desenvolvimento (149 frases) e de avaliação (50 frases) já são separados.

### Métricas do benchmark de 20 sessões

| Métrica | Como é calculada |
|---|---|
| Taxa de acerto (`taxa_acerto`) | Perguntas respondidas corretamente sobre o total. |
| Lembranças corretas (`taxa_lembranca_correta`) | Perguntas em que a memória esperada foi recuperada. |
| Informação desatualizada (`taxa_informacao_desatualizada`) | Perguntas em que a recuperação trouxe um valor da lista `proibido`, ou seja, um fato antigo já substituído. |
| Esquecimento correto (`taxa_esquecimento_correto`) | Perguntas sobre fatos apagados em que nada foi devolvido. |
| Redução de tokens (`reducao_tokens_percentual`) | Tokens médios de contexto com memória contra o histórico completo, por pergunta. Não é a mesma medida do `tokens_total` do comparativo. |

## Repetições e variação

O modelo local não é determinístico: o mesmo caso pode passar numa repetição e falhar na outra. Por isso os resultados oficiais usam 3 repetições, e diferenças de uma ou duas respostas não são conclusivas.

## Limitações conhecidas

- O conjunto de desenvolvimento tem 7 casos e o de teste tem 10. O de teste ainda não foi executado.
- O avaliador compara texto: respostas corretas com formato diferente podem ser reprovadas, e o modelo de 3 bilhões de parâmetros costuma deformar a palavra DESCONHECIDO.
- Os dados são sintéticos e pequenos; os números são preliminares.
- O `memoria_persistente_api` é pré-carregado com o estado esperado.

## Pendências do protocolo (a fechar antes do congelamento, em 21/11)

1. Registrar separadamente o custo em tokens da pergunta final e o custo de ensinar os fatos.
2. Avaliar o cenário de regras pelo estado estruturado e pela recuperação equivalente, mantendo a exata só como informação.
3. Rodar a avaliação oficial final com 3 repetições, no commit congelado, e registrar commit, data e hora.
