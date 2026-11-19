# Evidências da candidata v3 — 18/11/2026

Estado de entrega: **candidata para revisão**, não enviada. Avaliações usam Ollama real e dados sintéticos. A data da pasta é a data local de início; timestamps UTC dos brutos podem estar em 19/11. Arquivos históricos permanecem preservados.

| Afirmação/artefato | Fonte verificável |
|---|---|
| Pesquisa atual, 16 páginas textuais/25 totais e 11 referências | [PDF](../../docs/pesquisa-abnt.pdf), [metadados](pesquisa-geracao.json), [texto v3](../../docs/pesquisa-v3.md), [gerador](../../tools/gerar_pesquisa.py) |
| P6, 20 sessões por cenário | [JSONL evento a evento](../contexto-v3-20261118/p6-r01/eventos.jsonl), [resumo](../contexto-v3-20261118/p6-r01/resumo.json), [configuração](../contexto-v3-20261118/p6-r01/configuracao.json) |
| Persistência após reinícios, exclusão SQLite/RAM delimitada | [Evidências operacionais](../contexto-v3-20261118/p6-r01/evidencias-operacionais.json); snapshots e logs na mesma pasta |
| P6: 21/21 aprovações, tokens 3.593/22.228, 83,84% em 20/20 pares | [Respostas CSV](../contexto-v3-20261118/respostas-p6.csv), [tabela consolidada](resultados-consolidados.csv), [Figura P6](figuras/p6-v3.png) |
| Validação nova: 16 casos × 3 repetições × 4 cenários | [Dataset](../../eval/dataset_validacao_v3_20261118.json), [JSON original](../contexto-v3-20261118/validacao-nova-r02-3rep.json), [Figura validação](figuras/validacao-v3.png) |
| Automática 48/48; baseline 36/48; tokens 6.025/39.844 e 84,88% | Mesmos brutos acima: comparação de tokens usa somente **47/48 pares**, pois houve um timeout no baseline |
| Fontes e protocolo anteriores à medição | [Congelamento](../contexto-v3-20261118/congelamento-r02.json), [decisão](../../docs/revisao-experimental/decisao-contexto-v3-20261118.md), [protocolo](../../docs/revisao-experimental/protocolo-contexto-v3-20261118.json) |
| Engenharia v3 | [Validação da aplicação](../contexto-v3-20261118/validacao-final.json), [testes anteriores](../contexto-v3-20261118/testes-r02-final.xml), [testes da candidata](testes-candidata.xml) |
| Acadêmico e licenças | [Dados validados](../../docs/dados-academicos.json), [MIT](../../LICENSE), [NOTICE](../../NOTICE), [inventário](../../third_party/licenses/inventario-python.json) |
| Galeria histórica com fonte e data | [Recuperação 14/11](../entrega/20261114-entrega-ae9eb113/r04-02-recuperacao.png), [abstenção 14/11](../entrega/20261114-entrega-ae9eb113/r04-05-abstencao.png), [erro de modelo 14/11](../entrega/20261114-entrega-ae9eb113/r04-06-falha-modelo.png) |

## Falhas preservadas e análise

1. **Recuperação por paráfrase e negação na v2:** a rodada preservada inclui cidade/veículo não reconhecidos, carro antigo após negação e abstenção indevida sobre esporte. [Relatório com entradas e respostas](../../docs/melhorias-avaliacao-20261118.md) e [brutos v2](../melhorias-20261118/). A v3 ampliou busca por chave e negação por valor; a gramática continua limitada.
2. **Timeout técnico no baseline v3:** `V3T008`, repetição 2. A tentativa continua no JSON original; sua ausência de tokens não vira zero. O par é excluído somente do cálculo pareado (47/48), e permanece nas 48 tentativas de qualidade.
3. **Limitação de alias no julgador:** a resposta numérica “Quatro” do baseline não é aceita pelo gabarito numérico literal de um caso. Resultados não foram corrigidos retrospectivamente. Na P6, 12 respostas do baseline exigem revisão; não são 12 erros semânticos comprovados.
4. **Erro aritmético histórico do modelo:** o ensaio r05 respondeu 4 para 2 + 3. O [relatório Docker](../../docs/validacao-entrega-docker.md) preserva falha, diagnóstico e tentativas do inicializador. O percurso posterior aprovado não elimina essa ocorrência.
5. **Primeira tentativa interrompida da v3:** [log parcial](../contexto-v3-20261118/tentativa-r01-parcial.log). Reconhecimento de suporte foi corrigido também no baseline antes da rodada r02, para manter o contrato comum.

