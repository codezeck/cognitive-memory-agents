# Histórico individual — Vinicius — Cognitive Memory Agents

**Projeto:** Cognitive Memory Agents — Tema 11: Memória de longo prazo para agentes de IA  
**Repositório:** https://github.com/codezeck/cognitive-memory-agents  
**Data desta organização documental:** 22/11/2026  
**Método:** consolidação de registros fornecidos pelos integrantes, sem reexecutar testes, sem modificar o repositório e sem atribuir autoria apenas pelo merge de um PR.

As datas exatas são preservadas quando aparecem nas fontes. Resultados históricos, dados simulados, medições reais, relatos e planos não são intercambiáveis. As fontes completas foram preservadas em apêndice para que a síntese não substitua o registro original. A classificação "aceito" significa decisão/uso documentado, não aprovação automática de cada saída da IA.


## Responsabilidade e limites

Vinicius desenvolveu o contrato de memória de longo prazo, memória em RAM, estratégias de recuperação, regras para fatos/atualizações/contradições/esquecimento, dados sintéticos, benchmark e anotações P6. Paloma é responsável pela API e armazenamento operacional; Ezequiel integra modelos, executor e avaliação do agente. O merge por outro integrante não altera a autoria da implementação inicial.

## Linha do tempo consolidada

| Data/período | Desenvolvimento/decisão | Evidência ou ressalva |
|---|---|---|
| 25/10 | Contrato `MemoriaLongoPrazo`, armazenamento em RAM e recuperação lexical; 14 novos testes, 34 totais após correção de arquivos inicialmente vazios. | História Claude e PRs #5/#10 citadas nos documentos. |
| 25–27/10 | Dataset com quatro usuários, cinco sessões cada, 21 perguntas; correção de arquivo enviado que só continha exemplo; avaliador/benchmark sintético sem modelo. | Dados de desenvolvimento; não prova de 21 respostas LLM corretas. |
| 27/10–04/11 | Embedder semântico com Python 3.12 após incompatibilidade no 3.15; incidente de `.venv312` no Git, reparado na própria branch; baseline por regras. | Resultados por palavras 71,4% e semântico 100% (21/21) são **recuperação sintética**, não qualidade global do chatbot. |
| Fim de outubro–início de novembro | `regras.py`, `gerenciador.py`, conjuntos de desenvolvimento/avaliação, gestão de conflitos e esquecimento; testes e documentação das limitações. | Avaliação final de regras: 62% por frase; precisão 89,3%; recall 58,1%; F1 70,4%, segundo histórico do Claude. |
| 01–04/11 | Revisões de contrato, índice e persistência conforme implementação de API dos colegas; documentação de divergências e correções. | Parte de sugestões foi revisada ou descartada por já estar na `master`. |
| 10/11 | Anotações de 21 perguntas P6 e relatório de compatibilidade do julgador P4 (10 compatíveis/11 incompatíveis naquele momento). | PR #40 / `6af33c1`, merge `fc759f3`; compatibilidade antiga não representa situação posterior do P4. |
| 12–13/11 | Revisão das mudanças da `master`: suporte de novos atributos, `DELETE`/histórico e repercussões no contrato. | Registros mostram necessidade de reconferir mudanças recentes; não declarar aprovações não documentadas. |

## Alertas e correções que devem permanecer no histórico

- Os dois fatos que continham termos proibidos provocavam falso erro no benchmark; corrigiu-se o dataset antes de reavaliar. **Foi corrigido o experimento, não comprovada uma falha do agente.**
- O dataset `u03/s4/pergunta3` exigia contar gatos, não reproduzir nomes, e o cenário `u02/s5/esquecer_chaves` demandava mensagem/contrato aprovado.
- Houve relato de `45 passed` após correção versus `37 passed / 8 failed` antes dela, sem somar essas execuções.
- Resultados de `MemoriaEmRam`, regras, SQLite e respostas reais de LLM precisam ser relatados em camadas distintas.

## Fontes originais preservadas

### Apêndice A — Histórico do Projeto Integrador (resumo)

# Histórico do Projeto Integrador — Cognitive Memory Agents

**Período documentado:** outubro a novembro de 2026  
**Repositório:** https://github.com/codezeck/cognitive-memory-agents  
**Natureza do registro:** resumo consolidado das conversas e dos resultados compartilhados; não é transcrição integral de todos os chats.

## 1. Objetivo do projeto

Desenvolver um chatbot com memória de longo prazo capaz de guardar informações, recuperá-las entre sessões, atualizar fatos corrigidos, esquecer informações sob solicitação, isolar os dados de usuários diferentes e reconhecer quando não há informação suficiente para responder.

## 2. Responsabilidades atribuídas

