<#
  Coleta as evidências da parte "memória de longo prazo" (Vinicius) e monta o índice.

  Rode na RAIZ do repositório (a pasta que contém .git), com o ambiente .venv312 pronto:

    powershell -NoProfile -ExecutionPolicy Bypass -File evidencias\memoria\coletar_evidencias.ps1

  Tudo é gerado pela execução real: nada é escrito à mão. Cada arquivo traz no
  cabeçalho a data, o commit e o comando. Não edite os arquivos gerados; para
  atualizar, rode o script de novo.

  Parâmetros:
    -CommitAntes   commit da master ANTES do ajuste do índice (padrão: 69ba7c5)
    -RamoDepois    referência com o teste de contrato (padrão: origin/feature/memoria-indice-e-contrato)
    -SemAntes      não monta o "antes" (pula o worktree temporário)
    -SemSemantico  não roda a avaliação com embedder semântico
#>
param(
    [string]$CommitAntes = "69ba7c5",
    [string]$RamoDepois = "origin/feature/memoria-indice-e-contrato",
    [switch]$SemAntes,
    [switch]$SemSemantico
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path ".git")) { throw "Rode na raiz do repositório (pasta que contém .git)." }
$raiz = (Get-Location).Path
$py = Join-Path $raiz ".venv312\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Não achei $py. Crie o ambiente .venv312 antes." }

$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$pasta = Join-Path $raiz "evidencias\memoria"
New-Item -ItemType Directory -Force -Path $pasta | Out-Null
$agora = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commit = (git rev-parse --short HEAD)
$ramo = (git branch --show-current)
$perfil = $env:USERPROFILE

function Limpar([string]$arquivo) {
    # tira o caminho da pasta do usuário do Windows (evita dado pessoal nos logs)
    $t = [System.IO.File]::ReadAllText($arquivo, [System.Text.Encoding]::UTF8)
    if ($perfil) { $t = $t.Replace($perfil, "%USERPROFILE%") }
    [System.IO.File]::WriteAllText($arquivo, $t, $utf8)
}

function Registrar([string]$arquivo, [string]$comando, [string[]]$argumentos, [string]$diretorio, [string]$avaliado = "") {
    $destino = Join-Path $pasta $arquivo
    $linhaCodigo = if ($avaliado) { "# Código avaliado: $avaliado" } else { "# Commit: $commit ($ramo)" }
    $cabecalho = @("# Gerado em: $agora", $linhaCodigo, "# Comando: $comando", "")
    [System.IO.File]::WriteAllLines($destino, $cabecalho, $utf8)
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    Push-Location $diretorio
    try {
        $saida = & $py @argumentos 2>&1 | ForEach-Object { "$_" }
        $codigo = $LASTEXITCODE
    } finally {
        Pop-Location
        $ErrorActionPreference = $anterior
    }
    [System.IO.File]::AppendAllLines($destino, [string[]]@($saida), $utf8)
    [System.IO.File]::AppendAllText($destino, "`r`n# Código de saída: $codigo`r`n", $utf8)
    Limpar $destino
    Write-Host ("[ok] {0,-46} (saída {1})" -f $arquivo, $codigo) -ForegroundColor Green
}

function Linhas([string]$arquivo, [string]$padrao, [int]$maximo = 25) {
    $caminho = Join-Path $pasta $arquivo
    if (-not (Test-Path $caminho)) { return "(arquivo não gerado)" }
    $achadas = @(Select-String -Path $caminho -Pattern $padrao | Select-Object -First $maximo | ForEach-Object { $_.Line.Trim() })
    if ($achadas.Count -eq 0) { return "(nenhuma linha correspondente)" }
    return ($achadas -join "`n")
}

function GitSilencioso([string[]]$argumentos) {
    # git escreve progresso no stderr; com $ErrorActionPreference = "Stop" isso virava erro no PowerShell 5.1
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & git @argumentos 2>&1 | Out-Null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $anterior
    }
}

function NovoWorktree([string]$referencia, [string]$sufixo) {
    $caminho = Join-Path $env:TEMP ("_evidencia_" + $sufixo)
    if (Test-Path $caminho) {
        GitSilencioso @("worktree", "remove", "--force", $caminho) | Out-Null
        if (Test-Path $caminho) { Remove-Item -Recurse -Force $caminho }
        GitSilencioso @("worktree", "prune") | Out-Null
    }
    $codigoGit = GitSilencioso @("worktree", "add", "--detach", $caminho, $referencia)
    if ($codigoGit -ne 0) { return $null }
    return $caminho
}

