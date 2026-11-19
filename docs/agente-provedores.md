# Agente e provedores

Responsável por agente, adaptadores, prompts e avaliação: Zeck. A referência dos endpoints permanece no [README](../README.md#api); instalação e experimentos estão no [guia de avaliação](guia-avaliacao.md).

## Execução local

Para o professor, o caminho principal é o [Docker automático com chat](manual-professor.md), sem Ollama/Python no host ou token manual. Os comandos abaixo são da CLI de desenvolvimento, com escopo distinto da aplicação persistente.

Use Python 3.13 e o ambiente com `requirements.txt`, conforme o guia. Para a demonstração local, instale o Ollama, deixe o serviço disponível e prepare o modelo:

```powershell
ollama pull qwen2.5-coder:3b
ollama list
python -m src.agent
```

Digite `/sair` para encerrar. A CLI usa `usuario_demo`, modelo fixo `qwen2.5-coder:3b` e histórico apenas em RAM; não chama a API, o gerenciador ou o SQLite. Ela não seleciona OpenAI por `LLM_PROVIDER`. Para testar memória persistente e seleção de provedores, use a API conforme o README.

## Prompt, histórico e memória

**Contexto v3 (estado atual):** operações inteiramente reconhecidas pelas regras recebem confirmação local com origem e zero chamadas explícitas. Perguntas e pedidos mistos continuam no modelo. O prompt compacto é mais breve; consultas pessoais diretas com evidência recuperada usam somente os fatos atuais, sem histórico contraditório redundante. Outras conversas mantêm até três pares recentes/6.000 caracteres. A negação por valor requer correspondência unívoca com uma chave atual do usuário; valores antigos e referências ambíguas não apagam o fato novo. Após esquecer, a confirmação não recoloca o alvo na RAM. O baseline conserva geração e histórico completos. Veja [métricas e limites](acertos-tokens-contexto-v3.md). O parágrafo v2 abaixo é histórico.

**Versão local de 18/11:** a API usa `memoria-contexto-v2`: até três pares recentes, limitados a 6.000 caracteres de histórico, sem cortar um par. Sistema, pergunta atual e memórias recuperadas são preservados; esse limite não garante um teto de tokens da requisição completa. A montagem compacta retira duplicações textuais e orienta a priorizar fatos ativos. A RAM continua limitada a dez pares, e os resets após exclusão são preservados. A CLI mantém a política anterior; o baseline instancia `AgenteLocal(contexto_compacto=False)` e preserva o episódio completo em processo separado. Fatos fora do histórico enviado dependem da memória recuperada para dar suporte à resposta.

A busca usa correspondência de chave para consultas pessoais reconhecidas, selecionando apenas fatos ativos do usuário. Nesse caminho, `score=1.0` significa chave exata; no fallback, o score continua vindo do produto dos vetores. Não é recuperação semântica geral: paráfrases fora da gramática ainda falharam no teste separado. Consulte o [relatório de 18/11](melhorias-avaliacao-20261118.md).

Sem a opção de contexto compacto, `src/agent.py:responder()` combina o prompt de sistema, as memórias recuperadas fornecidas pelo chamador, até nove interações anteriores e a pergunta atual. Após sucesso, guarda até dez pares de mensagens por usuário. Em falha não acrescenta o turno incompleto. Textos longos ainda podem exceder a janela do modelo.

O histórico fica em `historicos_por_usuario`, por processo, e desaparece ao reiniciar. Usuários distintos não compartilham sua lista. As memórias externas aceitam textos ou dicionários com `texto`/`content` e não são copiadas como mensagem de sistema permanente. Entretanto, mensagens do usuário e respostas do modelo podem repetir os fatos, mantendo-os no histórico.

Na API, `Conversador` processa regras, recupera memórias e chama `AgenteLocal`. Esse fluxo está implementado; o agente não decide sozinho o que persistir. A lista vazia `memorias=[]` significa apenas ausência de contexto recuperado naquela chamada, não um comando de exclusão.

## Adaptadores e configuração

`ModeloLLM` define `gerar(mensagens) -> str`. Adaptadores podem oferecer `gerar_com_detalhes()` com resposta e tokens; métricas ausentes não devem ser interpretadas como custo zero. O adaptador Ollama legado pode devolver zero para metadados ausentes; P3/P6 tratam esses zeros como não verificados.

| Provedor | Implementação | Configuração |
|---|---|---|
| Ollama | `src/modelos/ollama_adapter.py` | Serviço/modelo local; `OLLAMA_HOST` é lido pelo cliente Ollama |
| OpenAI | `src/modelos/openai_adapter.py` | Modelo permitido e `OPENAI_API_KEY` no ambiente; opcional |

Na API, `LLM_PROVIDER`, `LLM_MODEL` e `MODELOS_PERMITIDOS` controlam a seleção pelo catálogo. `AgenteLocal` só instancia Ollama/OpenAI e recusa identificadores de modelo vazios ou com espaços externos. Ele não consulta instalação ou disponibilidade antes da geração; a allowlist pertence ao catálogo da API. Não há equivalência presumida entre modelos de provedores diferentes.

O Compose lê `.env`; a aplicação Python local usa `os.getenv` e não carrega esse arquivo automaticamente. O guia já contém o comando PowerShell para exportá-lo antes do `uvicorn` e do avaliador. Nunca versione `.env`, tokens ou chaves. Os testes usam credenciais fictícias. O suporte OpenAI não torna necessária uma chamada paga; a validação final deve preservar a execução local a custo zero.

## Timeout e falhas

Ambos os adaptadores configuram timeout de 60 segundos por requisição do cliente. Esse timeout não é um prazo total para um experimento. O supervisor do baseline histórico também impõe prazo ao processo; parâmetros e limites estão no guia. Não há fallback automático entre provedores.

| Falha | Tratamento no agente/API |
|---|---|
| Conteúdo vazio, ausente ou não textual | `RespostaModeloVaziaError`; `RespostaOpenAIVaziaError` herda dela; `AgenteLocal` converte para `503 provedor_indisponivel` |
| Conexão ou erro HTTP do provedor | Convertido para `503 provedor_indisponivel`, sem detalhe sensível na mensagem pública |
| Timeout | Convertido para `504 provedor_timeout` |
| OpenAI sem chave | `503 provedor_nao_configurado` |
| Provedor sem adaptador ou identificador de modelo inválido | `400 modelo_nao_permitido` |

Os tipos legados de conexão/timeout dos adaptadores foram preservados para compatibilidade. A ligação `AgenteLocal` normaliza a resposta pública; o contrato de endpoints e `src/api/erros.py` não precisaram mudar. Após falha, o histórico anterior permanece e uma nova tentativa pode funcionar; falha não é convertida em resposta textual nem aprovação experimental.

## Exclusão individual: reset integrado e limites restantes

Em 12/11, `src/api/main.py:esquecer_uma()` chamava apenas `memoria.esquecer()`, sem notificar o agente. A PR #43, integrada em `2be5d51`, acrescentou `conversador.nova_sessao(usuario_id)` após uma exclusão bem-sucedida. O histórico inteiro desse usuário é invalidado; um ID inexistente retorna 404 sem disparar reset. Não há invalidação seletiva de mensagens.

Os testes isolados em `tests/test_agent.py` reproduzem o resíduo e comprovam que `limpar_historico(usuario_id)` remove as mensagens daquele usuário, preservando outros usuários. Os testes de API da #43 verificam o acionamento do reset na rota; não são observação da RAM da API em execução real.

Na sondagem inicial de 14/11, o ID foi removido do SQLite e a busca ficou sem contexto, mas a resposta inventou Belo Horizonte. Após exclusão total, inventou São Paulo. Nenhuma era o fato apagado. Na [continuação da validação](validacao-entrega-docker.md#continuação--correção-da-abstenção-14112026), foi implementada uma política local para consultas pessoais diretas reconhecidas: sem suporte na mensagem, histórico do usuário ou memória recuperada, responde `DESCONHECIDO` antes de consultar o modelo. Perguntas gerais e suporte disponível continuam na geração; perguntas mistas preservam a parte geral. A versão final passou nas 65 verificações reais, sem certificar toda formulação de linguagem natural ou a RAM. O candidato baseado apenas em instruções falhou e foi descartado.

O DELETE individual não remove outras versões da mesma chave. A exclusão total removeu inclusive a linha substituída neste teste. Múltiplos workers e eventual invalidação seletiva exigem alinhamento de contrato/arquitetura com Paloma e Vinicius.

Validação necessária: pelo endpoint real, guardar um fato, fazê-lo aparecer em resposta, excluir a memória e inspecionar o próximo contexto do agente, cobrindo mensagem do usuário, resposta do assistente, isolamento e registros substituídos. Observar somente busca/banco vazio não comprova ausência na RAM. A observação deve ocorrer no processo real da API; importar o módulo em outro processo não observa o mesmo histórico.

Outra dependência de Paloma: `Catalogo.listar/resolver` verifica configuração de chave/allowlist, mas pode anunciar um provedor sem adaptador como configurado. `AgenteLocal` recusa a geração, porém a listagem precisa distinguir configuração e capacidade implementada. O catálogo não foi modificado. A descrição antiga de carregamento único do índice no README foi corrigida conforme `_carregar_indice_usuario`, que reconstrói o índice dos ativos. A limitação documentada do PATCH de metadados continua pertinente.

## Validação e limites

```powershell
python -B -m pytest tests/test_agent.py tests/test_agente_provedores.py tests/test_ollama_adapter.py tests/test_openai_adapter.py -q
```

Os testes dos provedores substituem os clientes de rede, exercitam adaptadores reais e verificam respostas vazias, conexão, HTTP, timeout e preservação do histórico. O teste de integração HTTP usa FastAPI em processo com memória em RAM: comprova o contrato 503 sem abrir SQLite nem chamar serviços externos.

A suíte completa, o julgador P4-v3 e a inspeção estrutural P6 estão no guia. Testes simulados não validam disponibilidade, credenciais reais, instalação do modelo, qualidade da geração nem persistência em infraestrutura real. Não houve nova rodada real de Ollama/OpenAI ou avaliação final nesta implementação. Os resultados históricos permanecem com seus limites e versões originais.
