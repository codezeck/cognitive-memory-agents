# Fechamento da validação P6 — 21/11/2026

Ezequiel declarou concluída a validação funcional no escopo testado após repetir a P6 e autorizou a publicação das alterações. Esse aceite não representa revisão humana dos colegas, integração de PR, tag, vídeo ou envio institucional.

## Cinco rodadas da P6 no mesmo ambiente

Foram preservados cinco relatórios completos do perfil Professor em 21/11: cem pares de sessões, 105 respostas por cenário, nenhuma falha técnica e mesma geração, modelo/digest, roteiro e anotações conforme hashes registrados. A análise v2 foi calculada sobre todos os originais, sem novas chamadas ao modelo. As notas P4 permanecem intactas. Datas/etapas abaixo descrevem desenvolvimento, não experimentos que isolem o efeito causal de cada manutenção.

| Horário local | Etapa registrada | Histórico | Automática | Redução |
|---|---|---:|---:|---:|
| 09:28 | Sem análise P6 adicional | 23.016 | 3.572 | 84,48% |
| 11:08 | Sem análise P6 adicional | 25.411 | 3.604 | 85,82% |
| 11:27 | Sem análise P6 adicional | 22.045 | 3.565 | 83,83% |
| 12:20 | Análise P6 v1 | 28.125 | 3.566 | 87,32% |
| 12:38 | Análise P6 v2 | 25.747 | 3.576 | 86,11% |

**Redução consolidada: 85,62%**, calculada como 1 − soma dos tokens automáticos / soma dos tokens do histórico. Foram 124.344 contra 17.883 tokens. Média por rodada completa: 24.868,8 no histórico e 3.576,6 na automática; por sessão, 1.243,44 e 178,83. A média aritmética dos percentuais individuais é 85,51%; é outra estatística e não foi chamada de redução das somas. A faixa observada foi de 83,83% a 87,32%.

## Resultados por etapa e limites da comparação

As três primeiras rodadas foram produzidas antes da análise P6 adicional; a quarta registra as fontes v1 e a quinta as fontes v2. Os arquivos de geração são idênticos no recorte comparado; mudanças de interface/análise não demonstram ganho causal de geração. O inventário registra os hashes de cada fonte e do gabarito incorporado. As médias por etapa e os critérios de qualidade P4/v2 ficam no JSON e no CSV, sem ocultar reprovados ou inconclusivos.

Na rodada final, o histórico usou 25.747 tokens e a automática 3.576, redução de 86,11%. A leitura v2 encontrou 9/17 fatos aprovados, quatro reprovados e quatro inconclusivos no histórico; 16/17 aprovados e um inconclusivo na automática. Abstenções: 3/4 e 4/4. Conteúdo mais formato: 3/21 e 12/21. A resposta automática inconclusiva foi “Torço para Coritiba”, uma formulação não coberta pela gramática; não foi promovida a aprovação nem tratada como erro confirmado. No histórico, os limites do julgador também permanecem registrados. Persistência: 19/19 oportunidades elegíveis; exclusão: 2/2, no escopo observado.

As leituras adicionais não modificam respostas, tokens, P4/P5 ou anotações. Dados pessoais, resíduos em RAM e informação antiga têm escopos próprios; aprovação dos checkpoints não certifica eliminação de todas as cópias externas. A pré-carregada e o controle sem memória não fazem parte da P6. O comparativo sintético e o conjunto personalizado continuam separados, com consolidados anteriores de 84,91% na rodada oficial atual e 74,13% no personalizado. Não se combinam esses protocolos em uma média universal.

## Evidência e reprodução

O [pacote de originais, leituras e recálculo](../evidencias/fechamento-p6-20261121/README.md) preserva SHA256 e compara os consumos diretamente das sessões. Executar o script de recálculo não chama API, Docker, banco nem modelo. As [regras e ressalvas da P6](julgamento-p6.md) continuam explícitas. Novos textos fora da gramática podem continuar inconclusivos; a validação funcional aceita pelo usuário não converte esse limite em revisão humana automática.

## Próximos itens de entrega

Publicar a revisão autorizada e conferir seu CI; obter revisão humana do grupo e integrar somente após aceite; revalidar em clone novo com projeto Docker próprio; revisar coletivamente a pesquisa; reunir os MDs dos colegas, gravar o vídeo, criar a tag aprovada e conferir o CI da tag e o envio. A limpeza dos ambientes antigos permanece adiada até preservar os relatórios e validar a instalação nova.
