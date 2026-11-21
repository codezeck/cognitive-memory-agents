# Reproduzir a avaliação v3 com Docker

Este é o caminho atual para executar os experimentos sem instalar Python/Ollama no host. Para testar somente o chat, use o [manual](manual-professor.md). Contratos e fórmulas detalhados: [guia de referência](guia-avaliacao.md). [Resultados originais](acertos-tokens-contexto-v3.md).

## Caminho principal: pelo navegador

Com a demonstração local iniciada, abra **Comparativo de tokens**. A interface executa os dois protocolos abaixo, mostra perguntas/objetivos antes e progresso, gráficos, respostas e julgamentos depois. Não precisa importar JSON para executar. Veja o [manual passo a passo](manual-professor.md#avaliar-pela-interface-sem-terminal).

O comparativo oferece uma ou três repetições dos mesmos 16 casos (64 ou 192 tentativas). A P6 mantém 20 sessões por cenário, 40 no total e 42 respostas; não tem modo abreviado. No comparativo é possível baixar o modelo/arquivo oficial e importar 1–20 casos próprios validados, sempre identificados separadamente dos oficiais. P6 personalizada não é aceita pela interface.

Os executores são os mesmos dos comandos técnicos abaixo: `src.interface.comparativo` com o dataset v3 e `tools.reproduzir_p6`. A imagem inclui `tools/` e o protocolo congelado. Rodadas da interface ficam no volume em `avaliacoes-interface/`, com hashes da árvore, origem, conjunto e resultados novos. Sem Git dentro da imagem, o commit é declarado como não informado e os hashes identificam as fontes; nenhum SHA é fabricado. Não se reaproveitam resultados históricos.

O caminho de terminal continua disponível para reprodução técnica e inspeção dos artefatos. Use o mesmo projeto Compose do iniciador; se usa `cma-validacao`, ajuste a variável abaixo para esse nome. Não apague volumes.

## Preparar

Use a candidata baixada conforme o README, Docker Desktop aberto e PowerShell na raiz. O override [docker-compose.avaliacao.yml](../docker-compose.avaliacao.yml) inicia um contêiner de avaliação sem portas públicas. Somente `src/`, `eval/`, `tools/` e os protocolos de revisão são montados para leitura; resultados novos ficam em `.env.reproducoes/`, ignorada pelo Git. API, SQLite e tokens de cada rodada são temporários. O banco e as credenciais do chat não são montados nesse serviço.

O serviço compartilha o Ollama do projeto Compose. Rodar experimentos pode aumentar a latência do chat: execute uma bateria por vez. Não remover caches ou volumes anteriores. Camadas e pesos em cache devem ser declarados; resultados exatos podem variar com o modelo estocástico.

```powershell
$projetoCma = 'cma-demonstracao'
$rodadaCma = Get-Date -Format 'yyyyMMdd-HHmmss'
$commitCma = git rev-parse HEAD
New-Item -ItemType Directory -Force .env.reproducoes | Out-Null
docker compose --env-file .env.example -p $projetoCma -f docker-compose.yml -f docker-compose.avaliacao.yml build avaliacao
docker compose --env-file .env.example -p $projetoCma -f docker-compose.yml -f docker-compose.avaliacao.yml run --rm avaliacao -c "import httpx,os; print([(m['name'],m['digest']) for m in httpx.get(os.environ['OLLAMA_HOST']+'/api/tags',timeout=10).json()['models']])"
```

O último comando prepara as dependências e lista nome/digest dos modelos realmente instalados, sem imprimir credenciais. Aguarde preparo concluído. Se escolheu outro projeto no manual, ajuste `$projetoCma` para ele. Ao baixar ZIP sem Git, use como `$commitCma` o SHA publicado junto ao pacote; não invente um identificador.

Após o preparo acima, os comandos seguintes usam `--no-deps` para reutilizar o backend pronto sem repetir o download/preparo. Se o projeto foi parado, repita o preparo antes de avaliar.

## Comparativo: 16 casos, três repetições e quatro cenários

```powershell
docker compose --env-file .env.example -p $projetoCma -f docker-compose.yml -f docker-compose.avaliacao.yml run --rm --no-deps avaliacao -m src.interface.comparativo --dataset eval/dataset_validacao_v3_20261118.json --saida "/saida/validacao-$rodadaCma.json" --repeticoes 3 --controle-sem-memoria modelo_direto --timeout-modelo 180
```

Resultado: `.env.reproducoes/validacao-<rodada>.json`, com respostas, julgamentos, falhas e comparações pareadas de tokens. O arquivo precisa ser novo. São 192 tentativas previstas; repetição não cria usuários independentes. `--repeticoes 1` serve para conferência rápida, mas não reproduz a bateria original de três repetições.

## P6: 20 sessões por cenário

```powershell
docker compose --env-file .env.example -p $projetoCma -f docker-compose.yml -f docker-compose.avaliacao.yml run --rm --no-deps avaliacao -m tools.reproduzir_p6 --saida-dir "/saida/p6-$rodadaCma" --commit-base $commitCma
```

Resultado: `.env.reproducoes/p6-<rodada>/`, contendo `eventos.jsonl`, `resumo.json`, `configuracao.json`, `api.log`, evidências operacionais e snapshots dos checkpoints. O diretório precisa ser novo. O preparo confere os hashes antes de iniciar e aceita somente a diferença de finais de linha LF/CRLF entre sistemas. Mudanças de fatos, aliases, gabaritos ou de outra formatação são recusadas. Um protocolo novo com hashes dos bytes do checkout fica ao lado da pasta da rodada (`p6-<rodada>.protocolo.json`), preservando a referência e os hashes históricos; não modifica os dados nem o protocolo original. A rodada preserva os dois cenários, cria seu próprio banco e reinicia sua própria API.

Inspecionar os resultados novos:

```powershell
Get-Content ".env.reproducoes/p6-$rodadaCma/resumo.json" -Raw
```

Não executar `tools.resumir_contexto_v3` sobre uma rodada nova: esse script consolida as evidências históricas da pasta datada. Não sobrescrever os originais para fazer números coincidir. Copiar uma nova rodada para `evidencias/` somente após verificar segredos, origem, interpretação e revisão.

## Interpretar e encerrar

P6 tem quatro usuários × cinco sessões, 21 perguntas por cenário e dois cenários. Persistência não vazia, consistência do vazio e exclusão são métricas distintas. Tokens incluem ingestão e perguntas; usar pares equivalentes com medição completa. Ausência de tokens não é zero. P4 pode deixar respostas não verificadas; `avaliacao_respostas_completa=false` não implica que a execução não ocorreu. Revisão humana complementar deve permanecer separada.

Os contêineres de avaliação são removidos ao terminar por `--rm`. Ollama e volumes permanecem; para encerrar o projeto, use o comando de parada do manual. Não acrescentar `-v`.


### Controle sem memória nas novas avaliações da interface

A interface usa o método `comparativo-v3-ollama-direto-v1`. Em cada tentativa
de **Sem memória**, envia somente a pergunta final ao Ollama (`/api/chat`),
sem histórico, memórias, agente ou regra local de abstenção, em um POST sem
repetição automática. O modelo e a pergunta são os mesmos do conjunto; os
parâmetros de geração usam os padrões do modelo no Ollama. O gabarito original
P4 avalia a resposta: qualquer cenário pode acertar. “Não sei”/“DESCONHECIDO”
não fornece um fato solicitado, mas continua correto quando o caso exige
abstenção. Isso não demonstra a recuperação interna da memória do modelo.

Os acertos dos quatro cenários aparecem primeiro; depois vêm os tokens de
geração por sessão, chamadas ao modelo e cobertura da medição. Cobertura de
tokens não é acerto de resposta. Contagens ausentes, inválidas ou não
devolvidas em falha permanecem desconhecidas; não são estimadas nem viram
zero. O controle direto registra uma chamada confirmada quando recebe uma
resposta válida do Ollama, mesmo se for “DESCONHECIDO”. A ingestão desse
controle não realiza chamadas. A preparação do modelo fica fora dos tokens
dos casos e não se afirma medir o custo total do sistema.

Relatórios antigos são preservados e identificados como controle via API,
que podia responder por política local sem chamar o modelo. Eles não são
transformados em resultados de Ollama direto. Histórico completo, memória
automática, pré-carregada e o roteiro P6 mantêm seus executores. A memória
pré-carregada continua sendo um controle com estado-ouro, cuja aquisição
não está incluída na medição. Não compare métodos diferentes como se fossem
repetições da mesma configuração.

Para reprodução por CLI, `src.interface.comparativo` preserva o padrão legado
`--controle-sem-memoria api_local`; acrescente
`--controle-sem-memoria modelo_direto` para reproduzir o novo controle Ollama.
Esse modo não está disponível para OpenAI. O JSON novo registra
`controle_sem_memoria`, `versao_metodo_comparativo`, a via `ollama_direto`
e a latência HTTP direta, separada da latência da API do agente.


## Limites da avaliação e relatório parcial

O comando de comparativo acima reproduz o controle direto e os novos limites
da interface: `--timeout-modelo 180` aplica o mesmo prazo por chamada aos
quatro cenários; a API temporária usa timeout HTTP de 210 segundos e o
histórico tem supervisão de 30 + 180 por turno. O wrapper conserva os
padrões legados `api_local` e 60 segundos se as opções forem omitidas.
Declare `limites_execucao` ao comparar resultados com as baterias anteriores.
Não se alteram os limites da conversa normal nem os da P6.

As chamadas concluídas do histórico são transmitidas por turno; em falha,
as parcelas recebidas ficam em `tokens_*_observados` e no subtotal visual.
Total ausente não vira zero. A faixa aponta o caso/repetição e a causa.
Falhas técnicas fazem o wrapper retornar código não zero, preservando o
relatório parcial e fechando a API temporária. Não há repetição automática
nem preenchimento retroativo de relatórios antigos. Uma nova rodada exige
saída nova e início explícito. O limite global da interface continua em
quatro horas. Consulte o [manual](manual-professor.md#medição-incompleta-e-tempo-limite).


### Gerar arquivos próprios sem confundir casos e repetições

Antes de gerar um JSON com uma IA, consulte os
[limites, atributos aceitos e classificação factual/abstenção](manual-professor.md#limites-para-gerar-um-conjunto-com-ajuda-de-ia).
A interface aceita 1–20 casos diferentes e 128 KB por conjunto; o julgador
reconhece uma lista fechada de atributos. DESCONHECIDO esperado por ausência
ou esquecimento deve ser anotado como abstenção, não recuperação factual.
O validador estrutural não substitui a revisão dos gabaritos.

Os 48 resultados por cenário do protocolo oficial vêm de 16 casos repetidos
três vezes, não de um arquivo com 48 casos. Um conjunto de 20 casos com três
repetições produz 60 tentativas por cenário e 240 nos quatro cenários.
Não confundir essa contagem com acertos ou chamadas ao modelo. Um arquivo
de 40 casos deve ser dividido em dois conjuntos de até 20; dividir não
dispensa corrigir atributos e classificações. Recusa de importação é
incompatibilidade do conjunto antes da execução, não resultado do agente.

## Consolidação de resultados, sem executar modelos

As médias de 20/11 estão na [consolidação por conjunto/versão](consolidacao-testes-20261120.md). Executar `python evidencias/consolidacao-interface-20261120/recalcular.py` verifica os relatórios preservados e recalcula consumos e reduções sem Docker, rede ou LLM. O histórico oficial de versões, a versão atual e o personalizado têm denominadores distintos; P6 é apresentada por sessão, separadamente. Médias de desenvolvimento não demonstram efeito causal de cada manutenção.

## Informação antiga na resposta final

Cada faixa mostra a [taxa de informação antiga indevida](informacao-antiga-respostas.md), com oportunidades, cobertura e inconclusivos. Maior taxa é pior. “Mostrar respostas” explica a classificação; sem anotações compatíveis não se assume taxa zero. Os resultados antigos, P4/P5 e tokens continuam preservados. A [conferência offline](../evidencias/informacao-antiga-20261121/README.md) não faz chamadas ao modelo. Esta entrega usa Ollama local, sem depender de créditos de API; [OpenAI permanece opcional](openai-opcional.md#escolha-de-provedor-para-a-entrega).
