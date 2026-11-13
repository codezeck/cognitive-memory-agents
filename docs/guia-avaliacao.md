# Guia de avaliação

Como reproduzir as avaliações do projeto e como ler as métricas. Comandos para Windows (PowerShell), na raiz do repositório.

## O que é avaliado

| Avaliação | Pergunta que responde | Script | Responsável |
|---|---|---|---|
| Comparativo do agente | A memória melhora as respostas do chatbot e reduz tokens em relação ao histórico completo? | `eval/avaliar_comparativo.py` | Ezequiel |
| Recuperação de memórias | Em 20 sessões simuladas, o sistema lembra, atualiza e esquece corretamente? | `eval/avaliar_memoria.py` | Vinicius |
| Regras de memória | As regras extraem, atualizam e esquecem fatos em frases novas? | `eval/avaliar_regras.py` | Vinicius |

## Pré-requisitos

1. Ambiente Python 3.13 (versão local registrada em `.python-version`):

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

## Verificação local de engenharia — 12/11/2026

A base foi reexecutada antes das alterações: **695 aprovados, 1 módulo ignorado, nenhuma falha**. Após a revisão P4-v3, testes dos provedores e teste de bloqueio do conjunto final: **826 aprovados, 1 módulo ignorado, nenhuma falha** (15,81 segundos nesta máquina). São resultados de testes, não novas métricas experimentais P3/P4/P5/P6. O módulo semântico foi ignorado porque sua ativação explícita pode baixar um modelo.

Comando usado, no `.venv` ativo, evitando bytecode, cache e conflito com a pasta temporária padrão:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
Remove-Item Env:TESTAR_EMBEDDER_SEMANTICO -ErrorAction SilentlyContinue
$pastaTestesZeck = Join-Path $env:TEMP ("cma-zeck-" + [guid]::NewGuid().ToString("N"))
python -B -m pytest tests -q -ra --tb=short -p no:cacheprovider --basetemp $pastaTestesZeck
git diff --check
```

As gravações dos testes ficam em temporários ou RAM; não executar os avaliadores completos como substituto dessa verificação. `pip check` não encontrou dependências quebradas. `git diff --check` passou. Docker não pôde ser conectado e Ollama recusou conexão na verificação local; OpenAI real não foi chamada. A rodada real P6 permanece bloqueada pelas dependências detalhadas abaixo, e os dez casos finais continuam sem metadados P4. Esses limites não são resolvidos pelos testes verdes.

## Avaliação comparativa do agente (um comando)

1. Subir a API (terminal 1; deixe aberto):

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=]+)=(.*)$') { Set-Item "env:$($matches[1].Trim())" $matches[2].Trim() } }
uvicorn src.api.main:app --port 8000
```

A API também pode subir por `docker compose up` (ver o README; subida validada em 05/11, ver `evidencias/agente/`).

2. Rodar a avaliação (terminal 2, com o `.venv` ativo). Carregue também neste terminal as variáveis de configuração usadas pela API, pois o controle de histórico chama o agente diretamente:

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=]+)=(.*)$') { Set-Item "env:$($matches[1].Trim())" $matches[2].Trim() } }
python eval/avaliar_comparativo.py --repeticoes 3 --saida evidencias/comparativo_NOME.json
```

Parâmetros: `--base-url` (padrão `http://127.0.0.1:8000`), `--provedor` (padrão `ollama`), `--modelo` (padrão `qwen2.5-coder:3b`), `--repeticoes` e `--saida`. O script não sobrescreve um arquivo de saída existente. Ao final ele imprime o bloco `===== RESUMO =====` e grava os resultados completos em JSON.

`--timeout-historico SEGUNDOS` define um prazo positivo e finito por caso do controle de histórico. Sem esse argumento, o prazo é 30 segundos mais 60 segundos por turno (mínimo de um turno). Inclui a inicialização, o recebimento do resultado e a saída do processo filho. Em timeout ou falha, o supervisor recolhe o filho; se necessário, usa encerramento forçado, com até duas esperas adicionais de dois segundos. O prazo não muda os timeouts nem os parâmetros dos adaptadores.

### Cenários

| Cenário | O que faz |
|---|---|
| `sem_memoria` | Envia só a pergunta final. Mostra o que o modelo inventa sem contexto. |
| `historico_completo` | Executa cada caso em um processo filho independente com `spawn` (compatível com Windows), reutilizando `AgenteLocal.responder` com `memorias=[]`, sem `/conversas` ou regras e busca de memórias. O filho amplia o limite para preservar todos os turnos do caso e limpa seu histórico antes e depois, inclusive em erro. |
| `memoria_persistente_api` | Grava o estado esperado como memórias e envia só a pergunta final. É um teto ideal, pois o estado é inserido à mão. |
| `memoria_regras_api` | Envia as mensagens anteriores pela API, deixando as regras extraírem os fatos; reinicia a sessão e faz a pergunta final sem histórico. |

Os casos estão em `eval/dataset_comparativo.json` (CMP001 a CMP007: recuperação, atualização, esquecimento e variações).

O controle de histórico reutiliza o mesmo agente, `SYSTEM_PROMPT`, adaptadores e critérios de resposta, com o provedor e modelo selecionados nos argumentos. Para uma comparação válida, configure o avaliador e a API para a mesma instância do modelo e os mesmos parâmetros efetivos. Em Docker ou API remota, o endereço acessível ao avaliador pode ser diferente do endereço dentro do contêiner: confira `OLLAMA_HOST` e as configurações do provedor em ambos os ambientes. O filho herda o ambiente do avaliador. O limite de dez interações permanece no produto e no processo principal; somente o filho usa um limite suficiente para o caso. Pedidos de esquecimento no controle são mensagens ao modelo, sem reset automático por regras.

Processos independentes isolam o `USUARIO_HISTORICO` e o estado em RAM, inclusive em execuções concorrentes desse controle. Isso não torna os demais cenários da API seguros para execução concorrente: eles ainda usam o usuário remoto compartilhado do benchmark. O contexto completo é montado pelo agente, mas a janela de contexto do modelo continua sendo um limite externo; não há garantia de que o runtime processe um prompt maior do que sua capacidade. Em encerramento forçado, o `finally` do filho pode não executar; o fim do processo descarta seu histórico em RAM.

Cada resultado identifica `via` como `agente_local` ou `api`. Os campos legados de latência do histórico medem a execução direta do agente, enquanto os demais medem o serviço da API; não devem ser interpretados como medições equivalentes. Os tokens são separados por etapa conforme a seção abaixo.

O tempo de criação e comunicação com o processo filho entra em `tempo_execucao_ms` do caso, sem ser acrescentado às latências individuais das chamadas. O isolamento por processo não é uma medição de custo computacional ou monetário.

### Métricas

