# Decisão de arquitetura: suporte a múltiplos modelos de IA

## Contexto

O projeto Cognitive Memory Agents iniciou sua implementação com um agente baseado em Ollama. Entretanto, o objetivo de longo prazo é permitir que a camada de memória seja reutilizada com diferentes modelos de linguagem, sem dependência obrigatória de um único fornecedor ou runtime.

## Decisão proposta

A arquitetura deverá permitir o uso de:

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

## Estado atual

A implementação existente utiliza Ollama e mantém o histórico de conversa em memória durante a execução. A integração completa com memória persistente, API e múltiplos provedores ainda precisa ser desenvolvida e validada.

## Pontos para alinhamento da equipe

- Definir o contrato de comunicação entre API, agente e memória.
- Escolher quais modelos e provedores serão suportados inicialmente.
- Definir quem gerencia a configuração e as credenciais dos provedores.
- Determinar como serão realizados os testes de integração entre os componentes.

Esta decisão é uma proposta arquitetural e deverá ser validada pela equipe antes da implementação integrada.

## Responsabilidades propostas da equipe

Esta divisão registra o entendimento atual e deve ser validada pelos integrantes.

### Agente e integração com modelos — responsável pelo agente

- Manter a lógica do agente independente de um provedor específico.
- Preparar prompts e organizar o contexto recebido da memória.
- Definir uma interface comum para integrar modelos locais e hospedados.
- Avaliar qualidade das respostas, consumo de tokens e latência.
- Integrar os componentes respeitando os contratos acordados pela equipe.

### Memória de longo prazo — Vinicius

- Implementar a memória persistente.
- Desenvolver a recuperação de memórias relevantes.
- Tratar atualização e contradições conforme os requisitos.
- Preparar os dados sintéticos para avaliação.

### API e integração — Paloma

- Alinhar como a API receberá as solicitações e se comunicará com o agente.
- Avaliar como selecionar e configurar o modelo ou provedor utilizado.
- Definir o contrato de comunicação entre API, agente e memória.
- Planejar o tratamento de credenciais, erros e particularidades dos provedores.

Os itens atribuídos à API são propostas de alinhamento e precisam ser confirmados com a responsável.

## Critérios para a arquitetura multimodelo

- O Ollama deve continuar como integração local inicial, sem ser uma dependência obrigatória da arquitetura final.
- Modelos hospedados devem ser acessados por integrações compatíveis com as APIs dos respectivos provedores.
- Modelos locais poderão utilizar diferentes runtimes, desde que seja desenvolvido um adaptador compatível.
- A memória deve manter um contrato independente do provedor de IA.
- A seleção do modelo não deve permitir acesso indevido às memórias de outros usuários.
- Custos, latência, limites de contexto e suporte a funcionalidades variam conforme o modelo e o provedor.
