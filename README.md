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
