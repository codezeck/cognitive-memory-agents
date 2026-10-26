# Cognitive Memory Agents

**Curso:** EAD_PROINT_100.DD-ADS-PI-10-74.2026.74  
**Disciplina:** Projeto Integrador

**Integrantes:**
- Ezequiel da Silva Manço — RA: 2410701 
- Vinícius Silva Dos Santos — RA: 2412504 
- Paloma Quimbely de Lima Silva — RA: 2411659 

---

## Sobre o projeto

O Cognitive Memory Agents é um projeto de desenvolvimento e avaliação de agentes inteligentes com foco em memória conversacional, recuperação de informações relevantes e otimização do contexto enviado a modelos de linguagem (LLMs).

O objetivo é investigar como diferentes estratégias de memória podem melhorar a continuidade das respostas e reduzir o consumo de tokens durante as interações com modelos de inteligência artificial.

## Funcionalidades

- Agente conversacional integrado ao Ollama.
- Utilização do modelo `qwen2.5-coder:3b`.
- Histórico de conversas separado por identificador de usuário durante a execução.
- Inclusão de memórias externas no contexto enviado ao modelo.
- Tratamento de mensagens inválidas e falhas na comunicação com o modelo.
- Testes automatizados para validar o comportamento do agente.
- Avaliação experimental de estratégias de memória, consumo de tokens e tempo de execução.

## Tecnologias utilizadas

- **Python:** desenvolvimento da aplicação.
- **Ollama:** execução local do modelo de linguagem.
- **pytest:** testes automatizados.
- **Git e GitHub:** controle de versão e colaboração.
- **GitHub Actions:** automação da execução dos testes.

## Arquitetura e funcionamento

O agente recebe uma mensagem e um identificador de usuário. O contexto enviado ao modelo pode conter instruções do sistema, histórico da conversa e memórias externas fornecidas pelo componente responsável pela chamada.

O projeto avalia três estratégias de construção de contexto:

1. **Sem memória:** envio da pergunta sem o histórico anterior ou as memórias externas do cenário.
2. **Histórico completo:** utilização das mensagens anteriores da conversa.
3. **Memória externa:** utilização de informações relevantes fornecidas separadamente, evitando o envio de todo o histórico usado no cenário de comparação.

Atualmente, o histórico é mantido em memória durante a execução do processo. A persistência das informações e a integração completa com o gerenciador de memória são etapas de desenvolvimento.

## Pré-requisitos

Antes de executar o projeto, instale:

- Python.
- Ollama.
- Git.

Também é necessário disponibilizar o modelo `qwen2.5-coder:3b` no Ollama.

## Instalação

Clone o repositório:

```bash
git clone https://github.com/codezeck/cognitive-memory-agents.git
cd cognitive-memory-agents
```

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente no Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Baixe o modelo utilizado:

```bash
ollama pull qwen2.5-coder:3b
```

## Execução

Com as dependências instaladas e o Ollama em execução, execute:

```bash
python src/agent.py
```

A forma de interação depende da implementação disponível no arquivo `src/agent.py`.

## Testes automatizados

Para executar os testes:

```bash
python -m pytest -v
```

Os testes validam aspectos como:

- Geração de respostas e tratamento de erros.
- Comportamento diante de mensagens vazias.
- Preservação e isolamento do histórico por usuário.
- Inclusão de memória externa no contexto.
- Comportamento do adaptador de modelo.

Os testes também podem ser executados automaticamente pelo GitHub Actions.

## Avaliação experimental

O projeto possui um conjunto de casos de avaliação em `eval/dataset.json`, um avaliador em `eval/evaluate.py` e resultados registrados em `eval/results.json`.

Execute a avaliação com:

```bash
python eval/evaluate.py
```

A avaliação compara a taxa de aprovação dos casos, o consumo de tokens, a quantidade de chamadas ao modelo e o tempo de execução.

### Resultados experimentais

| Indicador | Sem memória | Histórico completo | Memória externa |
|---|---:|---:|---:|
| Casos aprovados | 2 de 6 | 6 de 6 | 6 de 6 |
| Taxa de aprovação | 33,33% | 100% | 100% |
| Tokens totais | 1.222 | 2.675 | 1.407 |
| Chamadas ao modelo | 6 | 12 | 6 |
| Tempo total | 3,09 s | 4,27 s | 2,06 s |

Os resultados correspondem a uma execução experimental com seis casos por cenário. Portanto, são preliminares e podem variar em novas execuções.

Nesse experimento, o cenário de memória externa utilizou aproximadamente 47% menos tokens e 52% menos tempo do que o cenário de histórico completo. A memória externa foi simulada pelo avaliador e não representa, por si só, uma integração completa com um sistema persistente.

## Limitações conhecidas

- O histórico não é persistido após o encerramento do processo.
- O identificador de usuário não substitui mecanismos de autenticação e autorização.
- As memórias externas precisam ser fornecidas pelo componente que chama o agente.
- A integração completa entre agente, API e gerenciador de memória precisa ser validada.
- Os resultados experimentais utilizam um conjunto limitado de casos.

## Próximos passos

- Integrar o agente ao gerenciador de memória.
- Validar a integração com a API da aplicação.
- Implementar armazenamento persistente e recuperação de memórias relevantes.
- Desenvolver mecanismos de atualização, resumo e remoção de memórias.
- Ampliar os testes automatizados e os cenários de avaliação.
- Investigar a integração com diferentes modelos e provedores de IA.
- Reforçar os mecanismos de autenticação, isolamento e privacidade.

## Contribuição

As contribuições devem seguir a organização do projeto, incluir testes quando aplicável e passar por revisão antes da integração à branch principal.

## Licença

A licença do projeto será definida pela equipe responsável.