| Métrica | Como é calculada |
|---|---|
| Acertos (`taxa_aprovacao_pct`) | Conteúdo factual correto ou abstenção adequada, sem informação proibida. Usa todos os casos tentados como denominador. Formato é reportado separadamente. |
| Recuperação exata | Conjunto de memórias usadas igual ao esperado, texto por texto. |
| Recuperação equivalente | Igual à exata, mas reconhecendo variantes conhecidas de redação (por exemplo "Moro em X" e "Mora em X"). Complementar: cobre só os formatos previstos no código (cidade, esporte, carro, nome). |
| Estado das regras | Estado estruturado obtido pela API comparado ao esperado (`estado_regras_esperado`). |
| Sem resíduos | Em casos sem memória esperada, nenhuma memória foi usada. |
| Tokens | `tokens_por_etapa`: entrada, saída e total de ingestão, pergunta final e sessão. Os campos legados do caso representam a sessão observada. Valores desconhecidos são `null`. |
| Latência | Soma das latências das chamadas à API no caso. |

### Julgamento determinístico P4

`eval/julgamento_respostas.py` é um módulo puro: não chama LLM, API, agente ou memória. O comparativo registra `versao_julgador: p4-v3` e um objeto `julgamento` em cada resultado. A revisão v3 acrescenta padrões factuais e de abstenção para os oito atributos P6, preservando as regressões v2 e os conjuntos rotulados v1. Resultados históricos não foram reescritos. `eval/evaluate.py` e os outros scripts que o utilizam não foram migrados; seus resultados históricos têm outra política e não são diretamente comparáveis à P4.

**Atributos suportados:** `cidade`, `esporte`, `carro`, `nome`, `time`, `profissao`, `pet`, `filhos`, `disciplina`, `hobby`, `viagem`, `quantidade_pets` e `instrumento`. São reconhecidos valores literais e aliases explicitamente anotados, além de frases completas cobertas pela gramática (por exemplo, “Você trabalha como coordenadora”, “Você tem três filhos” e “São dois pets”). Números por extenso e algarismos só são equivalentes quando anotados como aliases; nomes de animais não são convertidos em quantidade pelo julgador. Sem escopo de espécie/sexo nas anotações, frases como “Seu gato se chama Thor”, “Você tem dois gatos” ou “Você tem três filhas” ficam não verificadas nos atributos genéricos correspondentes: acertar um nome/subtotal não comprova a espécie nem o total pedido. Valores isolados anotados continuam reconhecidos. A lista de atributos não implica compreensão geral do domínio.

| Critério | Significado |
|---|---|
| `acerto_factual` | Recupera o valor esperado ou alias anotado, sem negá-lo, especular ou apresentar alternativas. Aceita apenas formas explícitas cobertas. |
| `sem_informacao_proibida` | Não contém termos explicitamente proibidos ou seus aliases anotados. Isso verifica a política anotada, não garante ausência de todo vazamento semântico possível. |
| `abstencao_correta` | Expressa desconhecimento por uma forma coberta, sem palpite ou alegação pessoal adicional. Recusa genérica não comprova desconhecimento. |
| `formato_ok` | Valor isolado sem explicação/pontuação adicional no caso factual; token literal `DESCONHECIDO` no caso de abstenção. Espaços externos são tolerados. |

Cada critério contém `status`, `valor` e `motivo`. Os estados são `aprovado` (true), `reprovado` (false), `nao_aplicavel` (null) e `nao_verificado` (null). Não aplicável significa que a dimensão não é pedida, como acerto factual num caso de abstenção; não verificado significa anotação insuficiente, ausência de resposta ou conteúdo fora da cobertura. Esses estados não são intercambiáveis. Respostas ambíguas ou não verificadas não recebem aprovação automática.

`passou` exige a aprovação do critério primário (factual ou abstenção) e de ausência de informação proibida. `protocolo_ok` também exige formato aprovado. Assim, “Você mora em Campinas.” pode acertar o conteúdo e falhar no formato; “Não sei.” pode ser uma boa abstenção e falhar no token literal. Caixa e acentos são normalizados para conteúdo e aliases, sem alterar o texto original; a abstenção estrita exige `DESCONHECIDO` com essa grafia, sem ponto final. A gramática de valor isolado é limitada a até quatro palavras e não equivale a reconhecimento geral de entidades. Valores compostos anotados são reconhecidos; textos compostos sem essa evidência podem ter formato não verificado.

Confirmações explícitas como “Campinas com certeza” ou “Certamente Campinas” acertam o conteúdo, mas falham no formato de valor isolado. Frases curtas fora da cobertura, como “Campinas encantadora” ou “Cidade desconhecida”, não são automaticamente tratadas como valores incorretos: ficam não verificadas na dimensão de conteúdo. Isso é diferente de um palpite ou alternativa explícita, que continua reprovando o critério de resposta sem especulação. As regressões v2 estão nos testes, sem alterações nos rótulos separados de desenvolvimento e validação.

O dataset recebe apenas o objeto `avaliacao`: tipo de resposta, atributo consultado, aliases aceitos, valores antigos e informações proibidas adicionais. Mensagens, memórias, valores esperados e demais campos originais permanecem intactos. `informacoes_esquecidas` é usado explicitamente, mesmo quando o texto não pode ser reextraído por regras de cidade/time. Uma informação apagada é proibida mesmo em negação ou citação. Já `valores_antigos` representa fatos desatualizados: pode ser correto negar ou contextualizar um valor antigo, e isso não o transforma em dado proibido.

As listas vazias de proibições são explícitas: permitem julgar o conteúdo sem inventar restrições, mas não entram na taxa específica de ausência de informação proibida. Casos sem política completa não são aprovados silenciosamente. Aliases de proibições podem ser anotados em `aliases_proibidos`, por valor canônico; a correspondência considera limites de palavras e espaços normalizados. Repetir “Gol” não é o mesmo que conter a palavra “golfinho”.

No controle `sem_memoria`, somente os critérios efetivos da resposta mudam para abstenção. O dataset e os prompts não são reescritos; o fato originalmente esperado não é aceito como um palpite sem contexto. P1/P2 continuam com os mesmos percursos e histórico, e P3 contabiliza os mesmos tokens sem filtrar por aprovação.

O resumo separa as quatro dimensões, com casos considerados, verificados, aprovados, não aplicáveis e não verificados. As taxas por dimensão usam apenas decisões verificadas; a cobertura deve ser lida junto. A taxa de proibições considera casos com termos proibidos e casos de política desconhecida, expondo os não verificados; listas explicitamente vazias são excluídas. `protocolo_ok` no resumo é uma contagem, com denominador em `casos_tentados`. Falhas de execução não são interpretadas como respostas textuais incorretas: ficam não verificadas nas dimensões aplicáveis, mas não aprovam o caso global.

### Métricas separadas de resposta P5

O JSON identifica `versao_metricas_resposta: p5-v1`. Cada cenário contém `metricas_resposta`, separado dos indicadores globais e das taxas de recuperação de memórias. A P5 reutiliza a P4 sem mudar suas regras: não mistura formato, proibições adicionais ou aprovação global com o acerto factual da resposta.

