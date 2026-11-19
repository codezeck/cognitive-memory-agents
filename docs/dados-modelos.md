# Ficha dos dados e do modelo da demonstração

Referência operacional de 14/11/2026. O [guia](guia-avaliacao.md) concentra protocolos/comandos; a [matriz](andamento-entrega.md) distingue requisitos e pendências. Esta ficha não altera dados nem licenças.

| Componente | Origem e tratamento | Limite |
|---|---|---|
| `eval/dataset_comparativo.json` | Sete casos sintéticos de desenvolvimento elaborados no projeto; três repetições na rodada atual | Não são 21 casos independentes; não é P6 |
| `eval/dataset_teste.json` | Dez casos reservados; metadados P4 propostos em arquivo separado, sem alterar a fonte | Sem execução nesta etapa; revisão semântica e fase final ainda pendentes |
| Dados/anotações P6 em `eval/memoria/` | Quatro usuários, cinco sessões cada; alvos de recuperação e resposta precisam de revisão distinta | Vinte sessões não foram executadas nesta continuação; não confundir benchmark de recuperação com conversa integrada |
| Dados de ensaio Docker | Usuários A/B sintéticos em projeto/volumes próprios; pedidos/respostas em JSONL | Nenhum dado pessoal real solicitado; logs preservam exemplos sintéticos, sem cookies/tokens |
| Armazenamento padrão | SQLite persistente e recuperação por EmbedderHash | Hash lexical não é embedder semântico; exclusão por ID e total possuem escopos diferentes |

Modelo gerador: **`qwen2.5-coder:3b`**, distribuído pelo Ollama, modelo Qwen2 de aproximadamente 3,1 bilhões de parâmetros, GGUF/Q4_K_M. Digest observado `f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225`; pesos informados de 1.929.912.626 bytes. Runtime Ollama 0.40.12 em imagem fixada por digest no Compose. A API e o controle de histórico usaram o mesmo modelo/runtime no comparativo. Não houve override de temperatura, seed ou contexto; parâmetros retornados pelo runtime em `configuracao-final.json`. Não há determinismo garantido.

Origem primária: [Qwen2.5-Coder-3B-Instruct, ficha e licença Qwen Research](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct). A distribuição possui condições próprias; não atribuir a ela a licença dos SDKs. Uso sem API paga não significa ausência de custos de hardware, internet, energia ou restrições de licença. Em 18/11, o usuário confirmou autorização do grupo para o código sob [MIT](../LICENSE). O modelo mantém sua licença própria, descrita no [inventário](licencas.md).

O modelo é voltado a código e apresentou limitações na conversa em português: fatos inventados, respostas desatualizadas em controle histórico, abstenção indevida e erro aritmético em uma tentativa. A guarda pessoal é lexical e parcial. Não foi feita comparação real com OpenAI, modelos maiores, outros idiomas ou implantação pública. O [comparativo atual](ensaio-desenvolvimento-20261114.md) não atingiu economia global; uma ficha de modelo não substitui avaliação de uso.
