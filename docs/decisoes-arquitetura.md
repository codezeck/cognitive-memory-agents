# Decisão de arquitetura: suporte a múltiplos modelos de IA

## Escopo confirmado em 15/11/2026: entrega com Ollama

O usuário reafirmou que a entrega precisa funcionar sem assinatura ou créditos de API. Ollama é o caminho da demonstração e das avaliações planejadas. A preparação OpenAI fica preservada como material opcional fora do escopo atual, sem ativação nem rodada real.

O hardware do professor é desconhecido: manter caminho funcional em CPU e requisitos medidos documentados; GPU pode ser aceleração opcional, nunca requisito da entrega. Antes de trocar o modelo para reduzir peso/latência, comparar candidatos somente em desenvolvimento e registrar qualidade, tempos e recursos. O comparativo de memória deve manter o mesmo modelo e configuração nos cenários, medir ingestão e sessão completa e conservar os resultados anteriores. Esta decisão não libera P6/reservado nem altera seus critérios ou revisões pendentes.

## Decisões locais da entrega de 14/11/2026

1. **Reaproveitar chat e manter contratos:** conciliado o worktree existente com API atual, preservando reset de DELETE da PR #43. A UI usa intermediário no servidor e rotas reais autenticadas; não instancia agente falso nem substitui `main.py` pela base antiga.
2. **Preparar runtime em serviço próprio:** Compose inicia Ollama, preparo que valida credenciais/modelo e API. Pesos, banco e segredos possuem volumes separados. Padrão local Ollama não restringe a arquitetura dos adaptadores. Um worker delimita observação do histórico.
3. **Acesso local de demonstração:** credenciais aleatórias persistentes, cookie HttpOnly/SameSite, validação de origem e identidade definida no servidor. A/B são perfis sintéticos compartilhados. API Bearer permanece. Publicação exige outra configuração e revisão de autenticação.
4. **Observar antes de afirmar esquecimento:** observador RAM somente leitura, desligado por padrão e restrito a usuários autorizados, devolve contagens e instância/processo, sem textos. SQLite é verificado separadamente. Não equivale a toda memória de máquina nem a certificação semântica/legal.
5. **Separar política local de uso desconhecido:** extensão opcional autorizada `origem_uso`/`chamadas_modelo_observadas`; campos antigos preservados. Zero exige política local explícita e coerente. `p3-uso-local-v1` distingue resultados novos. Retries internos do SDK não são contados.

Mudanças locais para revisão da equipe, sem aprovação atribuída automaticamente. A economia global não foi demonstrada: houve aumento de tokens completos no desenvolvimento. Uma futura revisão de orçamento de contexto é decisão separada, não implementada nesta etapa.

## Contexto

O projeto Cognitive Memory Agents iniciou sua implementação com um agente baseado em Ollama. Entretanto, o objetivo de longo prazo é permitir que a camada de memória seja reutilizada com diferentes modelos de linguagem, sem dependência obrigatória de um único fornecedor ou runtime.

## Decisão implementada e extensões propostas

A arquitetura usa adaptadores para permitir:

- Modelos hospedados, acessados por APIs de provedores compatíveis.
- Modelos locais, executados por runtimes ou ferramentas compatíveis.
- Diferentes modelos por meio de adaptadores que padronizem a comunicação com o agente.

O Ollama será uma das integrações possíveis, e não um requisito obrigatório para toda a aplicação.

## Separação de responsabilidades

**Agente:** preparar instruções, organizar o contexto e encaminhar solicitações ao modelo selecionado.

**Memória:** persistir informações, recuperar memórias relevantes e tratar atualizações e contradições.

**API:** receber solicitações, coordenar a comunicação entre os componentes e encaminhar as chamadas ao modelo ou provedor configurado.

## Requisitos de integração

- Padronizar a entrada e a saída dos adaptadores de modelos.
- Definir como as memórias recuperadas serão entregues ao agente.
- Evitar dependência da lógica de memória em funcionalidades exclusivas de um provedor.
- Tratar autenticação, credenciais, erros e limites específicos de cada integração.
- Preservar o isolamento entre usuários e o controle de acesso às memórias.
- Avaliar qualidade das respostas, consumo de tokens e latência por modelo.

## Estado atual (revisão de 12/11/2026)

`ModeloLLM.gerar()` define o contrato textual; `gerar_com_detalhes()` é uma capacidade opcional utilizada para métricas. Ollama e OpenAI possuem adaptadores implementados. `AgenteLocal` seleciona e reutiliza adaptadores por provedor/modelo e traduz falhas para os erros de domínio já existentes. Respostas vazias de ambos os provedores compartilham `RespostaModeloVaziaError` (a classe específica OpenAI permanece compatível) e resultam em `503 provedor_indisponivel`. Não há fallback automático.

