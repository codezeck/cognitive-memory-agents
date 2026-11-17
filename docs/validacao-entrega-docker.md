# Validação real do percurso Docker — 14/11/2026

## Estado consolidado posterior: interface e instalação

**Complemento do iniciador:** a execução direta detectou e corrigiu dois problemas no PowerShell 5: progresso nativo em `stderr` era tratado como erro fatal ao redirecionar logs; a passagem de `-d` para uma função avançada podia consumir o parâmetro como opção do PowerShell. O auxiliar agora recebe um array explícito, converte a saída em texto e verifica o código de saída. `iniciador-real-r03.log` concluiu as três etapas com código zero no projeto próprio, reutilizando os pesos. `iniciador-real.log` e `iniciador-real-r02.log` preservam as tentativas; a segunda foi interrompida ao ficar anexada aos logs. O ensaio posterior `r06-iniciador-padrao.json` confirmou identidade/cookie HttpOnly, API/modelo reais e seis respostas corretas (cinco contas e uma pergunta geral), sem tokens gerados encontrados nos arquivos candidatos à publicação. **Antes dele, r05 respondeu 4 para 2 + 3**: falha real de conteúdo preservada no PNG e em `r05-interrupcao.json`; o JSON HTTP não havia sido gravado antes do assert e não foi reconstruído. Não foi feito ajuste para mascarar essa falha.

O chat em `/` e a preparação Docker automática foram conciliados localmente com `2be5d51`. As PRs #41/#42/#43 já estão integradas. O worktree original foi preservado. [Manual atual](manual-professor.md), [matriz](andamento-entrega.md) e [checklist](checklist-entrega.md). As seções das fases anteriores abaixo são históricas: a pendência de RAM direta foi tratada neste ensaio, sem alterar seus arquivos brutos.

Projeto exclusivo `cma-entrega-ae9eb113`, porta 59059, volumes próprios para dados, pesos e credenciais. Ollama `0.40.12` fixado por digest; modelo `qwen2.5-coder:3b`, digest `f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225`, GGUF Q4_K_M, 3.1B, tamanho informado de 1.929.912.626 bytes. CPU, cerca de 8 GiB disponíveis ao Docker, um worker. Não houve overrides de temperatura/seed/contexto no adaptador; defaults do modelo/runtime não garantem determinismo. Configuração selecionada e hashes em [configuracao-final.json](../evidencias/entrega/20261114-entrega-ae9eb113/configuracao-final.json), sem despejo de ambientes ou credenciais.

A primeira inicialização partiu de volume de pesos vazio e baixou a camada principal de 1.929.903.072 bytes. O primeiro build usou cache. Depois foi feito build com `--no-cache --pull` e download real de dependências Python, imagem final `sha256:2d50c26992afd03e756127ea00ba0453eca74c4884a17ba1c750ed33911cade4`. A base do sistema/Docker já existia: não foi simulado computador formatado nem apagado cache alheio. [Log de build](../evidencias/entrega/20261114-entrega-ae9eb113/build-frio-final.log), logs iniciais e configuração estão no [diretório desta etapa](../evidencias/entrega/20261114-entrega-ae9eb113/).

### Navegador e memória reais

Chromium/Playwright em perfil próprio, sem sessão pessoal, enviou pedidos pelo chat à API real e a Ollama. Computer Use não iniciou por erro de caminho do runtime Node; o fallback registrou PNG e estes foram inspecionados em desktop e mobile. Não houve agente falso. Rodada `r04`: **80 verificações aprovadas, zero falhas**; inclui os novos metadados de origem. A primeira rodada `r01` foi interrompida por espera inadequada de visibilidade de um `<option>`; o teste foi corrigido e todos os registros preservados. `r02` passou 51 verificações antes da extensão de uso. `r03` interrompeu apenas a própria API, comprovando erro de conexão na página e conservação da identidade após retorno.

O fluxo verificou extração, recuperação em nova sessão, atualização para Sorocaba sem reutilizar Niteroi, reinício real com mesmo usuário/dado, DELETE individual preservando versão inativa, DELETE total removendo todas as linhas de A inclusive inativas, B preservado e recusa de pedidos em nome alheio. Perguntas gerais e suporte atual/histórico continuaram no modelo. Modelo ausente e Ollama parado produziram 503 tratado; cookie ausente produziu 401 e retomada local sem copiar token. Capturas, pedidos/respostas, memórias usadas e snapshots SQLite somente leitura estão em [r04-interface.jsonl](../evidencias/entrega/20261114-entrega-ae9eb113/r04-interface.jsonl).

