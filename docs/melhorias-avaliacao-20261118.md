# Melhorias e avaliação real — 18/11/2026

Base Git `b912ab6`, branch `fix/confiabilidade-contexto-memoria`, com alterações locais identificadas pelos manifestos. Ollama real, `qwen2.5-coder:3b`, dados sintéticos, API e SQLite dedicados. Nenhuma chamada a API paga. Os resultados de 14/11 e os datasets originais foram preservados.

## O que mudou

- Consultas sobre carro atual, time, esporte, cargo e trabalho reconhecem suporte de forma mais coerente. Negação, hipótese, pergunta e fala do assistente não bastam como afirmação de um fato.
- Busca por chave prioriza fatos ativos em perguntas pessoais reconhecidas, mesmo sem palavras iguais. Quando não há correspondência por chave, continua a busca vetorial existente; não há compreensão semântica universal. O score 1,0 nesse caminho significa chave exata, não similaridade de cosseno.
- API envia até três turnos recentes e 6.000 caracteres de histórico, preservando pares completos. Pergunta atual, sistema e memórias recuperadas não são truncados por esse limite. A RAM continua limitada a dez turnos; fatos fora do contexto recente precisam estar na memória recuperada. Esse orçamento não é uma contagem exata de tokens.
- O baseline desliga explicitamente o contexto compacto e conserva todo o episódio. A montagem compacta retira instruções duplicadas e memórias textualmente repetidas.
- O coletor P6 inicia uma API descartável com um worker, lê SQLite/RAM e reinicia somente seu próprio processo. O estado vazio esperado é analisado separadamente da persistência de dados não vazios.

## Comparativo de desenvolvimento

Sete casos conhecidos, três repetições, quatro cenários: 84 tentativas. As repetições não são novos casos independentes.

| Cenário | Aprovados P4 | Tentativas | Tokens completos |
|---|---:|---:|---:|
| sem_memoria | 21 | 21 | 0 |
| historico_completo | 16 | 21 | 17090 |
| memoria_persistente_api | 21 | 21 | 5256 |
| memoria_regras_api | 20 | 21 | 15690 |

Redução da sessão completa: **8.19%**. A meta adicional de 30% não foi atingida. O controle pré-carregado não mede aquisição conversacional.

As falhas anteriores de carro e time não reapareceram nesta bateria. A memória automática falhou uma vez sobre esporte apesar de o estado das regras estar correto. Variação entre rodadas não prova efeito causal isolado de cada correção, pois o modelo é estocástico e várias mudanças foram avaliadas juntas.

## P6: vinte sessões por cenário

Rodada real completa, 40 registros de sessão, 42 perguntas e zero falhas técnicas. Os 19 checkpoints não vazios foram verificados após reinício; os dois checkpoints de exclusão foram verificados, com banco e RAM observados e preservação dos não alvos. O checkpoint de estado vazio foi registrado como `vazio_consistente`, fora do denominador de persistência de fatos.

| Cenário | Aprovados P4 / 21 | Reprovados verificados | Não verificados | Tokens completos |
|---|---:|---:|---:|---:|
| memoria_automatica | 14 | 2 | 5 | 17002 |
| historico_completo | 9 | 6 | 6 | 22751 |

Redução de **25.27%**, com **20/20** pares medidos. A meta de 30% continua não atingida. A avaliação automática de respostas não é completa: há onze julgamentos não verificados, que não são convertidos em acertos ou erros confirmados. As taxas apenas dos verificados não representam a taxa de todas as 21 perguntas.

Abstenção: 4/4 correta na memória automática e 3/4 no histórico; ocorrências de fatos esquecidos nas respostas: 0/4 e 1/4, respectivamente. Isso não certifica toda a RAM, buffers externos ou conformidade jurídica.

## Revisão textual complementar assistida por IA

A revisão abaixo examina todas as respostas não aprovadas usando os gabaritos congelados e as respostas literais. Não altera JSONL, P4, aliases ou gabaritos, nem representa revisão humana da equipe. Além do valor solicitado, considera detalhes contraditórios inventados: dizer dois gatos e trocar Luna por Leo não é resposta integralmente correta.

