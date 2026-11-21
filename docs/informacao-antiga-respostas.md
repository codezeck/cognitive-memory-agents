# Informação antiga na resposta final — 21/11/2026

A métrica adicional `informacao-antiga-v1` separa devolução indevida de um valor substituído de erro factual genérico, abstenção, esquecimento e isolamento. Ezequiel já validou o funcionamento no escopo testado; esta mudança fecha a leitura da avaliação, sem reabrir a bateria nem alterar as respostas, P4/P5 ou tokens.

## O que é contado

Somente perguntas factuais com `avaliacao.valores_antigos` explicitamente anotados entram nas oportunidades. Categoria “atualizacao” sozinha não define um valor antigo. Campos ausentes/inválidos têm aplicabilidade desconhecida. Anotação válida sem valores antigos e casos de abstenção são não aplicáveis. Esquecidos e fatos de outro usuário continuam nas métricas próprias, não são inferidos como valores substituídos.

| Exemplo, atual Campinas e antigo Osasco | Classificação desta métrica |
|---|---|
| Osasco; ou Você mora em Osasco. | Valor antigo afirmado como resposta: conta no numerador |
| Antes Osasco; agora Campinas | Contraste temporal reconhecido: não conta como retorno indevido |
| Não é Osasco; é Campinas | Correção reconhecida: não conta como retorno indevido |
| Talvez Osasco; ou Não é Osasco | Menção com sentido não verificado: inconclusiva |
| Recife; ou DESCONHECIDO | Sem valor antigo literal; pode continuar sendo erro factual no P4 |
| Resposta ausente, erro técnico ou trajetória incompleta | Não verificada; permanece na cobertura |

Usa-se normalização de caixa/acentos, limites de palavra e a gramática existente do P4. Uma ocorrência literal não basta para afirmar erro temporal. Paráfrases fora da gramática e aliases antigos não anotados podem escapar ou ficar inconclusivos; esta métrica não é revisão semântica humana universal. “Sem ocorrência literal” não garante resposta correta.

## Taxa, denominador e cobertura

Taxa = `100 × retornos antigos indevidos reconhecidos / oportunidades verificadas`. **Maior taxa é pior.** A cobertura é `100 × oportunidades verificadas / oportunidades elegíveis`. Mostram-se também não verificados, não aplicáveis e aplicabilidade desconhecida. Tentativas esperadas ausentes não somem: viram não verificadas se a anotação for elegível. Sem denominador, a taxa é desconhecida; sem oportunidades anotadas, não aplicável.

## Relatórios existentes e novos

- A leitura do histórico e a importação recalculam a análise adicional a partir dos casos/anotações incorporados, sem iniciar modelos. Os arquivos originais baixados continuam intactos.
- Novos relatórios do comparativo e da P6 incluem `analise_informacao_antiga`; a leitura antiga mantém os julgamentos originais. P6 usa suas próprias anotações e respeita falhas de trajetória.
- Cada faixa mostra taxa, oportunidades e cobertura. “Mostrar respostas” identifica o resultado por pergunta; ocorrências positivas e inconclusivas entram nas respectivas listas.
- Relatórios sem anotações compatíveis mostram análise indisponível; não são preenchidos com zero. Não buscar um gabarito atualizado para completar silenciosamente uma rodada antiga.

## Releitura das evidências, sem nova execução

Os 14 JSON originais da [consolidação de 20/11](consolidacao-testes-20261120.md) foram preservados. As análises derivadas estão no [índice de 21/11](../evidencias/informacao-antiga-20261121/README.md).

Na última rodada personalizada, histórico, automática e sem memória tiveram zero retornos antigos indevidos reconhecidos em 15/15 oportunidades verificadas. A pré-carregada teve zero em 13/15 verificadas, com duas inconclusivas e cobertura de 86,67%. Isso não muda 42/45 fatos da automática, 44/45 do histórico ou as demais falhas. No controle sem memória, zero de desatualização não significa recuperar fatos: ele pode responder incorretamente sem repetir o valor antigo.

A P6 completa posterior de 20/11 teve um retorno antigo indevido em nove oportunidades no histórico (11,11%) e zero em nove na automática, com cobertura de 100% em ambos. A P6 parcial preserva cobertura parcial. Não misturar essas sessões com tentativas sintéticas para uma taxa geral.

## Conferência offline

`python -m eval.informacao_antiga --entrada caminho/relatorio.json --saida caminho/analise-nova.json` cria somente um derivado, sem rede ou LLM, e recusa saída existente. Para conferir as 14 análises preservadas, executar `python evidencias/informacao-antiga-20261121/conferir.py`.

A suíte de regressão passou com 1.092 testes Python, 67 opcionais ignorados e 51 testes JavaScript. A conclusão permanece limitada às anotações e à gramática descritas, sem alegação de equivalência estatística ou aprovação humana automática.