| Campo em `metricas_resposta` | Tentativas elegíveis | Numerador | Denominador da taxa |
|---|---|---|---|
| `recuperacao_factual` | O critério efetivo do cenário exige resposta factual. | `acerto_factual` aprovado pela P4. | Julgamentos factuais aprovados + reprovados. |
| `abstencao_correta` | O critério efetivo exige abstenção. | `abstencao_correta` aprovada pela P4. | Julgamentos de abstenção aprovados + reprovados. |
| `vazamento_esquecidos` | Há alvos esquecidos explícitos; casos declarados de esquecimento com anotação ausente ou inválida também contam como tentativas, mas ficam não verificados. | Respostas com pelo menos uma ocorrência de alvo esquecido ou alias anotado. | Respostas verificadas quanto aos alvos esquecidos. |

Cada métrica apresenta `tentativas_elegiveis`, `julgamentos_verificados`, `numerador`, `denominador`, `nao_verificados`, `nao_aplicaveis`, `aplicabilidade_desconhecida`, `cobertura_pct` e `taxa_pct`.

- `taxa_pct = 100 * numerador / denominador`, sendo o denominador o número de julgamentos verificados. Na métrica de vazamento, menor é melhor; nas outras duas, maior é melhor.
- `cobertura_pct = 100 * julgamentos_verificados / tentativas_elegiveis`. Taxa e cobertura aparecem juntas no terminal. Um acerto e uma tentativa sem resposta dão taxa `1/1 = 100%`, cobertura `1/2 = 50%` e um não verificado, não dois julgamentos concluídos.
- Sem julgamentos verificados, a taxa é `null`. Sem tentativas elegíveis, a cobertura também é `null`. Cobertura zero com tentativas é conhecida, mas não transforma a taxa desconhecida em zero.
- Falhas sem resposta entram nas tentativas elegíveis e nos não verificados. Não contam como ausência comprovada de vazamento. A porcentagem global antiga continua usando todas as tentativas, com seu significado composto original.
- A dimensão oposta ao critério efetivo é não aplicável. Listas de alvos esquecidos explicitamente vazias também são não aplicáveis. Sem anotação de esquecimento e sem evento declarado, não há alvos para essa taxa. Caso declarado de esquecimento sem alvos identificáveis fica não verificado.
- Resultados antigos sem informações suficientes para determinar o escopo são contados em `aplicabilidade_desconhecida`, fora do denominador de elegíveis. Não se reconstituem alvos a partir das respostas, mensagens ou memórias utilizadas. Nas métricas, elegíveis + não aplicáveis + aplicabilidade desconhecida recompõem o total de tentativas do cenário.

Cada resultado novo contém `vazamento_esquecidos`, com aplicabilidade, status, `vazou`, ocorrências e motivo. A projeção filtra `ocorrencias_proibidas` da P4 por `informacoes_esquecidas` e seus aliases anotados. Proibições adicionais continuam afetando o julgamento P4 e a aprovação global, mas não viram vazamento de esquecidos. Valores antigos não são proibidos automaticamente. Várias ocorrências na mesma resposta contam como uma resposta com vazamento. Uma ocorrência confirmada pode ser preservada mesmo com política incompleta; a ausência exige julgamento suficiente. O escopo é a resposta final, sem medir vazamentos em turnos intermediários.

No desenvolvimento atual, por repetição:

| Cenário | Factuais elegíveis | Abstenções elegíveis | Casos com alvos esquecidos |
|---|---:|---:|---:|
| `sem_memoria` | 0 | 7 | 2 |
| `historico_completo` | 5 | 2 | 2 |
| `memoria_persistente_api` | 5 | 2 | 2 |
| `memoria_regras_api` | 5 | 2 | 2 |

São quantidades de casos, não resultados experimentais. Repetições contam como novas tentativas e não como casos independentes; as taxas usam somas de contagens, não médias de percentuais. Compare cenários em casos, repetições, provedor e modelo equivalentes. No controle sem memória, factual é não aplicável, porque todas as respostas esperadas são abstenções.

Nos casos de esquecimento atuais, os controles `sem_memoria` e `memoria_persistente_api` não recebem os fatos apagados; taxa zero de vazamento nesses controles não comprova esquecimento. O histórico completo conserva os turnos e avalia obediência à instrução; o cenário automático percorre aquisição e esquecimento pela API. A métrica cobre apenas os termos e aliases anotados segundo a P4, não todos os vazamentos semânticos possíveis nem exclusão completa no armazenamento. O dataset final continua sujeito à validação antecipada e à revisão dos metadados; a P5 não os preenche automaticamente.

### Respostas previamente rotuladas

`eval/julgamento/respostas_dev.json` contém 26 respostas de desenvolvimento; `respostas_validacao.json` contém 20 respostas separadas. Cada resposta tem quatro rótulos, aprovação de conteúdo/protocolo e justificativa. Os testes verificam que não há repetição de textos normalizados entre os conjuntos. A separação é de respostas, não de todos os fatos ou casos de conversa usados como referência.

Os rótulos foram preparados como artefatos de engenharia antes da execução dos testes. Exigem revisão humana, especialmente por quem cuida dos dados. A validação foi escrita no mesmo trabalho e não constitui avaliação cega independente nem prova de compreensão geral de português. O julgador não lê esses arquivos para escolher respostas: eles são referências exclusivas dos testes. Não ajuste os rótulos de validação para fazer o código passar; mudanças de política exigem justificativa, versão e nova validação.

Testes simulados, sem LLM real:

```powershell
python -m pytest tests/test_julgamento_respostas.py tests/test_avaliar_comparativo.py -q
```

Para julgar uma resposta isolada, sem rede nem gravação, use a função pura com uma anotação oficial. Exemplo em PowerShell:

```powershell
@'
import json
from pathlib import Path
from eval.julgamento_respostas import julgar_resposta
anotacoes = json.loads(Path("eval/memoria/anotacoes_p6.json").read_text(encoding="utf-8"))
print(json.dumps(julgar_resposta("Osasco", anotacoes["u01/s2/pergunta1"]), indent=2))
'@ | python -B -
```

### Como ler os tokens

Uma sessão experimental corresponde aos turnos de um caso do comparativo. Isso não representa uma medição integrada das vinte sessões do benchmark de recuperação.

| Etapa em `tokens_por_etapa` | Escopo |
|---|---|
| `ingestao` | Chamadas anteriores à última, incluindo prompts, histórico reenviado e respostas intermediárias. É preparação conversacional, não o custo isolado do extrator. |
| `pergunta_final` | Somente a última chamada, com seu contexto e sua resposta. |
| `sessao` | Todas as chamadas de geração observadas no caso. Com contagens completas, equivale à soma das duas etapas anteriores, por canal. |