function RemoverWorktree([string]$caminho) {
    if ($caminho) {
        GitSilencioso @("worktree", "remove", "--force", $caminho) | Out-Null
        GitSilencioso @("worktree", "prune") | Out-Null
    }
}

Write-Host "Coletando evidências em $pasta" -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $raiz "tests\test_contrato_memoria.py"))) {
    Write-Host "[aviso] Esta árvore NÃO tem tests/test_contrato_memoria.py (o ajuste do índice ainda não está aqui)." -ForegroundColor Yellow
    Write-Host "        Para evidência final, rode numa árvore que o contenha (master depois do merge do PR do ajuste)." -ForegroundColor Yellow
}

# 1) testes automatizados (com o nome de cada teste)
Registrar "01_testes_pytest.txt" "python -m pytest -v" @("-m", "pytest", "-v") $raiz

# 2) avaliação de recuperação (benchmark sintético de 20 sessões)
Registrar "02_recuperacao_palavras_hash.txt" "python eval/avaliar_memoria.py --embedder hash --saida evidencias/memoria/resultados_recuperacao_hash.json" @("eval\avaliar_memoria.py", "--embedder", "hash", "--saida", (Join-Path $pasta "resultados_recuperacao_hash.json")) $raiz
if (-not $SemSemantico) {
    Registrar "03_recuperacao_semantico.txt" "python eval/avaliar_memoria.py --embedder semantico --saida evidencias/memoria/resultados_recuperacao_semantico.json" @("eval\avaliar_memoria.py", "--embedder", "semantico", "--saida", (Join-Path $pasta "resultados_recuperacao_semantico.json")) $raiz
}

# 3) avaliação do baseline por regras (desenvolvimento e avaliação final) com as falhas
Registrar "04_regras_avaliacao_e_falhas.txt" "python eval/avaliar_regras.py --conjunto ambos --mostrar-falhas --saida evidencias/memoria/resultados_regras.json" @("eval\avaliar_regras.py", "--conjunto", "ambos", "--mostrar-falhas", "--saida", (Join-Path $pasta "resultados_regras.json")) $raiz

# 4) contrato da memória nas duas implementações: depois (com o ajuste) e antes (master sem o ajuste)
$testeContrato = Join-Path $raiz "tests\test_contrato_memoria.py"
$destinoDepois = Join-Path $pasta "05_contrato_depois_do_ajuste.txt"
if (Test-Path $testeContrato) {
    Registrar "05_contrato_depois_do_ajuste.txt" "python -m pytest tests/test_contrato_memoria.py -v" @("-m", "pytest", "tests\test_contrato_memoria.py", "-v") $raiz
} else {
    $wtDepois = NovoWorktree $RamoDepois "depois"
    if ($wtDepois) {
        Registrar "05_contrato_depois_do_ajuste.txt" "worktree em $RamoDepois; python -m pytest tests/test_contrato_memoria.py -v" @("-m", "pytest", "tests\test_contrato_memoria.py", "-v") $wtDepois $RamoDepois
        RemoverWorktree $wtDepois
    } else {
        $aviso = @("# Gerado em: $agora", "# NÃO FOI POSSÍVEL gerar o 'depois': a árvore atual não tem o teste e não consegui criar um worktree em $RamoDepois (rode git fetch --all).")
        [System.IO.File]::WriteAllLines($destinoDepois, [string[]]$aviso, $utf8)
        Write-Host "[aviso] 05_contrato_depois_do_ajuste.txt não gerado" -ForegroundColor Yellow
    }
}