| Cenário | Pergunta | Resposta literal | Análise complementar |
|---|---|---|---|
| historico_completo | u03/s2/pergunta1 | Desculpe, mas como uma inteligência artificial, não posso acessar informações pessoais ou personalizar detalhes como hobbies. Você gostaria de compartilhar mais sobre seus interesses ou interesses? | Recusa informar o hobby já declarado: fotografia. |
| memoria_automatica | u01/s3/pergunta2 | Hoje você mora em Campinas. | Afirma Campinas, valor atual anotado. |
| historico_completo | u01/s3/pergunta2 | Hoje você mora em Campinas. | Afirma Campinas, valor atual anotado. |
| memoria_automatica | u03/s3/pergunta2 | Você planeja viajar para Portugal em dezembro. | Afirma Portugal em dezembro, destino atual anotado. |
| historico_completo | u03/s3/pergunta2 | Você está viajando para Portugal em dezembro. | Afirma Portugal em dezembro, destino atual anotado. |
| memoria_automatica | u04/s3/pergunta1 | Você é um analista de dados. | Afirma analista de dados; o artigo um não muda o cargo. |
| historico_completo | u04/s3/pergunta1 | Atualmente, seu trabalho envolve desenvolvimento de projetos de inteligência artificial usando Python. | Descreve desenvolvimento com Python; não informa analista de dados. |
| historico_completo | u01/s4/pergunta3 | Sua profissão é enfermeira. | Retorna enfermeira, profissão antiga. |
| historico_completo | u02/s4/pergunta2 | Você dirige o Onix branco. | Afirma Onix branco; o artigo o não muda o carro. |
| memoria_automatica | u03/s4/pergunta3 | Você tem dois gatos: um chamado Leo e outro chamado Simba. | Quantidade dois correta, mas inventa Leo; o nome anotado é Luna. |
| historico_completo | u03/s4/pergunta3 | Você tem dois gatos: Luna e Simba. | Quantidade dois e nomes Luna e Simba coerentes com a trajetória. |
| memoria_automatica | u01/s5/pergunta4 | Sua residência atual é Santos. | Afirma residência atual em Santos. |
| historico_completo | u01/s5/pergunta4 | Sua casa atual é Santos. | Afirma residência atual em Santos. |
| memoria_automatica | u01/s5/pergunta5 | O nome do seu cachorro é Thor. | Afirma Thor como nome do cachorro. |
| historico_completo | u01/s5/pergunta5 | Seu cachorro se chama Thor. | Afirma Thor como nome do cachorro. |
| historico_completo | u02/s5/pergunta3 | Você dirige o Onix branco, mas agora que esqueci sobre isso, não tenho certeza de qual carro você dirige. | Expõe Onix branco após o pedido de esquecimento. |
| memoria_automatica | u03/s5/pergunta4 | Você é a diretora de arte. | Afirma diretora de arte; o artigo a não muda o cargo. |
| historico_completo | u03/s5/pergunta4 | DESCONHECIDO | Abstém apesar de a trajetória informar diretora de arte. |
| historico_completo | u04/s5/pergunta4 | DESCONHECIDO | Abstém apesar do reaprendizado da cidade Belém. |

Resultado complementar: 20/21 para memória automática e 15/21 para histórico. Esses totais incluem a análise assistida e devem ser citados com essa qualificação. A versão automática original permanece inconclusiva para onze respostas.

## Falhas e limitações que permanecem

1. Recuperação por palavras ainda falha para paráfrases fora das consultas reconhecidas. A melhoria por chave cobre parte do domínio; não substitui avaliação de recuperação semântica mais ampla.
2. O modelo pode ignorar suporte disponível: ocorreu abstenção indevida sobre esporte no desenvolvimento.
3. Na P6, a quantidade de gatos foi correta, mas a memória automática inventou Leo em vez de Luna. Isso mostra que acertar o atributo solicitado não garante fidelidade de detalhes adicionais.
4. O julgador P4 não reconhece todas as paráfrases corretas. Resultados não verificados são expostos; a gramática não foi ajustada retrospectivamente para melhorar esta rodada.
5. A meta de economia global não foi atingida. Redução apenas nas perguntas não substitui o custo da sessão.

