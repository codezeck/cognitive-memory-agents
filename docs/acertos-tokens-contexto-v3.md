# Acertos e tokens: contexto v3 — 18/11/2026

Versão posterior à [rodada v2](melhorias-avaliacao-20261118.md). Base Git `b912ab6`, árvore local identificada nos manifestos. Ollama real, mesmo modelo `qwen2.5-coder:3b`, API e banco descartáveis. Dados e gabaritos P6 originais preservados.

## Mudanças do produto

- Operações de memória inteiramente reconhecidas recebem confirmação local. Salvar, atualizar e apagar continuam executando o armazenamento; apenas a confirmação deixa de invocar o gerador. Perguntas factuais e tarefas gerais continuam usando o modelo quando há suporte.
- Operações locais informam origem explícita e zero chamadas. Tokens nulos não são convertidos em zero sem essa prova. As regras, o banco e os embeddings têm custo computacional que não é medido em tokens do gerador.
- Consultas diretas com evidência recuperada usam prompt breve, fatos atuais e pedido de resposta restrita ao valor. O histórico redundante não entra nessa consulta; perguntas de continuidade e tarefas mistas preservam a janela recente.
- Busca e verificação de suporte compartilham atributos e formas canônicas. A busca aceita também registros com chave personalizada cujo texto canônico fornece suporte; não há tratamento especial para IDs de casos, sementes de avaliação ou respostas esperadas.
- Negação por valor remove todas as versões da chave apenas quando identifica uma única chave ativa do próprio usuário. Uma referência antiga ou ambígua não remove o fato novo.
- Confirmação de esquecimento não recoloca o alvo na RAM. Após pedido misto com esquecimento, o turno gerado também é limpo para não manter resíduos.

## Bateria de validação sintética

Dezesseis casos, três repetições e quatro cenários: 192 tentativas. Os exemplos anteriores passam a ser material de desenvolvimento. Esta bateria usa valores e trajetórias novos, mas foi escrita com conhecimento do domínio; não é teste cego ou validação independente. A primeira tentativa foi interrompida para corrigir suporte de fatos válidos no baseline; o log parcial foi preservado e a rodada final usa nova saída. Não há resultado final para a tentativa interrompida.

| Cenário | Aprovados P4 | Tentativas | Falhas técnicas | Tokens de ingestão | Tokens da sessão |
|---|---:|---:|---:|---:|---:|
| sem_memoria | 48 | 48 | 0 | 0 | 0 |
| historico_completo | 36 | 48 | 1 | desconhecido | desconhecido |
| memoria_persistente_api | 48 | 48 | 0 | 0 | 6212 |
| memoria_regras_api | 48 | 48 | 0 | 0 | 6212 |

Memória automática: **48/48** aprovações P4; histórico: **36/48**. Economia de tokens completos: **84.88%** em **47/48 pares medidos**. O controle pré-carregado não mede aquisição e não substitui a comparação principal.

Se houver falha técnica, o custo completo desse caso continua desconhecido e não entra na comparação de tokens. Subtotais observados não são tratados como custo completo; a economia em pares medidos não representa uma medição dos pares ausentes.

Há uma limitação identificada na anotação numérica nova: o esperado é `4` e o modelo do baseline pode responder `Quatro`. Esse equivalente não foi adicionado retrospectivamente aos aliases. O JSON/P4 original permanece preservado; não interpretar automaticamente toda reprovação desse caso como erro semântico do modelo.

## P6: continuidade, custo completo e qualidade

Foram coletadas 40 sessões e 42 respostas, com 0 falhas técnicas. Modelo, fontes, estados do SQLite, RAM e reinícios estão vinculados à execução. Mantêm-se 21 perguntas por cenário, sem substituir as anotações oficiais.

| Cenário | Aprovados P4 / 21 | Não verificados | Chamadas observadas ao modelo | Operações locais |
|---|---:|---:|---:|---:|
| memoria_automatica | 21 | 0 | 23 | 30 |
| historico_completo | 8 | 12 | 50 | 3 |

Sessões completas: **3593 tokens** com memória e **22228** no histórico; economia de **83.84%**, com **20/20 pares medidos**. A economia inclui arquitetura de confirmação local, recuperação, prompt e histórico; não é atribuída somente à compressão textual.

O baseline mantém geração a cada mensagem, ressalvadas abstenções locais já existentes, e conserva todo o histórico do episódio. O reconhecimento de suporte foi corrigido para preservar também suas afirmações válidas sobre filhos, profissão e viagem.

### Checkpoints e métricas complementares

