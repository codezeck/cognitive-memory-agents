"""Deriva tabelas do ensaio de desenvolvimento sem rejulgar respostas."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PASTA=ROOT/'evidencias/entrega/20261114-entrega-ae9eb113'
d=json.loads((PASTA/'comparativo-desenvolvimento.json').read_text(encoding='utf-8'))
linhas=['# Comparativo exploratório de desenvolvimento - 14/11/2026','',
'Modelo real `qwen2.5-coder:3b`, Ollama isolado em Docker, CPU, sete casos conhecidos de desenvolvimento, três repetições e quatro cenários: 84 tentativas, sem falhas de execução. Não é P6 nem uso do conjunto reservado. Versões P4-v3, P5-v1 e p3-uso-local-v1. Critérios prévios: redução mínima de 30% da sessão, perda máxima de 5 p.p. e nenhum novo vazamento/desatualização.','',
'| Cenário | Conteúdo aprovado | Ingestão | Pergunta final | Sessão completa | Cobertura de tokens |',
'|---|---:|---:|---:|---:|---:|']
for c,s in d['resumo'].items():
    t=s['tokens_por_etapa']
    linhas.append(f"| {c} | {s['aprovados']}/21 | {t['ingestao']['tokens_total']} | {t['pergunta_final']['tokens_total']} | {t['sessao']['tokens_total']} | {t['sessao']['casos_medidos']}/21 |")
linhas += ['', '## Interpretação e alcance', '',
'A memória automática usou 17.094 tokens, contra 16.017 do histórico completo, nos mesmos 21 pares medidos: redução de -6,72%, ou aumento de 6,72%. Na pergunta final houve redução de 13,35% (5.633 contra 6.501), mas a ingestão aumentou de 9.516 para 11.461. Portanto, o critério de economia global não foi atingido. A presença de memórias no contexto e o histórico ainda mantido durante a ingestão podem acrescentar texto; a rodada não decompõe causalmente esses custos nem demonstra qual mudança produziria economia. Não reduzir artificialmente o denominador ou contabilizar só a última consulta.', '',
'O conteúdo aprovado foi 17/21 (80,95%) para automática e 12/21 (57,14%) para histórico, diferença de +23,81 p.p. Factualidade foi 12/15 e 9/15; abstenção foi 5/6 e 3/6. Ambos têm cobertura integral nesses subconjuntos. Nos seis casos elegíveis de esquecimento houve 0/6 ocorrências proibidas na automática e 2/6 no histórico. Não houve novo vazamento anotado na automática nesse subconjunto. A ausência de ocorrência não comprova exclusão no banco ou em toda RAM. A métrica atual de vazamento não substitui uma avaliação completa de desatualização em vinte sessões.', '',
'A memória pré-carregada usou 5.636 tokens e aprovou 17/21, mas não mede aquisição conversacional. Sua comparação oficial é somente a pergunta final: redução de 13,31%, também inferior à meta de 30%. Somar zero ingestão desse controle e chamá-lo de economia de produção seria enganoso. No cenário sem memória, 16/21 aprovações refletem principalmente a capacidade de abstenção, sem recuperação factual aplicável; não significam que remover memória é a melhor arquitetura.', '',
'As falhas mostram o limite da guarda local. Na automática, CMP006 respondeu DESCONHECIDO nas três repetições apesar de haver suporte esperado para Corolla. CMP004 inventou um time na primeira repetição. No histórico, CMP003 retomou Osasco em duas repetições após o esquecimento esperado, CMP005 falhou nas três e CMP006 absteve nas três. O caminho sem memória também produziu esporte/time inventados. Assim, o ensaio Docker da pergunta de cidade passou, mas a abstenção geral permanece reproduzível como falha em outras formas pessoais de desenvolvimento. Não alterar silenciosamente regras, anotações ou gramática para esconder esses resultados.', '',
'A recuperação textual exata marcou 0/15 porque os textos canônicos diferem, enquanto a equivalência anotada marcou 15/15 nas duas condições com memória. O estado ativo das regras coincidiu em 21/21. Isso localiza diferenças entre texto retornado, estado e resposta, sem equiparar busca correta a resposta correta. Para a pré-carregada houve um julgamento de abstenção não verificado; no sem memória também houve um. Essas lacunas ficam no JSON e não devem ser removidas das tabelas.', '',
'O modelo mostrou variação entre repetições, mas o estudo não estima equivalência estatística. O histórico aprovou 4/7 em cada repetição; a automática aprovou 5/7, 6/7 e 6/7. Foram repetidos sete casos, não observados 21 usuários independentes. As taxas do P4 julgam conteúdo, enquanto protocolo e formato têm campos próprios. Este ensaio não compara OpenAI, GPUs, outros modelos, línguas, grandes históricos ou usuários reais. Resultados negativos permanecem úteis para decidir uma futura revisão do orçamento de contexto, depois da análise coletiva, sem iniciar essa frente nesta etapa.', '',
'Fonte bruta: [comparativo-desenvolvimento.json](../evidencias/entrega/20261114-entrega-ae9eb113/comparativo-desenvolvimento.json); [log](../evidencias/entrega/20261114-entrega-ae9eb113/comparativo-desenvolvimento.log). As fontes históricas continuam inalteradas. A P6 segue bloqueada pela revisão documentada em [revisão experimental](revisao-experimental/README.md).','',
'## Todas as falhas de conteúdo observadas','',
'A tabela é derivada do booleano P4 `passou`, sem novo julgamento. “Não verificado” não foi convertido em acerto.','',
'| Cenário | Caso | Repetição | Resposta real | Esperado do protocolo |','|---|---|---:|---|---|']
falhas=[]
for r in d['resultados']:
    if not r['passou']:
        falhas.append({k:r[k] for k in ('cenario','id','repeticao','resposta','esperado')})
        campos=[str(r[k]).replace('|','/').replace('\n',' ') for k in ('cenario','id','repeticao','resposta','esperado')]
        linhas.append('| '+' | '.join(campos)+' |')
(ROOT/'docs/ensaio-desenvolvimento-20261114.md').write_text('\n'.join(linhas)+'\n',encoding='utf-8')
with (PASTA/'falhas-desenvolvimento.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['cenario','id','repeticao','resposta','esperado']);w.writeheader();w.writerows(falhas)
print(json.dumps({'tentativas':len(d['resultados']),'falhas_conteudo':len(falhas),'falhas_execucao':sum(s['falhas'] for s in d['resumo'].values())}))
