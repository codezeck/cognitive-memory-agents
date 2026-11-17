# Decisão autorizada: contagem das respostas sem geração

Situação observada: a guarda local pode responder `DESCONHECIDO` sem consultar o modelo. A API preserva `tokens_entrada: null` e `tokens_saida: null`; os protocolos P3/P6 tratam isso como medição desconhecida. O ensaio anterior comprovou zero chamadas por traço externo, mas esse conhecimento não acompanha cada resposta do comparativo. Converter todo `null` em zero seria incorreto.

Proposta autorizada pelo usuário nesta conversa em 14/11/2026 e implementada como extensão compatível: acrescentados dois campos **opcionais** na resposta de conversa e no resultado interno do agente:

- `origem_uso`: `politica_local`, `provedor` ou `provedor_com_abstencao_local`.
- `chamadas_modelo_observadas`: 0 quando a resposta termina antes da invocação do adaptador; 1 quando há uma invocação observada com resposta. Não representa retries HTTP internos do SDK.

Os campos antigos de tokens permanecem inalterados, inclusive `null` nas respostas locais. Somente o novo par explícito `politica_local` + inteiro 0 permitiria ao avaliador derivar consumo de geração zero, com origem registrada. Ausência, inconsistência ou zeros do provedor continuam desconhecidos. Pergunta mista que chama o modelo mantém o consumo real do provedor, sem atribuir tokens gerados por IA ao prefixo local.

Foram acrescentadas propagação API/transportes e validação estrita de origem. A agregação é identificada como `p3-uso-local-v1`. Os resultados anteriores permanecem preservados e não são preenchidos retrospectivamente. Origem ausente conserva o comportamento legado; metadados contraditórios permanecem desconhecidos. A avaliação continua sujeita aos critérios prévios e às revisões dos dados. A autorização do usuário não constitui revisão humana de Paloma/Vinicius nem aprovação de PR.

A alternativa de conservar apenas o contrato anterior foi superada pela autorização acima. A instrumentação de RAM não substitui esses metadados de geração; os bloqueios de revisão experimental permanecem.