```json
{
  "checkpoints": {
    "memoria_automatica": {
      "checkpoint_persistencia": {
        "tentativas_previstas": 20,
        "tentativas_elegiveis": 19,
        "julgamentos_verificados": 19,
        "numerador": 19,
        "denominador": 19,
        "nao_verificados": 0,
        "nao_aplicaveis": 1,
        "cobertura_pct": 100.0,
        "taxa_pct": 100.0
      },
      "checkpoint_exclusao": {
        "tentativas_previstas": 2,
        "tentativas_elegiveis": 2,
        "julgamentos_verificados": 2,
        "numerador": 2,
        "denominador": 2,
        "nao_verificados": 0,
        "nao_aplicaveis": 0,
        "cobertura_pct": 100.0,
        "taxa_pct": 100.0
      }
    },
    "historico_completo": {
      "checkpoint_persistencia": {
        "tentativas_previstas": 20,
        "tentativas_elegiveis": 0,
        "julgamentos_verificados": 0,
        "numerador": 0,
        "denominador": 0,
        "nao_verificados": 0,
        "nao_aplicaveis": 20,
        "cobertura_pct": null,
        "taxa_pct": null
      },
      "checkpoint_exclusao": {
        "tentativas_previstas": 2,
        "tentativas_elegiveis": 0,
        "julgamentos_verificados": 0,
        "numerador": 0,
        "denominador": 0,
        "nao_verificados": 0,
        "nao_aplicaveis": 2,
        "cobertura_pct": null,
        "taxa_pct": null
      }
    }
  },
  "vazio": {
    "memoria_automatica": {
      "u04/s4/checkpoint_persistencia": "vazio_consistente"
    },
    "historico_completo": {
      "u04/s4/checkpoint_persistencia": "nao_aplicavel"
    }
  },
  "respostas": {
    "memoria_automatica": {
      "recuperacao_factual": {
        "tentativas_elegiveis": 17,
        "julgamentos_verificados": 17,
        "numerador": 17,
        "denominador": 17,
        "nao_verificados": 0,
        "nao_aplicaveis": 4,
        "aplicabilidade_desconhecida": 0,
        "cobertura_pct": 100.0,
        "taxa_pct": 100.0
      },
      "abstencao_correta": {
        "tentativas_elegiveis": 4,
        "julgamentos_verificados": 4,
        "numerador": 4,
        "denominador": 4,
        "nao_verificados": 0,
        "nao_aplicaveis": 17,
        "aplicabilidade_desconhecida": 0,
        "cobertura_pct": 100.0,
        "taxa_pct": 100.0
      },
      "vazamento_esquecidos": {
        "tentativas_elegiveis": 4,
        "julgamentos_verificados": 4,
        "numerador": 0,
        "denominador": 4,
        "nao_verificados": 0,
        "nao_aplicaveis": 17,
        "aplicabilidade_desconhecida": 0,
        "cobertura_pct": 100.0,
        "taxa_pct": 0.0
      }
    },
    "historico_completo": {
      "recuperacao_factual": {
        "tentativas_elegiveis": 17,
        "julgamentos_verificados": 6,
        "numerador": 5,
        "denominador": 6,
        "nao_verificados": 11,
        "nao_aplicaveis": 4,
        "aplicabilidade_desconhecida": 0,
        "cobertura_pct": 35.29,
        "taxa_pct": 83.33
      },
      "abstencao_correta": {
        "tentativas_elegiveis": 4,
        "julgamentos_verificados": 3,
        "numerador": 3,
        "denominador": 3,
        "nao_verificados": 1,
        "nao_aplicaveis": 17,
        "aplicabilidade_desconhecida": 0,
        "cobertura_pct": 75.0,
        "taxa_pct": 100.0
      },
      "vazamento_esquecidos": {
        "tentativas_elegiveis": 4,
        "julgamentos_verificados": 4,
        "numerador": 0,
        "denominador": 4,
        "nao_verificados": 0,
        "nao_aplicaveis": 17,
        "aplicabilidade_desconhecida": 0,
        "cobertura_pct": 100.0,
        "taxa_pct": 0.0
      }
    }
  }
}
```

O custo contabiliza ingestão e perguntas, com tokens de entrada e saída. Ausência de ocorrência de um alvo nas respostas não certifica toda a RAM ou conformidade jurídica. Os checkpoints observam um worker e o SQLite dedicado; estado vazio é separado da persistência de fatos não vazios.

## Limites e reprodução

As regras e a gramática ainda são limitadas. Negação por referência ambígua exige reformulação do usuário. Texto não reconhecido segue para o modelo; confirmações locais não significam que toda mensagem possível tenha sido compreendida. Memórias fornecidas manualmente e metadados contraditórios exigem cuidado. O orçamento de histórico continua em caracteres, não é garantia sobre a janela total em tokens.

Uma rodada P6 e três repetições de casos sintéticos não comprovam equivalência estatística ou generalização para todos os usuários. O backend Ollama é compartilhado no host, embora as chamadas destas baterias sejam sequenciais; latência não é benchmark de hardware isolado. Os resultados da v2 não foram sobrescritos. Comparações entre versões não isolam causalmente cada alteração nem removem variabilidade do modelo.

```powershell
python -B -m src.interface.comparativo --dataset eval/dataset_validacao_v3_20261118.json --saida SAIDA_NOVA.json --repeticoes 3
python -B -m tools.executar_p6_local --saida-dir PASTA_NOVA --commit-base b912ab6 --protocolo docs/revisao-experimental/protocolo-contexto-v3-20261118.json
python -B -m tools.resumir_contexto_v3
```

Nos ensaios, `OLLAMA_HOST=http://ollama:11434` em container descartável. [Decisão anterior à medição](revisao-experimental/decisao-contexto-v3-20261118.md), [validação original](../evidencias/contexto-v3-20261118/validacao-nova-r02-3rep.json), [P6 JSONL](../evidencias/contexto-v3-20261118/p6-r01/eventos.jsonl), [resumo P6](../evidencias/contexto-v3-20261118/p6-r01/resumo.json) e [respostas CSV](../evidencias/contexto-v3-20261118/respostas-p6.csv).

## Aplicação local e validação de engenharia

954 testes Python aprovados, 66 ignorados, oito testes JavaScript e lint crítico aprovados. As 38 fontes de src permanecem iguais às identificadas na P6. Após a validação, a API local foi reconstruída e reiniciada na porta 8002, com os mesmos volumes de banco e credenciais e sem reiniciar o Ollama. Saúde ok, chat HTTP 200 e versão memoria-contexto-v3 confirmados. O [PDF v3](pesquisa-abnt.pdf) incorpora os resultados. O [índice da candidata](../evidencias/entrega-v3-20261118/README.md) registra publicação, instalação e pendências finais.
