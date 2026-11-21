# Contexto v3: decisão anterior à medição

Autorização: pedido do usuário nesta sessão, em 18/11/2026: “precisamos melhorar
os acertos e a quantia de tokens”. A nova versão altera a política de execução;
não substitui os resultados ou as decisões da v2.

1. Confirmar localmente operações de memória inteiramente reconhecidas pelas
   regras. Gravação, atualização e exclusão continuam reais; a confirmação não
   exige geração. Mensagens mistas e trechos não cobertos seguem para o modelo.
2. Registrar explicitamente `origem_uso=politica_local` e zero chamadas. Campos
   de uso não medidos continuam nulos; o avaliador pode derivar zero apenas
   dessa origem explícita e da contagem zero. CPU, SQLite e embeddings não são
   contabilizados como tokens do gerador e não são custo computacional zero.
3. Preservar fatos confirmados na conversa; após esquecer, não reintroduzir
   os valores removidos no histórico ao confirmar a ação. Pedidos mistos com
   esquecimento limpam também o turno gerado.
4. Resolver negação por valor somente quando o valor corresponde a uma única
   chave ativa do próprio usuário. Fato antigo e referência ambígua não apagam
   o estado atual. A exclusão de uma chave inclui suas versões substituídas.
5. Usar o mesmo reconhecimento de atributos na busca e na verificação de
   suporte. Consultas diretas com suporte recuperado usam prompt breve e
   somente as memórias pertinentes, sem histórico contraditório redundante.
   O modelo continua gerando respostas factuais e gerais.
6. O baseline permanece com geração em cada mensagem e histórico completo do
   episódio. Essa diferença arquitetural é declarada; não apresentar a economia
   como redução obtida apenas por compressão do prompt.

As baterias já observadas, inclusive os dez casos anteriormente separados,
passam a ser material de desenvolvimento desta versão. Não serão chamadas de
teste reservado ou cego. Uma nova bateria sintética de 16 casos foi preparada
e revisada antes da primeira medição v3; contém novos valores e trajetórias,
mas foi elaborada com conhecimento do domínio e não é validação independente
da equipe. Uma inconsistência preliminar de anotação foi corrigida antes de
qualquer execução: a pergunta sem resposta passou a ser sobre nome, de acordo
com o atributo nome suportado pelo P4.

Manter os mesmos gabaritos P6 e o julgador P4-v3. Não ajustar o julgador para
acompanhar novas respostas. Separar conteúdo aprovado, não verificados,
respostas desatualizadas, vazamentos e checkpoints. Expor falhas e comparar
ingestão, perguntas e sessão completa, com cobertura.

O manifesto anterior à medição fica em
`evidencias/contexto-v3-20261118/congelamento.json`. A primeira tentativa foi
interrompida após constatar falta de suporte de fatos válidos também no baseline;
o log parcial está preservado e o manifesto da correção é `congelamento-r02.json`.
As duas tentativas são identificadas e não constituem teste cego. A execução P6 guarda os
hashes efetivamente usados e a identificação do modelo. Metas adicionais:
economia mínima de 30%, perda máxima de 5 p.p. e nenhum novo vazamento ou
resposta desatualizada; uma amostra pequena não comprova equivalência estatística.