O observador RAM leu o histórico dentro do processo real que atende a API, sem criá-lo ou limpá-lo. Identificou instância, PID, usuário, momento e escopo de um worker. No primeiro ensaio completo, havia 7 mensagens antes do reinício, 6 pessoais e 4 contendo alvos; após reinício, nova instância e histórico ausente. Após DELETE individual: apenas sistema, 0 pessoais/alvos. Após nova pergunta sem suporte: 3 mensagens, 2 pessoais legítimas, 0 alvos. B manteve suas 3 mensagens quando A foi apagado. A contagem é literal normalizada; não prova toda memória da máquina, buffers de terceiros ou equivalência semântica geral. O observador fica desligado no Compose padrão.

### Contagem autorizada e testes

O usuário autorizou a extensão opcional `origem_uso`/`chamadas_modelo_observadas`. Respostas locais mantêm os campos antigos de tokens `null` e declaram política local com zero invocações; o novo protocolo deriva zero somente com esse par explícito coerente. Respostas geradas declaram uma invocação do adaptador, sem contar retries internos. Dados antigos não foram preenchidos nem reprocessados. [Decisão](proposta-contagem-local.md).

Suíte final: **897 aprovados e 66 ignorados**, 8 JavaScript aprovados e lint crítico aprovado. Os 65 testes reais opt-in anteriores foram executados separadamente, não no total local. A primeira tentativa desta suíte registrou 212 erros de preparação por acesso negado ao temporário global do Windows; a repetição usou `--basetemp` exclusivo no repositório e passou, com um aviso de escrita do cache pytest. Logs de ambas as tentativas preservados.

### Resultado experimental e bloqueios atuais

[Comparativo exploratório](ensaio-desenvolvimento-20261114.md): 84 tentativas reais em desenvolvimento, sem falhas de execução, **22 falhas de conteúdo preservadas**. Memória automática: 17/21 aprovações e 17.094 tokens completos; histórico: 12/21 e 16.017. **Aumento de 6,72%, não redução**. Pergunta final isolada economizou 13,35%, insuficiente para a meta e incapaz de substituir o custo completo. Persistem respostas pessoais sem suporte fora da gramática ensaiada e abstenção indevida mesmo com suporte. A falha das formas de cidade foi resolvida no roteiro ensaiado; abstenção geral ainda falha em desenvolvimento. Não declarar sucesso universal ou entrega integral pronta.

P6 e conjunto reservado não foram executados. Os critérios de ≥30%/≤5 p.p./nenhum novo vazamento ou desatualização estão definidos; revisão semântica/contratos, metadados reservados e checkpoint vazio aguardam referência efetiva da revisão informada pelo usuário. [Pacote preparado](revisao-experimental/README.md). O rascunho PDF tem 14 páginas textuais/11 referências, mas dados institucionais, composição do grupo e revisão coletiva permanecem. Vídeo, LICENSE do projeto, CI da tag, publicação e envio continuam pendentes.

Os dois contêineres anteriores conservaram ID/StartedAt; os oito volumes anteriores e os hashes do worktree de origem e das evidências anteriores foram conferidos e preservados em `configuracao-final.json`. Nenhum commit, push, PR, merge, tag ou envio nesta etapa. O encerramento do ambiente próprio será registrado separadamente, sem `-v`.

---

## Registros das fases anteriores

**Estado atual:** a falha de abstenção foi resolvida no escopo das consultas diretas ensaiadas, por política local de suporte, na continuação descrita ao final. A versão final passou em 65 verificações reais; as rodadas anteriores e suas falhas continuam preservadas abaixo e nos artefatos. A entrega integral permanece parcial: este ensaio não é P6 nem comparação de tokens. [Manual curto do professor](manual-professor.md).

## Base, requisitos e interface