Cada etapa contém `tokens_entrada`, `tokens_saida`, `tokens_total`, `chamadas_modelo` e `metricas_completas`. Entrada e saída são calculadas independentemente; o total só é conhecido quando ambas estão completas. Metadados ausentes ou inválidos produzem `null`, sem serem substituídos por zero. Em chamadas realizadas, somente contagens inteiras positivas são verificáveis pelo contrato atual; zeros reportados ficam desconhecidos, pois o avaliador não recebe sua origem.

Os campos `tokens_entrada_observados`, `tokens_saida_observados` e `tokens_total_observados` preservam as parcelas positivas disponíveis, mesmo que falte outra chamada ou canal. São subtotais, não custos completos. Zero é conhecido quando uma etapa comprovadamente não realizou chamadas, inclusive ingestão sem turnos anteriores quando a pergunta final falha. `chamadas_com_tokens_zero` sinaliza zeros reportados por chamadas; os campos `chamadas_com_entrada_zero_nao_verificado` e `chamadas_com_saida_zero_nao_verificado` identificam os canais afetados. O adaptador Ollama pode converter metadados ausentes em zero; esses valores não entram como parcelas conhecidas e não sustentam economia. Uma contagem positiva do outro canal permanece utilizável. Essa política conservadora também descarta zeros que poderiam ser legítimos, pois sua origem não é distinguível sem mudar o contrato dos adaptadores.

No resumo por cenário, cada etapa informa casos tentados, medidos, desconhecidos e quantos possuem cada canal conhecido. A soma completa fica `null` se algum caso não tiver a contagem necessária; os subtotais observados continuam disponíveis. A média por caso medido usa apenas os casos com total conhecido e explicita seu denominador. Respostas reprovadas pelo avaliador também entram nos custos quando medidas. Essa média condicional não é a média de todos os casos tentados.

Em erro ou timeout, o consumo pode ter ocorrido sem retornar metadados. Chamadas já recebidas pelo avaliador são preservadas: etapas incompletas mantêm seus subtotais observados, com `chamadas_previstas`, `chamadas_observadas` (respostas recebidas) e `chamadas_modelo: null` quando não se conhece o total efetivo de chamadas. Uma etapa totalmente medida antes de outro erro continua utilizável. A P1/P2 não devolve contagens parciais do filho em falha; parcelas não recebidas são desconhecidas, não zero. Tentativas internas do provedor/SDK também não são rastreadas separadamente. Nenhum consumo é estimado a partir do tamanho da resposta.

### Comparações pareadas

`comparacoes_tokens` compara cada cenário com `historico_completo`, usando pares únicos de `(id, repeticao, provedor, modelo)` na mesma rodada. Registros sem essa identificação não são pareados. Chaves duplicadas são descartadas, sem escolher o resultado mais favorável. Para cada canal e etapa entram apenas os pares com ambas as contagens conhecidas; a lista `casos_repeticoes`, os pares identificados, medidos, sem medição e as duplicatas descartadas ficam no JSON.

- `memoria_regras_api`: comparação de ingestão, pergunta final e sessão observada.
- `memoria_persistente_api`: somente pergunta final, condicionada ao estado correto fornecido.
- `sem_memoria`: somente pergunta final, como controle sem fatos anteriores. Seus critérios de resposta esperam abstenção, portanto menor consumo não comprova melhor recuperação factual.

A redução percentual é `100 * (1 - soma_cenario / soma_historico)` nos mesmos pares. Não é a média de percentuais de casos com pesos diferentes. Sem pares ou com denominador zero, a redução é `null`. Contagens com zeros de origem não verificável são excluídas do pareamento no canal afetado; resultados legados que sinalizam zeros sem distinguir os canais são descartados conservadoramente. Zero de uma etapa comprovadamente sem chamadas continua comparável. Cada canal pode ter um conjunto diferente de pares, explicitado no relatório. Para economia de contexto, examine primeiro a entrada da pergunta final; o total também varia com o tamanho das respostas. Quantidade de tokens e qualidade devem ser lidas juntas, sem filtrar os custos apenas pelas respostas aprovadas.

O resumo do terminal usa todos os casos tentados tanto na fração de acertos quanto na porcentagem, e informa separadamente execuções concluídas e falhas. Um acerto e uma falha operacional são apresentados como `1/2 acertos (50.0%)`, com uma execução concluída e uma falha.

Os campos de provedor/modelo identificam a seleção solicitada. O mesmo runtime, parâmetros e significado das contagens continuam sendo condições externas da comparação. Os números não demonstram economia monetária, e repetições do mesmo caso não são casos independentes. Resultados antigos sem etapas não permitem reconstruir a pergunta final; não são usados nessas comparações.

### Preparação manual e custos não medidos

`preparacao` identifica o estado-ouro fornecido pelo dataset em `memoria_persistente_api`, o número de memórias previstas e `custo_obtencao_estado_ouro: nao_medido`. A inserção é feita pelo script, mas a informação correta foi preparada previamente: esse cenário não mede aquisição automática. Sua ingestão de geração tem zero chamadas; isso não significa preparação gratuita nem custo completo menor.

Regras, hashing/embeddings, gravação, busca, operações HTTP e infraestrutura realizam trabalho fora dos tokens do LLM gerador. Na configuração atual, a API usa hashing local para os vetores. A criação dos processos da P2 também tem custo fora dessa unidade. Esses recursos e a preparação do estado-ouro não recebem valores fictícios em tokens; `custo_total_sistema_medido` é `false`. Não compare o total observado da pré-carregada com a sessão completa do histórico para alegar economia de aquisição e uso.

## P6 — primeira etapa do experimento integrado

`eval/avaliar_sessoes_integradas.py` acrescenta um executor independente; não substitui P1–P5. Ele lê `eval/memoria/sessoes.json` sem modificá-lo: quatro usuários, cinco sessões por usuário, 31 fatos e 21 perguntas. As sessões são intercaladas por número para que os usuários coexistam no mesmo experimento. Sessões sem perguntas também geram evidência e custo. São 20 sessões por cenário, 40 registros de sessão ao comparar memória automática e histórico completo.

Inspecionar o plano, sem API, modelo ou arquivo de saída:

```powershell
python eval/avaliar_sessoes_integradas.py --dataset eval/memoria/sessoes.json
```

### Compatibilidade atual P4/P6 e revisão semântica

O arquivo `eval/memoria/anotacoes_p6.json` foi trazido sem alterações do commit remoto `fc759f31f47ca4fb8dc6b28e5b4f5491cddda986` (blob Git `4ceb37705b0c3ac681a12bd95ca36d06a182303d`). O relatório histórico daquela revisão registrou 10 compatíveis e 11 incompatíveis com P4-v2; esse resultado permanece histórico. Com P4-v3, a inspeção estrutural deve produzir **21 compatíveis, 0 incompatíveis e 0 ausentes**:

