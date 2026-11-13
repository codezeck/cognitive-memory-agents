# Roteiro de demonstração — agente e memória

Responsável pelo roteiro e narração: Zeck. Preparado em 12/11/2026, sem executar as operações descritas. Duração-alvo: **4 minutos e 30 segundos**; limite do enunciado: 3–5 minutos, com tela inteira, subida por `docker compose up` e fluxo principal.

O vídeo final deve mostrar a versão avaliada/tag `v1.0`. Enquanto a PR #41 estiver aberta, identificar sua funcionalidade como “em revisão”; não afirmar que o tratamento 503 de resposta vazia ou a política P4-v3 já pertencem à master. Este roteiro usa o fluxo existente da API e não depende de executar as 20 sessões no vídeo.

## 1. Evidência disponível e afirmações permitidas

| Trecho | Evidência existente | O que falta para a gravação final |
|---|---|---|
| Agente, contexto e provedores | Código e testes; adaptadores Ollama/OpenAI implementados | Serviço/modelo local disponível e geração real no ambiente gravado |
| Lembrar, atualizar e persistir | [Log Docker de 05/11](../evidencias/agente/fluxo-memoria-docker-2026-11-05.txt), commit `c7451fe` | Reproduzir o fluxo na versão final, preservando logs datados |
| Exclusão total e segurança | Testes de API/contrato e log histórico | Mostrar a operação real; inspeção de busca não prova sozinha toda a RAM/inativos |
| Julgador e métricas | Implementação/documentação e testes; PR #41 com CI verde | Separar demonstração de engenharia de resultado de modelo |
| P6 integrada | Planejador e anotações, sem rodada real versionada | Contratos, revisão semântica e evidências do [plano P6](plano-execucao-p6.md) |

Não usar `USAR_FALSOS=1` na gravação apresentada como chatbot real. Não substituir resposta ruim por saída escrita à mão, fixture ou trecho de outra rodada. Se um serviço não estiver disponível, uma apresentação do log histórico deve ser identificada como histórica e não satisfaz a gravação final do fluxo ao vivo.

## 2. Preparação e ensaio, fora da gravação

- Paloma prepara um ambiente/volume **dedicado à demonstração**, com o usuário sintético `demo_zeck` autorizado e sem dados de outras atividades. Não reutilizar identidades P6 ou o usuário do benchmark. Não excluir volumes para preparar o vídeo neste trabalho.
- Paloma provisiona o token e confirma a configuração de Docker, persistência e modelo. Ollama e pesos podem estar instalados antes; declarar esses pré-requisitos. Não prometer que o Compose instala o modelo ou sobe PostgreSQL: ele sobe a API e usa SQLite no volume.
- Zeck ensaia as mensagens abaixo e mede os tempos na máquina final. Aquecer o modelo pode ser parte da preparação, declarada no vídeo; não comparar essa latência com partidas frias.
- Manter o Compose em um terminal e as operações em outro. A API deve iniciar no ambiente dedicado durante a gravação. Se build/download ou chamadas excederem o orçamento, ajustar o ensaio e regravar uma execução íntegra; não ocultar atrasos ou falhas para fabricar sucesso.
- Disponibilizar antecipadamente `DEMO_API_TOKEN` no ambiente do terminal de operações, sem exibi-lo. Não abrir `.env`, imprimir cabeçalhos, usar `docker compose config` com valores resolvidos ou mostrar histórico de comandos que contenha segredos. Inspecionar o vídeo antes de publicar.
- Deixar abertas as tabelas históricas de [resultados](resultados-avaliacoes-agente.md), os [casos de falha](casos-de-falha.md) e o CI da versão final. A captura da PR não substitui o CI exigido na tag.

A lista opcional de cinco capturas pode cobrir: início, recuperação em nova sessão, atualização, persistência e exclusão/falha tratada. O manual com capturas é um requisito técnico distinto; as capturas e o vídeo ainda precisam ser produzidos.

## 3. Linha do tempo e fala sugerida

| Tempo | Tela/ação | Narração sugerida e critério observável |
|---|---|---|
| 00:00–00:25 | Nome do projeto, commit/tag e desenho do fluxo | “Minha parte organiza o agente, seus provedores e a avaliação. Vamos observar memória entre sessões, atualização e exclusão em dados sintéticos.” Identificar a versão real mostrada. |
| 00:25–00:50 | Executar `docker compose up`; abrir `/saude` | “O serviço usa SQLite persistente em volume e um modelo Ollama local previamente instalado.” Mostrar API iniciando e saúde; não apresentar saúde como prova de disponibilidade do LLM. |
| 00:50–01:45 | Informar cidade, iniciar nova sessão e perguntar | “A sessão nova limpa a conversa recente, mas preserva os fatos. A resposta mostra quais memórias foram recuperadas.” Conferir `resposta` e `memorias_usadas`, sem inventar o texto retornado. |
| 01:45–02:20 | Informar mudança para Campinas; consultar memórias ativas | “Um fato atualizado substitui o anterior na busca ativa.” Mostrar consulta por Campinas e por Osasco; explicar que busca vazia não inspeciona registros inativos. |
| 02:20–03:05 | Reiniciar o serviço API e repetir busca/pergunta | “Agora reiniciamos o processo, em vez de apenas abrir nova sessão.” Confirmar reinício real e recuperação posterior. Não remover/recriar o volume. |
| 03:05–03:50 | Apagar todas as memórias do usuário demo, buscar e perguntar | “A operação remove as memórias desse usuário e limpa sua conversa pelo fluxo existente. A busca está vazia; a prova completa da RAM e dos registros pertence aos checkpoints de avaliação.” Mostrar contagem real de removidas, busca e resposta. |
| 03:50–04:30 | Mostrar 401 sem token, tabelas históricas e pendências | “Estas tabelas são históricas; a P6 real aguarda contratos e evidências. Testes verdes e anotações compatíveis não são acerto do chatbot.” Mostrar o erro tratado e apontar uma falha documentada, sem executar experimento longo. |

