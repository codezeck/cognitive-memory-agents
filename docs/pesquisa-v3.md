# Pesquisa v3 — texto consolidado

## Introdução

Assistentes de linguagem precisam selecionar quais informações de uma interação anterior devem permanecer disponíveis em uma nova sessão. Reenviar o histórico integral aumenta o volume de contexto, enquanto descartar conversas anteriores prejudica a continuidade. Além disso, fatos mudam: uma informação anteriormente válida pode precisar ser substituída ou removida. O problema investigado neste projeto é como integrar uma memória externa ao contexto de um assistente, preservando a separação entre usuários e tornando observáveis atualização, recuperação e esquecimento.

O objetivo é desenvolver e avaliar um chatbot com memória persistente, usando um modelo local como caminho de execução a custo zero. A pergunta de pesquisa proposta é: **como a seleção de memórias altera a qualidade das respostas e o consumo de tokens em comparação ao envio do histórico completo, incluindo situações de atualização e exclusão?** A hipótese de redução de contexto deve ser testada junto com qualidade, cobertura e custos de aquisição; ela não é uma conclusão antecipada de economia total ou de manutenção do acerto.

O projeto integra três frentes de trabalho: Ezequiel da Silva Manço atua em agente, contexto, provedores e avaliação; Vinícius Silva Dos Santos em regras, conflitos e recuperação; Paloma Quimbely de Lima Silva em API, persistência e infraestrutura. O estudo considera o funcionamento conjunto dessas frentes e distingue os testes de engenharia, a qualidade das respostas e as evidências operacionais de armazenamento.

## Referencial teórico

Vaswani et al. (2017) apresentam a arquitetura Transformer baseada em atenção, uma referência para a discussão de modelos de linguagem. Isso contextualiza o componente gerador do projeto; o grupo não treinou um Transformer nem avaliou sua arquitetura interna.

A extensão de uma janela de entrada não garante uso uniforme de todas as informações. Liu et al. (2024) observam variação de desempenho conforme a posição da informação em contextos longos. O resultado motiva comparar histórico integral e contexto selecionado, mas não demonstra que a mesma magnitude de efeito ocorre no modelo local usado aqui.

Lewis et al. (2020) combinam memória paramétrica e recuperação em uma arquitetura RAG. A relação com este projeto é conceitual: recuperar informação externa para condicionar a geração. Nossa implementação não reproduz o treinamento, o índice de Wikipedia ou o recuperador neural daquele artigo; utiliza fatos sintéticos associados ao usuário e regras próprias de atualização.

Packer et al. (2023) propõem gerenciamento de diferentes níveis de memória para ampliar o contexto utilizável em interações e documentos. Sumers et al. (2023) organizam agentes por componentes de memória, ações e decisão no framework CoALA. Esses trabalhos ajudam a distinguir histórico transitório, memória persistente e controle de execução. O nome do projeto não significa implementação de MemGPT ou de todo o framework CoALA.

Reimers e Gurevych (2019) descrevem embeddings de sentenças adequados a comparações de similaridade. O conceito fundamenta a distinção entre semelhança lexical e semântica. O projeto possui um benchmark com embedder semântico e um hash lexical determinístico; o resultado de um não pode ser atribuído ao outro, nem à geração do chatbot.

As bibliotecas Python oficiais de Ollama e OpenAI são referências de integração com provedores. No trabalho, elas sustentam a origem dos clientes utilizados, não uma comparação experimental entre os serviços nem a validação de versões futuras dos SDKs. Os contratos efetivamente usados estão no código e nas dependências do repositório. Ollama e OpenAI são identificadas nas referências de documentação oficial.

## Arquitetura v3

O sistema recebe mensagens e identidade do usuário pela API FastAPI, valida autorização e coordena regras, recuperação e geração. O gerenciador identifica fatos reconhecidos, substitui valores atuais e executa pedidos de esquecimento no escopo definido. O armazenamento persistente é SQLite; fatos ativos e versões substituídas pertencem a uma identidade. A implementação utiliza busca por chave em consultas pessoais reconhecidas e EmbedderHash no fallback. O benchmark com embedder semântico é separado e não representa a configuração padrão da API.

O histórico transitório é mantido em RAM por usuário e processo, com até dez interações armazenadas. Na política compacta v3, a seleção geral envia até três turnos recentes e respeita um orçamento de seis mil caracteres apenas para esse histórico. Sistema, memórias recuperadas e pergunta atual não estão incluídos nesse orçamento. Consultas diretas com suporte recuperado podem omitir o histórico redundante. O limite de caracteres não equivale à janela total do modelo em tokens. O baseline conserva o histórico completo do episódio para a comparação.