```powershell
python -B eval/avaliar_sessoes_integradas.py --anotacoes eval/memoria/anotacoes_p6.json
python -B -m pytest tests/test_julgamento_respostas.py tests/test_sessoes_integradas.py -q
```

O primeiro comando não usa `--executar`: não abre transportes, não chama modelos e não cria resultado. Os testes consomem as anotações oficiais e o dataset de sessões sem alterá-los. As respostas de referência usadas nos testes são artificiais; sua aprovação não mede o chatbot.

**Revisão de Vinicius ainda pendente: `u03/s4/pergunta3`.** A pergunta “Quantos gatos eu tenho?” tem `esperado: ["Luna", "Simba"]` no benchmark de recuperação e `esperado: "dois"`, alias `"2"`, na anotação de resposta. A hipótese é que recuperar os dois nomes fornece a evidência para responder à quantidade. O teste preserva ambos os gabaritos e a diferença de finalidade, sem certificar essa interpretação nem inferir automaticamente a contagem. Vinicius precisa confirmar e registrar a revisão. Portanto, 21/21 significa apenas compatibilidade estrutural; validade semântica integral e aprovação funcional continuam não verificadas.

Para cada novo atributo, os testes verificam fatos corretos/incorretos, aliases, abstenção, incerteza, proibições e valores antigos. Respostas ambíguas não ganham aprovação automática. A revisão dos cinco atributos antigos continua coberta sem alterar os rótulos históricos.

### Condições para liberar a rodada real

O avaliador já planeja 20 sessões por cenário, captura tokens por etapa, compara pares equivalentes, preserva JSONL incremental e recusa arquivo de saída existente. A barreira operacional e a espera com timeout permanecem cobertas por testes simulados. Não executar a rodada apenas porque a compatibilidade chegou a 21/21.

| Dependência | Entrega necessária | Responsabilidade |
|---|---|---|
| Esquecimento `u02/s5/esquecer_chaves` | Mensagem literal, `aprovado: true` e referência da revisão; mesma mensagem nos dois cenários | Vinicius revisa o conteúdo, Paloma valida o contrato |
| Anotações | Revisão semântica dos 21 casos, principalmente a quantidade de gatos e aliases explícitos | Vinicius, com Zeck no julgador |
| Ambiente inicial | Quatro IDs dedicados `p6_`, credenciais externas e evidência aprovada de ativos/substituídos/histórico vazios | Paloma |
| RAM real da API | Observação somente leitura no processo que atende as chamadas, com identificação do worker e cobertura de todos os processos relevantes | Solução compartilhada Paloma/Zeck, ainda não implementada |
| Reinício e exclusão | Snapshots e medições vinculados ao evento, incluindo alvos anteriores, ativos, substituídos e resíduos no histórico | Paloma, com revisão de Zeck |
| Serviços/configuração | API real, modelo disponível e mesmo backend/configuração efetiva no baseline e na API | Paloma/Zeck |

Com as entregas revisadas, usar os argumentos de execução, credenciais, contratos e evidências descritos nas etapas abaixo, sempre com `--saida` novo e `--execucao-id` exclusivo. Não versionar tokens. O executor não prepara o banco, não reinicia infraestrutura e não inventa aprovação ou evidência de RAM. Resultados antigos P3/P4/P5 e o conjunto de teste final devem permanecer preservados.

A orquestração recebe dois transportes independentes. O contrato `Transporte` e as implementações HTTP/histórico ficam em `eval/sessoes_transporte.py`; os clientes falsos existem somente nos testes. O transporte HTTP usa `/conversas` para fatos e perguntas, inicia sessões sem apagar memórias, e usa `DELETE /usuarios/{id}/memorias` para a ação explícita `apagar_usuario`. Não cadastra o estado esperado por `POST /memorias`. IDs de destino precisam ser distintos e dedicados, com prefixo `p6_`, mapeados a tokens provisionados por Paloma. Usuário com estado de regras não vazio na primeira sessão é recusado; isso não substitui a preparação de ambiente limpo, inclusive registros inativos, pela responsável pelo armazenamento.

**A execução HTTP do dataset atual permanece bloqueada sem contrato aprovado de esquecimento.** `esquecer_chaves` é estruturado e não contém mensagem textual. A API não possui exclusão por chave. O executor não inventa uma frase nem substitui silenciosamente a ação por outra operação. Um arquivo externo em `--contratos-acoes` deve fornecer, para `u02/s5/esquecer_chaves`, os campos `mensagem` (texto literal revisado), `aprovado: true` e `referencia` (identificação da revisão). Essa aprovação é declarada externamente, não certificada pelo programa. Vinícius revisa o conteúdo; Paloma valida o contrato. Ambos os cenários precisam receber a mesma mensagem. A estrutura dos contratos e do mapeamento de credenciais é validada antes da primeira requisição ou chamada de modelo; a autenticidade dos tokens depende das respostas da API.

A CLI só executa quando recebe `--executar`, `--saida` e `--credenciais`. O arquivo externo de credenciais contém um objeto por ID original (`u01` a `u04`), com `usuario_id` dedicado e `token`. Não versione esse arquivo nem exponha os tokens no terminal. `--base-url`, `--provedor`, `--modelo` e `--timeout-historico` configuram a execução. Não foi realizada uma execução real nesta etapa; os testes usam clientes falsos, `httpx.MockTransport` e um executor de histórico simulado.

O histórico completo reutiliza P1/P2 com `memorias=[]`: um lote por trajetória/episódio do usuário, sem repetir prefixos a cada pergunta, preservando os turnos de sessões anteriores. `apagar_usuario` encerra o episódio; perguntas posteriores não recebem o histórico apagado. O filho devolve o lote completo antes de seus resultados serem registrados individualmente. A criação/processamento do lote afeta o tempo de orquestração do primeiro evento; não compare esse tempo diretamente com latência HTTP. Em falha do filho, os consumos não devolvidos continuam desconhecidos, sem repetir o lote automaticamente.

O arquivo JSONL é criado exclusivamente, sem sobrescrever evidências. Cabeçalho, tentativa anterior à operação, resultado e resumo de sessão são gravados e descarregados incrementalmente. O cabeçalho inclui commit, hashes do código, dataset/anotações, seleção do modelo, repetição e identificação explícita de simulação. Contratos usados são registrados sem credenciais. Interrupções preservam o log parcial e fecham os transportes; ausência do registro `fim` indica execução incompleta. Falhas não provocam novas tentativas automáticas de operações com efeitos. Uma trajetória com falha fica sinalizada; julgamentos factuais posteriores não são promovidos a resultados válidos de um protocolo completo. Vazamentos observados continuam preservados quando há anotação compatível.