- Código testado: `2be5d51` (`master` obtida em 14/11), incluindo #41 (`b5c7234`), #42 (`2c06d6d`) e #43 (reset após DELETE individual). Nenhum desses PRs continua pendente de integração.
- Enunciado original **disponível localmente e efetivamente lido**: `reference/Projetos-IA-Programacao-Enunciados.md`, versão de 09/10/2026, seções de entrega/evidências/documentação e Tema 11. A pasta é ignorada pelo Git; esta conferência não verifica orientações posteriores do professor.
- Interface integrada: FastAPI Swagger UI em `/docs`, HTML 200 e esquema OpenAPI conferidos; `/` respondeu 404. O HTML referencia JavaScript/CSS do CDN `cdn.jsdelivr.net`, sem comprovação visual do carregamento nesta sessão. Não há chat próprio no código integrado; o manual oferece chamadas diretas à API como alternativa ao Swagger.
- Outro worktree local, branch `feature/interface-instalacao`, possui arquivos de interface, iniciador, testes e imagens preparados no índice, sobre `fc759f3`; não possui esses arquivos integrados no commit da branch/master. Foi somente inspecionado, sem alterar seu trabalho nem usar suas capturas como evidência desta rodada.

## Ambiente e preservação

| Item | Identificação observada |
|---|---|
| Execução | `20261114-07701ee5` |
| Projeto Compose | `cma-professor-20261114-07701ee5` |
| Contêiner | `cma-professor-20261114-07701ee5-api` |
| ID | `30d1d52256b3db6763388432715b84adeb29b2b36ccc6e45e84be2b1d1f70db7` |
| Volume exclusivo | `cma-professor-20261114-07701ee5-dados`, montado em `/app/dados` |
| Porta HTTP | `127.0.0.1:54561` |
| Imagem construída | `sha256:6978ccccb20122b6f82418f710c4370784ba1e31dfec5f6cf44cda439096e28d` |
| Docker | Engine 29.9.2, Compose 5.6.1, Docker Desktop/contêiner Linux |
| LLM | Ollama do host, `qwen2.5-coder:3b`; digest e configuração constam no JSONL |
| Autenticação | Dois tokens de teste gerados para `professor_a`/`professor_b`, fora dos artefatos públicos |

`up --build -d` foi executado com o Compose original e o override de professor. As camadas de instalação das dependências e os pesos do modelo estavam em cache; instalação fria/download não foram repetidos. `USAR_FALSOS=0`, seleção exclusiva de Ollama e `OPENAI_API_KEY` vazia foram conferidos no contêiner. A conexão contêiner → `host.docker.internal:11434/api/tags` respondeu e apresentou o modelo.

A API existente `cognitive-memory-api` na porta 8000 não foi reiniciada; seu `StartedAt` permaneceu igual. Os volumes que existiam foram preservados. Todas as escritas de dados foram direcionadas ao volume novo. O `.env` original não foi alterado; o teste usou arquivo próprio ignorado pelo Git, sem publicar tokens. A permissão inicial negada pelo sandbox não representava indisponibilidade do Docker: o daemon foi acessado com autorização de execução apropriada, sem mudar configurações de segurança.

Ao encerrar a validação, foi executado `down` **somente no projeto dedicado, sem `-v`**. O contêiner/rede de teste foram removidos; o volume `cma-professor-20261114-07701ee5-dados` ficou preservado. A API original continuava em execução com o mesmo `StartedAt`, e os dois volumes anteriores continuavam presentes. [Registro real do encerramento](../evidencias/agente/validacao-docker-20261114-07701ee5-encerramento.json). A porta 54561 identificada acima já não atende após esse encerramento; o manual cria uma nova instância.

## Evidências novas, sem sobrescrever as antigas

- [JSONL original da rodada](../evidencias/agente/validacao-docker-20261114-07701ee5.jsonl): tentativas e respostas HTTP, verificações, snapshots SQLite somente leitura e identificação/reinício do contêiner.
- [Log da API](../evidencias/agente/validacao-docker-20261114-07701ee5-api.log): saída real do contêiner com timestamps.
- [Registro do encerramento](../evidencias/agente/validacao-docker-20261114-07701ee5-encerramento.json): remoção somente do contêiner/rede dedicados, volumes preservados e serviço original sem reinício.
- Não foram executados P6, conjuntos reservados ou comparativos para ajustar prompts/regras/gabaritos. As mensagens foram sintéticas e previamente definidas para esta sondagem.
- A inspeção visual automatizada do navegador não pôde iniciar: o runtime Node da ferramenta retornou caminho não encontrado. HTTP/OpenAPI foram verificados; renderização completa/uso interativo no navegador e capturas desta rodada ficam não verificados.

