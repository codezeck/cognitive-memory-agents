# Referência da API

Caminho da entrega: [manual do professor](manual-professor.md). No Docker padrão, use `http://127.0.0.1:8001/docs`; a porta 8000 abaixo pertence ao desenvolvimento Python manual.

API em FastAPI que recebe as conversas, escolhe o modelo, busca as memórias do usuário e chama o agente. Documentação interativa em `http://127.0.0.1:8000/docs` com a API no ar.

### Variáveis de ambiente

| Variável | Para que serve | Padrão |
| --- | --- | --- |
| `API_TOKENS` | Tokens de acesso, no formato `token:usuario,token:usuario`. Necessária no desenvolvimento manual; o iniciador Docker a preenche no servidor a partir do volume privado | vazio |
| `LLM_PROVIDER` | Provedor padrão | `ollama` |
| `LLM_MODEL` | Modelo padrão | `qwen2.5-coder:3b` |
| `MODELOS_PERMITIDOS` | Combinações `provedor:modelo` aceitas, separadas por vírgula. Qualquer outra é recusada | só o padrão |
| `OLLAMA_HOST` | Endereço do Ollama | local: `http://localhost:11434`; Compose padrão: `http://ollama:11434` |
| `OPENAI_API_KEY` | Chave de um provedor hospedado (opcional; o projeto funciona só com o Ollama local) | vazio |
| `USAR_FALSOS` | `1` troca o agente real por um agente de teste, sem Ollama. **Só para desenvolvimento** | desligado |

Para execução Python manual, configure as variáveis localmente. O iniciador Docker usa `.env.example` e gera credenciais em volume próprio; não exige copiar ou editar `.env`. **Nunca coloque tokens ou chaves no repositório.**

Para gerar um token:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Como executar

Localmente (com o ambiente virtual ativo, na raiz do projeto):

```powershell
$env:API_TOKENS="SEU_TOKEN:u001"
uvicorn src.api.main:app --reload
```

Sem o Ollama aberto, use `$env:USAR_FALSOS="1"` antes do `uvicorn` para testar a API com um agente de teste.

Com Docker:

```powershell
docker compose --env-file .env.example up --build
```

O Compose padrão prepara Ollama, modelo e acesso local e publica somente `127.0.0.1:8001`. A execução manual do uvicorn continua usando 8000. O log de 05/11 em `evidencias/agente/fluxo-memoria-docker-2026-11-05.txt` é histórico e não descreve esta instalação automática.

Para conferir a entrega, siga o [manual do professor](manual-professor.md). Não precisa preparar Ollama no host nem fornecer token. O override `docker-compose.professor.yml` permanece como caminho técnico legado para avaliações com Ollama externo, separado do padrão atual. A [validação de 14/11](validacao-entrega-docker.md) preserva as falhas iniciais e os novos ensaios da correção; nenhuma dessas sondagens substitui P6.

A interface de chat foi conciliada com a API atual e está disponível em **http://127.0.0.1:8001/**. O worktree original `feature/interface-instalacao` foi preservado. Swagger continua em `/docs`; usa Bearer manual para operações protegidas. O chat usa um intermediário autenticado no servidor, sem expor a credencial ao JavaScript.

### Autenticação

As operações de usuários exigem o cabeçalho abaixo. `/saude`, `/provedores`, `/docs` e o esquema `/openapi.json` são públicos:

```
Authorization: Bearer <token>
```

Cada token pertence a um usuário. Se o `usuario_id` do pedido for de outra pessoa, a API responde 403, e nada é lido ou apagado.

### Endpoints