1. **Lógica da memória:** revisar regras de salvar, atualizar e esquecer, além de persistência e isolamento.
2. **Dados sintéticos:** conferir cenários e sessões de avaliação.
3. **Revisão das anotações:** preparar e validar respostas esperadas, critérios e evidências da avaliação P6.

Durante as revisões, foi adotado o procedimento de executar **um comando PowerShell por vez**, analisar o resultado e avançar sem alterar código de outros colaboradores. A orientação foi não modificar arquivos, fazer merge ou trocar de branch sem autorização.

## 3. Ambiente e primeiras revisões

O repositório já estava baixado no VS Code, no diretório `C:\Projeto Integrador`. Houve tentativa de usar Codex no VS Code, mas foram encontrados erros de inicialização e autenticação (`401 Unauthorized`); a revisão continuou diretamente no chat.

Foram examinados branches, commits, pull requests, evidências de testes e arquivos de implementação. Em uma revisão das evidências do módulo de memória, os resultados apresentados foram:

- **Após a correção:** 45 testes aprovados.
- **Antes da correção:** 37 aprovados e 8 falhas.

Esses resultados foram usados para demonstrar a diferença de comportamento antes e depois da correção.

## 4. Revisão da lógica da memória

Arquivos consultados, entre outros:

- `src/memoria/regras.py` — extração de decisões a partir das mensagens.
- `src/memoria/gerenciador.py` — aplicação das decisões.
- `src/memoria/store_mem.py` — armazenamento em RAM.
- `src/armazenamento/repositorio.py` — persistência SQLite.
- `src/armazenamento/banco.py` — configuração do banco.
- `src/api/dependencias.py` — integração com a API.
- `tests/test_gerenciador_regras.py` e testes de contrato, persistência e API.

Foram avaliados atualização de fatos, não duplicação, negações, esquecimento, remoção de histórico, exclusão de usuário, isolamento entre usuários e recuperação do estado após reinicialização.

**Resultados de testes informados:** execução geral com **695 aprovados e 1 ignorado**; testes específicos do gerenciador com **23 aprovados**; teste de persistência SQLite após reinício com **1 aprovado**.

**Observação técnica:** quando uma chave tinha apenas histórico inativo e um novo fato era salvo, o efeito retornado podia ser `atualizado` em vez de `salvo`. O novo valor era armazenado corretamente. A documentação não estabelecia explicitamente o rótulo esperado nesse cenário, de modo que a diferença foi tratada como observação ou lacuna de cobertura, e não como falha comprovada.

## 5. Dados sintéticos P6

Arquivo: `eval/memoria/sessoes.json`.

Foram revisados **4 usuários sintéticos**, **20 sessões** (5 por usuário) e **21 perguntas de avaliação**.

- **u01:** alterações de cidade, profissão e esporte; referência ao cachorro Thor.
- **u02:** quantidade de filhos, troca de carro Gol → Onix, esquecimento do carro, time e profissão.
- **u03:** cidade Recife, gatos Luna e Simba, fotografia, viagem Japão → Portugal, mudança profissional.
- **u04:** mudança de cidade e profissão, instrumento musical, exclusão integral do usuário na sessão 4 e novos dados na sessão 5.

O cenário `u04` foi importante para verificar que dados anteriores à exclusão não deveriam reaparecer.

## 6. Anotações e relatório P6

Arquivos entregues:

- `eval/memoria/anotacoes_p6.json`
- `eval/memoria/relatorio_revisao_p6.md`

As **21 anotações** foram revisadas. O relatório registrava compatibilidade com o avaliador P4 anterior:

| Situação | Quantidade |
|---|---:|
| Compatíveis | 10 |
| Incompatíveis | 11 |
| Ausentes | 0 |
| Total | 21 |

A incompatibilidade ocorria porque o avaliador P4 reconhecia somente atributos como `cidade`, `esporte`, `carro`, `nome` e `time`, enquanto as anotações P6 também usavam `profissao`, `pet`, `filhos`, `disciplina`, `hobby`, `viagem`, `quantidade_pets` e `instrumento`.

### Pendências registradas

1. **u03, sessão 4, pergunta 3:** a pergunta “Quantos gatos eu tenho?” solicitava quantidade; o dataset indicava os nomes `Luna` e `Simba`, enquanto a anotação esperava `dois` / `2`. A divergência precisava ser alinhada com a equipe antes de qualquer alteração.
2. **u02, sessão 5, esquecimento do carro:** a execução real exigia aprovação e referência do cenário de esquecimento. Não se deveria tratar uma referência fictícia como aprovação real.

