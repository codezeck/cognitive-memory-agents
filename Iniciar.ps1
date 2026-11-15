[CmdletBinding()]
param(
    [ValidateRange(1024,65535)][int]$Porta = 8001,
    [ValidatePattern('^[a-z][a-z0-9-]{0,47}$')][string]$Projeto = 'cma-demonstracao',
    [switch]$SemAbrir
)
$ErrorActionPreference = 'Stop'
function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Argumentos)
    # Windows PowerShell 5 transforma stderr nativo em NativeCommandError
    # quando a saida e redirecionada. Docker usa stderr tambem para progresso.
    $preferenciaAnterior=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        & docker @Argumentos 2>&1 | ForEach-Object { $_.ToString() }
        $script:LASTEXITCODE=$LASTEXITCODE
    } finally { $ErrorActionPreference=$preferenciaAnterior }
    if ($script:LASTEXITCODE -ne 0) {
        throw ('Docker falhou com codigo '+$script:LASTEXITCODE+'. Confira a mensagem acima; volumes preservados.')
    }
}
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Instale e abra o Docker Desktop antes de iniciar.'
}
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) { throw 'Abra o Docker Desktop e aguarde o mecanismo iniciar.' }
# Nao ler ou alterar .env, Ollama do host, clipboard ou credenciais existentes.
$compose = @('compose','--env-file','.env.example','-p',$Projeto)
$portaAnterior = [Environment]::GetEnvironmentVariable('CMA_PORT','Process')
try {
    $env:CMA_PORT = [string]$Porta
    $ocupada = New-Object Net.Sockets.TcpClient
    $emUso = $false
    try { $ocupada.Connect('127.0.0.1',$Porta); $emUso=$true } catch {} finally { $ocupada.Dispose() }
    if ($emUso) {
        $portas = docker ps --filter ("label=com.docker.compose.project="+$Projeto) --filter 'label=com.docker.compose.service=api' --format '{{.Ports}}'
        if (($portas -join '') -notmatch ('127\.0\.0\.1:'+$Porta+'->8000')) {
            throw "A porta $Porta esta ocupada por outro servico. Use -Porta com outra porta livre."
        }
    }
    Write-Host '1/3 Construindo a aplicacao e preparando o Ollama no Docker...'
    Invoke-Docker -Argumentos ($compose + @('build','api','preparar'))
    if ($LASTEXITCODE -ne 0) { throw 'O build nao foi concluido. Confira a conexao e o Docker.' }
    $inicioPreparacao=[DateTime]::UtcNow.ToString('o')
    Invoke-Docker -Argumentos ($compose + @('up','-d','preparar'))
    if ($LASTEXITCODE -ne 0) { throw 'O Ollama ou a preparacao nao iniciaram. Volumes preservados.' }
    $preparacao = docker @compose ps -aq preparar
    if (-not $preparacao) { throw 'Conteiner de preparacao nao encontrado.' }
    Invoke-Docker -Argumentos @('logs','--since',$inicioPreparacao,'--follow',$preparacao)
    $codigoPreparacao = docker inspect --format '{{.State.ExitCode}}' $preparacao
    if ($codigoPreparacao -ne '0') { throw 'A preparacao do modelo falhou. Corrija a causa acima e repita o mesmo comando; volumes preservados.' }
    Invoke-Docker -Argumentos ($compose + @('up','--no-deps','-d','api'))
    if ($LASTEXITCODE -ne 0) { throw 'A API nao iniciou depois de preparar o modelo.' }
    Write-Host '2/3 Conferindo API e acesso local...'
    $base='http://127.0.0.1:'+$Porta
    $pronta=$false
    for ($i=0;$i -lt 60;$i++) {
        try { Invoke-RestMethod ($base+'/saude') -TimeoutSec 2 | Out-Null; $pronta=$true; break } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $pronta) { throw 'A API nao respondeu depois da preparacao. Confira os logs do projeto.' }
    $config=Invoke-RestMethod ($base+'/interface/configuracao') -TimeoutSec 5
    if (-not $config.demonstracao_local) { throw 'O acesso local automatico nao ficou disponivel.' }
    Write-Host ('3/3 Aplicacao pronta: '+$base)
    Write-Host 'Acesso sintetico por cookie HttpOnly; nao e preciso copiar tokens.'
    Write-Host ('Para parar sem apagar dados: docker compose --env-file .env.example -p '+$Projeto+' stop')
    if (-not $SemAbrir) { Start-Process -FilePath $base -WindowStyle Hidden }
} finally {
    [Environment]::SetEnvironmentVariable('CMA_PORT',$portaAnterior,'Process')
}