Meta de tempo não é previsão de latência do modelo. Se o agente inventar uma cidade após exclusão, manter a ocorrência visível: ausência de memória recuperada e qualidade da resposta são dimensões diferentes. A explicação da falha é parte legítima da demonstração.

## 4. Comandos para o ensaio futuro

**Não executados nesta preparação.** Os POST/DELETE abaixo alteram o estado do usuário demo; usar apenas após Paloma confirmar o ambiente dedicado. Referência dos endpoints: [README — API](../README.md#api).

Terminal da API, durante a gravação:

```powershell
docker compose up
```

Preparar estas definições no terminal de operações, sem imprimir o token:

```powershell
$baseDemo = "http://127.0.0.1:8000"
$usuarioDemo = "demo_zeck"
if (-not $env:DEMO_API_TOKEN) { throw "Token do usuario demo nao provisionado." }
$cabecalhoDemo = @{ Authorization = "Bearer $env:DEMO_API_TOKEN" }
function Conversar-Demo([string]$mensagemDemo) {
    $corpoDemo = @{ usuario_id = $usuarioDemo; mensagem = $mensagemDemo;
        provedor = "ollama"; modelo = "qwen2.5-coder:3b" } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$baseDemo/conversas" -Headers $cabecalhoDemo `
        -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($corpoDemo))
}
```

Na ordem das cenas:

```powershell
Invoke-RestMethod "$baseDemo/saude"
Conversar-Demo "Moro em Osasco." | Format-List resposta,memorias_usadas,provedor,modelo
Invoke-RestMethod -Method Post -Uri "$baseDemo/usuarios/$usuarioDemo/sessoes" -Headers $cabecalhoDemo
Conversar-Demo "Em que cidade moro? Responda apenas a cidade ou DESCONHECIDO." | Format-List resposta,memorias_usadas
Conversar-Demo "Agora moro em Campinas." | Format-List resposta,memorias_usadas
Invoke-RestMethod "$baseDemo/usuarios/$usuarioDemo/memorias?consulta=Campinas&k=5" -Headers $cabecalhoDemo
Invoke-RestMethod "$baseDemo/usuarios/$usuarioDemo/memorias?consulta=Osasco&k=5" -Headers $cabecalhoDemo
```

Com Paloma coordenando o ambiente dedicado, em um terminal de controle:

```powershell
docker compose restart api
```

Aguardar saúde após o reinício e observar persistência antes de excluir:

```powershell
Invoke-RestMethod "$baseDemo/saude"
Invoke-RestMethod "$baseDemo/usuarios/$usuarioDemo/memorias?consulta=Campinas&k=5" -Headers $cabecalhoDemo
Conversar-Demo "Em que cidade moro? Responda apenas a cidade ou DESCONHECIDO." | Format-List resposta,memorias_usadas
Invoke-RestMethod -Method Delete -Uri "$baseDemo/usuarios/$usuarioDemo/memorias" -Headers $cabecalhoDemo
Invoke-RestMethod "$baseDemo/usuarios/$usuarioDemo/memorias?consulta=Campinas&k=5" -Headers $cabecalhoDemo
Conversar-Demo "Em que cidade moro? Responda apenas a cidade ou DESCONHECIDO." | Format-List resposta,memorias_usadas
```

Para mostrar o erro de autenticação, fazer somente GET sem credencial ao mesmo recurso protegido e mostrar status/corpo público, sem dump de objetos de requisição. Não induzir falha externa cara nem usar chave OpenAI real no vídeo.

Os retornos esperados são critérios para conferir: nova sessão preserva o fato, atualização muda a memória ativa, reinício preserva o registro e exclusão total deixa busca vazia. Resposta ideal após exclusão é `DESCONHECIDO`; se o modelo produzir outra resposta, registrá-la como falha. O número de registros removidos deve ser lido da execução, inclusive registros substituídos, e não preenchido antecipadamente.

## 5. Limites e material para entregar

- A cena usa **exclusão total**. Não apresentar DELETE individual como resolvido: a API ainda não invalida o histórico nesse caminho; a PR #41 documenta o problema e testes do mecanismo de reset.
- O reinício real observado no vídeo é evidência de demonstração. Checkpoints P6 requerem snapshots, identidade do processo/ambiente, escopo e aprovação próprios; o vídeo sozinho não os fornece.
- A comparação entre modelos/provedores, a rodada P6 e a observação completa de RAM não foram feitas neste roteiro. Não inserir percentuais fictícios em legendas.
- Guardar vídeo íntegro de 3–5 minutos, commit/tag, data/hora/fuso, logs reais e vínculo no índice. Não substituir o log histórico de 05/11.
- Zeck prepara narração, inspeção de resultados e revisão de privacidade; Paloma confirma ambiente/persistência; Vinicius revisa o significado de atualizar e esquecer. A equipe grava e revisa o material antes da publicação.
