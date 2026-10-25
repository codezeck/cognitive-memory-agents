# Cognitive Memory Agents



Projeto de desenvolvimento e avaliação de agentes inteligentes com foco em memória conversacional, recuperação de informações relevantes e otimização do contexto enviado a modelos de linguagem (LLMs).



## Objetivo



O objetivo do projeto é investigar como o uso de histórico conversacional e memórias externas pode melhorar a continuidade das respostas e reduzir o consumo de tokens.



A proposta de longo prazo é desenvolver uma camada de memória reutilizável, capaz de trabalhar com diferentes modelos de IA por meio de integrações específicas.



> **Status:** o projeto está em desenvolvimento. A implementação atual inclui um agente baseado em Ollama e uma estrutura experimental de avaliação. A integração completa com outros serviços e a persistência da memória ainda são etapas futuras.



## Funcionalidades atuais



- Agente conversacional baseado em Ollama.

- Utilização do modelo `qwen2.5-coder:3b`.

- Histórico de conversa separado por identificador de usuário durante a execução.

- Recebimento de memórias externas como contexto adicional.

- Tratamento de mensagens inválidas e falhas na chamada ao modelo.

- Testes automatizados para validar o comportamento do agente.

- Avaliação experimental de estratégias de contexto e consumo de tokens.



## Tecnologias



- Python

- Ollama

- pytest

- Git e GitHub

- GitHub Actions para automação de testes



## Como funciona



O agente recebe uma mensagem e um identificador de usuário. Quando disponíveis, as informações de memória externa são adicionadas ao contexto enviado ao modelo, junto com as instruções do sistema e o histórico daquela conversa.



A implementação atual mantém o histórico em memória durante a execução do processo. As memórias externas são fornecidas ao agente pelo componente que o chama.



### Estratégias avaliadas



1. **Sem memória:** a pergunta é enviada sem o histórico anterior ou as memórias externas do cenário.

2. **Histórico completo:** o contexto é construído com as mensagens anteriores da conversa.

3. **Memória externa:** informações relevantes são fornecidas como contexto, evitando o envio de todo o histórico utilizado no cenário de comparação.



## Pré-requisitos



- Python instalado.

- Ollama instalado e em execução.

- Modelo `qwen2.5-coder:3b` disponível no Ollama.

- Git instalado.



## Instalação



Clone o repositório:



```bash

git clone https://github.com/codezeck/cognitive-memory-agents.git

cd cognitive-memory-agents

```



Crie um ambiente virtual:



```powershell

python -m venv .venv

```



Ative o ambiente virtual no Windows PowerShell:



```powershell

..venv\Scripts\Activate.ps1

```



Instale as dependências:



```powershell

python -m pip install -r requirements.txt

```



Baixe o modelo:



```powershell

ollama pull qwen2.5-coder:3b

```



## Execução



Com o Ollama em execução e as dependências instaladas, execute:



```powershell

python src/agent.py

```



A forma de interação disponível depende da implementação atual do arquivo `src/agent.py`.



## Testes automatizados



Execute a suíte de testes:



```powershell

python -m pytest -v

```



Os testes cobrem aspectos como:



- Geração de respostas e tratamento de erros.

- Manutenção e isolamento do histórico por usuário.

- Comportamento diante de mensagens vazias.

- Inclusão de memória externa no contexto.

- Avaliação das respostas e cálculo de métricas.



## Avaliação experimental



O projeto contém um conjunto de casos em `eval/dataset.json`, um avaliador em `eval/evaluate.py` e resultados registrados em `eval/results.json`.



Para executar a avaliação:



```powershell

python eval/evaluate.py

```



A avaliação compara aprovação dos casos, consumo de tokens, chamadas ao modelo e tempo de execução.



### Resultados de uma execução experimental



| Indicador | Sem memória | Histórico completo | Memória externa |

|---|---:|---:|---:|

| Casos aprovados | 2 de 6 | 6 de 6 | 6 de 6 |

| Taxa de aprovação | 33,33% | 100% | 100% |

| Tokens totais | 1.222 | 2.675 | 1.407 |

| Chamadas ao modelo | 6 | 12 | 6 |

| Tempo total | 3,09 s | 4,27 s | 2,06 s |



Os valores são resultados preliminares de uma execução com seis casos por cenário. Eles não garantem o mesmo desempenho em outras execuções.



Nesse experimento, o cenário de memória externa utilizou aproximadamente 47% menos tokens e 52% menos tempo do que o cenário de histórico completo. Essa comparação é experimental: a memória externa foi simulada pelo avaliador, e não representa uma integração completa com um sistema persistente de memória.



## Limitações atuais



- O histórico não é persistido após o encerramento do processo.

- O identificador de usuário separa históricos na implementação, mas não substitui autenticação e autorização.

- A memória externa precisa ser fornecida pelo componente que chama o agente.

- A integração com API e gerenciador de memória ainda precisa ser validada.

- Os resultados de avaliação utilizam um conjunto pequeno de casos.



## Próximos passos



- Integrar o agente ao gerenciador de memória do projeto.

- Integrar o agente à API da aplicação.

- Implementar armazenamento persistente e recuperação de memórias relevantes.

- Avaliar mecanismos de resumo, atualização e remoção de memórias.

- Criar adaptadores para diferentes modelos e provedores de IA.

- Ampliar os testes e repetir as avaliações para obter comparações mais robustas.

- Reforçar autenticação, isolamento de dados e controles de privacidade.



## Contribuição



Alterações devem respeitar a divisão de responsabilidades do projeto, incluir testes quando aplicável e passar pela revisão da equipe antes de serem integradas à branch principal.



## Licença



A licença do projeto deverá ser definida pela equipe responsável.