Foi verificado que o julgador reconhecia os termos esquecidos para penalizar respostas que revelassem fatos proibidos, mesmo quando a lista explícita `informacoes_proibidas` estivesse vazia na anotação correspondente.

## 7. Entrega ao repositório

A contribuição foi preparada na branch `feature/anotacoes-p6`:

- Commit `6af33c1` — `docs(p6): adicionar anotacoes e relatorio de revisao`.
- Pull request **#40**, incorporado à `master` no merge `fc759f3`, em **10/11/2026**.

Isso confirmou a incorporação dos arquivos de anotações e do relatório à branch principal naquele momento.

## 8. Comparação de branches antigas

Foram verificadas branches remotas que ainda apareciam como não incorporadas à `master`:

| Branch | Último commit | Data |
|---|---|---|
| `feature/memoria-avaliacao` | `02d9522` | 26/10/2026 |
| `feature/memoria-benchmark` | `2d98abd` | 25/10/2026 |
| `feature/memoria-longo-prazo` | `cfc6c01` | 25/10/2026 |
| `feature/memoria-regras` | `4c97d13` | 29/10/2026 |

A comparação de `feature/memoria-regras` com a `master` revelou diferenças em `base.py`, `chaves.py`, `gerenciador.py`, `sqlite_chaves.py`, `store_mem.py` e testes.

A branch antiga utilizava uma interface de memória com operações diretas como `listar()` e `esquecer_por_chave()`, sem índice interno do gerenciador. A `master` reconstruía seu índice a cada chamada a partir dos registros da memória.

Os testes da branch antiga cobriam cenários relevantes, mas vários já estavam representados na versão atual. **Conclusão da revisão:** não havia justificativa comprovada para incorporar a branch antiga ou substituir a implementação atual.

## 9. Documentação das regras

Foi lido `docs/regras-memoria.md`, que documentava:

1. Mesma chave com valor diferente substitui o fato anterior.
2. Mesmo valor, ignorando acentos e maiúsculas, não duplica.
3. Negação de fato antigo não apaga um valor atual diferente.
4. Esquecimento de tópico também remove o histórico substituído.
5. Em uma mesma mensagem, prevalece a última afirmação.
6. Apagar usuário remove seus dados sem afetar outros usuários.

Os testes executados apoiavam a conclusão de que os principais comportamentos estavam implementados. A diferença de classificação `salvo`/`atualizado` permaneceu apenas como observação técnica.

## 10. Novas atualizações identificadas no GitHub

Após a revisão anterior, foi executado:

```powershell
git fetch origin
git log --all --since="2026-11-10" --date=short --format="%ad | %h | %s" --name-only
```

O `fetch` mostrou avanço da branch remota `master` de `fc759f3` para **`2be5d51`** e três novas branches remotas:

- `docs/preparacao-academica-zeck`
- `feature/conclusao-avaliacao-p6`
- `fix/delete-limpa-historico`

Commits e merges identificados:

| Data | Commit | Descrição |
|---|---|---|
| 13/11/2026 | `2be5d51` | Merge PR #43 — correção do DELETE e histórico |
| 13/11/2026 | `b5c7234` | Merge PR #41 — conclusão da avaliação P6 |
| 13/11/2026 | `2c06d6d` | Merge PR #42 — preparação acadêmica |
| 13/11/2026 | `b3841fa` | API: DELETE de uma memória também zera o histórico da conversa |
| 12/11/2026 | `3d677d4` | Documentação acadêmica e plano de avaliação P6 |
| 12/11/2026 | `29d1255` | Ampliação do julgador P4 para P6 e tratamento de respostas vazias dos provedores |
| 10/11/2026 | `fc759f3` | Merge PR #40 — anotações P6 |
| 10/11/2026 | `6af33c1` | Adição das anotações e relatório de revisão |

### Impacto potencial nas responsabilidades

**Lógica da memória:** o commit `b3841fa` alterou `src/api/main.py` e `tests/test_api.py` para tratar a limpeza do histórico da conversa na exclusão de uma memória. Era recomendável verificar a interação dessa correção com o esquecimento e a possibilidade de reaparecimento de informações.

**Dados sintéticos:** na listagem apresentada, não houve alteração recente de `eval/memoria/sessoes.json`.

**Anotações e avaliação P6:** o commit `29d1255` alterou `eval/julgamento_respostas.py` e testes de avaliação, possivelmente solucionando incompatibilidades anteriormente registradas entre os atributos P4 e P6. Isso ainda precisava ser confirmado com inspeção do código atualizado.

O próximo comando sugerido, **ainda sem resultado apresentado**, foi:

```powershell
git show origin/master:eval/julgamento_respostas.py | Select-String -Pattern "ATRIBUTOS|profissao|pet|filhos|disciplina|hobby|viagem|quantidade_pets|instrumento" -Context 2,4
```