## Resultado do fluxo real — etapa inicial, antes da correção

| Procedimento | Observação real | Alcance da conclusão |
|---|---|---|
| A diz “Moro em Niteroi.” | Resposta “Você mora em Niterói.”; memória `Mora em Niteroi.`; linha ativa com chave `cidade` | Extração automática comprovada, sem pré-carga por POST de memória |
| Nova sessão A e pergunta | Resposta “Niterói”, contexto contendo o fato | Recuperação em nova sessão validada neste caso |
| B diz “Moro em Maceio.” e pergunta | Resposta “Maceio”, contexto próprio sem Niterói | Isolamento funcional entre os dois usuários |
| GET, DELETE e conversa direcionados a B com token A | Três respostas 403; banco antes/depois idêntico | Recusa de acesso e ausência de modificação nesses pedidos |
| Sem token em recurso protegido | 401 | Autenticação exigida |
| A atualiza para Vitória | SQLite: Vitória ativa e Niterói inativa; busca não retorna o texto antigo; resposta posterior “Vitoria” | Atualização e recuperação ativa validadas. A confirmação livre da mensagem de atualização foi uma pergunta, não uma boa confirmação do fato |
| Reinício real do contêiner | Mesmo ID, `StartedAt` alterado; snapshots completos iguais; resposta “Vitoria” | Persistência validada, distinta de nova sessão |
| DELETE do ID ativo de A | 204; ID ausente no SQLite; uma linha substituída de A ainda existe | Contrato por ID exercitado; não equivale a esquecimento de toda a chave |
| Pergunta após DELETE individual | `memorias_usadas=[]`, resposta “A cidade registrada é Belo Horizonte.” | **Falha de abstenção/factualidade**, não cidade recuperada da busca |
| DELETE de todas as memórias de A | Removeu a linha substituída restante; SQLite sem linhas de A, inclusive inativas; B preservado | Exclusão total no armazenamento comprovada nesta rodada |
| Pergunta após exclusão total | `memorias_usadas=[]`, resposta “Você mora em São Paulo.” | **Falha de abstenção/factualidade** permanece |
| B pergunta depois das exclusões | Resposta “Maceio” | Usuário não alvo preservado |

O JSONL termina com 49 verificações auxiliares positivas e duas negativas. São verificações sobre HTTP, banco, configuração e respostas desta única sondagem; não são 51 casos independentes, não são a suíte pytest e não medem a taxa de acerto do projeto.

Nenhuma das cidades inventadas foi o fato apagado. Isso não comprova vazamento de Niterói/Vitória nem ausência de todo vazamento possível. O histórico do processo real não foi observado diretamente; ler SQLite, executar outro Python ou observar uma abstenção não fornece esse snapshot. A #43 e seus testes comprovam o mecanismo de reset no código, e esta rodada observa o comportamento público, sem substituir a evidência RAM exigida pela P6.

## Matriz de requisitos e lacunas — etapa inicial

