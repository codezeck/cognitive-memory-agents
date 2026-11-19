# Ficha dos dados e do modelo — v3

Estado de 18/11/2026. Todos os exemplos experimentais são sintéticos. Não foram usados dados pessoais reais, treinamento do modelo ou fine-tuning. [Reprodução](reproduzir-avaliacao-v3.md), [resultados e limites](acertos-tokens-contexto-v3.md), [licenças](licencas.md).

| Componente | Origem, tratamento e estado atual | Limite |
|---|---|---|
| `eval/dataset_comparativo.json` | Sete casos sintéticos históricos de desenvolvimento | Três repetições não são 21 casos independentes |
| `eval/dataset_teste.json` e cópia anotada de 18/11 | Dez casos originalmente reservados; a cópia anotada foi executada na v2 e seus resultados preservados | Após uso no desenvolvimento, não apresentar como teste final cego da v3 |
| `eval/dataset_validacao_v3_20261118.json` | Dezesseis trajetórias sintéticas novas; três repetições, quatro cenários e 192 tentativas na rodada v3 | Escrita com conhecimento do domínio; um timeout do baseline; uma limitação de alias numérico preservada |
| `eval/memoria/sessoes.json` e `anotacoes_p6.json` | Quatro usuários, cinco sessões cada, 21 perguntas por cenário; fontes oficiais preservadas | P6 executada; baseline com 12 respostas não verificadas, aguardando revisão complementar |
| Coleta P6 v3 | API/SQLite temporários, identidades dedicadas, snapshots, reinícios reais e observador RAM do worker | Persistência não vazia, consistência vazia e exclusão são critérios distintos |
| Ensaios do chat | Perfis A/B sintéticos em projetos próprios; logs sem cookies ou tokens | Capturas de navegador existentes são históricas de 14/11; ver datas no índice |
| Armazenamento do produto | SQLite por usuário; chave canônica nas consultas reconhecidas e EmbedderHash no fallback | Não atribuir recuperação semântica geral à busca lexical |

## Modelo e runtime

Gerador: **`qwen2.5-coder:3b`**, pelo Ollama. Nos ensaios foi identificado o digest `f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225`, quantização GGUF/Q4_K_M e pesos informados de 1.929.912.626 bytes. Ollama 0.40.12 tem imagem fixada por digest no Compose. A configuração efetiva de cada rodada está nos seus arquivos `configuracao.json`; tags futuras podem mudar, por isso o digest precisa ser conferido.

A API e o baseline usaram o mesmo modelo/runtime. Não há garantia de determinismo; seed/temperatura não foram controladas para isolar causalmente cada mudança. A integração OpenAI possui testes simulados, sem comparação real. Não é necessária chave de serviço pago para a entrega.

## Licenças e tratamento

Código e documentação próprios: [MIT](../LICENSE), autorizada pelo grupo. Modelo: [ficha oficial Qwen](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) e licença Qwen Research, distinta da MIT; pesos não entram no Git. [NOTICE](../NOTICE) e [inventário de dependências](licencas.md) preservam atribuições.

As anotações não são enviadas ao modelo como gabaritos. Resultados brutos, respostas não verificadas e falhas técnicas foram mantidos. Revisão humana posterior deve ser publicada como análise complementar, sem alterar retrospectivamente os originais. Não se demonstrou generalização irrestrita, equivalência estatística ou conformidade jurídica; o modelo já apresentou erros factuais e aritméticos em ensaios preservados.
