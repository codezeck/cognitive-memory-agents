# Casos de falha

Casos em que o sistema errou, com a análise da causa e como reproduzir. Os dados vêm das avaliações oficiais em `evidencias/` (ver `docs/guia-avaliacao.md`). Onde a causa ainda não foi confirmada no código, o texto diz "a confirmar".

## Caso 1: o modelo inventa um valor depois que a memória foi esquecida

- **Onde:** comparativo, casos `CMP003` (esquecer a cidade) e `CMP004` (remover o time), cenários `memoria_persistente_api` e `memoria_regras_api`.
- **Entrada:** "Moro em Osasco." → "Esqueça minha cidade." → "Em que cidade moro? [...] Se não houver informação suficiente, responda exatamente DESCONHECIDO."
- **Esperado:** `DESCONHECIDO` (ou equivalente a "não sei").
- **Obtido:** em 9 das 21 respostas dos dois cenários com memória, o modelo respondeu outra coisa. Em 6 inventou um valor (Lisboa, Londres, São Paulo, Belo Horizonte, Internacional, Grêmio) e em 3 deformou a palavra (DENAH, DESAFIO, SPORTS-FOOTBALL).
- **Causa:** o esquecimento funcionou. Nenhuma resposta errada trouxe o valor apagado (Osasco, Vasco), e os casos sem memória esperada tiveram 6 de 6 sem resíduos. O erro está no modelo local de 3 bilhões de parâmetros, que não obedece à instrução de responder `DESCONHECIDO`. Nos casos de esquecimento o estado de memória é vazio, então o cenário equivale a `sem_memoria`, que também inventa valores.
- **Impacto:** a camada de memória cumpre o direito ao esquecimento, mas a resposta final depende do modelo. Um modelo maior ou uma verificação de formato na resposta reduziria o problema.
- **Como reproduzir:** subir a API (ver `docs/guia-avaliacao.md`) e rodar `python eval/avaliar_comparativo.py --repeticoes 3 --saida evidencias/comparativo_reproducao.json`. O modelo não é determinístico: o número exato varia entre execuções.

## Caso 2: a recuperação não encontra a memória quando a pergunta usa outras palavras

- **Onde:** benchmark de 20 sessões com embedder `hash` (`evidencias/memoria/resultados_recuperacao_hash.json`). Acerto de 71,4% e lembranças corretas de 64,7%, contra 100% e 100% com o embedder semântico.
- **Entrada e fato guardado:**

| Pergunta | Fato guardado |
| --- | --- |
| "Em que cidade eu moro hoje?" | "Mudei para Campinas." |
| "Qual é a minha profissão?" | "Agora sou coordenadora de enfermagem." |
| "Qual cidade é a minha casa atualmente?" | "Me mudei para Santos." |
| "Que hobby eu tenho?" | "Gosto de fotografia." |
| "Qual é o meu cargo?" | "Virei diretora de arte." |

- **Esperado:** recuperar o fato correto.
- **Obtido:** a memória esperada não foi recuperada em 5 desses casos (`recuperou_esperado: false`) e nenhum devolveu informação antiga (`devolveu_proibido: false`).
- **Causa:** em todos os casos a pergunta e o fato não têm nenhuma palavra em comum. O `EmbedderHash` (`src/memoria/embeddings.py`) transforma cada palavra, em minúsculas e sem acento, em uma posição de um vetor, então só aproxima textos que repetem as mesmas palavras. Pares como "profissão" e "coordenadora", ou "hobby" e "fotografia", não se aproximam.
- **Impacto:** a API usa `EmbedderHash` por padrão (`src/armazenamento/repositorio.py` e `src/memoria/store_mem.py`), então este é o comportamento do sistema como entregue. O embedder semântico só foi usado no benchmark. O comentário do próprio `EmbedderHash` diz que ele serve para testes e CI e que a avaliação final deve usar um embedder semântico.
- **Como reproduzir:** `python eval/avaliar_memoria.py --embedder hash --saida evidencias/memoria/reproducao_hash.json` e depois com `--embedder semantico` para comparar.

## Caso 3: pergunta que depende de mais de uma memória

- **Onde:** benchmark, usuário `u03`, sessão 4, tipo `multiplas_memorias`.
- **Entrada:** fatos "Minha gata se chama Luna." (sessão 1) e "Adotei um segundo gato, o Simba." (sessão 4). Pergunta: "Quantos gatos eu tenho?"
- **Esperado:** recuperar as duas memórias (Luna e Simba).
- **Obtido:** nenhuma das esperadas foi recuperada (`recuperou_esperado: false`).
- **Causa:** o `EmbedderHash` compara palavras inteiras, sem reduzir à raiz. "gatos", "gata" e "gato" são palavras diferentes e não se aproximam. A pergunta também exige combinar duas memórias, o que o benchmark cobre com um único caso.
- **Como reproduzir:** o mesmo comando do Caso 2.

## Observações

- **Formato do avaliador:** no `historico_completo`, a resposta "Pratico yoga." foi reprovada para o esperado `yoga` (`CMP005`, repetição 2). A resposta correta foi reprovada por formato.
- **Resposta sem relação com o caso:** no `historico_completo`, a resposta "Pratico natação." (`CMP005`, repetição 3) não aparece nas mensagens do caso. A confirmar se foi erro do modelo ou resíduo de outro caso na mesma conversa.
- **Limite do experimento:** o conjunto comparativo tem 7 casos e o modelo varia entre repetições. Os números são preliminares.