Tokens são separados em `ingestao`, `perguntas` e `sessao`, usando P3. Com várias perguntas na sessão, nenhuma pergunta anterior é reclassificada como ingestão. Operações administrativas não são chamadas de modelo. Falhas preservam parcelas conhecidas e totais desconhecidos como `null`; zeros sem origem verificável não sustentam economia. Comparações pareiam usuário e sessão na mesma execução, modelo, provedor e repetição, explicitando os pares medidos por canal. Latência das chamadas e duração da orquestração são registradas separadamente.

As referências `esperado`/`proibido` do benchmark são de recuperação, não gabaritos automáticos da resposta. Por padrão, todas as respostas ficam não verificadas pelo julgador P4, com aplicabilidade desconhecida nos resumos P5. Um arquivo externo opcional `--anotacoes`, indexado pelo ID de pergunta (por exemplo `u01/s2/pergunta1`), pode fornecer `categoria`, `esperado` e `avaliacao` compatíveis com P4, além de alvos esquecidos explícitos quando pertinentes. Ele é validado antes da execução e nunca é enviado ao modelo. Os domínios ainda não cobertos pela P4 exigem revisão de política antes de uma avaliação oficial. Não se reinterpretam nomes de animais, contagens ou valores antigos para fabricar acertos.

Checkpoints são observações, não provas presumidas:

- Persistência exige reinício confirmado e estados observáveis não vazios e iguais antes/depois. Nova sessão ou leitura de estado não comprova reinício.
- Exclusão exige contagens zero dos alvos ativos, substituídos e presentes no histórico, além de preservação dos não alvos. Estado de regras ou busca vazios não bastam.
- O HTTP padrão registra o estado disponível e mantém o checkpoint como `nao_verificado`. Uma função verificadora externa pode fornecer evidência adicional, coordenada com Paloma. O executor não reinicia Docker nem inspeciona ou altera o banco por conta própria.
- Evidência obtida com cliente falso é `verificado_simulado`; nunca vira comprovação real. Checkpoints de armazenamento são não aplicáveis ao baseline de histórico.

Testes simulados da etapa: `python -m pytest tests/test_sessoes_integradas.py -q`. A rodada real, a revisão das anotações por Vinícius e a validação de persistência/exclusão por Paloma continuam pendentes.

### P6 — Etapa 2: barreira operacional e preparação das evidências

Esta etapa mantém o dataset original, P1–P5 e o julgador P4. Antes de **qualquer resposta nos dois cenários**, o transporte HTTP faz quatro GETs autenticados de `/usuarios/{id}/estado-regras`. Falha de autenticação, erro de transporte, formato inesperado ou estado não vazio bloqueiam globalmente fatos, perguntas e o processo de histórico. Mesmo quatro estados vazios não liberam a execução: é obrigatória evidência externa aprovada de ausência de memórias ativas, substituídas e histórico para cada identidade dedicada. O endpoint existente `GET /provedores` também precisa informar o par solicitado como configurado e permitido; esse catálogo não comprova disponibilidade do modelo no backend. Não há limpeza automática, sondagem por perguntas, endpoint novo nem inspeção do banco pelo executor.

A verificação inicial e suas falhas são registradas no JSONL antes dos eventos. Falha inicial produz `fim` com `estado_orquestracao: incompleta`, zero perguntas observadas, métricas desconhecidas e fechamento dos clientes. A CLI retorna **1** para orquestração incompleta, **2** para argumentos/estrutura inválidos e **0** para orquestração concluída. Código 0 não significa conformidade experimental: consulte cobertura de anotações e checkpoints. Ausência de `fim` continua indicando interrupção.

`--anotacoes` continua opcional para uma rodada operacional. A inspeção sem `--executar` também aceita esse argumento e informa a cobertura das **21** perguntas: compatíveis, ausentes, incompatíveis, motivos e IDs. Uma anotação incompatível não chega ao julgador: a resposta fica não verificada, com aplicabilidade desconhecida, sem converter isso em reprovação ou não aplicável. A anotação compatível usa exatamente P4 e os resumos P5; reprovações observadas continuam reprovações. A execução não inventa políticas para domínios que P4 não cobre. Uma rodada sem cobertura integral não é avaliação completa de respostas. Vinícius ainda precisa revisar as 21 anotações e a mensagem literal aprovada de `u02/s5/esquecer_chaves`.

**Documento externo de evidências.** `--evidencias CAMINHO` liga a CLI ao callback de checkpoints existente por meio de `eval/sessoes_evidencias.py`. `--execucao-id ID` deve ser exclusivo e compartilhado previamente com Paloma; sem ele, o UUID gerado no cabeçalho dificilmente corresponderá ao documento e o início será bloqueado. O formato abaixo é um contrato **local de avaliação**, não uma extensão HTTP nem aprovação de evidências reais. Sua produção e aprovação operacional continuam dependendo de Paloma.

| Campo do documento | Conteúdo exigido |
|---|---|
| `execucao_id`, `ambiente_id`, `api_url` | Execução exclusiva, ambiente identificado e mesma URL base da CLI, sem credenciais. |
| `usuarios` | Mapeamento exato `u01`–`u04` para os quatro IDs `p6_` do arquivo de credenciais; nenhum token. |
| `configuracao_efetiva` | `agente_real: true`, `provedor`, `modelo`, `commit_api`, `backend_id` e `backend_historico_id` iguais. São declarações externas revisadas; a API atual não expõe toda a configuração efetiva. Não incluir segredos. |
| `eventos` | Objeto indexado por ID de preflight ou checkpoint. IDs iniciais: `u01/s1/preflight` até `u04/s1/preflight`. Os checkpoints usam os IDs do plano existente. |

Cada entrada de `eventos` exige `execucao_id`, `ambiente_id`, `usuario_id` original, `usuario_api_id` dedicado, `sessao` inteira, `evento_id`, `tipo`, `chaves` exatas (lista vazia quando não há), `aprovado: true`, `responsavel`, `referencia`, `origem`, `coletado_em` ISO 8601 com fuso e `observacao` como objeto. Preflight tem `tipo: preflight` e sessão 1. Sua observação exige inteiros zero em `alvos_ativos`, `alvos_substituidos`, `alvos_no_historico`; `/estado-regras` vazio não substitui esses dados. A evidência inicial deve ser coletada para aquele ambiente/execução antes de iniciar, com ambiente reservado e sem escritores concorrentes.

O documento é relido a cada checkpoint, permitindo que o verificador externo disponibilize a evidência quando a operação ocorrer. Por padrão não há espera, reinício, retry ou intervenção automática; a Etapa 3 acrescenta espera explícita pelo documento local. Ausência deixa o checkpoint não verificado. Documento malformado, identidade, escopo, aprovação ou configuração incompatíveis geram erro registrado, sem aproveitar parcelas da evidência para aprovar o checkpoint. A data não pode estar no futuro; em checkpoints precisa ser posterior ao início da execução e à última ação de modelo/exclusão daquele usuário. Paloma deve coordenar a coleta e a substituição atômica do documento; evidências ainda indisponíveis no instante do checkpoint ficam não verificadas nessa rodada.