O contrato ModeloLLM separa a lógica do agente do SDK do provedor. A operação textual gerar é complementada por gerar_com_detalhes, que permite observar tokens quando reportados pelo backend. A entrega usa Ollama e qwen2.5-coder:3b. OpenAI mantém um adaptador opcional, testado com clientes simulados, sem avaliação real desse serviço. O estudo não compara provedores e não presume tokenização, custo ou qualidade equivalentes.

O caminho padrão inicia Ollama, preparação e API em contêineres. O preparo confirma disponibilidade e carregamento do modelo e mantém credenciais aleatórias em volume privado. Os dois perfis da interface são sintéticos e usam cookie HttpOnly; as rotas de usuário continuam verificando autorização. Pesos, banco e credenciais possuem volumes distintos. A publicação é restrita ao loopback para a demonstração local, sem identidade individual de produção.

A CLI simples do agente mantém conversa em RAM e não substitui o fluxo persistente da API. A continuidade é verificada em novas sessões e em reinícios reais do processo. A exclusão individual remove um ID e limpa o histórico, podendo deixar outras versões armazenadas; a exclusão total remove todas as linhas do usuário, inclusive inativas. Resposta sem o alvo, busca vazia, estado do banco e estado do histórico são evidências distintas.

## Protocolo e métricas

O protocolo separa testes de engenharia, recuperação de memórias, conteúdo das respostas e custo de geração. Há quatro condições no comparativo: pergunta sem memória, histórico completo, memória pré-carregada com estado esperado e memória adquirida automaticamente pela conversa. A condição pré-carregada é um controle de recuperação/geração e não mede aquisição conversacional. O modelo e o backend são mantidos iguais nas condições comparadas.

P3 registra tokens de entrada e saída por ingestão, pergunta e sessão completa, com cobertura e proveniência. Somente pares equivalentes e completamente medidos entram na redução percentual. Tokens ausentes continuam desconhecidos. Uma operação local só permite derivar zero de geração quando origem e contagem observada são explícitas e coerentes; regras, hashing, banco e infraestrutura continuam tendo custo computacional fora dessa unidade.

P4 julga critérios determinísticos de factualidade, formato, abstenção e proibições anotadas. P5 agrega taxas com denominadores verificados, não verificados e não aplicáveis. Uma resposta fora da gramática não vira erro semântico por definição. A revisão humana complementar deve identificar autor, data e justificativa e permanecer separada dos resultados originais. Na rodada P6 v3, doze respostas do baseline exigem esse tratamento.

A P6 utiliza quatro usuários sintéticos com cinco sessões cada e vinte e uma perguntas por cenário. A orquestração observa persistência após reinício, exclusão, recuperação lexical e respostas. Dezenove checkpoints possuem fatos não vazios; uma oportunidade posterior à exclusão verifica consistência de estado vazio, separadamente. As duas ações de exclusão têm checkpoints próprios. O observador RAM é opt-in, identifica o processo/instância e não representa toda a memória da máquina.

As fontes e os protocolos foram identificados antes das respectivas medições. Rodadas anteriores usadas para corrigir o sistema são material de desenvolvimento. A validação sintética v3 tem dezesseis casos e três repetições, elaborados com conhecimento do domínio; não constitui teste cego ou independente. A primeira tentativa interrompida e todos os resultados negativos foram preservados. Repetições dos mesmos casos não são usuários independentes e não permitem afirmar equivalência estatística.

## Metodologia v3

A versão v3 mantém a API e as operações reais de memória, mas separa confirmação de armazenamento e geração de linguagem. Quando a mensagem inteira é coberta por regras de gravação, atualização ou exclusão, a API executa a operação e devolve uma confirmação local. A origem dessa resposta e a contagem zero de chamadas são informadas explicitamente. Perguntas factuais com suporte e tarefas gerais continuam sendo respondidas pelo modelo. Essa mudança evita pagar em tokens de geração por uma confirmação que não exige inferência linguística. Regras, armazenamento e recuperação continuam consumindo CPU e memória; não são custo computacional zero.

A busca e a verificação de suporte compartilham os atributos reconhecidos. Uma consulta pessoal direta pode recuperar por chave um fato atual, mesmo quando a pergunta usa outra palavra, como ocupação em lugar de profissão. Registros com texto canônico também podem fornecer suporte sem uma chave tipada. Quando a consulta direta possui evidência recuperada, o agente envia o fato atual com um prompt breve e pede somente o valor solicitado. O histórico redundante é omitido nessa condição; perguntas de continuidade e tarefas mistas preservam a janela recente. Não há consulta a gabaritos experimentais pelo produto.