| Método e rota | Autenticação | Descrição | Resposta |
| --- | --- | --- | --- |
| `GET /saude` | Não | Verifica se a API está no ar | 200 |
| `GET /provedores` | Não | Lista os modelos permitidos e o padrão | 200 |
| `POST /conversas` | Sim | Envia uma mensagem. Corpo: `usuario_id`, `mensagem`, `provedor` e `modelo` (opcionais) | 200 |
| `POST /usuarios/{usuario_id}/sessoes` | Sim | Começa uma sessão nova (limpa só a conversa em andamento, não as memórias) | 204 |
| `GET /usuarios/{usuario_id}/estado-regras` | Sim | Consulta o estado ativo das regras para avaliação | 200 |
| `POST /usuarios/{usuario_id}/memorias` | Sim | Cria uma memória. Corpo: `texto`, `chave` (opcional) | 201 com `id` |
| `GET /usuarios/{usuario_id}/memorias?consulta=...&k=5` | Sim | Busca as memórias mais relevantes para a consulta | 200 |
| `PATCH /usuarios/{usuario_id}/memorias/{memoria_id}` | Sim | Altera o texto de uma memória. Corpo: `texto` | 204 |
| `DELETE /usuarios/{usuario_id}/memorias/{memoria_id}` | Sim | Apaga o ID e limpa a conversa em andamento; não apaga outras versões da chave | 204 |
| `DELETE /usuarios/{usuario_id}/memorias` | Sim | Apaga **todas** as memórias do usuário, inclusive inativas, e limpa sua conversa em andamento | 200 com `removidas` |

Exemplo de conversa (PowerShell):

```powershell
$h = @{ Authorization = "Bearer SEU_TOKEN" }
$corpo = '{"usuario_id": "u001", "mensagem": "Oi!"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/conversas -Headers $h -ContentType "application/json" -Body $corpo
```

A resposta traz `resposta`, `memorias_usadas`, `provedor`, `modelo`, `latencia_ms`, `tokens_entrada` e `tokens_saida` (estes podem ser `null` quando indisponíveis). A extensão opcional `origem_uso`/`chamadas_modelo_observadas` identifica respostas locais sem invocação do adaptador; os campos antigos são preservados. Consulte a [decisão de contagem](proposta-contagem-local.md).

### Erros

Todo erro sai no formato `{"codigo": "...", "mensagem": "..."}`:

| Status | Código | Quando |
| --- | --- | --- |
| 400 | `modelo_nao_permitido` | O modelo ou provedor pedido não está em `MODELOS_PERMITIDOS` |
| 401 | `nao_autenticado` | Sem token ou token inválido |
| 403 | `acesso_negado` | O token é de outro usuário |
| 404 | `memoria_nao_encontrada` | A memória não existe para esse usuário |
| 422 | `entrada_invalida` | JSON quebrado, campo vazio ou `usuario_id` com caracteres inválidos |
| 503 | `provedor_indisponivel` / `provedor_nao_configurado` | Ollama fora do ar, modelo não instalado ou provedor sem chave |
| 504 | `provedor_timeout` | O modelo demorou demais |
| 500 | `erro_interno` | Erro inesperado. O detalhe só aparece no log, nunca na resposta |

### Privacidade

- O log registra usuário, modelo, quantidade de memórias e latência, **nunca o texto da mensagem**.
- Use apenas dados sintéticos e IDs como `u001`, nunca nome, CPF ou e-mail reais.

### Testes

```powershell
python -m pytest -q
```

Os testes da API não precisam do Ollama. Cobrem escolha de modelo, tradução dos erros do Ollama, isolamento entre usuários, autenticação, atualização e esquecimento.

### Limitações conhecidas

- A memória da API é salva em SQLite (arquivo `dados/memorias.db`, ou o volume `memoria_dados` no Docker) e **sobrevive ao reiniciar o servidor**.
- O gerenciador reconstrói seu índice de conflitos a partir das memórias ativas do usuário ao processar/consultar estado; não depende de reiniciar a API para refletir exclusões do banco.
- O `PATCH` altera o texto da memória (e a busca passa a usar o texto novo), mas não altera o `valor` guardado nos metadados, que é o que as regras de conflito do gerenciador comparam. Para trocar um fato pela conversa (por exemplo, "agora moro em Campinas"), use `POST /conversas`.
- Busca vazia não prova exclusão de registros inativos ou ausência na RAM. O DELETE individual aciona reset desde a PR #43; o observador opt-in foi ensaiado no processo real, com um worker e contagem literal, sem certificar toda a memória. A P6 v3 verificou persistência e exclusão no escopo de um worker; ver o [relatório atual](acertos-tokens-contexto-v3.md). A guarda corrigiu formas pessoais ensaiadas, mas o comparativo revelou outras respostas inventadas e abstenção indevida. Na P6 v3 houve redução de 83,84% nos vinte pares medidos; outras linguagens e formulações exigem avaliação; estes testes não certificam conformidade jurídica.
