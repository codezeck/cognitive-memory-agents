"""Resume a v3 sem mudar gabaritos, resultados anteriores ou o julgador."""
import csv
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / 'evidencias/contexto-v3-20261118'


def main():
    validacao = json.loads((PASTA / 'validacao-nova-r02-3rep.json').read_text(encoding='utf-8'))
    p6 = json.loads((PASTA / 'p6-r01/resumo.json').read_text(encoding='utf-8'))
    registros = [json.loads(l) for l in (PASTA / 'p6-r01/eventos.jsonl').read_text(encoding='utf-8').splitlines()]
    perguntas = [r for r in registros if r['tipo'] == 'resultado' and r['evento']['tipo'] == 'pergunta']
    tokens = p6['comparacoes_tokens']['sessao']['tokens_total']
    linhas = ['# Acertos e tokens: contexto v3 — 18/11/2026', '',
              'Versão posterior à [rodada v2](melhorias-avaliacao-20261118.md). Base Git `b912ab6`, '
              'árvore local identificada nos manifestos. Ollama real, mesmo modelo `qwen2.5-coder:3b`, '
              'API e banco descartáveis. Dados e gabaritos P6 originais preservados.', '',
              '## Mudanças do produto', '',
              '- Operações de memória inteiramente reconhecidas recebem confirmação local. Salvar, atualizar '
              'e apagar continuam executando o armazenamento; apenas a confirmação deixa de invocar o gerador. '
              'Perguntas factuais e tarefas gerais continuam usando o modelo quando há suporte.',
              '- Operações locais informam origem explícita e zero chamadas. Tokens nulos não são convertidos '
              'em zero sem essa prova. As regras, o banco e os embeddings têm custo computacional que não é '
              'medido em tokens do gerador.',
              '- Consultas diretas com evidência recuperada usam prompt breve, fatos atuais e pedido de resposta '
              'restrita ao valor. O histórico redundante não entra nessa consulta; perguntas de continuidade '
              'e tarefas mistas preservam a janela recente.',
              '- Busca e verificação de suporte compartilham atributos e formas canônicas. A busca aceita '
              'também registros com chave personalizada cujo texto canônico fornece suporte; não há tratamento '
              'especial para IDs de casos, sementes de avaliação ou respostas esperadas.',
              '- Negação por valor remove todas as versões da chave apenas quando identifica uma única chave '
              'ativa do próprio usuário. Uma referência antiga ou ambígua não remove o fato novo.',
              '- Confirmação de esquecimento não recoloca o alvo na RAM. Após pedido misto com esquecimento, '
              'o turno gerado também é limpo para não manter resíduos.', '',
              '## Bateria de validação sintética', '',
              'Dezesseis casos, três repetições e quatro cenários: 192 tentativas. Os exemplos anteriores passam '
              'a ser material de desenvolvimento. Esta bateria usa valores e trajetórias novos, mas foi escrita '
              'com conhecimento do domínio; não é teste cego ou validação independente. A primeira tentativa '
              'foi interrompida para corrigir suporte de fatos válidos no baseline; o log parcial foi preservado '
              'e a rodada final usa nova saída. Não há resultado final para a tentativa interrompida.', '',
              '| Cenário | Aprovados P4 | Tentativas | Falhas técnicas | Tokens de ingestão | Tokens da sessão |',
              '|---|---:|---:|---:|---:|---:|']
    for c, s in validacao['resumo'].items():
        ingestao = s['tokens_por_etapa']['ingestao']['tokens_total']
        total = s['tokens_total']
        linhas.append(f"| {c} | {s['aprovados']} | {s['casos']} | {s['falhas']} | {ingestao if ingestao is not None else 'desconhecido'} | {total if total is not None else 'desconhecido'} |")
    a = validacao['resumo']['memoria_regras_api']
    h = validacao['resumo']['historico_completo']
    comparacao = validacao['comparacoes_tokens']['memoria_regras_api']['sessao']['tokens_total']
    economia = comparacao['reducao_pct']
    linhas += ['', f"Memória automática: **{a['aprovados']}/{a['casos']}** aprovações P4; "
               f"histórico: **{h['aprovados']}/{h['casos']}**. Economia de tokens completos: **{economia}%** "
               f"em **{comparacao['pares_medidos']}/{comparacao['pares_identificados']} pares medidos**. "
               'O controle pré-carregado não mede aquisição e não substitui a comparação principal.', '',
               'Se houver falha técnica, o custo completo desse caso continua desconhecido e não entra na '
               'comparação de tokens. Subtotais observados não são tratados como custo completo; a economia '
               'em pares medidos não representa uma medição dos pares ausentes.', '',
               'Há uma limitação identificada na anotação numérica nova: o esperado é `4` e o modelo do '
               'baseline pode responder `Quatro`. Esse equivalente não foi adicionado retrospectivamente '
               'aos aliases. O JSON/P4 original permanece preservado; não interpretar automaticamente '
               'toda reprovação desse caso como erro semântico do modelo.', '',
               '## P6: continuidade, custo completo e qualidade', '',
               f"Foram coletadas {len(p6['sessoes'])} sessões e {len(perguntas)} respostas, com "
               f"{p6['falhas']} falhas técnicas. Modelo, fontes, estados do SQLite, RAM e reinícios estão vinculados "
               'à execução. Mantêm-se 21 perguntas por cenário, sem substituir as anotações oficiais.', '',
               '| Cenário | Aprovados P4 / 21 | Não verificados | Chamadas observadas ao modelo | Operações locais |',
               '|---|---:|---:|---:|---:|']
    contagens = {}
    for c in ('memoria_automatica', 'historico_completo'):
        rs = [r for r in perguntas if r['cenario'] == c]
        chamadas = [r['resultado'] for r in registros if r['tipo'] == 'resultado' and r['cenario'] == c
                    and r['evento']['tipo'] in {'fato', 'pergunta', 'esquecer_chaves'}]
        assert all(type(r.get('chamadas_modelo_observadas')) is int for r in chamadas)
        valor = {'aprovados':sum(r['julgamento']['passou'] for r in rs),
                 'nao_verificados':sum(r['julgamento']['revisao_necessaria'] for r in rs),
                 'chamadas_modelo':sum(r['chamadas_modelo_observadas'] for r in chamadas),
                 'operacoes_locais':sum(r.get('origem_uso') == 'politica_local' for r in chamadas)}
        contagens[c] = valor
        linhas.append(f"| {c} | {valor['aprovados']} | {valor['nao_verificados']} | {valor['chamadas_modelo']} | {valor['operacoes_locais']} |")
    linhas += ['', f"Sessões completas: **{tokens['tokens_automaticos']} tokens** com memória e "
               f"**{tokens['tokens_historico']}** no histórico; economia de **{tokens['reducao_pct']}%**, "
               f"com **{tokens['pares_medidos']}/{tokens['pares_previstos']} pares medidos**. "
               'A economia inclui arquitetura de confirmação local, recuperação, prompt e histórico; '
               'não é atribuída somente à compressão textual.', '',
               'O baseline mantém geração a cada mensagem, ressalvadas abstenções locais já existentes, '
               'e conserva todo o histórico do episódio. O reconhecimento de suporte foi corrigido para '
               'preservar também suas afirmações válidas sobre filhos, profissão e viagem.', '',
               '### Checkpoints e métricas complementares', '',
               '```json', json.dumps({'checkpoints':p6['metricas_checkpoints'],
                                      'vazio':p6['consistencia_estado_vazio'],
                                      'respostas':p6['metricas_resposta']}, ensure_ascii=False, indent=2), '```', '',
               'O custo contabiliza ingestão e perguntas, com tokens de entrada e saída. Ausência de '
               'ocorrência de um alvo nas respostas não certifica toda a RAM ou conformidade jurídica. '
               'Os checkpoints observam um worker e o SQLite dedicado; estado vazio é separado da '
               'persistência de fatos não vazios.', '',
               '## Limites e reprodução', '',
               'As regras e a gramática ainda são limitadas. Negação por referência ambígua exige '
               'reformulação do usuário. Texto não reconhecido segue para o modelo; confirmações locais '
               'não significam que toda mensagem possível tenha sido compreendida. Memórias fornecidas '
               'manualmente e metadados contraditórios exigem cuidado. O orçamento de histórico continua '
               'em caracteres, não é garantia sobre a janela total em tokens.', '',
               'Uma rodada P6 e três repetições de casos sintéticos não comprovam equivalência estatística '
               'ou generalização para todos os usuários. O backend Ollama é compartilhado no host, embora '
               'as chamadas destas baterias sejam sequenciais; latência não é benchmark de hardware isolado. '
               'Os resultados da v2 não foram sobrescritos. Comparações entre versões não isolam '
               'causalmente cada alteração nem removem variabilidade do modelo.', '',
               '```powershell',
               'python -B -m src.interface.comparativo --dataset eval/dataset_validacao_v3_20261118.json --saida SAIDA_NOVA.json --repeticoes 3',
               'python -B -m tools.executar_p6_local --saida-dir PASTA_NOVA --commit-base b912ab6 --protocolo docs/revisao-experimental/protocolo-contexto-v3-20261118.json',
               'python -B -m tools.resumir_contexto_v3', '```', '',
               'Nos ensaios, `OLLAMA_HOST=http://ollama:11434` em container descartável. '
               '[Decisão anterior à medição](revisao-experimental/decisao-contexto-v3-20261118.md), '
               '[validação original](../evidencias/contexto-v3-20261118/validacao-nova-r02-3rep.json), '
               '[P6 JSONL](../evidencias/contexto-v3-20261118/p6-r01/eventos.jsonl), '
               '[resumo P6](../evidencias/contexto-v3-20261118/p6-r01/resumo.json) e '
               '[respostas CSV](../evidencias/contexto-v3-20261118/respostas-p6.csv).', '',
               '## Aplicação local e validação de engenharia', '',
               '954 testes Python aprovados, 66 ignorados, oito testes JavaScript e lint crítico aprovados. '
               'As 38 fontes de src permanecem iguais às identificadas na P6. Após a validação, a API local '
               'foi reconstruída e reiniciada na porta 8002, com os mesmos volumes de banco e credenciais '
               'e sem reiniciar o Ollama. Saúde ok, chat HTTP 200 e versão memoria-contexto-v3 confirmados. '
               'Mudanças continuam na branch local, sem publicação no GitHub. O PDF anterior registra '
               'a rodada v2; o relatório atual é a referência para estes resultados.', '']
    csv_linhas = [{'cenario':r['cenario'], 'evento_id':r['evento']['id'], 'pergunta':r['evento']['texto'],
                  'resposta':r['resultado']['resposta'], 'passou_p4':r['julgamento']['passou'],
                  'revisao_necessaria':r['julgamento']['revisao_necessaria']} for r in perguntas]
    with (PASTA / 'respostas-p6.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(csv_linhas[0]))
        w.writeheader()
        w.writerows(csv_linhas)
    (RAIZ / 'docs/acertos-tokens-contexto-v3.md').write_text('\n'.join(linhas), encoding='utf-8')
    resumo = {'validacao':{'automatica':a['aprovados'], 'historico':h['aprovados'],
                          'tentativas':a['casos'], 'economia_tokens_pct':economia},
              'p6':contagens, 'p6_tokens':tokens,
              'validacao_tokens_pareados':comparacao,
              'dataset_sha256':hashlib.sha256((RAIZ/'eval/dataset_validacao_v3_20261118.json').read_bytes()).hexdigest()}
    (PASTA / 'resumo-leitura.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'validacao':resumo['validacao'],'p6':contagens,
                      'p6_tokens':{k:v for k,v in tokens.items() if k!='sessoes'}},ensure_ascii=False))


if __name__ == '__main__':
    main()