$destinoAntes = Join-Path $pasta "06_contrato_antes_do_ajuste.txt"
if (-not $SemAntes) {
    $wtAntes = NovoWorktree $CommitAntes "antes"
    if ($wtAntes) {
        $codigoCheckout = GitSilencioso @("-C", $wtAntes, "checkout", $RamoDepois, "--", "tests/test_contrato_memoria.py")
        if ($codigoCheckout -eq 0) {
            Registrar "06_contrato_antes_do_ajuste.txt" "worktree em $CommitAntes + tests/test_contrato_memoria.py de $RamoDepois; python -m pytest tests/test_contrato_memoria.py -v" @("-m", "pytest", "tests\test_contrato_memoria.py", "-v") $wtAntes $CommitAntes
        } else {
            $aviso = @("# Gerado em: $agora", "# NÃO FOI POSSÍVEL gerar o 'antes': não consegui trazer tests/test_contrato_memoria.py de $RamoDepois (rode git fetch --all).")
            [System.IO.File]::WriteAllLines($destinoAntes, [string[]]$aviso, $utf8)
            Write-Host "[aviso] 06_contrato_antes_do_ajuste.txt não gerado" -ForegroundColor Yellow
        }
        RemoverWorktree $wtAntes
    } else {
        $aviso = @("# Gerado em: $agora", "# NÃO FOI POSSÍVEL gerar o 'antes': não consegui criar um worktree em $CommitAntes (o commit existe? rode git fetch --all).")
        [System.IO.File]::WriteAllLines($destinoAntes, [string[]]$aviso, $utf8)
        Write-Host "[aviso] 06_contrato_antes_do_ajuste.txt não gerado" -ForegroundColor Yellow
    }
}

# 5) histórico do Git (só nomes, sem e-mails) e ambiente
$destinoGit = Join-Path $pasta "07_git_historico.txt"
$linhasGit = @("# Gerado em: $agora", "# Commit: $commit ($ramo)", "# Comando: git log --all --date=short --format='%h %ad %an %s'  e  git shortlog -sn --all", "")
$linhasGit += @(git -c i18n.logOutputEncoding=UTF-8 log --all --date=short --format="%h %ad %an %s")
$linhasGit += ""
$linhasGit += "# Commits por pessoa"
$linhasGit += @(git -c i18n.logOutputEncoding=UTF-8 shortlog -sn --all)
[System.IO.File]::WriteAllLines($destinoGit, [string[]]$linhasGit, $utf8)
Write-Host ("[ok] {0,-46}" -f "07_git_historico.txt") -ForegroundColor Green

Registrar "08_ambiente.txt" "python --version; python -m pip freeze" @("-c", "import sys, platform; print(sys.version); print(platform.platform())") $raiz
$freeze = & $py -m pip freeze 2>&1 | ForEach-Object { "$_" }
$linhasFreeze = @("", "# python -m pip freeze") + @($freeze)
[System.IO.File]::AppendAllLines((Join-Path $pasta "08_ambiente.txt"), [string[]]$linhasFreeze, $utf8)

# 6) índice (README) montado a partir dos arquivos gerados
$cerca = '```'
$modelo = @'
# Evidências da parte de memória de longo prazo

Responsável: Vinicius. Gerado em **__DATA__**, commit **__COMMIT__**.

Todos os arquivos desta pasta foram produzidos pelo script `coletar_evidencias.ps1` a partir da execução real do projeto. Cada um traz no cabeçalho a data, o commit e o comando. Não foram editados à mão. Para regerar tudo, na raiz do repositório:

__CERCA__powershell
powershell -NoProfile -ExecutionPolicy Bypass -File evidencias\memoria\coletar_evidencias.ps1
__CERCA__

## Índice: afirmação do trabalho, evidência e como conferir

| # | Afirmação | Evidência | Como conferir |
|---|---|---|---|
| 1 | A suíte de testes do projeto passa. | `01_testes_pytest.txt` | Última linha com o total; `python -m pytest -v` |
| 2 | A recuperação semântica acerta mais que a por palavras no benchmark de 20 sessões, sem devolver informação desatualizada. | `02_recuperacao_palavras_hash.txt`, `03_recuperacao_semantico.txt` e os `resultados_recuperacao_*.json` | `python eval/avaliar_memoria.py --embedder hash` e `--embedder semantico` |
| 3 | O baseline por regras guarda, atualiza e esquece fatos; o desempenho no conjunto de avaliação final é menor que no de desenvolvimento. | `04_regras_avaliacao_e_falhas.txt` e `resultados_regras.json` | `python eval/avaliar_regras.py --conjunto ambos --mostrar-falhas` |
| 4 | Fato antigo é substituído e fato apagado deixa de ser recuperado (nas memórias em RAM e em SQLite). | Testes `test_fato_substituido_e_apagado_nao_voltam_pela_busca`, `test_esquecer_usuario_conta_tudo_e_nao_afeta_outros` e `test_esquecer_por_topico_depois_de_reiniciar` em `01_testes_pytest.txt` e `05_contrato_depois_do_ajuste.txt` | `python -m pytest tests/test_contrato_memoria.py -v` |
| 5 | O ajuste do índice corrigiu cenários que falhavam: antes falhavam, depois passam. | `06_contrato_antes_do_ajuste.txt` (falhas) e `05_contrato_depois_do_ajuste.txt` (verde) | Compare os dois arquivos; o "antes" usa um worktree no commit anterior ao ajuste |
| 6 | O sistema erra em casos conhecidos, com causa analisada (evidência 6 do enunciado). | Lista de frases e conversas que falham em `04_regras_avaliacao_e_falhas.txt` e análise por causa em `docs/falhas-conhecidas-regras.md` | Rodar o comando da linha 3 e ler as falhas |
| 7 | Os integrantes contribuíram e os PRs foram revisados por outro membro. | `07_git_historico.txt` (commits e autores). A revisão dos PRs está nas páginas dos pull requests no GitHub | Ver o histórico no repositório |
| 8 | Ambiente de execução. | `08_ambiente.txt` | `python --version` e `pip freeze` |