- Persistência reutiliza `reinicio_confirmado`, `estado_antes` e `estado_depois`: exige reinício confirmado e estados não vazios iguais. A confirmação precisa vir da observação real de Paloma; nova sessão não é reinício.
- Exclusão reutiliza `alvos_ativos`, `alvos_substituidos`, `alvos_no_historico` e `nao_alvos_preservados`; exige ainda `alvos_antes` inteiro positivo para impedir que ausência prévia seja apresentada como remoção. `chaves` vincula o escopo à exclusão parcial ou total do evento. Observações completas que contradizem a condição são reprovadas; medições insuficientes ficam não verificadas.
- O hash SHA-256 identifica cada documento lido e acompanha usuário, sessão, evento, ambiente, origem e referência no JSONL. Não autentica seu produtor nem certifica a veracidade da aprovação declarada. Os artefatos originais e a revisão externa precisam ser conservados. O executor não implementa a coleta pelo armazenamento nem o reinício do Docker.

**Proveniência e métricas.** O cabeçalho registra a URL e o mapeamento dos usuários mesmo se a barreira falhar. O registro de preflight acrescenta configuração efetiva declarada, identidade do ambiente e evidências iniciais. Respostas HTTP mantêm o modelo/provedor devolvidos; ausência fica desconhecida, divergência marca erro e invalida a trajetória, preservando tokens recebidos. Hashes do executor, transporte e verificador distinguem código local de evidências de versões anteriores.

Os resumos de resposta incluem todas as 21 oportunidades por cenário, inclusive as não executadas, com elegibilidade e desconhecidos conforme P5. `avaliacao_respostas_completa` exige 21 anotações compatíveis e 21 respostas de trajetória íntegra, sem critérios pendentes, em ambos os cenários; não significa que todas foram aprovadas. Recuperação é separada da resposta: `metricas_recuperacao_lexical` compara somente `memorias_usadas` com os termos já presentes em `esperado` e `proibido`. Mostra presença dos esperados, presença de proibidos e contexto vazio nas perguntas sem esperado, com numerador, denominador verificado, não verificados, não aplicáveis e cobertura. O histórico completo não possui recuperador e recebe não aplicável. Ausência do campo ou falha de trajetória não vira contexto vazio comprovado. Esses indícios lexicais têm as limitações do benchmark: `proibido` mistura valores antigos, isolamento e esquecidos; **não** representa por si só vazamento de dados esquecidos nem prova de exclusão. Vazamento na resposta continua exigindo alvos esquecidos explícitos pelas regras P4/P5.

Tokens mantêm entrada, saída, ingestão, perguntas e sessão da P3. Acrescenta-se cobertura por canal (chamadas medidas/previstas), cobertura de latência e pares de sessões medidos/20. Sem chamadas, o zero é conhecido e a cobertura percentual de chamadas é não aplicável (`null`). Checkpoints separam persistência (20 oportunidades) e exclusão (2), com denominador verificado, cobertura e não verificados; no histórico são não aplicáveis. Evidências falsas continuam identificadas como simulação. Nenhum teste simulado comprova funcionamento real do chatbot, persistência ou exclusão.

Pendências antes da rodada real: Paloma deve prover ambiente dedicado, credenciais, configuração efetiva equivalente e evidências aprovadas de estado inicial/persistência/exclusão; Vinícius deve revisar mensagem de esquecimento e anotações; Ezequiel deve revisar cobertura e coordenar a rodada após autorização. A Etapa 2 prepara e bloqueia essas dependências, sem executar as 20 sessões reais.

### P6 — Etapa 3: sincronização local dos checkpoints (aguardando revisão)

`--aguardar-evidencias` habilita uma pausa explícita em cada checkpoint de persistência e exclusão do cenário `memoria_automatica`. O baseline de histórico continua sem checkpoints de armazenamento. A barreira inicial da Etapa 2 permanece obrigatória e não espera por evidência inicial: sem ela, os dois cenários ficam bloqueados.

Os parâmetros `--timeout-evidencia` (padrão 300 segundos) e `--intervalo-evidencia` (padrão 1 segundo) devem ser positivos e finitos. O prazo é por checkpoint, medido em relógio monotônico, incluindo as leituras. O intervalo é limitado ao tempo restante. Sem `--executar`, a CLI só inspeciona o plano e informa esses parâmetros, sem abrir transportes nem esperar por arquivos.

Durante a pausa, o verificador relê **somente o documento local**. Não repete fatos, perguntas, resets, exclusões, lotes do histórico ou qualquer pedido HTTP. O evento anterior já foi executado uma única vez. Depois da liberação, o transporte consome a observação aceita em cache e faz uma única leitura normal de estado do checkpoint; não relê a evidência para substituí-la por outra versão.

Arquivo/entrada ausentes e medições `null` ou omitidas podem ser aguardados. A exigência da Etapa 2 de `alvos_antes` inteiro positivo em entradas de exclusão permanece: sua ausência torna a entrada incompatível. Documento malformado, entrada presente nula, identidade, escopo, configuração, aprovação ou tipos de medição incompatíveis são rejeitados imediatamente. Permanecem os vínculos da Etapa 2: execução, API, ambiente, usuário original/dedicado, sessão, ID/tipo do evento, lista exata de chaves e data posterior à última ação do usuário. Não se aceitam evidências antigas ou de outro ambiente para liberar a pausa. Paloma deve publicar o documento por substituição atômica; um JSON parcialmente escrito é erro, não ausência.

Uma medição completa libera a espera mesmo quando contradiz o resultado esperado: o checkpoint pode ser `reprovado`. Ausência de confirmação de reinício, por exemplo, nunca vira sucesso. Completude e aprovação experimental são decisões distintas. A espera não executa reinícios nem coleta provas sozinha.

Em timeout ou rejeição durante a espera, a rodada para imediatamente, inclusive antes do próximo evento do baseline. O resultado do checkpoint fica `nao_verificado`; o JSONL conserva todas as operações anteriores, registra `rodada_interrompida` e termina com `fim`, `estado_orquestracao: incompleta` e o motivo. Os dois transportes são fechados; a CLI retorna **1**. Interrupção externa continua preservando o log parcial e fechando transportes; ausência de `fim` sinaliza interrupção. Falhas inesperadas na espera também interrompem a rodada com segurança. Não há retomada/repetição automática.

O JSONL registra os parâmetros no cabeçalho, `aguardando_evidencia` antes da primeira consulta (identidade, escopo, campos necessários, horário e prazo), `evidencia_recebida` com as medições aceitas e seu hash/proveniência, resultado/classificação e eventual interrupção. O indicador `simulado` acompanha a execução e os registros de espera/recebimento; testes com cliente falso nunca comprovam execução real. O hash identifica os bytes lidos, sem autenticar o produtor.

