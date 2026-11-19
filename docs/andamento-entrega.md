# Integração da entrega — 14/11/2026

**Estado atual em 18/11 — v3:** avaliação, PDF, composição de três integrantes e MIT estão no [checklist atual](checklist-entrega.md) e [índice](../evidencias/entrega-v3-20261118/README.md). O restante preserva o histórico de 14/11, inclusive pendências e números superados. Não usar a matriz histórica como estado atual.

Branch `fix/validacao-entrega-docker`, base `2be5d51`. Master remota conferida com `git ls-remote`: mesma referência. Trabalho anterior preservado. Enunciado original lido em `reference/Projetos-IA-Programacao-Enunciados.md`, versão de 09/10/2026; não foi encontrada orientação posterior na pasta local nem nos itens recentes do repositório consultados. As PRs #41/#42/#43 estão integradas; suas descrições históricas não são pendências atuais.

| Origem/requisito | Implementação e teste | Evidência | Estado inicial/próximo passo |
|---|---|---|---|
| Professor: serviço de memória integrado a chatbot | API e guarda de suporte já existentes | Relatório Docker e 65 verificações reais anteriores | Preservar; integrar chat |
| Usuário: reaproveitar interface existente | Worktree `feature/interface-instalacao`, sobre `fc759f3`, com alterações preparadas | Inspeção de diferenças; fonte preservada | Conciliar somente a interface com API atual; não copiar main.py antigo |
| Professor: execução com um comando, custo zero | Docker API existente depende de Ollama do host e tokens manuais | Manual anterior | Automatizar Ollama/modelo/credenciais em volumes próprios |
| Professor: continuidade em 20 sessões, atualização, esquecimento | Executor P6 e 21 anotações estruturais | Guia/plano P6 | Contratos/revisões/evidências ainda bloqueiam rodada real |
| Professor: tokens/sessão versus histórico | P3/P6 existentes | Resultados históricos preservados | Critérios do usuário definidos antes do comparativo |
| Usuário: redução ≥30%, perda ≤5 p.p., nenhum novo vazamento/desatualização | Critérios aprovados pelo usuário na conversa | `criterios-avaliacao-final.md` | Não são limites impostos pelo professor; não equivalem a revisão da equipe |
| Professor: apagar todas as memórias | DELETE total e testes existentes | SQLite/HTTP anteriores | Acrescentar observação RAM somente leitura no processo real |
| Professor: manual com capturas | Interface localizada, manual existente | Documentos e capturas históricas diferenciados | Inspeção visual nova e percurso completo |
| Professor: PDF ABNT, 12–20 páginas textuais, ≥8 referências, ≥4 primárias | Contribuição Markdown existente | Fontes e resultados históricos | Preparar PDF com pendências experimentais explícitas |
| Professor: testes, lint, CI/tag v1.0, vídeo e revisão humana | CI atual tem pytest; sem tag/vídeo final nesta etapa | Workflow e histórico Git | Completar verificações locais; preparar publicação sem executar |

Etapas previstas: (1) enunciado/matriz; (2) integração do chat; (3) inicialização automática; (4) ensaio real/visual; (5) observação RAM; (6) materiais de revisão experimental; (7) avaliação somente quando liberada; (8) documentação/artefatos e plano de publicação. Registrar abaixo os resultados efetivamente obtidos em cada etapa.

Decisões que precisam da equipe não serão substituídas por `aprovado: true`. Não enviar mensagens a terceiros, publicar, criar commits/PR/tag ou alterar os resultados históricos.

## Etapas realizadas

1. Enunciado e situação atual conferidos. Os limites de 30%/5 p.p./nenhum novo vazamento ou desatualização foram aprovados pelo usuário antes de qualquer rodada confirmatória, em `criterios-avaliacao-final.md`.
2. Interface reaproveitada manualmente, preservando o worktree de origem e o reset da PR #43. Inclui conversa, nova sessão, busca, exclusão por ID e total, perfis sintéticos separados, leitor de relatórios. A execução do comparativo pela UI fica desligada por padrão.
3. `Iniciar.ps1` agora precisa somente do Docker em execução: prepara Ollama 0.40.12 fixado por digest, baixa `qwen2.5-coder:3b`, confirma carregamento, gera credenciais aleatórias em volume privado e abre o chat. O padrão `docker compose --env-file .env.example up --build` também sobe a pilha. Nenhum `.env` ou Ollama do host foi alterado. O primeiro ensaio criou volume de modelos vazio e baixou a camada de 1.929.903.072 bytes; a imagem/dependências Python usaram cache nessa primeira subida.
4. Chromium isolado/Playwright exercitou o fluxo real: **51 verificações aprovadas**, incluindo identidade persistente após reinício real, novo/antigo fato, exclusões com contratos distintos, abstenção, conversa geral e suporte atual/histórico, isolamento, modelo ausente, Ollama parado e cookie removido. Capturas em `../evidencias/entrega/20261114-entrega-ae9eb113/r02-*.png`. O primeiro teste de navegador foi interrompido por esperar visibilidade de um `<option>`; corrigida a espera para presença, preservando `r01-interface.jsonl`. A ferramenta Computer Use não iniciou (runtime Node, caminho não encontrado); a inspeção visual foi feita nos PNG reais do Chromium, em desktop e mobile.
5. Observador RAM opt-in implementado no processo que atende a API, desligado por padrão. Antes do reinício: 7 mensagens totais, 6 pessoais, 4 com alvos. Depois do DELETE individual: 1 mensagem de sistema, 0 pessoais/alvos. Depois da pergunta de abstenção: 3 totais, 2 pessoais legítimas, 0 alvos. O histórico de B permaneceu com 3 mensagens ao excluir A. Instância/processo/timestamps e snapshots SQLite estão em `r02-interface.jsonl`; a leitura de um histórico ausente não o cria. Um único worker foi configurado no ensaio. Correspondência é literal normalizada, sem certificação jurídica/semântica geral.

