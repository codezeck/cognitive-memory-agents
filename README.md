# Cognitive Memory Agents

**Curso:** EAD_PROINT_100.DD-ADS-PI-10-74.2026.74  
**Disciplina:** Projeto Integrador

**Integrantes:**
- Ezequiel da Silva Manço — RA: 2410701
- Vinícius Silva Dos Santos — RA: 2412504
- Paloma Quimbely de Lima Silva — RA: 2411659

---

## 1. Sobre o projeto

O Cognitive Memory Agents é um projeto de desenvolvimento e avaliação de agentes inteligentes com foco em memória conversacional, recuperação de informações relevantes e otimização do contexto enviado a modelos de linguagem (LLMs).

O projeto busca melhorar a continuidade das respostas, recuperar informações relevantes de conversas anteriores e reduzir o consumo desnecessário de contexto enviado aos modelos.

## 2. Objetivo da API mult provedores

Desenvolver uma API modular, extensível e independente de provedores de inteligência artificial, permitindo integrar modelos locais e serviços externos por meio de uma interface padronizada.

A aplicação não deve depender exclusivamente de um provedor, modelo, fabricante ou tecnologia específica. A inclusão de novos provedores deve preservar a lógica central, os endpoints existentes e as funcionalidades de memória.

## 3. Estado das integrações

### Implementados
- **Ollama:** execução local de modelos de linguagem.
- **OpenAI:** integração por meio da API oficial, com chave de acesso configurada no ambiente.

### Planejados
- **Anthropic Claude:** possível integração futura por meio da API oficial.
- **Google Gemini:** possível integração futura por meio da API oficial.
- **Outros provedores:** poderão ser adicionados por meio de novos adaptadores.

Os provedores planejados não devem ser considerados funcionais até que seus adaptadores sejam implementados e testados.

## 4. Arquitetura

A arquitetura separa a lógica central do agente das integrações específicas de cada provedor.

Cada adaptador deve implementar um contrato comum para enviar mensagens ao modelo e retornar o texto gerado. Dessa forma, a lógica de negócio não precisa depender diretamente do SDK ou do formato de requisição de um fornecedor.

A seleção do provedor e do modelo deve ser centralizada, respeitando as configurações e as integrações realmente disponíveis.

## 5. Seleção de provedor e modelo

A API deve permitir:
- Configurar o provedor e o modelo padrão.
- Definir quais combinações de provedores e modelos são permitidas.
- Consultar os provedores e modelos configurados.
- Validar a combinação selecionada.
- Informar quando um provedor não está configurado ou não possui adaptador implementado.

Os nomes dos modelos e os parâmetros específicos de cada provedor não devem ser presumidos como equivalentes.

## 6. Memória conversacional

A API mantém a integração com o sistema de memória do projeto, permitindo recuperar informações relevantes associadas ao usuário e utilizá-las no contexto das respostas.

O armazenamento e a recuperação de memórias devem preservar o isolamento entre usuários. As operações de consulta e exclusão devem respeitar a identidade do usuário correspondente.

## 7. Segurança

- Manter chaves de API em variáveis de ambiente ou em um mecanismo seguro de gerenciamento de segredos.
- Não versionar credenciais reais.
- Não expor chaves em logs, respostas da API ou código do cliente.
- Permitir a utilização local com Ollama sem exigir o envio de dados para um provedor externo.
- Enviar solicitações a provedores externos somente quando selecionados e configurados.
- Validar entradas e tratar falhas sem revelar detalhes internos sensíveis.

## 8. Configuração

As principais configurações da API são:

- `LLM_PROVIDER`: provedor padrão.
- `LLM_MODEL`: modelo padrão.
- `MODELOS_PERMITIDOS`: combinações permitidas de provedor e modelo.
- `OPENAI_API_KEY`: chave de acesso à OpenAI, quando utilizada.

O arquivo `.env.example` serve como referência de configuração. Credenciais reais devem permanecer no ambiente local e não devem ser adicionadas ao repositório.

## 9. Testes e critérios de qualidade

