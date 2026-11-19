# Pacote de revisão experimental, não liberado para execução

**Estado atualizado em 18/11:** o usuário autorizou resolver as decisões nesta sessão. A [decisão local](decisao-20261118.md) e o protocolo com hashes permitiram uma rodada P6 real com coleta automática; a cópia anotada dos dez casos separados também foi executada. Os textos abaixo e os arquivos `.proposta.json` preservam a preparação anterior e não representam o estado atual de execução. Não houve aprovação atribuída a Vinícius ou Paloma. Consulte os [resultados atuais](../melhorias-avaliacao-20261118.md); revisão humana cruzada permanece um requisito acadêmico separado.

Preparado em 14/11/2026. O usuário informou que existe revisão registrada e que fornecerá a referência; ela ainda não foi recebida. Nenhum arquivo desta pasta representa aprovação de Vinicius/Paloma. Propostas usam `aprovado: false` e não são datasets executáveis.

| Item | Proposta/revisão necessária | Responsável pelo aceite |
|---|---|---|
| `u02/s5/esquecer_chaves` | Mensagem literal “Esqueça tudo sobre meu carro.”; confirmar escopo da chave carro e contrato operacional | Vinicius e Paloma |
| `u03/s4/pergunta3` | Luna/Simba como alvos de recuperação; “dois”/“2” como resposta de quantidade | Vinicius |
| Valores antigos, aliases e proibições | Conferir cada anotação e validade temporal, sem ajustar pelo resultado do modelo | Vinicius |
| Dez casos reservados | Conferir proposta de atributos, categorias, aliases e proibições; 10 compatíveis estruturalmente não significa 10 corretos semanticamente | Vinicius |
| `u04/s4` vazio | Separar consistência do estado vazio de persistência de dados não vazios; o classificador atual continua não verificado para vazio | Paloma e Vinicius |
| Evidências operacionais | Vincular execução/evento, snapshots SQLite, reinício real e observação RAM de um único worker | Paloma |

Os arquivos [p6.proposta.json](p6.proposta.json) e [metadados-reservados.proposta.json](metadados-reservados.proposta.json) mantêm hashes das fontes. O gerador `tools/preparar_revisao_experimental.py` fez somente preparação estrutural, sem chamar modelo/HTTP. Os datasets oficiais continuam inalterados.

Ao chegar a referência: registrar autor, data, URL/identificador e itens efetivamente aprovados; confrontar com hashes atuais; incorporar somente o escopo aprovado em mudança revisável; rodar validadores e congelar fontes/configuração. Aprovação de critérios ou de metadados opcionais de tokens não substitui essa revisão. Não marcar automaticamente `aprovado: true` com base na afirmação de existência de revisão.

Antes da P6: instância e banco próprios; nomes de usuários sintéticos distintos; estado inicial capturado; observador RAM habilitado somente para esses usuários; um worker identificado; evidência de reinício no mesmo volume e de exclusão por camada; critérios de 30%/5 p.p./nenhum novo vazamento ou desatualização previamente definidos. Usar o [plano P6](../plano-execucao-p6.md) e o [guia](../guia-avaliacao.md), preservando suas barreiras. Não executar os dez casos reservados para aperfeiçoar o sistema.