Evidências novas desta integração: `../evidencias/entrega/20261114-entrega-ae9eb113/`. Nenhuma P6 ou conjunto reservado foi executado. A extensão de metadados opcionais foi autorizada e implementada, preservando resultados antigos. Apenas origem local e zero explícito permitem derivar zero de geração.

## Matriz final desta etapa

Complemento do caminho padrão: `Iniciar.ps1` foi executado realmente com logs redirecionados. Duas falhas do tratamento nativo no PowerShell 5 foram corrigidas e a terceira tentativa concluiu. Navegador confirmou acesso sem token e seis respostas corretas posteriores. A tentativa r05 anterior respondeu 4 para 2 + 3; captura e interrupção preservadas, sem considerar isso falha de instalação nem apagar o erro do modelo. O ensaio de seis respostas não é avaliação estatística.

As linhas anteriores registram o ponto de partida e o primeiro ensaio. Estado consolidado:

| Requisito/origem | Implementação e procedimento | Evidência | Pendência |
|---|---|---|---|
| Professor: Docker e custo zero | Ollama/preparo/API; volume inicialmente sem pesos; build posterior sem cache Python | `primeira-inicializacao.json`, logs iniciais e `build-frio-final.log` | Não equivale a SO recém-instalado; recursos variam |
| Usuário: chat sem copiar tokens | Cookie HttpOnly, credenciais privadas, perfis sintéticos A/B; reinício real | `r04-interface.jsonl` e capturas r04 | Demonstração somente local; revisão da equipe |
| Tema 11: recuperação e atualização | Salvar, nova sessão, atualizar e nova sessão; API/regras/SQLite reais | r04 e snapshots SQLite somente leitura | Cobertura linguística limitada |
| Tema 11: persistência | Reinício real, mesma identidade e valor atualizado nos volumes | r04 com instâncias antes/depois | Vincular checkpoints específicos da P6 |
| Tema 11: esquecimento | DELETE individual preserva versão inativa; total remove todas A; B preservado | r04, SQLite e RAM real | Não certifica toda RAM/semântica |
| Usuário: observar RAM real | Endpoint opt-in somente leitura, desligado por padrão; um worker | r02/r04 com PID, instância, timestamps, sistema/pessoais/alvos | Não cobre múltiplos workers nem buffers externos |
| Usuário: abstenção e conversa comum | Guarda limitada; provedor para gerais e suporte | 65 verificações históricas e 80 verificações r04 | Outras formas pessoais falharam no comparativo; não resolvida universalmente |
| Professor: tokens/qualidade | P3/P4/P5 com proveniência, 7 casos de desenvolvimento ×3×4 reais | [Relatório](ensaio-desenvolvimento-20261114.md), JSON e figuras | Automática aumentou tokens 6,72%; meta adicional ≥30% não atingida |
| Tema 11: 20 sessões | Executor existente, dados oficiais preservados; preparação estrutural | [Revisão experimental](revisao-experimental/README.md) | Receber referência da revisão; decidir vazio; aprovar anotações/metadados |
| Professor: pesquisa 12–20 páginas textuais; 8 fontes/4 primárias | A4, Times 12, 1,5; 14 páginas textuais, 22 totais, 11 referências; render de todas as páginas | `pesquisa-geracao.json`; [rascunho](pesquisa-abnt.pdf) | Instituição/cidade/docente, composição 3×4 e revisão coletiva |
| Professor: manual/capturas/vídeo | [Manual](manual-professor.md), PNG desktop/mobile e [roteiro](roteiro-demonstracao.md) | r04 PNG; r03 falha API | Vídeo oficial não gravado |
| Professor: falhas e correções | Tentativas intermediárias preservadas; falhas de modelo, conexão, autenticação e linguagem | r01/r03, logs e CSV com 22 falhas de conteúdo | Não esconder negativos |
| Professor: testes/lint/CI/tag | 897 Python aprovados/66 ignorados, 8 JS e lint; workflow com gatilho `v1.0` preparado | Logs desta etapa | CI remoto/tag `v1.0` não executados |
| Professor: licença/equipe/revisão/envio | Registro de IA e plano de publicação | `PROMPTS.md`, checklist | LICENSE do projeto não definido; composição do grupo; licença Qwen Research |

O comparativo executou 84 tentativas sem falhas técnicas e teve 22 falhas de conteúdo. Não é P6 nem confirmação de equivalência. A primeira tentativa da suíte teve 212 erros de preparação por acesso negado ao temporário global; com `--basetemp` próprio passou, com um aviso de cache. Ambos os logs foram preservados. A rodada final no navegador teve 80 aprovações e zero falhas; isso não elimina falhas de linguagem dos outros casos.

Etapas 1–5 concluídas no escopo descrito; etapa 6 preparada aguardando referência de revisão humana; etapa 7 somente exploratória; etapa 8 com rascunho/roteiro, sem vídeo/submissão/CI/tag. **Entrega integral ainda não pronta.** Ver [ordem de revisão/publicação](checklist-entrega.md).