| Requisito e fonte no enunciado | Funcionalidade/procedimento | Evidência | Situação/pendência |
|---|---|---|---|
| Execução reproduzível por Docker — itens de envio | Construir/subir API com modelo local, tokens e rede preparados | Build executado, imagem/volume/porta conferidos; JSONL | Validado com cache em Windows/Docker Desktop; instalação fria e outros SOs não verificados |
| Software funcional com IA a custo zero | Conversas reais pelo adaptador Ollama | Respostas e contagens de tokens no JSONL; OpenAI vazia | Validado neste percurso, sem agente falso ou chamadas pagas |
| Serviço salvar/buscar/atualizar/esquecer — Tema 11 | Fato via conversa, nova sessão, atualização, reinício e exclusão total | HTTP e snapshots SQLite | Fluxo de armazenamento validado; resposta pós-exclusão falhou |
| Continuidade em 20 sessões — MVP Tema 11 | Executar dataset de 4 usuários × 5 sessões contra baseline | Planejador e [plano P6](plano-execucao-p6.md) | **Pendente**: esta sondagem não cobre 20 sessões |
| Resolver fatos que mudam — desafio Tema 11 | Substituição de Niterói por Vitória e pergunta posterior | Linha antiga inativa, nova ativa e resposta Vitória | Validado neste exemplo; não taxa experimental geral |
| Esquecimento — desafio Tema 11 | Exclusão de ID e exclusão total; observar resposta e RAM | Banco inclui inativos; respostas inventadas registradas | Banco total validado; abstenção reprovada e RAM direta não verificada |
| Teste automatizado que apaga todas as memórias — critério Tema 11 | Testes de API/contrato em temporários | `tests/test_api.py`, `tests/test_contrato_memoria.py`; suíte atual com 827 aprovados, 1 ignorado | Testes passaram; não equivalem a prova real de RAM |
| Lembranças corretas e desatualizadas — critério Tema 11 | Medir respostas/recuperação com denominadores e cobertura | Artefatos históricos e implementação P4/P5 | Rodada final pendente; não preencher com esta amostra |
| Tokens por sessão versus histórico completo — critério Tema 11 | Comparação pareada e custos por etapa P3/P6 | Tokens desta sondagem são reportados, sem baseline; protocolo existente | Comparação experimental pendente |
| Dados separados, baseline e métricas — rubrica experimental | Revisar metadados e congelar protocolo | Dataset final reservado, julgador e testes | Dez casos finais ainda dependem de metadados; não foram usados para ajuste |
| Manual técnico/API/interface | Abrir Swagger, autenticar e reproduzir exemplos | `/docs` HTTP 200, OpenAPI e [manual](manual-professor.md) | Manual produzido; QA visual e capturas desta rodada pendentes; chat próprio não integrado |
| Evidências verificáveis e análise de falhas | Logs reais, versão, entradas/saídas e limitações | Novos JSONL/log; histórico preservado | Produzido; não substitui vídeo final de 3–5 minutos, CI/tag `v1.0` ou pesquisa PDF |

## Correções da etapa inicial e decisões então pendentes

Verificação independente: `python -B -m pytest tests -q -ra --tb=short -p no:cacheprovider --basetemp <temporario-novo>` passou com **827 aprovados, 1 ignorado em 18,00 s**. Plugins automáticos/cache/bytecode desativados; módulo semântico opt-in não executado para não baixar modelo. A inspeção `python -B eval/avaliar_sessoes_integradas.py --anotacoes eval/memoria/anotacoes_p6.json`, **sem `--executar`**, retornou 4 usuários, 20 sessões, 21 perguntas e 21 anotações compatíveis/0 incompatíveis/0 ausentes. Não houve geração P6; a ação `u02/s5/esquecer_chaves` continua exigindo contrato.

1. Acrescentado override **opt-in** para professor: nome, porta e volume exclusivos; somente Ollama e agente real. Corrige a lacuna operacional de tentar isolar apenas por `-p`, mantendo o nome/porta fixos do Compose original. O padrão do projeto não foi modificado.
2. Manual e documentação atualizados para refletir as integrações #41/#42/#43, a interface realmente disponível e as limitações de comprovação.
3. README corrigido quanto à reconstrução do índice do gerenciador e ao alcance do DELETE individual. Não alterado o contrato de armazenamento ou de endpoints.

Arquivos documentais alinhados: `README.md`, `docs/agente-provedores.md`, `docs/decisoes-arquitetura.md`, `docs/guia-avaliacao.md`, `docs/contribuicao-academica-zeck.md`, `docs/resultados-avaliacoes-agente.md`, `docs/roteiro-demonstracao.md`, `docs/plano-execucao-p6.md`, `evidencias/README.md` e `PROMPTS.md`. Novos: o manual, este relatório, o override e as três evidências vinculadas acima. Links locais/âncoras, colunas das tabelas e sintaxe dos blocos PowerShell foram conferidos; a configuração resolvida do manual foi validada sem exibir tokens. `git diff --check` passou. Credenciais sintéticas não aparecem nos arquivos candidatos; arquivos de credenciais e scripts temporários da sondagem foram removidos ao final.

Na etapa inicial não houve alteração em `src/`, `tests/`, `eval/`, datasets, resultados históricos, `Dockerfile`, Compose padrão ou dependências. A continuação abaixo modifica somente o agente e seus testes. Trabalho local na branch `fix/validacao-entrega-docker`, sem commit, push, PR ou merge.

**Decisão registrada na etapa inicial, tratada na continuação:** era necessário definir se e como perguntas sobre fatos pessoais sem evidência seriam impedidas de gerar afirmações — identificação da pergunta, evidência no histórico/memória e política de abstenção. Um bloqueio genérico de toda pergunta sem memória também impediria perguntas gerais ou respostas com evidência no histórico. Naquela etapa não foi introduzida guarda, fallback, troca de modelo ou ajuste seletivo de prompt.

