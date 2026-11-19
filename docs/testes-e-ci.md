# Testes e integração contínua

## Cobertura e alcance

A validação documental acrescentou seis regressões de reprodução LF/CRLF; a suíte atual registrou **960 testes Python aprovados e 66 ignorados**, além de **8 testes JavaScript**. [XML atual](../evidencias/entrega-v3-20261118/verificacao-documentacao/testes.xml); [execução anterior de 954 testes](../evidencias/entrega-v3-20261118/testes-candidata.xml). Sessenta e cinco ignorados exigem API/Ollama reais e ambiente isolado opt-in; um registro é de coleção ignorada. Não são 66 funcionalidades ausentes. Não foi medida uma porcentagem de cobertura de linhas; não atribuir um percentual fictício.

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
