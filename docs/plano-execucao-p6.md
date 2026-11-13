# Plano operacional da P6 — 20 sessões

Documento de preparação de Zeck, em 12/11/2026. **Não houve execução real, limpeza de banco, chamada de modelo ou geração de resultado experimental neste trabalho.** Foi feita somente inspeção do planejador e leitura dos dados/código.

Este plano organiza a sequência e as evidências. Os formatos completos de credenciais, contratos e observações continuam no [guia de avaliação — P6](guia-avaliacao.md#p6--primeira-etapa-do-experimento-integrado); não criar outro contrato concorrente. A análise acadêmica está em [contribuição](contribuicao-academica-zeck.md), e a classificação dos resultados existentes em [resultados](resultados-avaliacoes-agente.md).

## 1. Versão e condição de liberação

| Referência em 12/11/2026 | Estado confirmado | Consequência |
|---|---|---|
| Master `fc759f3` | `p4-v2`; inspeção atual: 10 compatíveis, 11 incompatíveis, 0 ausentes | Não tratar como avaliação completa das respostas P6 |
| [PR #41](https://github.com/codezeck/cognitive-memory-agents/pull/41), `29d1255` | P4-v3 e 21/21 compatíveis registrados nos testes da PR; ainda não integrada | Aguardar revisão e versão congelada; não copiar código para esta branch documental |
| Anotações oficiais | 21 presentes; quantidade de gatos ainda depende de revisão | Compatibilidade não certifica validade semântica |
| Execução real | Nenhum JSONL real P6 encontrado entre os artefatos versionados | Não há taxa funcional para preencher |

O experimento oficial deve usar uma versão aprovada/congelada com cobertura estrutural integral e política semântica revisada. O enunciado pede evidência do chatbot em 20 sessões; um benchmark de busca sem LLM ou um transporte simulado não substitui essa exigência.

## 2. Pré-requisitos e responsáveis

| Porta de entrada | Critério para liberar | Responsabilidade |
|---|---|---|
| Código e protocolo | Commit identificado, testes adequados, política P4 aprovada; versões da API e avaliador registradas | Zeck; revisão da equipe |
| Gabaritos | 21 anotações revisadas; resolver recuperação de Luna/Simba versus resposta “dois”; aliases/proibições explícitos | Vinicius com Zeck |
| Esquecimento parcial | Contrato externo de `u02/s5/esquecer_chaves` com mensagem literal, aprovação efetiva e referência | Vinicius revisa conteúdo; Paloma valida integração |
| Usuários | Mapeamento exato de u01–u04 para quatro identidades distintas `p6_`, com tokens provisionados fora do Git | Paloma |
| Estado inicial | Evidência aprovada de ativos, substituídos e histórico vazios, sem escritores concorrentes | Paloma; Zeck revisa vínculo ao experimento |
| RAM | Observação dentro do processo real da API, sem criar/limpar histórico ao observar; worker identificado e cobertura dos processos relevantes | Solução compartilhada Paloma/Zeck, ainda pendente |
| Serviços | API real sem falsos, Ollama/modelo disponível, mesmo backend e configuração efetiva no baseline e API | Paloma/Zeck |
| Persistência/exclusão | Operador e observador disponíveis durante os checkpoints; estados anteriores, posteriores, escopo e timestamps coerentes | Paloma, com revisão de Zeck/Vinicius |
| Recursos de evidência | Diretório de saída com nome novo, ID combinado da execução e documento de evidências compatível | Zeck/Paloma |

Não usar um GET vazio como atalho para o estado inicial. Não inventar `aprovado: true`, zeros de RAM, reinício, aliases ou conteúdo do contrato. O hash identifica o documento lido, não autentica seu autor. Não operar sobre usuários de desenvolvimento, produção ou demonstração.

**Questão a resolver antes do congelamento:** em `u04/s4`, apagar o usuário é seguido de perguntas de abstenção, sem fatos novos. Espera-se estado persistente vazio. `classificar_checkpoint` exige estado anterior não vazio para comprovar persistência, enquanto `medicao_completa` pode aceitar snapshots vazios como completos. Assim, `{}` antes/depois não aprova persistência e tende a ficar `nao_verificado`; aguardar o documento não altera essa regra. Zeck e Paloma precisam definir/documentar a aplicabilidade desse checkpoint após exclusão, com Vinicius revisando a semântica. Não inserir um fato artificial, falsificar snapshot ou marcar manualmente como verificado. Este trabalho não altera o código nem o contrato.

## 3. Plano das sessões, copiado estruturalmente do dataset

Fonte: `eval/memoria/sessoes.json`; ordem do planejador: número da sessão e, dentro dele, u01, u02, u03, u04. Cada linha abaixo aparece nos dois cenários. `p1`, por exemplo, significa `pergunta1` daquele usuário; o índice não reinicia a cada sessão.

| Ordem | Usuário/sessão | Fatos | Perguntas após os fatos | Ação administrativa do dataset |
|---:|---|---:|---|---|
| 1 | u01/s1 | 3 | — | — |
| 2 | u02/s1 | 3 | — | — |
| 3 | u03/s1 | 3 | — | — |
| 4 | u04/s1 | 3 | — | — |
| 5 | u01/s2 | 2 | p1 | — |
| 6 | u02/s2 | 2 | — | — |
| 7 | u03/s2 | 2 | p1 | — |
| 8 | u04/s2 | 2 | — | — |
| 9 | u01/s3 | 1 | p2 | — |
| 10 | u02/s3 | 1 | p1 | — |
| 11 | u03/s3 | 1 | p2 | — |
| 12 | u04/s3 | 1 | p1 | — |
| 13 | u01/s4 | 1 | p3 | — |
| 14 | u02/s4 | 1 | p2 | — |
| 15 | u03/s4 | 1 | p3 | — |
| 16 | u04/s4 | 0 | p2, p3 | Apagar usuário e checkpoint de exclusão antes das perguntas |
| 17 | u01/s5 | 2 | p4, p5, p6 | — |
| 18 | u02/s5 | 0 | p3, p4, p5 | Esquecer chave `carro`, com contrato, e checkpoint antes das perguntas |
| 19 | u03/s5 | 1 | p4, p5 | — |
| 20 | u04/s5 | 1 | p4, p5 | Reaprendizado após exclusão anterior |

Cada sessão possui evento inicial e checkpoint de persistência ao final. O transporte automático inicia nova sessão mantendo as memórias; o baseline conserva seu histórico por episódio e o segmenta em `apagar_usuario`. Checkpoints de armazenamento são não aplicáveis ao baseline de histórico.

Inspeção do plano: **96 eventos por cenário** — 20 inícios, 31 fatos, 21 perguntas, 1 pedido de esquecimento, 1 exclusão total, 2 checkpoints de exclusão e 20 checkpoints de persistência. Há **53 eventos lógicos de geração por cenário** (fatos + perguntas + pedido de esquecimento), não 96 chamadas de modelo; tentativas internas do SDK e consumo perdido em falhas não são quantificados por essa contagem.

Uma rodada completa prevê 20 sessões por cenário, **40 registros de sessão e 42 perguntas observadas** na comparação. Esses números são cobertura planejada, não números de acertos nem contagens já medidas. A quantidade de linhas JSONL depende também de tentativas, esperas e interrupções; não fixá-la artificialmente.

## 4. Preparação segura e inspeção sem execução

Na versão aprovada, com o ambiente Python do guia, executar apenas a inspeção para conferir cobertura antes de liberar a rodada:

```powershell
python -B eval/avaliar_sessoes_integradas.py --dataset eval/memoria/sessoes.json --anotacoes eval/memoria/anotacoes_p6.json
```

Na base desta branch, o retorno observado foi 4 usuários, 20 sessões, 21 perguntas, 10 compatíveis/11 incompatíveis e uma ação exigindo contrato: `u02/s5/esquecer_chaves`. A PR #41 registra a resolução estrutural para 21/21; conferir novamente após integração. Não executar com cobertura parcial e depois chamar a rodada de avaliação completa.

Antes de qualquer rodada oficial:

1. Registrar commit, versão do julgador, hashes de código/dados, Python/dependências, modelo e sua identificação efetiva, runtime, parâmetros, hardware e condição de aquecimento. Quando algum campo não estiver disponível no JSONL, registrá-lo em metadados externos revisados; não inventá-lo.
2. Revisar os testes do avaliador e dos provedores, conforme o guia, usando temporários. Não confundir essa etapa com execução real.
3. Combinar antecipadamente `execucao_id`, API, identidades, contrato, observador e documento de evidências. O documento precisa referenciar esse mesmo ID.
4. Confirmar os pré-requisitos da seção 2 e a decisão do checkpoint vazio de u04/s4. Se faltar qualquer entrega, manter a rodada bloqueada.

## 5. Comando de execução futura — não executado

Usar somente depois da liberação conjunta. Os caminhos são para arquivos externos reais, previamente produzidos/revisados; este documento não os cria. O script realizará POST/DELETE e gravará JSONL novo no ambiente dedicado.

Configurar no ambiente, sem exibir segredos: `P6_EXECUCAO_ID` (ID já combinado), `P6_CREDENCIAIS`, `P6_CONTRATOS_ACOES` e `P6_EVIDENCIAS` (caminhos dos documentos). API/modelo nos argumentos abaixo devem coincidir com a configuração aprovada.

```powershell
$execucaoP6 = $env:P6_EXECUCAO_ID
if (-not $execucaoP6 -or $execucaoP6 -notmatch '^[A-Za-z0-9_.-]+$') {
    throw "ID da execucao ausente ou invalido."
}
foreach ($caminhoP6 in @($env:P6_CREDENCIAIS, $env:P6_CONTRATOS_ACOES, $env:P6_EVIDENCIAS)) {
    if (-not $caminhoP6 -or -not (Test-Path -LiteralPath $caminhoP6 -PathType Leaf)) {
        throw "Falta documento externo revisado."
    }
}
$saidaP6 = Join-Path "evidencias/agente" ($execucaoP6 + ".jsonl")
if (Test-Path -LiteralPath $saidaP6) { throw "Saida existente; preservar e usar novo ID." }
$argumentosP6 = @(
    "--dataset", "eval/memoria/sessoes.json",
    "--anotacoes", "eval/memoria/anotacoes_p6.json",
    "--credenciais", $env:P6_CREDENCIAIS,
    "--contratos-acoes", $env:P6_CONTRATOS_ACOES,
    "--evidencias", $env:P6_EVIDENCIAS,
    "--execucao-id", $execucaoP6,
    "--base-url", "http://127.0.0.1:8000",
    "--provedor", "ollama", "--modelo", "qwen2.5-coder:3b",
    "--aguardar-evidencias", "--timeout-evidencia", "300",
    "--intervalo-evidencia", "1", "--saida", $saidaP6, "--executar"
)
python -B eval/avaliar_sessoes_integradas.py @argumentosP6
```

Os 300 segundos são um orçamento inicial proposto para chegada de cada evidência, não uma medição de duração da P6; ajustar previamente com o operador. Sem `--timeout-historico`, o supervisor usa o prazo padrão por episódio definido no guia. O transporte HTTP usa timeout próprio; não confundir os três limites. O diretório `evidencias/agente` deve existir e o backend precisa ser acessível ao baseline local e à API.

Não existe `--repeticoes` nem `--repeticao` na CLI P6 atual; `repeticao` é parâmetro da função e a CLI usa o padrão 1. O protocolo de três repetições do comparativo é separado. Se a equipe decidir replicar P6, planejar execuções independentes com novos ambientes/IDs/evidências e registrar a réplica externa honestamente; não editar o cabeçalho nem inventar argumentos para rotular uma execução como repetição 2/3.

## 6. Checkpoints e coleta durante a rodada

| Momento | Observação necessária | Critério e risco |
|---|---|---|
| Preflight de u01–u04 | Autenticação, estado de regras, catálogo e evidências iniciais | A barreira global impede geração em ambos os cenários se faltar identidade/configuração/estado limpo comprovado |
| Após cada sessão, memória automática | Reinício real, snapshots antes/depois ligados à execução e ao evento | Nova sessão não é reinício; o caso vazio u04/s4 exige decisão explícita |
| u04/s4/checkpoint_exclusao | Alvos existentes antes, zeros depois em ativos, substituídos e histórico; preservação de não alvos | Medir o usuário inteiro; busca vazia ou resposta DESCONHECIDO não provam exclusão total |
| u02/s5/checkpoint_exclusao_chaves | Mesmas observações no escopo `carro` | Verificar valores ativos e substituídos, resíduos em respostas e preservação dos demais fatos |
| Perguntas de todos os usuários | Resposta literal, memórias usadas, tokens/latência disponíveis e estado da trajetória | Separar busca, resposta, formato e exclusão; não converter erro em abstenção correta |

Paloma produz os snapshots/medições reais e substitui atomicamente o documento conforme o contrato existente. A RAM deve ser observada no processo correto; um script externo que apenas importe `src.agent` observa outro dicionário. Timestamps de checkpoint precisam ser coerentes com o início e as ações relevantes. Manter aprovação/referência genuínas, sem tokens.

Com `--aguardar-evidencias`, o executor espera somente o documento local; não faz reinício nem repete POST/DELETE. Timeout ou incompatibilidade interrompem a sequência preservando o que já foi registrado. Não reiniciar uma rodada sobre estado parcialmente alterado nem continuar manualmente no mesmo arquivo. Separar diagnóstico da falha e nova execução dedicada.

## 7. Resultados esperados como estrutura, sem metas inventadas

| Indicador ao analisar | Critério de interpretação |
|---|---|
| Cabeçalho `inicio` | `simulado: false`, versão, ID, commit e hashes; API/backend/configuração revisados |
| Trajetórias | Conferir as 21 perguntas por cenário e 40 sessões previstas; expor faltantes e falhas |
| Tokens | Ingestão, perguntas e sessão, entrada/saída/total; preservar `null`, parcelas observadas e cobertura |
| Comparação de tokens | Até 20 pares usuário/sessão por etapa/canal; mesmos pares nos dois cenários; duplicatas/configurações incompatíveis excluídas explicitamente |
| P4/P5 | Taxas acompanhadas de elegíveis, verificados, não verificados e não aplicáveis; vazamento somente de alvos explícitos |
| Persistência/exclusão | Estados `verificado`, `reprovado`, `nao_verificado` ou não aplicável, com proveniência; `verificado_simulado` não comprova execução real |
| Registro `fim` | Conferir `estado_orquestracao`, falhas, perguntas observadas, cobertura e `avaliacao_respostas_completa`; ausência de `fim` indica log parcial |
| Saída da CLI | 0: orquestração concluída; 1: incompleta; 2: argumentos/estrutura inválidos. Código 0 não equivale a todas as respostas/checkpoints aprovados |

Não exigir acerto de 100% como condição para publicar ciência honesta. Um erro factual observado é resultado; uma medição ausente não é resultado zero. `avaliacao_respostas_completa` não substitui inspeção dos checkpoints nem aprovação semântica dos dados. O checkpoint vazio não pode desaparecer do relatório para melhorar cobertura.

## 8. Pacote de evidências após a execução

- JSONL original íntegro, inclusive parciais e falhas, com nome/ID exclusivos; nenhuma sobrescrita.
- Registro de versão/configuração e hashes, horários com fuso, identidades sintéticas e protocolo aprovado. Distinguir hashes canônicos do cabeçalho de hashes dos bytes de arquivos, que podem variar por CRLF/LF.
- Documentos de evidência e referências de snapshots/observação, aprovados e sem segredos; credenciais ficam fora do pacote público.
- Tabelas e gráficos de tokens/qualidade/cobertura e análise dos erros, com vínculo exato à fonte; usar os modelos reservados em [resultados](resultados-avaliacoes-agente.md).
- Log e captura do CI da versão final, vídeo/índice e contribuição à pesquisa. Revisão humana antes de disponibilizar artefatos.

Não confundir esta P6 com o teste reservado `eval/dataset_teste.json`: seus dez casos ainda precisam de metadados P4 e revisão de Vinicius, em uma entrega independente. Este plano não altera esses dados nem executa a avaliação final.