Continuam necessários: contrato de `u02/s5/esquecer_chaves`, revisão semântica dos gatos/aliases, metadados do conjunto final, observação da RAM real, evidências de reinício/exclusão P6 e decisão sobre persistência de estado vazio em u04/s4. A aprovação de 21/21 anotações é estrutural; os novos resultados reais acima não foram promovidos a resultados P6.

## Continuação — correção da abstenção, 14/11/2026

### Causa e decisão implementada

O caminho foi conferido de ponta a ponta: `GerenciadorMemoria.processar` aplica extração/conflitos; `MemoriaSQLite.buscar` seleciona somente ativos do usuário; `Conversador` recupera contexto e aciona o reset nos caminhos de esquecimento; `AgenteLocal` seleciona o adaptador; `agent.responder` monta sistema, memórias, histórico recente e mensagem atual. Os DELETEs integrados já acionavam reset. Portanto, a falha original não foi atribuída à exclusão do SQLite nem à ausência de um reset no código.

No contexto realmente encaminhado ao Ollama após excluir, não havia o fato pessoal. O agente ainda delegava a resposta irrestrita ao gerador: quando a busca estava vazia, omitia o bloco externo e dependia da instrução geral “não invente”. O [traço da base](../evidencias/agente/20261114-abstencao-c4468914-base-modelo.jsonl) registra pedidos e respostas reais; a reprodução mostrou tanto abstenções quanto cidades inventadas. Isso observa o contexto entregue ao SDK, não todos os objetos da RAM.

Uma primeira tentativa com instruções mais explícitas e um bloco final de fontes foi rejeitada: ainda produziu “Descobri que você mora em São Paulo.” após exclusão e também recusou fatos disponíveis. Esse candidato não integra o código final.

A correção final acrescenta `src/evidencias_pessoais.py` e uma integração curta em `src/agent.py`. Para consultas pessoais diretas reconhecidas, procura suporte literal na mensagem atual, no histórico **do usuário** efetivamente incluído na chamada e nas memórias recuperadas. Perguntas e respostas anteriores do assistente não comprovam o fato. Uma memória sobre turismo não comprova residência. Sem suporte, devolve `DESCONHECIDO` localmente, sem consultar o modelo. Com suporte, preserva o percurso de geração original; não há cidade/resposta-ouro embutida no produto. Perguntas gerais seguem o percurso original. Em perguntas mistas, remove somente a consulta pessoal sem suporte do pedido ao LLM e prefixa a abstenção à resposta geral, mantendo a mensagem original no histórico.

Não foram alterados endpoints, schema de respostas, catálogo, adaptadores, banco, regras de aquisição/conflito ou datasets. Nenhum provedor alternativo/falso foi usado. O enunciado original do Tema 11 não exige que uma abstenção seja gerada pelo LLM; a política é compatível com o objetivo de responder com apoio nos fatos. Não foi identificada divergência nesse ponto. Isso não certifica os demais requisitos acadêmicos.

### Protocolo e ambiente real

Exemplos sintéticos de desenvolvimento definidos em [teste real opt-in](../tests/test_abstencao_docker_real.py), sem P6 ou conjunto reservado: 13 situações × 5 repetições, limpando exclusivamente os dois usuários sintéticos antes de cada tentativa. Não houve seleção de uma resposta melhor, retry automático de caso ou ajuste de gabaritos oficiais.

Cada rodada usou outro contêiner, volume e porta. A final usou `cma-professor-20261114-abstencao-c4468914-correcao-final-api`, volume de mesmo prefixo terminado em `-dados`, porta `62197`, imagem `sha256:ba024966dda615d84dfc153c1e9c6b47367283f26a889e94d875a287a2fee24b`. Ollama **0.40.12**, modelo `qwen2.5-coder:3b`, digest `f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225`. Configuração exclusiva de Ollama, `USAR_FALSOS=0`, OpenAI vazia; instalação/dependências/modelo em cache. Nenhum seed/temperature foi forçado: `options=None`; o servidor não informou parâmetros adicionais de Modelfile, portanto não foi presumido um valor de temperatura.

