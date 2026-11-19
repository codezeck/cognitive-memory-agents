"""Figuras e tabela consolidadas dos resultados brutos preservados da v3."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
ENTREGA = RAIZ / 'evidencias/entrega-v3-20261118'


def main():
    figura = ENTREGA / 'figuras'
    figura.mkdir(parents=True, exist_ok=True)
    p6 = json.loads((RAIZ/'evidencias/contexto-v3-20261118/p6-r01/resumo.json').read_text(encoding='utf-8'))
    validacao = json.loads((RAIZ/'evidencias/contexto-v3-20261118/validacao-nova-r02-3rep.json').read_text(encoding='utf-8'))
    eventos = [json.loads(linha) for linha in
               (RAIZ/'evidencias/contexto-v3-20261118/p6-r01/eventos.jsonl').read_text(encoding='utf-8').splitlines()]
    perguntas = {cenario: [e for e in eventos if e.get('tipo') == 'resultado'
                           and e.get('evento', {}).get('tipo') == 'pergunta'
                           and e['cenario'] == cenario]
                 for cenario in ('memoria_automatica', 'historico_completo')}
    aprovados = [sum(e.get('julgamento', {}).get('passou') is True for e in grupo)
                 for grupo in perguntas.values()]
    nao_verificados = [sum(e.get('julgamento', {}).get('revisao_necessaria') is True for e in grupo)
                      for grupo in perguntas.values()]
    reprovados = [len(grupo) - ok - nv for grupo, ok, nv in
                 zip(perguntas.values(), aprovados, nao_verificados)]
    validos = {cenario: [r for r in validacao['resultados'] if r['cenario'] == cenario]
               for cenario in ('memoria_regras_api', 'historico_completo')}
    aprovados_validacao = [sum(r.get('passou') is True for r in grupo)
                          for grupo in validos.values()]
    tokens = p6['comparacoes_tokens']['sessao']['tokens_total']
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
    nomes = ['Memória automática', 'Histórico completo']
    a.bar(nomes, [tokens['tokens_automaticos'],tokens['tokens_historico']], color=['#23635a','#9aaba7'])
    a.bar_label(a.containers[0], padding=4)
    a.set_title('Tokens completos: 20/20 pares')
    a.set_ylim(0,26000)
    valores = {'Aprovados':aprovados,'Reprovados verificados':reprovados,'Não verificados':nao_verificados}
    base = [0,0]
    for (rotulo, ys), cor in zip(valores.items(), ['#23635a','#b87659','#c4b276']):
        b.bar(nomes, ys, bottom=base, color=cor, label=rotulo)
        base = [x+y for x,y in zip(base,ys)]
    b.set_title('P4: 21 perguntas por cenário')
    b.set_ylim(0,29)
    b.legend(fontsize=8, loc='upper center')
    for eixo in (a,b):
        eixo.tick_params(axis='x',labelsize=9)
        eixo.spines[['top','right']].set_visible(False)
    fig.suptitle('P6 v3: uma rodada, 20 sessões por cenário; redução de 83,84%')
    fig.savefig(figura/'p6-v3.png',dpi=180)
    plt.close(fig)
    pareados = validacao['comparacoes_tokens']['memoria_regras_api']['sessao']['tokens_total']
    fig, (a,b) = plt.subplots(1,2,figsize=(10,4),layout='constrained')
    a.bar(nomes,aprovados_validacao,color=['#23635a','#9aaba7'])
    a.bar_label(a.containers[0],padding=4)
    a.set_ylim(0,55)
    a.set_title('Aprovações P4 / 48 tentativas')
    b.bar(nomes,[pareados['tokens_cenario'],pareados['tokens_historico']],color=['#23635a','#9aaba7'])
    b.bar_label(b.containers[0],padding=4)
    b.set_ylim(0,48000)
    b.set_title('Tokens: somente 47/48 pares medidos')
    for eixo in (a,b):
        eixo.tick_params(axis='x',labelsize=9)
        eixo.spines[['top','right']].set_visible(False)
    fig.suptitle('16 casos sintéticos × 3 repetições; um timeout no baseline')
    fig.savefig(figura/'validacao-v3.png',dpi=180)
    plt.close(fig)
    linhas = [
        {'rodada':'p6','cenario':'memoria_automatica','aprovados_p4':aprovados[0],'tentativas':len(perguntas['memoria_automatica']),
         'tokens_pareados':tokens['tokens_automaticos'],'pares_medidos':20,'pares_previstos':20},
        {'rodada':'p6','cenario':'historico_completo','aprovados_p4':aprovados[1],'tentativas':len(perguntas['historico_completo']),
         'tokens_pareados':tokens['tokens_historico'],'pares_medidos':20,'pares_previstos':20},
        {'rodada':'validacao_16x3','cenario':'memoria_automatica','aprovados_p4':aprovados_validacao[0],'tentativas':len(validos['memoria_regras_api']),
         'tokens_pareados':pareados['tokens_cenario'],'pares_medidos':47,'pares_previstos':48},
        {'rodada':'validacao_16x3','cenario':'historico_completo','aprovados_p4':aprovados_validacao[1],'tentativas':len(validos['historico_completo']),
         'tokens_pareados':pareados['tokens_historico'],'pares_medidos':47,'pares_previstos':48},
    ]
    with (ENTREGA/'resultados-consolidados.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(linhas[0]));w.writeheader();w.writerows(linhas)
    print(json.dumps({'figuras':2,'linhas_csv':len(linhas)}))


if __name__ == '__main__':
    main()