A negação por valor é resolvida apenas quando identifica uma única chave ativa do próprio usuário. Uma menção a um valor antigo não elimina seu substituto, e uma referência ambígua não escolhe silenciosamente uma chave. Esquecer uma chave remove também as versões substituídas. A confirmação da operação não reintroduz o alvo no histórico; após pedidos mistos com esquecimento, o turno gerado é limpo. Essa política é delimitada e não interpreta toda a linguagem natural.

O baseline mantém a geração por mensagem e o histórico completo do episódio, ressalvadas as abstenções locais já existentes. O reconhecimento de suporte também foi corrigido nesse caminho para aceitar fatos válidos sobre filhos, profissão e viagem. A diferença entre confirmação local e geração é parte da arquitetura comparada e deve ser declarada. A redução observada não pode ser atribuída exclusivamente à compressão do prompt ou a uma alteração isolada.

Os conjuntos de rodadas anteriores passaram a ser material de desenvolvimento. A validação nova contém dezesseis casos sintéticos, três repetições e quatro cenários. Foi elaborada com conhecimento do domínio e não é cega nem independente da equipe. A primeira tentativa foi interrompida após uma verificação de suporte do baseline revelar uma lacuna; o log parcial foi preservado e a correção foi medida em nova saída. Uma anotação numérica admite o numeral 4, mas não a palavra equivalente Quatro; essa limitação permaneceu explícita, sem alteração retrospectiva de aliases após observar respostas.

Na P6, foram mantidos os quatro usuários sintéticos, vinte sessões e vinte e uma perguntas por cenário. O coletor inicia API e SQLite próprios, com um worker, e identifica as fontes e o modelo. São observados ativos e substituídos no banco, histórico no processo correto e identidade da instância antes e depois dos reinícios. O checkpoint vazio após exclusão verifica consistência do vazio e fica separado da persistência de fatos não vazios. Esses procedimentos não representam certificação jurídica nem observação de todos os buffers externos ao processo.

## Resultados v3

A P6 v3 completou quarenta registros de sessão e quarenta e duas respostas, sem falhas técnicas. Na memória automática, as vinte e uma respostas foram aprovadas pelo P4, sem julgamentos não verificados. No baseline, oito foram aprovadas, uma reprovada e doze ficaram não verificadas pela gramática do julgador. Portanto, oito aprovações não significam que apenas oito respostas sejam semanticamente corretas: a cobertura parcial impede converter as demais diretamente em erros e exige revisão textual separada.

O custo completo foi de 3.593 tokens na memória automática e 22.228 no histórico completo, redução de 83,84% nos vinte pares de sessão medidos. Foram observadas 23 invocações do adaptador e trinta operações locais na condição automática, contra cinquenta invocações e três abstenções locais no histórico. A contagem de adaptador não quantifica todas as tentativas internas de SDKs. Os campos nulos só permitem derivar zero quando a origem e a contagem zero são explícitas e coerentes. Ingestão e perguntas integram o custo da sessão.

Os dezenove checkpoints não vazios comprovaram persistência no escopo observado após reinício real, os dois checkpoints de exclusão foram verificados e o checkpoint vazio foi consistente. Não foram observadas ocorrências dos alvos esquecidos nas quatro respostas elegíveis da memória automática. Esses resultados comprovam o roteiro medido; ausência literal nas respostas não equivale a ausência de toda cópia em RAM, disco ou outros processos.

Na bateria sintética de dezesseis casos e três repetições, a memória automática teve 48 aprovações em 48 tentativas, contra 36 no baseline. O baseline concluiu 47 tentativas e teve um timeout. A comparação de tokens usa somente os 47 pares medidos: 6.025 tokens na automática e 39.844 no histórico, redução de 84,88%. O total dos 48 casos automáticos foi 6.212, mas esse número não deve ser dividido pelo subtotal do baseline para inventar uma comparação completa. O custo perdido no timeout permanece desconhecido.

O controle de memória pré-carregada também teve 48 aprovações, mas recebe um estado fornecido pelo experimento e não mede aquisição conversacional. O controle sem memória avalia sobretudo abstenção e não permite concluir que remover a memória seja a melhor arquitetura. As três repetições dos mesmos casos não representam quarenta e oito usuários independentes. As taxas automáticas continuam condicionadas à gramática do P4; o caso numérico Quatro exemplifica uma possível reprovação sem erro semântico.

