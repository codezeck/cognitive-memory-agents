# Reproduzir a avaliação v3 com Docker

Este é o caminho atual para executar os experimentos sem instalar Python/Ollama no host. Para testar somente o chat, use o [manual](manual-professor.md). Contratos e fórmulas detalhados: [guia de referência](guia-avaliacao.md). [Resultados originais](acertos-tokens-contexto-v3.md).

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
docker compose --env-file .env.example -p $projetoCma -f docker-compose.yml -f docker-compose.avaliacao.yml run --rm --no-deps avaliacao -m src.interface.comparativo --dataset eval/dataset_validacao_v3_20261118.json --saida "/saida/validacao-$rodadaCma.json" --repeticoes 3
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