**Espera desativada (padrão):** conserva o comportamento da Etapa 2, com uma leitura de evidência por checkpoint. Ausência ou RAM desconhecida deixam o checkpoint não verificado e a sequência continua; incompatibilidade gera erro e orquestração incompleta, sem repetir a operação. A sincronização exige o argumento explícito.

**Formato local para revisão de Paloma — não aprovado por esta implementação.** Reutiliza integralmente o envelope e os campos da Etapa 2 descritos acima. A semântica de `observacao` é:

| Campo | Medição e limites |
|---|---|
| `alvos_ativos` | Inteiro não negativo: registros ativos no SQLite, daquele usuário e do escopo exato do evento. |
| `alvos_substituidos` | Inteiro não negativo: registros inativos/substituídos no SQLite, com o mesmo usuário/escopo; não apenas os resultados de busca. |
| `alvos_no_historico` | Inteiro não negativo: resíduos dos alvos no histórico de conversa **em RAM no processo real da API**. Desconhecido deve ser `null` ou omitido; o observador SQLite não preenche esse campo. |
| `alvos_antes` | Inteiro positivo: medição dos alvos antes da exclusão, ligada pela referência externa à ação e ao escopo; ausência prévia não prova remoção. |
| `nao_alvos_preservados` | Booleano observado: preservação do que fica fora do escopo da ação. Não presumir `true` pelo estado dos alvos. |
| `reinicio_confirmado`, `estado_antes`, `estado_depois` | Observação externa de reinício e snapshots de persistência; nova sessão não comprova reinício. |

Um observador **apenas SQLite** pode fornecer, por exemplo, `alvos_ativos: 0` e `alvos_substituidos: 0`, deixando `alvos_no_historico: null`. Isso é medição parcial, nunca prova suficiente de exclusão. Não preencher `aprovado: true`, responsável ou referência sem a revisão externa efetiva. As fixtures dos testes são explicitamente fictícias.

No preflight, os três zeros exigidos representam ambiente dedicado limpo para o usuário inteiro: o zero de RAM exige ausência de mensagens de conversa, excluído o SYSTEM_PROMPT. Nos checkpoints de exclusão, `alvos_no_historico: 0` significa ausência **dos alvos**, não necessariamente histórico totalmente vazio. Na exclusão parcial, outras mensagens podem permanecer. O observador não deve contar o SYSTEM_PROMPT como resíduo do usuário, nem inventar aliases, fatos ou termos esquecidos.

**Observação real da RAM — proposta mínima, bloqueada fora deste escopo.** O caminho atual é `src/api/dependencias.py:get_agente` → `AgenteLocal` → `src.agent.historicos_por_usuario`. O histórico é um dicionário em memória por processo; `nova_sessao` o limpa mantendo o SYSTEM_PROMPT. Importar `src.agent` em um script separado observa outro dicionário e não comprova a RAM usada pela API. A API existente não expõe esse histórico.

Paloma e Ezequiel precisam revisar um mecanismo somente leitura **dentro do processo que atende a API**, sem criar/limpar históricos ao observar (não usar `obter_historico` para coletar). A coleta proposta deve identificar instância/processo e instante, usuário e escopo; observar mensagens de conversa, inclusive resíduos em respostas, excluindo o SYSTEM_PROMPT; registrar contagem total de mensagens separada da contagem de resíduos dos alvos, com a política de correspondência previamente revisada. A referência externa deve conservar esses detalhes e os artefatos, ligados ao envelope existente. Havendo vários workers, a coleta deve cobrir todos os processos que podem atender aquele usuário, ou o ambiente dedicado deve garantir um único worker identificado. A coleta deve ocorrer sem escritores concorrentes e produzir um snapshot coerente com o checkpoint.

Esse mecanismo exigiria alteração em `src/`, API ou contrato compartilhado e **não foi implementado**. Nenhum endpoint novo foi presumido. O SQLite preparado por Paloma já cobre ativos/substituídos; RAM continua desconhecida até a coleta real e sua revisão. Isso também pode bloquear a barreira inicial, antes de alcançar a espera.

**Próximas entregas:** Paloma deve revisar este formato local, vincular as medições SQLite aos eventos e coordenar a solução aprovada para observar a RAM no processo da API, além das evidências reais de início/reinício/exclusão. Vinícius deve fornecer a mensagem literal e a referência de aprovação de `u02/s5/esquecer_chaves`, revisar as 21 anotações e os alvos/aliases explícitos que forem necessários. Ezequiel revisa a implementação e as evidências antes de autorizar qualquer rodada real. A Etapa 3 não inventa essas entregas nem executa sessões reais.

Validação simulada: `python -m pytest tests/test_sessoes_integradas.py -q`; suíte completa: `python -m pytest -q`. Os testes usam relógio controlado, arquivo local, HTTP falso e clientes simulados; cobrem chegada posterior, timeout, incompatibilidade, RAM desconhecida, não repetição de operações, JSONL preservado, fechamento e saída da CLI.


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

**Bloqueio verificado em 12/11/2026:** os dez casos TST001–TST010 ainda não possuem o objeto `avaliacao` exigido pelo P4. O comparativo recusa o arquivo antes de carregar token, abrir HTTP, chamar modelo ou criar resultado. O teste `test_dataset_final_oficial_sem_metadados_p4_bloqueia_antes_de_rede` lê o dataset oficial e comprova esse bloqueio sem modificá-lo ou executar respostas reservadas.

Vinicius precisa preparar/revisar os metadados explícitos (tipo de resposta, atributo, aliases, valores antigos e proibições) com Zeck na política de julgamento. Não inferir nem preencher esses campos automaticamente e não ajustar gabaritos olhando respostas do conjunto final. Quando os metadados forem entregues, atualizar o teste de bloqueio para exigir validação positiva dos dados revisados. Esse bloqueio é independente das 21 anotações do benchmark P6.

Comando reservado para depois dessa revisão (API e Ollama abertos, como na avaliação comparativa):

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
- A P4 separa conteúdo e formato, mas cobre somente construções determinísticas e aliases anotados. Paráfrases fora dessa cobertura ficam não verificadas, mesmo quando um humano as consideraria corretas. Resultados anteriores precisam ser identificados pela política antiga.
- Os dados são sintéticos e pequenos; os números são preliminares.
- O `memoria_persistente_api` é pré-carregado com o estado esperado.

## Pendências do protocolo (a fechar antes do congelamento, em 21/11)

1. Separação de tokens implementada na P3; ainda é necessária uma rodada experimental no código congelado. Custos locais, preparação do estado-ouro e consumo perdido em falhas permanecem não medidos.
2. Estado estruturado e recuperação equivalente já estão implementados e testados; falta produzir a evidência experimental atual, mantendo a exata como informação complementar.
3. Rodar a avaliação oficial final com 3 repetições, no commit congelado, e registrar commit, data e hora.
4. Revisar com Vinicius os metadados P4 ausentes dos dez casos de teste, antes da rodada reservada.