O [observador utilizado](../evidencias/agente/20261114-abstencao-c4468914-observador.py) registra e encaminha integralmente os pedidos/respostas do SDK real, sem fallback nem substituição, em um worker. O comando instrumentado usa o mesmo aplicativo uvicorn; não é agente simulado. A [configuração final](../evidencias/agente/20261114-abstencao-c4468914-configuracao-final.json) registra imagem, hashes de código/teste/observador, rede, volume, modelo e ambiente sem credenciais.

| Rodada | Resultado estrito dos 65 casos | Chamadas reais ao modelo | Observação |
|---|---:|---:|---|
| Base, reprodução r02 | 37 aprovados / 28 reprovados | 145 | Cidades inventadas, palavras deformadas e falhas de formato; todas preservadas |
| Candidato só com instruções | 45 / 20 | 125 | Rejeitado: alucinação permanece e há abstenção indevida com fato disponível; alguns casos param na pré-condição |
| Guarda local v2 | 63 / 2 | 115 | Duas falhas de formato em `historico_usuario`: “Minha palavra de exemplo é BRISA.” em vez de somente “BRISA”; conteúdo correto |
| Versão final, incluindo compatibilidade de formas canônicas | **65 / 0** | **115** | As 13 situações passaram nas cinco repetições |

A diferença de 63/65 para 65/65 não isola um efeito causal da revisão de compatibilidade: aquelas duas falhas eram de formato, com o mesmo conteúdo correto, e a geração continua variando. Não se conclui que a correção eliminou toda falha de formato.

Houve também uma tentativa inicial de instrumentação que não chegou à API/modelo: importação de `src` falhou no observador, e o pytest registrou 65 falhas de conexão. O caminho de importação foi corrigido, sem atribuir essas falhas ao agente ou escondê-las: [log da preparação falha](../evidencias/agente/20261114-abstencao-c4468914-base-pytest.log). A suíte local intermediária também detectou cinco expectativas antigas sobre a quantidade de mensagens do candidato de prompt; elas não eram falhas reais do modelo. O candidato foi removido, e essas expectativas originais ficaram preservadas no código final.

### Resultado por situação na versão final

| Situação | Resultado observado nas 5 repetições |
|---|---|
| Fato disponível, recuperado em nova sessão | Niterói, com o fato em `memorias_usadas` |
| Atualização, conservando o histórico antigo | Vitória; contexto recuperado sem Niterói |
| Fato nunca informado, após iniciar sessão | `DESCONHECIDO` local |
| Após DELETE individual | `DESCONHECIDO` local |
| Após DELETE total | `DESCONHECIDO` local |
| Após DELETE total e nova sessão | `DESCONHECIDO` local |
| Isolamento | B desconhece cidade de A; depois responde Maceió e A mantém Niterói |
| Pergunta geral sem memórias | Paris |
| Apoio só na mensagem atual | NEVOA, sem memória recuperada |
| Apoio só na mensagem anterior do usuário | BRISA, sem memória recuperada |
| Memória de turismo, sem apoio para residência | `DESCONHECIDO` local, mesmo com `memorias_usadas` não vazias |
| Conselho sobre estudos | Resposta normal; o teste verifica não vazio/ausência de abstenção, sem avaliar rigorosamente estilo ou concisão |
| Pergunta mista | Abstenção local para cidade e resposta do LLM contendo 5 para `2 + 3` |

As **30 abstenções completas foram locais e não chamaram Ollama**; os demais pedidos produziram 115 chamadas efetivas registradas. `tokens_entrada`/`tokens_saida` ficam `null` no caminho local. Os consumos das chamadas realizadas continuam sendo os reportados pelo provedor. Não converter os `null` em zeros experimentais nem calcular economia contra as rodadas de desenvolvimento.

Os quatro projetos desta continuação foram encerrados com `down` sem `-v`, após capturar os artefatos. Seus volumes e todos os volumes anteriores ficaram preservados; a API original continuava em execução com o mesmo `StartedAt`. As portas de ensaio já não atendem. [Registro real do encerramento e snapshots SQLite somente leitura](../evidencias/agente/20261114-abstencao-c4468914-encerramento.json). A instância do professor deve ser nova, conforme o manual.