## Resumo lido dos arquivos gerados (não digitado)

**Testes (`01_testes_pytest.txt`)**

__CERCA__
__RESUMO_PYTEST__
__CERCA__

**Recuperação por palavras (`02_*`)**

__CERCA__
__RESUMO_HASH__
__CERCA__

**Recuperação semântica (`03_*`)**

__CERCA__
__RESUMO_SEMANTICO__
__CERCA__

**Regras (`04_*`)**

__CERCA__
__RESUMO_REGRAS__
__CERCA__

**Contrato da memória, depois do ajuste (`05_*`) e antes (`06_*`)**

__CERCA__
depois: __RESUMO_DEPOIS__
antes:  __RESUMO_ANTES__
__CERCA__

## Limites desta pasta

- Cobre só a parte de memória. O vídeo com `docker compose up`, o link da integração contínua na tag `v1.0`, os logs da API em execução completa e as capturas de tela são do grupo e não estão aqui.
- Os conjuntos de dados são sintéticos e pequenos; os números são preliminares.
- Os conjuntos de desenvolvimento e de avaliação das regras foram escritos pela mesma pessoa que escreveu as regras.
- Resultado ruim não é escondido: as falhas do baseline estão listadas no arquivo `04_*`.
'@
$resumoPytest = Linhas "01_testes_pytest.txt" "passed|failed|error" 3
$resumoHash = Linhas "02_recuperacao_palavras_hash.txt" "Embedder|Taxa|Lembran|Informa|Esquecimento|Redu" 10
$resumoSem = if ($SemSemantico) { "(não executado: -SemSemantico)" } else { Linhas "03_recuperacao_semantico.txt" "Embedder|Taxa|Lembran|Informa|Esquecimento|Redu|rror" 10 }
$resumoRegras = Linhas "04_regras_avaliacao_e_falhas.txt" "Conjunto|Frases|precis|Conversas" 12
$resumoDepois = (Linhas "05_contrato_depois_do_ajuste.txt" "passed|failed|error" 1)
$resumoAntes = if ($SemAntes) { "(não executado: -SemAntes)" } else { (Linhas "06_contrato_antes_do_ajuste.txt" "passed|failed|error|NÃO FOI" 1) }
$readme = $modelo.Replace("__DATA__", $agora).Replace("__COMMIT__", $commit).Replace("__CERCA__", $cerca)
$readme = $readme.Replace("__RESUMO_PYTEST__", $resumoPytest).Replace("__RESUMO_HASH__", $resumoHash).Replace("__RESUMO_SEMANTICO__", $resumoSem)
$readme = $readme.Replace("__RESUMO_REGRAS__", $resumoRegras).Replace("__RESUMO_DEPOIS__", $resumoDepois).Replace("__RESUMO_ANTES__", $resumoAntes)
[System.IO.File]::WriteAllText((Join-Path $pasta "README.md"), $readme, $utf8)
Write-Host "[ok] README.md (índice)" -ForegroundColor Green

Write-Host ""
Write-Host "Concluído. Antes do commit:" -ForegroundColor Cyan
Write-Host "  1) abra os arquivos e confira que não há senha, chave de API nem dado pessoal;"
Write-Host "  2) git status --short   (devem aparecer só arquivos em evidencias/memoria/)."