Os testes devem cobrir:
- Configuração e seleção de provedores e modelos.
- Funcionamento dos adaptadores.
- Tratamento de erros, indisponibilidade e timeout.
- Recuperação, isolamento e exclusão de memórias.
- Compatibilidade com os endpoints existentes.

A inclusão de um novo provedor deve exigir o mínimo possível de alterações na lógica central, sem anunciar suporte que ainda não foi implementado.

## 10. Evolução do projeto

O projeto poderá evoluir com novos adaptadores de modelos, melhorias na recuperação de memórias, otimização de contexto e recursos de observabilidade.

Toda evolução deve preservar a modularidade, a segurança e o comportamento já validado por testes.

## API

API em FastAPI que recebe as conversas, escolhe o modelo, busca as memórias do usuário e chama o agente. Documentação interativa em `http://127.0.0.1:8000/docs` com a API no ar.

### Variáveis de ambiente

| Variável | Para que serve | Padrão |
| --- | --- | --- |
| `API_TOKENS` | Tokens de acesso, no formato `token:usuario,token:usuario`. **Obrigatória**: sem ela, a API recusa os pedidos protegidos | vazio |
| `LLM_PROVIDER` | Provedor padrão | `ollama` |
| `LLM_MODEL` | Modelo padrão | `qwen2.5-coder:3b` |
| `MODELOS_PERMITIDOS` | Combinações `provedor:modelo` aceitas, separadas por vírgula. Qualquer outra é recusada | só o padrão |
| `OLLAMA_HOST` | Endereço do Ollama | `http://localhost:11434` (no Docker: `http://host.docker.internal:11434`) |
| `OPENAI_API_KEY` | Chave de um provedor hospedado (opcional; o projeto funciona só com o Ollama local) | vazio |
| `USAR_FALSOS` | `1` troca o agente real por um agente de teste, sem Ollama. **Só para desenvolvimento** | desligado |

Copie o `.env.example` para `.env` (que está no `.gitignore`) e preencha localmente. **Nunca coloque tokens ou chaves no repositório.**

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
docker compose up --build
```

O `docker-compose.yml` lê as variáveis do `.env`. A API fica em `http://127.0.0.1:8000`. **[confirmar]** Escreva aqui quem validou o Docker e em qual computador (ou Codespaces).

### Autenticação

Todas as rotas, exceto `/saude` e `/provedores`, exigem o cabeçalho:

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
| `POST /usuarios/{usuario_id}/memorias` | Sim | Cria uma memória. Corpo: `texto`, `chave` (opcional) | 201 com `id` |
| `GET /usuarios/{usuario_id}/memorias?consulta=...&k=5` | Sim | Busca as memórias mais relevantes para a consulta | 200 |
| `PATCH /usuarios/{usuario_id}/memorias/{memoria_id}` | Sim | Altera o texto de uma memória. Corpo: `texto` | 204 |
| `DELETE /usuarios/{usuario_id}/memorias/{memoria_id}` | Sim | Apaga uma memória | 204 |
| `DELETE /usuarios/{usuario_id}/memorias` | Sim | Apaga **todas** as memórias do usuário e a conversa em andamento (direito ao esquecimento, LGPD) | 200 com `removidas` |

Exemplo de conversa (PowerShell):

```powershell
$h = @{ Authorization = "Bearer SEU_TOKEN" }
$corpo = '{"usuario_id": "u001", "mensagem": "Oi!"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/conversas -Headers $h -ContentType "application/json" -Body $corpo
```

A resposta traz `resposta`, `memorias_usadas`, `provedor`, `modelo` e `latencia_ms`.

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

- A memória usada pela API fica em RAM e **se perde ao reiniciar o servidor**, até a memória persistente ser integrada. **[confirmar]** Atualize esta linha quando o banco definitivo entrar.
- O `PATCH` altera o texto, mas o índice de conflitos do gerenciador de memória não é atualizado.
- Os tokens de uso (`tokens_entrada` e `tokens_saida`) só aparecem se o agente os devolver.