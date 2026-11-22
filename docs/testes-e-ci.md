# Testes e integração contínua

## Conferência de 22/11

O [CI anterior da PR #46](https://github.com/codezeck/cognitive-memory-agents/actions/runs/45058788502) aprovou 1.175 testes Python, com 66 ignorados, e 76 JavaScript. A correção do manifesto P6 não muda respostas ou tokens. Os três comandos de conferência offline do [pacote de fechamento](../evidencias/fechamento-entrega-20261122/README.md) passaram localmente e foram adicionados ao workflow para detectar arquivos ausentes em checkout limpo. Os checks do novo commit devem passar antes do merge; o CI da futura tag continua obrigatório. As contagens datadas abaixo permanecem históricas.

**P6, revisão final de 21/11:** 1.174 testes Python aprovados, 67 ignorados e 70 testes JavaScript aprovados. Inclui os casos positivos/negativos da [análise P6 v2](julgamento-p6.md), preservação do P4/comparativo, conferência visual clara/escura/estreita e os doze testes de [proteção das entradas](seguranca-entradas.md). Nenhuma chamada de modelo foi executada para validar o julgador. Os registros datados abaixo permanecem históricos.

**Atualização de 21/11:** 1.092 testes Python aprovados e 67 opcionais ignorados; 51 testes JavaScript aprovados. A nova métrica foi validada sem LLM real: afirmação antiga, contraste temporal, menção ambígua, esquecimento, falha, anotação inválida, cobertura e preservação de resultados. [XML e log](../evidencias/informacao-antiga-20261121/README.md). Os números anteriores abaixo são registros datados.

## Cobertura e alcance

**Atualização de 20/11:** a última validação do código do painel e do comparativo registrou **1.057 testes Python aprovados e 67 ignorados**, além de **46 testes JavaScript**. O [registro da validação](../evidencias/consolidacao-interface-20261120/verificacao-codigo-20261120.json) foi preservado. Esta atualização de texto e PDF não repetiu a suíte nem fez chamadas reais ao modelo; validou recálculo, hashes, links locais e renderização. Os testes ignorados dependem de condições opcionais; não são aprovações nem prova de funcionalidades ausentes.

Registro de 18/11: a validação documental acrescentou seis regressões de reprodução LF/CRLF; a suíte daquela revisão registrou **960 testes Python aprovados e 66 ignorados**, além de **8 testes JavaScript**. [XML de 18/11](../evidencias/entrega-v3-20261118/verificacao-documentacao/testes.xml); [execução anterior de 954 testes](../evidencias/entrega-v3-20261118/testes-candidata.xml). Sessenta e cinco ignorados exigem API/Ollama reais e ambiente isolado opt-in; um registro é de coleção ignorada. Não são 66 funcionalidades ausentes. Não foi medida uma porcentagem de cobertura de linhas; não atribuir um percentual fictício.

Os testes cobrem extração e conflitos, recuperação por chave/fallback, atualização, exclusão total/individual, isolamento, SQLite temporário, contexto, suporte e abstenção, adaptadores simulados, autenticação, erros, contratos de tokens e avaliadores. Testes de exclusão incluem `tests/test_memoria.py` e `tests/test_gerenciador_regras.py`. Os testes JS verificam apresentação de métricas, desconhecidos e proveniência do zero local.

Esses testes não são a medição de qualidade do LLM. A [P6 e validação reais](acertos-tokens-contexto-v3.md) são evidências separadas. O [percurso do manual](../evidencias/entrega-v3-20261118/percurso-resumo.json) teve 19 verificações HTTP aprovadas após instalação limpa.

## Executar localmente

Para desenvolvimento, instalar Python 3.13 e Node 22. Na raiz do repositório, em PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.env.pytest-local -o cache_dir=.env.pytest-cache
.\.venv\Scripts\python.exe -m ruff check --select E9,F63,F7,F82 src eval tests tools
node --test tests/test_relatorio.mjs
```

Essas ferramentas de desenvolvimento não são pré-requisitos para o professor usar o chat com Docker. Repetições do pytest devem usar apenas a pasta temporária indicada, criada para testes.

## CI no GitHub e fechamento

O [workflow](../.github/workflows/tests.yml) instala dependências, executa Ruff crítico, os testes JS e pytest. Os testes padrão não usam serviços pagos nem baixam pesos de LLM. Consulte [GitHub Actions](https://github.com/codezeck/cognitive-memory-agents/actions/workflows/tests.yml) e os checks do [PR #45](https://github.com/codezeck/cognitive-memory-agents/pull/45).

O workflow roda em PRs para `master`/`main`, push nessas branches/`feature/**` e na tag `v1.0`. CI aprovado em PR não substitui o CI da tag exigido pelo enunciado. Depois da revisão e integração, criar a tag uma única vez, guardar URL/PNG da execução verde e SHA. [Checklist](checklist-entrega.md). Não mover tag publicada nem atribuir a alguém uma revisão inexistente.


## Conferência local posterior — P6 e entradas

Em 21/11, a suíte completa posterior registrou **1.150 testes Python aprovados, 67 opcionais ignorados e 67 testes JavaScript aprovados**. Inclui análise P6 versionada, preservação do P4 e do comparativo, proteção contra aprovação por palavra isolada, trajetória incompleta e análise desalinhada. Doze testes adicionais conferem entradas em SQLite temporário e API simulada. A apresentação P6 foi inspecionada nos modos claro, escuro e estreito; conversa e importação foram verificadas no navegador quanto à renderização literal de marcação.

Essa validação local não é um novo resultado de LLM nem CI da versão publicada. Os registros datados anteriores não são substituídos. Para executar todos os testes JavaScript no PowerShell, use:

```powershell
$testes = (Get-ChildItem -LiteralPath tests -Filter '*.mjs').FullName
node --test $testes
```