## 11. Situação ao final do histórico disponível

| Responsabilidade | Estado conhecido |
|---|---|
| Lógica da memória | Revisão anterior concluída; conferir impacto do DELETE recente |
| Dados sintéticos | 20 sessões e 21 perguntas revisadas; nenhuma mudança recente identificada na listagem de commits |
| Revisão das anotações | 21 anotações entregues; conferir suporte P6 no julgador atualizado |
| Evidências e documentação | Arquivos entregues e incorporados via PR #40 |
| Pendências de equipe | Alinhar pergunta sobre quantidade de gatos e aprovação do cenário real de esquecimento |

**Importante:** o histórico acima termina nos resultados do Git compartilhados na conversa. Não há confirmação posterior, neste registro, de que as novas verificações P6 ou da correção do DELETE tenham sido executadas.


---

### Apêndice B — Histórico da conversa com Claude (cronologia de prompts)

# Histórico da conversa com o Claude: Projeto Integrador (Tema 11)

**Projeto:** Cognitive Memory Agents (memória de longo prazo para agentes de IA)
**Integrante:** Vinicius (lógica da memória)
**Colegas:** Ezequiel (agente e modelos) e Paloma (API)
**Repositório:** codezeck/cognitive-memory-agents

## Como ler este arquivo

- **Isto não é a transcrição literal.** A conversa tem dezenas de trocas, com saídas de terminal muito longas e vários arquivos gerados. Aqui está um **registro resumido e cronológico**. As aspas indicam trechos **copiados** de mensagens suas; todo o resto é resumo.
- Cada entrada segue o formato que o enunciado pede para o `PROMPTS.md`: **pedido**, **resposta (resumo)** e **resultado** (aceito, corrigido ou descartado).
- Foram omitidos e-mails, caminhos de pastas pessoais e saídas de terminal longas.
- **Revise antes de entregar.** O resumo foi escrito pelo Claude a partir do histórico. O que entra no `PROMPTS.md` oficial deve ser conferido por você, porque o enunciado cobra que você explique o que usou e o que aceitou.
- As datas só aparecem onde o histórico do Git ou das mensagens as mostra: o primeiro commit é de 25/10/2026, o PR #17 foi mergeado em 27/10, o PR #23 em 01/11 e o último download de script em 04/11.

---

## Fase 1: ambiente e leitura do projeto

### 1. Configurar o ambiente
- **Pedido:** contexto do trabalho do Tema 11, a divisão do grupo em três (Ezequiel: agente e integração com modelos; Vinicius: memória de longo prazo; Paloma: API), o print do VS Code e o link do repositório. Fechou com "me ajude a configurar o ambiente".
- **Resposta:** o Claude leu o enunciado enviado e tentou abrir o repositório. A página pública que conseguiu ver estava desatualizada (poucos commits e arquivos vazios). Passou instalação de Git, Python, Docker e Ollama, clone, ambiente virtual e um esboço de PostgreSQL com pgvector.
- **Resultado:** **corrigido.** Você avisou em seguida que não usaria Ollama e precisava seguir o que o grupo já tinha feito. O plano de PostgreSQL ficou de lado mais tarde, porque o time já usava SQLite.

### 2. Sem Ollama, seguir as atualizações do projeto
- **Pedido:** "lembrando que eu não vou utilizar ollama, e preciso seguir com as atualizações que já foram feitas no projeto, preciso clonar o repositório e trabalhar na minha area".
- **Resposta:** comandos de clone e de `git fetch`, como ver os PRs e as branches, e alternativas de embeddings sem Ollama (`fastembed` ou `sentence-transformers`).
- **Resultado:** **aceito.**

### 3. Leitura das branches e do contrato do agente
- **Pedido:** você colou `git branch -a`, `git log`, `git grep` em `src/agent.py` e depois o código do agente, o README e o `requirements.txt` da branch `camada-modelos`.
- **Resposta:** só existiam branches do Ezequiel (`agente-ollama`, `camada-modelos`), uma `docs/readme-projeto` e uma `api-armazenamento` vazia. O agente recebe as memórias já prontas em `responder(mensagem, usuario_id, memorias)`, aceitando texto ou dicionário com a chave `"texto"`. O Claude propôs uma interface `MemoriaLongoPrazo` com salvar, buscar, atualizar, esquecer e esquecer usuário. Avisou que o `requirements.txt` estava em UTF-16 e com linhas repetidas.
- **Resultado:** **aceito.** A interface virou `src/memoria/base.py`.