## Reproduzir e interpretar

[Relatório v3](../../docs/acertos-tokens-contexto-v3.md) contém comandos de avaliação e limites. Para regenerar somente os gráficos/CSV a partir dos brutos: instalar as dependências de documentação em ambiente separado e executar `python -m tools.gerar_figuras_v3`. Gerar PDF: `python tools/gerar_pesquisa.py`, com fontes Times disponíveis. Não sobrescrever brutos ao repetir experimentos: escolher outra pasta.

P4 é automático e limitado. O baseline da P6 tem 8 aprovações, 1 reprovação verificada e 12 não verificados. Os resultados não comprovam equivalência estatística, generalização irrestrita ou conformidade jurídica. Zero local exige origem e contagem explícitas. A galeria de 14/11 é histórica, não captura nova da v3.

## Consolidação documental

O [README](../../README.md) preserva nomes/RA e o parágrafo do Tema 11/portfólio. O [índice técnico](../../docs/README.md) reúne os nove itens do enunciado. [Manual do professor](../../docs/manual-professor.md), [reprodução Docker](../../docs/reproduzir-avaliacao-v3.md), [prompt de continuidade](../../docs/prompt-finalizacao.md) e [contextos de IA](../../docs/registro-ia/README.md) preparados. A [revisão complementar](../../docs/revisao-experimental/revisao-humana-baseline-v3.csv) contém 12 respostas originais e campos humanos em branco. A pesquisa foi consolidada com metodologia v3, bibliografia ordenada e apêndice de reprodução.

Validação desta consolidação (retomada em 19/11): **960 testes Python aprovados/66 ignorados**, oito JavaScript e lint crítico aprovados; [XML](verificacao-documentacao/testes.xml), [resumo](verificacao-documentacao/validacao.json). O [preflight Docker](verificacao-documentacao/preflight.log) confirmou modelo/digest e ausência do banco/segredos do host no contêiner. O [comparativo curto](verificacao-documentacao/comparativo-comando.json) teve quatro respostas sem falhas técnicas. A [reprodução P6](verificacao-documentacao/p6-comando/resumo.json) concluiu 40 registros de sessão e 42 respostas, sem falhas técnicas; essa conferência não substitui as medições originais do PDF. O [preparo LF/CRLF](verificacao-documentacao/fontes-lf-crlf.json) confere o congelamento preservando conteúdo. A [prova de preservação](verificacao-documentacao/preservacao-readme.json) verifica o cabeçalho, os nomes/RA e o texto do Tema 11/portfólio.

## Publicação e pendências

[PR #45](https://github.com/codezeck/cognitive-memory-agents/pull/45) publicado; revisão solicitada a **Palomalimaa** e **Vinicius000011**, sem parecer registrado até a consulta. [CI #140 verde](https://github.com/codezeck/cognitive-memory-agents/actions/runs/44435946851) no commit `8b89b4b33bd9697ce3cf9b98506a1944b61b8edd`; [registro dos jobs](publicacao.json). Esta execução é do PR, não de uma tag final. Não foi possível obter captura da tela por causa do bloqueio do controle de UI.

**Instalação pelo manual aprovada:** checkout limpo do commit acima, `Iniciar.ps1 -Porta 18003 -Projeto cma-candidata-v3 -SemAbrir`. Camadas de imagem usaram cache; volume de pesos novo, com download observado de 1.929.903.072 bytes. Preparo real concluído, chat HTTP 200, cookies/identidade e **19 verificações HTTP aprovadas**, incluindo reinício real, recuperação, atualização, isolamento, esquecimento e pergunta geral. [Log da instalação](instalacao-manual.log), [resumo](instalacao-resumo.json), [percurso JSONL](percurso-http.jsonl), [verificações](percurso-resumo.json), [script exato](verificar-percurso.py). Não houve nova inspeção visual da interface.

Galeria atual do documento: [capa v3](galeria/pdf-capa-v3.png), [resultados v3](galeria/pdf-resultados-v3.png). São renders do PDF entregue, separados das capturas históricas de navegador. [Manifesto SHA256](manifesto-sha256.json) permite conferir os artefatos. **Vídeo pendente:** o controle de tela encerrou a sessão por não confirmar a URL no Windows; [roteiro v3](../../docs/roteiro-demonstracao.md) preparado para gravação pelo grupo. **Revisão humana, integração aprovada, tag `v1.0`, CI dessa tag e envio acadêmico** ainda dependem dos respectivos registros. [Checklist e explicação do fechamento](../../docs/checklist-entrega.md).