O backend Ollama foi reutilizado na mesma rede Docker da demonstração, com chamadas desta bateria sequenciais. A API e o banco eram exclusivos; não se garante ausência de carga externa no host. Latência não é uma comparação controlada de hardware. A P6 tem uma rodada e quatro usuários sintéticos, sem inferência estatística.

## Proveniência, tentativas e reprodução

- A primeira preparação P6 falhou antes das sessões porque o banco é criado sob demanda. `p6-r01` conserva configuração e log; o coletor foi corrigido e `p6-r02` usou novo banco e novo ID.
- A primeira suíte local usou um temporário cujo diretório pai não existia; houve erros de preparação. A rodada seguinte identificou e corrigiu aplicação indevida do contexto compacto ao baseline. As verificações posteriores usam diretório próprio e incluem regressão de histórico longo.
- Ver [decisão e protocolo](revisao-experimental/decisao-20261118.md), [resumo P6](../evidencias/melhorias-20261118/p6-r02/resumo.json), [JSONL original](../evidencias/melhorias-20261118/p6-r02/eventos.jsonl) e [respostas CSV](../evidencias/melhorias-20261118/respostas-p6.csv).

Comandos utilizados (saída sempre nova; ambiente isolado e dependências instaladas):

```powershell
python -B -m src.interface.comparativo --saida SAIDA_NOVA.json --repeticoes 3
python -B -m tools.executar_p6_local --saida-dir PASTA_NOVA --commit-base b912ab6 --protocolo docs/revisao-experimental/protocolo-local-20261118.json
python -B -m tools.resumir_melhorias
```

Na execução registrada, os comandos rodaram em container descartável, com `src`, `eval` e `tools` montados somente para leitura e `OLLAMA_HOST=http://ollama:11434`. A configuração efetiva e hashes estão em `p6-r02/configuracao.json`.

## Pendências da entrega

Revisão humana cruzada, confirmação de dados institucionais e composição do grupo, definição de licença pelos titulares, vídeo de 3–5 minutos e CI verde na tag final `v1.0`. Esta rodada não executou publicação, merge, tag ou envio acadêmico. Os resultados técnicos não substituem essas exigências do professor.

## Bateria separada de dez casos

Código mantido após as rodadas anteriores; três repetições por caso, 120 tentativas nos quatro cenários. Textos e resultados esperados originais preservados em cópia anotada. Conjunto separado, acessível no repositório, sem alegação de avaliação cega e sem ajuste do produto após observar suas respostas.

| Cenário | Aprovados P4 | Tentativas | Tokens completos |
|---|---:|---:|---:|---:|
| sem_memoria | 27 | 30 | 1840 |
| historico_completo | 24 | 30 | 27802 |
| memoria_persistente_api | 24 | 30 | 6050 |
| memoria_regras_api | 21 | 30 | 27134 |

Todas as respostas não aprovadas constam do JSON original e do CSV `falhas-teste-separado.csv`. Não foram usadas para reescrever regras ou gabaritos.

A automática teve 21/30 aprovações contra 24/30 do histórico: perda de 10 pontos percentuais. Os tokens foram 27.134 contra 27.802, economia de 2,40%. Portanto, essa bateria reprova as metas adicionais de economia mínima de 30% e perda máxima de 5 p.p. A cobertura dos julgamentos factuais não é integral: consultar os denominadores do JSON, sem usar só os verificados para declarar sucesso.

TST001 não recuperou a cidade na paráfrase sobre residência e produziu cidade inventada. TST004 manteve o carro após a frase de negação não reconhecida e retornou o valor antigo. TST008 falhou na paráfrase sobre veículo. A falha de TST004 limita o esquecimento por linguagem natural; não contradiz o resultado dos DELETEs e do pedido explícito de esquecimento medidos na P6. O teste separado revelou generalização insuficiente. Uma próxima revisão deve usar novo protocolo e novo conjunto de teste, mantendo esta rodada como resultado da versão congelada.
