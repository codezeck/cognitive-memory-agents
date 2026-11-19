# Cognitive Memory Agents

**Curso:** EAD_PROINT_100.DD-ADS-PI-10-74.2026.74  
**Disciplina:** Projeto Integrador
**Instituição:** Faculdade União Chinita

**Integrantes:**
- Ezequiel da Silva Manço — RA: 2410701
- Vinícius Silva Dos Santos — RA: 2412504
- Paloma Quimbely de Lima Silva — RA: 2411659

Este projeto corresponde ao Tema 11 de um conjunto de 16 temas propostos para a disciplina e representa o primeiro trabalho desenvolvido para a construção do portfólio da equipe. Os demais temas serão explorados posteriormente, com foco no aprendizado contínuo, na troca de experiências e na diversificação dos papéis e responsabilidades entre os integrantes.

---

## 1. Sobre o projeto

**Versão atual em desenvolvimento — contexto v3:** confirmações de operações reconhecidas são locais; perguntas factuais continuam no modelo com contexto reduzido. Na nova validação sintética, a memória automática teve 48/48 aprovações P4 e economia de 84,88% em 47/48 pares medidos (um timeout do baseline). Na P6, teve 21/21 aprovações e usou 3.593 contra 22.228 tokens de sessão, economia de 83,84% nos 20 pares. São resultados dos casos medidos, sem garantia de generalização ou equivalência estatística. Consulte [acertos, tokens, uso local e limites da v3](docs/acertos-tokens-contexto-v3.md). O [PDF v3](docs/pesquisa-abnt.pdf) incorpora a avaliação atual (16 páginas textuais). Consulte o [checklist](docs/checklist-entrega.md) e o [índice de evidências](evidencias/entrega-v3-20261118/README.md). Código sob [MIT](LICENSE), com [licenças de terceiros](docs/licencas.md) separadas.

**Registro histórico da v2, 18/11/2026:** melhorias de consulta, busca por chave e contexto compacto foram avaliadas com Ollama real. A P6 local executou 20 sessões por cenário, com persistência e exclusão observadas; houve redução de 25,27% dos tokens completos. No teste separado, porém, a memória automática aprovou 21/30 respostas contra 24/30 do histórico e teve economia de 2,40%. As metas adicionais não foram atingidas; permanecem falhas de paráfrase e negação. Veja o [relatório com resultados, cobertura e limitações](docs/melhorias-avaliacao-20261118.md) e a [decisão de protocolo](docs/revisao-experimental/decisao-20261118.md). Essa rodada foi sucedida pela v3 descrita acima; seus resultados negativos permanecem preservados.

**Execução local atual:** com Docker Desktop aberto, execute `.\Iniciar.ps1` na raiz ou `docker compose --env-file .env.example up --build`. Acesse **http://127.0.0.1:8001/** para conversar. O preparo inicia Ollama, baixa `qwen2.5-coder:3b`, confirma carregamento e gera acesso local automaticamente, sem copiar tokens. Primeira execução exige internet/download; dados, pesos e identidade ficam em volumes. Não é necessário instalar Ollama/Python no host. Consulte o [manual com capturas](docs/manual-professor.md), a [matriz de requisitos](docs/andamento-entrega.md) e o [relatório real](docs/validacao-entrega-docker.md). A demonstração é local, com perfis sintéticos; não deve ser exposta na internet.

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

## Agente, provedores e avaliação

- [Agente e provedores](docs/agente-provedores.md): execução da CLI, configuração local, histórico, contexto, timeout e erros. Ollama e OpenAI têm testes simulados; isso não comprova disponibilidade de um serviço real.
- [Guia de avaliação](docs/guia-avaliacao.md): instalação do ambiente Python 3.13, carregamento do `.env`, testes e reprodução dos experimentos P4/P5/P6.
- [Arquitetura](docs/decisoes-arquitetura.md) e [evidências](evidencias/README.md).
- [Dados e modelo](docs/dados-modelos.md): origem, versão efetiva, licença e limites do ensaio local.
- [Material opcional OpenAI, fora do escopo da entrega](docs/openai-opcional.md): configuração preservada, sem validação real. A decisão de 15/11 mantém Ollama para demonstração e avaliações, sem exigir assinatura ou créditos de API.

O julgador `p4-v3` reconhece os treze atributos usados pela avaliação. A decisão local de 18/11 separou a recuperação de Luna/Simba da resposta de quantidade dois, preservando as 21 anotações oficiais. A rodada real coletou todas as respostas, mas onze julgamentos ficaram não verificados pelo P4. A análise textual assistida por IA é complementar e não substitui revisão humana; compatibilidade estrutural não significa respostas corretas.

## API

API em FastAPI que recebe as conversas, escolhe o modelo, busca as memórias do usuário e chama o agente. Documentação interativa em `http://127.0.0.1:8000/docs` com a API no ar.

### Variáveis de ambiente

| Variável | Para que serve | Padrão |
| --- | --- | --- |
| `API_TOKENS` | Tokens de acesso, no formato `token:usuario,token:usuario`. **Obrigatória**: sem ela, a API recusa os pedidos protegidos | vazio |
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

Para conferir a entrega, siga o [manual do professor](docs/manual-professor.md). Não precisa preparar Ollama no host nem fornecer token. O override `docker-compose.professor.yml` permanece como caminho técnico legado para avaliações com Ollama externo, separado do padrão atual. A [validação de 14/11](docs/validacao-entrega-docker.md) preserva as falhas iniciais e os novos ensaios da correção; nenhuma dessas sondagens substitui P6.

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

A resposta traz `resposta`, `memorias_usadas`, `provedor`, `modelo`, `latencia_ms`, `tokens_entrada` e `tokens_saida` (estes podem ser `null` quando indisponíveis). A extensão opcional `origem_uso`/`chamadas_modelo_observadas` identifica respostas locais sem invocação do adaptador; os campos antigos são preservados. Consulte a [decisão de contagem](docs/proposta-contagem-local.md).

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
- Busca vazia não prova exclusão de registros inativos ou ausência na RAM. O DELETE individual aciona reset desde a PR #43; o observador opt-in foi ensaiado no processo real, com um worker e contagem literal, sem certificar toda a memória. Checkpoints P6 permanecem pendentes. A guarda corrigiu formas pessoais ensaiadas, mas o comparativo revelou outras respostas inventadas e abstenção indevida. A meta de economia global não foi atingida; estes testes não certificam conformidade jurídica.