### 4. Erro de política de execução do PowerShell
- **Pedido:** a ativação do ambiente virtual falhou com "execução de scripts desabilitada".
- **Resposta:** `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, ou chamar o Python do ambiente direto.
- **Resultado:** **aceito.**

### 5. Primeira entrega de código
- **Resposta:** o Claude escreveu `base.py`, `embeddings.py` (embedder por palavras), `store_mem.py` (memória em RAM) e 14 testes, e validou a lógica no ambiente dele.
- **Resultado:** **corrigido.** Seus quatro arquivos chegaram **vazios** (não tinham sido salvos no VS Code). O Claude reenviou o conteúdo inline, e depois disso passaram os 34 testes (20 do time mais 14 novos). O PR foi aprovado por outro integrante.

---

## Fase 2: integração com o time e a master

### 6. "O que já foi feito e o que falta"
- **Pedido:** "DENTRO DAS MINHAS OBRIGAÇÕES O QUE JA FOI FEITO E O QUE AINDA PRECISO FAZER".
- **Resposta:** quadro das quatro responsabilidades (persistência, recuperação, atualização e contradições, dados sintéticos), com o estado de cada uma e os marcos do enunciado.
- **Resultado:** **aceito.**

### 7. PROMPTS no fim e ordem de trabalho
- **Pedido:** "os promts serao entregues no fim com todas as interações [...]" e que a parte da Paloma ainda não tinha alterações.
- **Resposta:** o Claude concordou em deixar o `PROMPTS.md` para o fim, sugeriu guardar o histórico e propôs: fechar o avaliador, embedder semântico, persistência, integração.
- **Resultado:** **aceito.**

### 8. Master reescrita pelo dono do repositório
- **Pedido:** você colou o `git fetch` e o `git log` mostrando `forced update` na `master` e o erro `no merge base`.
- **Resposta:** o Claude explicou que o histórico foi reescrito (mesmos commits, hashes novos) e que o seu PR #10 já estava dentro. Recomendou `git checkout -B master origin/master` e não fazer `merge` nem `push --force` na master. Mais tarde o dono confirmou que a reescrita corrigiu um erro de commit.
- **Resultado:** **aceito.**

### 9. "Quero fazer minha parte sem interferir"
- **Pedido:** continuar só a sua parte, sem mexer nos arquivos da Paloma e do Ezequiel.
- **Resposta:** quadro de donos por pasta e regras: criar só arquivos novos, usar os arquivos deles apenas para leitura, evitar `git add .`.
- **Resultado:** **aceito.**

### 10. Benchmark sintético de 20 sessões
- **Pedido:** "me passa o proximo passo".
- **Resposta:** formato de `sessoes.json` com um exemplo. O arquivo que você enviou ao GitHub tinha só 694 bytes e 36 linhas, ou seja, o próprio exemplo. O Claude notou o tamanho do `push` e pediu para conferir. Depois escreveu o benchmark completo: 4 usuários fictícios, 5 sessões cada e 21 perguntas (fatos que mudam, paráfrases, esquecimento, apagar usuário, recomeço e isolamento).
- **Resultado:** **corrigido.** O arquivo foi substituído pelo completo, e o PR foi revisado por outro membro.

### 11. Revisão cruzada do PR
- **Pedido:** "mais o PR nao deve ser validado por outro colaborador pelas regras do projeto ?"
- **Resposta:** o Claude confirmou a regra do enunciado (ninguém aprova o próprio PR) e reconheceu que tinha dito apenas "abra o PR". Passou a descrição do PR e a sugestão de proteção da `master`.
- **Resultado:** **aceito.**

---

## Fase 3: avaliador, embedder semântico e incidentes

### 12. Avaliador do benchmark
- **Resposta:** `src/memoria/benchmark.py`, `eval/avaliar_memoria.py` e 8 testes. Mede acerto geral, lembranças corretas, informação desatualizada devolvida, esquecimento correto e tokens (estimados em 1 token para cada 4 caracteres), sem chamar modelo de linguagem.
- **Resultado:** **aceito.**

### 13. Embedder semântico e Python 3.15
- **Pedido:** rodar `pip install fastembed --dry-run`.
- **Resposta:** o `fastembed` depende do `onnxruntime`, que não tinha pacote para o Python 3.15 no Windows. Solução: um segundo ambiente (`.venv312`) com Python 3.12, fora do Git (regra em `.git/info/exclude`).
- **Resultado:** **aceito.** Depois houve erros de arquivos que não tinham sido criados, e o `--embedder semantico` foi recusado porque o `avaliar_memoria.py` era a versão antiga. Foi corrigido trocando o dicionário `EMBEDDERS`.

### 14. Incidente: `.venv312` foi para o Git
- **Pedido:** você colou um `git push` com 3.836 objetos e 23 MB.
- **Resposta:** o Claude identificou que o `git add` levou a pasta do ambiente virtual. Conferiu que a `master` estava limpa (contagem 0) e orientou `git reset --soft HEAD~1`, `git rm -r --cached .venv312`, regra de exclusão local e `git push --force-with-lease` só na sua branch. Depois explicou "de forma simples" o que cada comando faz e os dois cuidados: nunca `git add .` e nunca force em branch alheia.
- **Resultado:** **aceito.** O novo `push` teve 12 objetos e 3 KB.

### 15. Editor vim no merge
- **Resposta:** `Esc`, `:wq`, `Enter`; configurar `core.editor` para o VS Code. Merge sem conflito, 70 testes passando.
- **Resultado:** **aceito.**

### 16. Defeito do benchmark descoberto na análise de erros
- **Contexto:** o resultado semântico foi 90,5% e restavam duas perguntas erradas.
- **Resposta:** o Claude viu que dois fatos atualizados continham o termo proibido da própria pergunta (por exemplo, "Troquei a corrida pela natação" tinha "corrida", proibida). Era **erro dele ao escrever o benchmark**, não da memória. Os fatos foram reescritos e os dois embedders foram reavaliados.
- **Resultado:** **corrigido.** Resultados depois da correção: por palavras 71,4%; semântico 100% (21 de 21). O Claude também pediu que isso conste no trabalho como transparência.

---

## Fase 4: regras de memória, integração e contrato

### 17. Novas obrigações (checklist de 7 itens)
- **Pedido:** a lista com revisar regras de extração, 5 conversas sintéticas, baseline por regras, conflitos e atualizações, 100 casos de teste, separar dados de desenvolvimento e de avaliação, e documentar falhas. Depois colou o texto "Vinicius — lógica da memória".
- **Resposta:** o Claude mapeou o checklist ao que existia, notou que não havia regras de extração no repositório e passou a construí-las.
- **Resultado:** **aceito.**

### 18. Baseline por regras, dados e testes
- **Resposta:** `regras.py`, `gerenciador.py`, `avaliacao_regras.py`, `eval/avaliar_regras.py`, 149 frases e 6 conversas de desenvolvimento, 50 frases e 4 conversas de avaliação final, três arquivos de teste e dois documentos. Política de conflitos (substitui por chave, não duplica, negação só apaga se o valor atual coincide, esquecer apaga o histórico, apagar usuário remove tudo). O teste de separação encontrou 4 frases repetidas entre os conjuntos, que foram trocadas **antes** de rodar a avaliação final. Resultado: desenvolvimento 100%; avaliação final 62,0% de exatidão por frase, precisão 89,3%, revocação 58,1%, F1 70,4%, conversas 9 de 13.
- **Resultado:** **aceito**, com ressalva registrada: os dois conjuntos foram escritos pela mesma pessoa que escreveu as regras.

### 19. Aplicar tudo por PowerShell
- **Pedido:** "quero que todas as alterações sejam executadas pelo powershell".
- **Resposta:** scripts `.ps1` com o conteúdo embutido e conferência por hash.
- **Resultado:** **corrigido.** A primeira versão deu `[ATENCAO]` em todos os 13 arquivos: faltava 1 byte em cada um (a quebra de linha final que o PowerShell não inclui num bloco `@'...'@`). O Claude calculou os tamanhos, achou a causa e entregou a versão 2, que passou (283 testes).

### 20. Descoberta: persistência e API dos colegas
- **Pedido:** você colou `repositorio.py`, `servico.py` e `dependencias.py`.
- **Resposta:** a `MemoriaSQLite` já implementava a interface da memória, então **PostgreSQL com pgvector foi descartado**. O Claude também apontou que a API não gravava memórias a partir da conversa (hipótese depois **corrigida**: os colegas fizeram essa integração dias depois, e o Claude só viu isso quando você colou o histórico do Git).
- **Resultado:** **aceito** (PostgreSQL descartado); a hipótese sobre a API foi **corrigida**.

### 21. Gerenciador sem estado e testes de contrato
- **Resposta:** como o índice chave para identificadores ficava em RAM e a API mexe na memória por outros caminhos, o Claude propôs `chaves.py` e `sqlite_chaves.py` (métodos `listar` e `esquecer_por_chave`) e um gerenciador sem estado, com testes de contrato rodando na memória em RAM e no SQLite. 327 testes passaram.
- **Resultado:** **descartado depois** (ver 22).

### 22. Conflito do PR e solução dos colegas
- **Pedido:** o PR deu conflito com Ezequiel e Paloma. Você colou `git merge-base`, o log e o `diff --stat`.
- **Resposta:** o Claude viu que o PR #17 (primeira versão das regras) já estava na `master` e que os colegas tinham integrado as regras às conversas e corrigido o índice com `listar_por_usuario`. Pediu os diffs, reconstruiu a `master` no ambiente dele e escreveu testes de contrato para as duas memórias. Antes do ajuste, 8 testes falhavam (4 cenários × 2 memórias): apagar o usuário direto na memória, apagar uma memória pela API e repetir o fato, memória criada à mão com chave e pedido de esquecer pelo chat, e `estado()` com chave sem memória ativa. A correção foi reconstruir o índice a cada mensagem. Na sua máquina: 321 testes antes, 8 falhas nos novos, **366 passando** depois, com a avaliação das regras inalterada. O PR #24 foi mergeado.
- **Resultado:** **aceito**, e a refatoração do item 21 foi **descartada**: o fix da `master` cobre os mesmos cenários, e manter as duas criaria duas formas de fazer a mesma coisa. O PR antigo foi fechado.

### 23. Pasta de evidências
- **Resposta:** o script `coletar_evidencias.ps1` roda testes, avaliações e o "antes e depois" do contrato (em um `git worktree` no commit anterior ao fix) e monta um índice. Nenhum resultado é escrito à mão.
- **Resultado:** **corrigido em duas rodadas.** A primeira versão tinha três defeitos: o PowerShell 5.1 tratava o texto de progresso do `git` como erro, uma precedência de operadores quebrava o final do script (e impedia o `README.md`), e o worktree ia para a raiz do disco. Além disso, você rodou a versão antiga duas vezes por causa de um download antigo. Na versão 2: `05` com 45 passed e `06` com 8 failed, 37 passed, como esperado.

---

## Fase 5: trabalho acadêmico (ABNT)

### 24. Introdução e Referencial Teórico
- **Resposta:** o Claude verificou na internet oito fontes (Liu et al. 2024; Park et al. 2023; Packer et al. 2023; Lewis et al. 2020; Reimers e Gurevych 2019 e 2020; Wu et al. 2025; Chhikara et al. 2025) e a Lei 13.709/2018, e escreveu os capítulos 1 e 2 em um documento. Deixou marcadores `[conferir]` e `[inserir data]`.
- **Resultado:** **aceito com pendência.** O grupo ainda precisa abrir cada referência na fonte original, e o enunciado trata referência inexistente como falta grave.

### 25. Metodologia e Resultados da parte de memória
- **Resposta:** capítulos 3 e 4 (arquitetura, regras, dados, métricas, resultados, falhas e limitações), com números tirados das saídas que você colou. Inclui a declaração de que dois fatos do benchmark foram corrigidos depois de ver o resultado.
- **Resultado:** **aceito com pendência:** conferir cada número contra `evidencias/memoria/` antes de entregar. A classificação das 19 falhas por causa foi feita pelo Claude e deve ser contada por você.

---

## Fase 6: redistribuição de obrigações (P6, Etapa 3)

### 26. Preparar os dados para o P6
- **Pedido:** analisar `eval/memoria/sessoes.json` (4 usuários, 20 sessões, 31 fatos, 21 perguntas), preparar anotações das 21 perguntas, investigar a mensagem de esquecimento de `u02/s5/esquecer_chaves`, validar a continuidade das sessões, e entregar diagnóstico, anotações, proposta de mensagem, inconsistências, casos para revisão humana e dependências da API. Sem alterar o dataset, a API, o armazenamento, o Docker nem os avaliadores, e sem commit antes da revisão.
- **Resposta até agora (em andamento):** o Claude reconstruiu o dataset (as contagens 4, 20, 31 e 21 batem) e rodou as regras atuais sobre os 31 fatos e sobre mensagens candidatas de esquecimento. Achados parciais:
  - `Toco violão.` e `Meu projeto usa Python.` **não geram decisão** nas regras atuais, então o teste de exclusão do violão não prova nada;
  - a lista de proibidos de `u03-q05` não inclui Belém;
  - o dataset não tem mensagem literal para esquecer nem para apagar usuário;
  - `Esqueça meu carro.` e `Esqueça o que eu disse sobre o carro.` são interpretadas pelas regras como esquecer a chave `carro`, mas **isso não é uma mensagem aprovada**, porque as regras foram escritas pelo próprio autor.
- **Resultado:** **pendente.** O relatório e os arquivos propostos ainda não foram apresentados. É preciso confirmar, no commit `b5eec2f`, o hash do dataset, o uso dos campos pelo executor P6, as rotas da API e se existe mensagem de esquecimento já aprovada.

---

## Decisões técnicas tomadas durante a conversa

| Decisão | Motivo | Estado |
|---|---|---|
| Interface `MemoriaLongoPrazo` independente de modelo e banco | o agente já recebe memórias prontas | em uso |
| Memória com `chave` que substitui a anterior e esquecer físico | evitar fato antigo e atender o direito de eliminação (LGPD) | em uso |
| Sem Ollama; embeddings locais com `fastembed` e modelo multilíngue | custo zero e português | em uso, em Python 3.12 |
| PostgreSQL com pgvector | substituído, porque os colegas usam SQLite | descartado |
| Baseline por regras, sem IA | transparência, custo zero e falhas mensuráveis | em uso |
| Dados de desenvolvimento e de avaliação das regras separados | evitar inflar o resultado | em uso, com teste |
| Índice do gerenciador reconstruído a cada mensagem | a API mexe na memória por outros caminhos | em uso (PR #24) |
| Tokens estimados em 1 para cada 4 caracteres | não há contagem real nesta etapa | em uso, como aproximação |

## Erros do Claude que foram corrigidos durante a conversa

- Afirmou que a API ainda não gravava memórias a partir da conversa; os colegas já tinham feito isso.
- Contou 15 arquivos em vez de 13 ao descrever o script das regras.
- Os arquivos do benchmark tinham dois fatos com o termo proibido dentro do texto novo, o que gerava falso positivo.
- O primeiro script de criação de arquivos omitia a quebra de linha final, causando falha de conferência em todos os arquivos.
- O script de evidências teve três defeitos na primeira versão (saída do `git` como erro, precedência de operadores e worktree na raiz do disco).
- Os números do embedder por palavras antes da correção do benchmark (61,9%) vieram de uma simulação do Claude, não da sua máquina. Os números válidos são os posteriores à correção.

## Resultados finais (a conferir contra `evidencias/memoria/`)

| Item | Resultado |
|---|---|
| Recuperação por palavras (21 perguntas, k = 3) | acerto 71,4%; lembranças corretas 64,7%; desatualizada 0,0%; esquecimento 100%; tokens 10,3 contra 40,6 do histórico completo (redução de 74,5%) |
| Recuperação semântica (mesmo benchmark) | acerto 100%; lembranças corretas 100%; desatualizada 0,0%; esquecimento 100%; tokens 17,9 contra 40,6 (redução de 55,9%) |
| Regras, desenvolvimento | 149 frases com 100%; conversas 17 de 17 |
| Regras, avaliação final | 50 frases: exatidão 62,0%, precisão 89,3%, revocação 58,1%, F1 70,4%; conversas 9 de 13 |
| Contrato da memória (RAM e SQLite) | antes do ajuste 8 falhas em 45; depois 45 passam |
| Suíte completa do projeto | 366 passam, 1 ignorado |

## Arquivos produzidos com ajuda do Claude

- **Código (`src/memoria/`):** `base.py`, `embeddings.py`, `store_mem.py`, `benchmark.py`, `embeddings_semantico.py`, `regras.py`, `gerenciador.py`, `avaliacao_regras.py`. Os arquivos `chaves.py` e `sqlite_chaves.py` foram escritos e depois descartados.
- **Avaliação (`eval/`):** `avaliar_memoria.py`, `avaliar_regras.py`, `memoria/sessoes.json`, quatro arquivos de dados em `memoria/regras/`.
- **Testes (`tests/`):** `test_memoria.py`, `test_benchmark_memoria.py`, `test_embeddings_semantico.py`, `test_regras.py`, `test_gerenciador_regras.py`, `test_separacao_dados.py`, `test_contrato_memoria.py`.
- **Documentos:** `docs/regras-memoria.md`, `docs/falhas-conhecidas-regras.md`.
- **Evidências:** `evidencias/memoria/` e o script `coletar_evidencias.ps1`.
- **Trabalho ABNT:** documento com Introdução, Referencial Teórico, Metodologia e Resultados da parte de memória.

## Pendências registradas na conversa

1. **P6, Etapa 3:** apresentar o relatório e os arquivos propostos e aguardar revisão; confirmar no commit `b5eec2f` o que depende do repositório.
2. **Referências do trabalho:** conferir cada uma na fonte original e preencher as datas de acesso.
3. **Números do trabalho:** conferir contra `evidencias/memoria/` antes de entregar.
4. **Casos de avaliação dos colegas:** pedir ao Ezequiel e à Paloma uns 20 casos novos para as regras, escritos sem ver `regras.py`.
5. **Integração com os resultados do grupo:** o comparativo do Ezequiel (`evidencias/comparativo_oficial_3rep.json`) não foi lido pelo Claude.
6. **`PROMPTS.md`:** montar o arquivo final a partir deste registro, conferindo cada entrada.