```mermaid
flowchart LR
    API[API /conversas] --> S[Conversador]
    S --> G[Gerenciador de regras]
    G --> M[Memória SQLite + EmbedderHash]
    S --> M
    S --> A[AgenteLocal]
    A --> C[Agente: prompt + memória recuperada + histórico por usuário]
    C --> L[Adaptador Ollama ou OpenAI]
```

A API processa as regras, busca memórias persistentes e entrega o contexto ao agente. O histórico de conversa fica em RAM por processo e é limitado a dez interações; memórias recuperadas são inseridas como contexto somente na chamada atual, mas respostas e mensagens podem conservar fatos. A CLI é uma demonstração Ollama com usuário fixo e não conecta a persistência. A memória semântica existe para benchmarks; não é o embedder padrão da API.

Testes simulados validam agente, seleção, adaptadores e erros. Testes com SQLite temporário validam persistência; existe evidência histórica do fluxo Docker. Isso não substitui execução atual dos serviços nem os checkpoints reais P6. A P4-v3 reconhece os treze atributos; a compatibilidade estrutural das anotações é independente da revisão semântica e da avaliação real.

## Pontos para alinhamento da equipe

- Concluir contrato aprovado de esquecimento P6 e evidências de início/reinício/exclusão.
- Definir observação real da RAM da API; a invalidação após exclusão individual já foi integrada pela PR #43, sem comprovar por si só o estado do processo real.
- Revisar os limites da política local de abstenção implementada na [continuação do ensaio](validacao-entrega-docker.md#continuação--correção-da-abstenção-14112026). Consultas pessoais diretas reconhecidas sem suporte terminam antes do LLM; suporte atual/histórico/memória e perguntas gerais preservam a geração. A gramática é limitada, sem mudança de endpoint ou armazenamento. A tentativa de corrigir apenas por instruções foi rejeitada na execução real.
- Alinhar o catálogo anunciado pela API aos adaptadores implementados; a configuração de uma chave não implementa um adaptador.
- Concluir a avaliação final, preservando a execução local a custo zero. O percurso inicial Docker/Ollama foi exercitado em 14/11, com falhas registradas; não substitui a P6.

A integração descrita acima já existe. Os pontos de alinhamento são dependências compartilhadas; endpoints, armazenamento e regras não foram alterados nesta revisão. Detalhes: [agente e provedores](agente-provedores.md) e [guia de avaliação](guia-avaliacao.md).

## Responsabilidades da equipe

Esta divisão segue os escopos informados pela equipe para esta implementação. Mudanças em contratos compartilhados precisam ser alinhadas com os responsáveis.

### Agente e integração com modelos — Zeck

- Manter a lógica do agente independente de um provedor específico.
- Preparar prompts e organizar o contexto recebido da memória.
- Definir uma interface comum para integrar modelos locais e hospedados.
- Avaliar qualidade das respostas, consumo de tokens e latência.
- Integrar os componentes respeitando os contratos acordados pela equipe.

### Memória de longo prazo — Vinicius

- Manter a lógica de memória de longo prazo, extração e esquecimento.
- Desenvolver a recuperação de memórias relevantes.
- Tratar atualização e contradições conforme os requisitos.
- Preparar os dados sintéticos para avaliação.

### API, armazenamento e integração — Paloma

- Alinhar como a API receberá as solicitações e se comunicará com o agente.
- Avaliar como selecionar e configurar o modelo ou provedor utilizado.
- Definir o contrato de comunicação entre API, agente e memória.
- Manter armazenamento, persistência, Docker e infraestrutura.
- Planejar o tratamento de credenciais, erros e particularidades dos provedores.

O agente participa dos contratos de integração, sem alterar unilateralmente endpoints, armazenamento ou regras de memória.

## Critérios para a arquitetura multimodelo

- O Ollama deve continuar como integração local inicial, sem ser uma dependência obrigatória da arquitetura final.
- Modelos hospedados devem ser acessados por integrações compatíveis com as APIs dos respectivos provedores.
- Modelos locais poderão utilizar diferentes runtimes, desde que seja desenvolvido um adaptador compatível.
- A memória deve manter um contrato independente do provedor de IA.
- A seleção do modelo não deve permitir acesso indevido às memórias de outros usuários.
- Custos, latência, limites de contexto e suporte a funcionalidades variam conforme o modelo e o provedor.