Evidências: [pedidos/respostas HTTP finais](../evidencias/agente/20261114-abstencao-c4468914-correcao-final-http.jsonl), [pedidos/respostas reais do modelo](../evidencias/agente/20261114-abstencao-c4468914-correcao-final-modelo.jsonl), [log da API](../evidencias/agente/20261114-abstencao-c4468914-correcao-final-api.log), [pytest real](../evidencias/agente/20261114-abstencao-c4468914-correcao-final-pytest.log) e [resumo de todas as rodadas, incluindo cada falha](../evidencias/agente/20261114-abstencao-c4468914-resumo.json). São sondagens de desenvolvimento, não 65 casos acadêmicos independentes nem taxas gerais de acerto.

### Testes e reprodução opcional de desenvolvimento

A base foi reexecutada antes de modificar código: **827 aprovados, 1 ignorado em 18,97 s**. Na versão final: **855 aprovados, 66 ignorados em 26,26 s** ([log](../evidencias/agente/20261114-abstencao-c4468914-final-testes-locais.log)). Dos ignorados, 1 é o módulo semântico opt-in e 65 são os casos reais, executados separadamente com **65 aprovados em 140,53 s**. Os 28 testes locais novos incluem modelo adversarial, suporte na mensagem/histórico/memória, isolamento, reset, negação, formas canônicas e pergunta mista. `pip check` não encontrou dependências quebradas.

Código final alterado nesta continuação: [agente](../src/agent.py), [política de suporte](../src/evidencias_pessoais.py), [regressão do reset](../tests/test_agent.py), [28 regressões locais](../tests/test_evidencias_pessoais.py) e [65 verificações reais opt-in](../tests/test_abstencao_docker_real.py). Os testes do comparativo e do processo de histórico permaneceram com o conteúdo original após a rejeição do candidato de instruções. Links/âncoras/tabelas, sintaxe Python/PowerShell e `git diff --check` conferidos. A configuração registrada corresponde aos hashes do código final e do protocolo. O trabalho local anterior e as evidências originais foram preservados, sem publicação.

Para repetir a bateria real em **nova instância dedicada** preparada pelo manual, é preciso Python/dependências no host (opcional para desenvolvimento, não para usar o produto pelo Docker). As operações abaixo apagam exclusivamente `professor_a` e `professor_b` dessa instância; nunca apontar para um ambiente compartilhado:

```powershell
$env:ABSTENCAO_AMBIENTE_ISOLADO = "1"
$env:ABSTENCAO_URL = "http://127.0.0.1:$env:CMA_PORTA"
$env:ABSTENCAO_TOKEN_A = $env:CMA_TOKEN_A
$env:ABSTENCAO_TOKEN_B = $env:CMA_TOKEN_B
$env:ABSTENCAO_ARTEFATO = "evidencias/agente/abstencao-" + [guid]::NewGuid().ToString("N") + ".jsonl"
python -B -m pytest tests/test_abstencao_docker_real.py -q --tb=short -p no:cacheprovider
```

### Limites e próximas pendências, sem iniciar outra frente

1. Revisar a política local e sua gramática com a equipe. Ela reconhece consultas diretas como “Onde eu moro?”, “Em que cidade moro?” e “Qual é meu/minha …?”, com suporte literal conservador. **Não cobre toda formulação de pergunta pessoal**; fora da gramática continua dependendo do LLM. Paráfrases de suporte não reconhecidas podem causar abstenção indevida. O resultado é restrito ao percurso ensaiado, não uma garantia universal de factualidade.
2. Acompanhar formato/qualidade da geração: houve variação em rodadas anteriores mesmo com conteúdo correto. Cinco repetições não demonstram ausência de falhas futuras. A rodada final não valida exaustivamente conselhos nem estilo.
3. Planejar a observação direta do histórico no processo real. Busca vazia, abstenção local e traço encaminhado ao SDK não comprovam limpeza de toda a RAM; o novo guarda não substitui esse checkpoint nem inspeção de armazenamento.
4. Concluir, em etapa própria, os contratos/gabaritos e evidências exigidos para a P6. Não foi executada nesta continuação, e o conjunto reservado não foi utilizado para ajustar regras, prompts ou gabaritos.
5. Antes do comparativo, definir a perda máxima pequena tolerada e o critério de equivalência/superioridade de acerto. A meta de reduzir substancialmente tokens/contexto mantendo qualidade **não foi comprovada** nesta etapa. Revisão e futuras avaliações devem incluir a política local em todos os cenários pertinentes.