## Erros e alcance

Três falhas anteriores orientaram o desenvolvimento: recuperação perdida em paráfrases sobre residência ou veículo; manutenção de um carro após negação por valor não reconhecida; e resposta com quantidade correta de gatos, mas um nome inventado. As respostas originais, inclusive resultados negativos da v2, continuam disponíveis. A v3 amplia o reconhecimento e reduz a oportunidade de acrescentar detalhes não solicitados, mas as baterias conhecidas não se tornam testes reservados após serem usadas para correção.

O estudo não isola o efeito causal de confirmação local, recuperação, prompt e histórico, porque as mudanças foram avaliadas em conjunto e o modelo é estocástico. O backend Ollama é compartilhado no host, embora as chamadas de cada bateria sejam sequenciais. A latência não é benchmark de hardware isolado. Os dados são sintéticos; resultados de uma rodada P6 e três repetições curtas não provam equivalência estatística, segurança universal ou generalização para qualquer formulação pessoal.

## Conclusão v3

A versão v3 demonstrou continuidade, atualização e esquecimento no roteiro P6 e ultrapassou a meta adicional de redução de 30% dos tokens nos vinte pares medidos. A memória automática teve vinte e uma respostas aprovadas pelo julgador, enquanto a avaliação do baseline manteve doze julgamentos não verificados. A redução inclui evitar geração nas confirmações de operações já resolvidas pelas regras e limitar o contexto de consultas diretas. O componente de linguagem continua produzindo respostas factuais com suporte e conversas gerais.

A contribuição é um percurso local reproduzível que separa fatos persistidos, histórico, geração e evidência operacional. Permanecem limites de gramática, referências ambíguas, metadados inconsistentes e avaliação automática. Os ensaios anteriores negativos são parte da pesquisa, e não foram apagados para sustentar a conclusão nova. A publicação da versão do software, sua revisão humana e a execução de testes no GitHub são itens de entrega distintos da qualidade observada do modelo.

O grupo possui três integrantes, composição confirmada pelo usuário. O código e a documentação próprios são disponibilizados sob MIT, com autorização do grupo; o modelo Qwen2.5-Coder-3B-Instruct mantém sua licença Qwen Research, voltada a pesquisa e avaliação não comerciais. As dependências conservam seus termos e avisos. Trabalhos futuros incluem conjuntos realmente independentes, mais diversidade linguística, análise de custo computacional além de tokens e cobertura de múltiplos workers. Essas extensões não são apresentadas como resultados já obtidos.


## Apêndice A

Este apêndice identifica os materiais produzidos pelo grupo que permitem conferir a pesquisa. O código e a documentação estão no repositório codezeck/cognitive-memory-agents, branch da candidata fix/confiabilidade-contexto-memoria. O marcador final v1.0 e sua execução de CI devem ser associados ao código aprovado, conforme o checklist; a pesquisa não declara uma revisão humana inexistente.

O roteiro técnico de reprodução está em docs/reproduzir-avaliacao-v3.md. Ele utiliza docker-compose.avaliacao.yml, monta o código somente para leitura e grava uma rodada nova em diretório próprio. O comparativo executa os dezesseis casos com três repetições e quatro cenários. O coletor P6 inicia API e SQLite temporários e percorre os quatro usuários, cinco sessões por usuário e vinte e uma perguntas em cada cenário.

As fontes experimentais são eval/dataset_validacao_v3_20261118.json, eval/memoria/sessoes.json e eval/memoria/anotacoes_p6.json. O protocolo e os hashes anteriores à execução estão em docs/revisao-experimental/protocolo-contexto-v3-20261118.json e nos congelamentos preservados. As anotações não são fornecidas como respostas ao modelo.

Os resultados brutos da P6 estão em evidencias/contexto-v3-20261118/p6-r01/eventos.jsonl e resumo.json, acompanhados de configuração, logs e snapshots. O comparativo está em validacao-nova-r02-3rep.json na pasta contexto-v3-20261118. O índice entrega-v3-20261118 liga tabelas, gráficos, CSV e manifesto SHA256 aos originais. Fontes históricas de resultados ruins não foram sobrescritas.

A revisão humana complementar das doze respostas não verificadas do baseline pode ser registrada em docs/revisao-experimental/revisao-humana-baseline-v3.csv. Os campos de parecer, autor e data permanecem em branco até revisão real. Essa análise não deve alterar retrospectivamente o JSON ou os aliases do julgador. O registro de uso de IA está em PROMPTS.md, com contexto disponível e modelo para coleta das conversas dos demais integrantes.
