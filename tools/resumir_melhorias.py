"""Deriva relatório, CSV e figura das rodadas preservadas de 18/11/2026."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / 'evidencias/melhorias-20261118'

# Revisão textual complementar, assistida por IA. Não muda P4 ou gabaritos.
REVISAO = {
    ('memoria_automatica', 'u04/s3/pergunta1'): (True, 'Afirma analista de dados; o artigo um não muda o cargo.'),
    ('memoria_automatica', 'u03/s5/pergunta4'): (True, 'Afirma diretora de arte; o artigo a não muda o cargo.'),
    ('historico_completo', 'u03/s2/pergunta1'): (False, 'Recusa informar o hobby já declarado: fotografia.'),
    ('historico_completo', 'u01/s4/pergunta3'): (False, 'Retorna enfermeira, profissão antiga.'),
    ('historico_completo', 'u02/s4/pergunta2'): (True, 'Afirma Onix branco; o artigo o não muda o carro.'),
    ('historico_completo', 'u02/s5/pergunta3'): (False, 'Expõe Onix branco após o pedido de esquecimento.'),
    ('historico_completo', 'u03/s5/pergunta4'): (False, 'Abstém apesar de a trajetória informar diretora de arte.'),
    ('historico_completo', 'u04/s5/pergunta4'): (False, 'Abstém apesar do reaprendizado da cidade Belém.'),
    ('memoria_automatica', 'u01/s3/pergunta2'): (True, 'Afirma Campinas, valor atual anotado.'),
    ('historico_completo', 'u01/s3/pergunta2'): (True, 'Afirma Campinas, valor atual anotado.'),
    ('memoria_automatica', 'u03/s3/pergunta2'): (True, 'Afirma Portugal em dezembro, destino atual anotado.'),
    ('historico_completo', 'u03/s3/pergunta2'): (True, 'Afirma Portugal em dezembro, destino atual anotado.'),
    ('historico_completo', 'u04/s3/pergunta1'): (False, 'Descreve desenvolvimento com Python; não informa analista de dados.'),
    ('memoria_automatica', 'u03/s4/pergunta3'): (False, 'Quantidade dois correta, mas inventa Leo; o nome anotado é Luna.'),
    ('historico_completo', 'u03/s4/pergunta3'): (True, 'Quantidade dois e nomes Luna e Simba coerentes com a trajetória.'),
    ('memoria_automatica', 'u01/s5/pergunta4'): (True, 'Afirma residência atual em Santos.'),
    ('historico_completo', 'u01/s5/pergunta4'): (True, 'Afirma residência atual em Santos.'),
    ('memoria_automatica', 'u01/s5/pergunta5'): (True, 'Afirma Thor como nome do cachorro.'),
    ('historico_completo', 'u01/s5/pergunta5'): (True, 'Afirma Thor como nome do cachorro.'),
}


def celula(valor):
    return str(valor).replace('|', '/').replace('\n', ' ')


def main():
    dev = json.loads((PASTA / 'comparativo-r01.json').read_text(encoding='utf-8'))
    p6 = json.loads((PASTA / 'p6-r02/resumo.json').read_text(encoding='utf-8'))
    origem = PASTA / 'p6-r02/eventos.jsonl'
    eventos = [json.loads(l) for l in origem.read_text(encoding='utf-8').splitlines()]
    perguntas = [r for r in eventos if r['tipo'] == 'resultado' and r['evento']['tipo'] == 'pergunta']
    anotacoes = json.loads((RAIZ / 'eval/memoria/anotacoes_p6.json').read_text(encoding='utf-8'))
    revisados = []
    linhas = [
        '# Melhorias e avaliação real — 18/11/2026', '',
        'Base Git `b912ab6`, branch `fix/confiabilidade-contexto-memoria`, com alterações locais identificadas pelos manifestos. '
        'Ollama real, `qwen2.5-coder:3b`, dados sintéticos, API e SQLite dedicados. Nenhuma chamada a API paga. '
        'Os resultados de 14/11 e os datasets originais foram preservados.', '',
        '## O que mudou', '',
        '- Consultas sobre carro atual, time, esporte, cargo e trabalho reconhecem suporte de forma mais coerente. '
        'Negação, hipótese, pergunta e fala do assistente não bastam como afirmação de um fato.',
        '- Busca por chave prioriza fatos ativos em perguntas pessoais reconhecidas, mesmo sem palavras iguais. '
        'Quando não há correspondência por chave, continua a busca vetorial existente; não há compreensão semântica universal. '
        'O score 1,0 nesse caminho significa chave exata, não similaridade de cosseno.',
        '- API envia até três turnos recentes e 6.000 caracteres de histórico, preservando pares completos. '
        'Pergunta atual, sistema e memórias recuperadas não são truncados por esse limite. A RAM continua limitada a dez turnos; '
        'fatos fora do contexto recente precisam estar na memória recuperada. Esse orçamento não é uma contagem exata de tokens.',
        '- O baseline desliga explicitamente o contexto compacto e conserva todo o episódio. '
        'A montagem compacta retira instruções duplicadas e memórias textualmente repetidas.',
        '- O coletor P6 inicia uma API descartável com um worker, lê SQLite/RAM e reinicia somente seu próprio processo. '
        'O estado vazio esperado é analisado separadamente da persistência de dados não vazios.', '',
        '## Comparativo de desenvolvimento', '',
        'Sete casos conhecidos, três repetições, quatro cenários: 84 tentativas. As repetições não são novos casos independentes.', '',
        '| Cenário | Aprovados P4 | Tentativas | Tokens completos |', '|---|---:|---:|---:|']
    for c, s in dev['resumo'].items():
        linhas.append(f"| {c} | {s['aprovados']} | {s['casos']} | {s['tokens_total']} |")
    automatico = dev['resumo']['memoria_regras_api']['tokens_total']
    historico = dev['resumo']['historico_completo']['tokens_total']
    linhas += ['', f'Redução da sessão completa: **{100 * (1 - automatico / historico):.2f}%**. '
               'A meta adicional de 30% não foi atingida. O controle pré-carregado não mede aquisição conversacional.', '',
               'As falhas anteriores de carro e time não reapareceram nesta bateria. A memória automática falhou uma vez '
               'sobre esporte apesar de o estado das regras estar correto. Variação entre rodadas não prova efeito causal '
               'isolado de cada correção, pois o modelo é estocástico e várias mudanças foram avaliadas juntas.', '',
               '## P6: vinte sessões por cenário', '',
               'Rodada real completa, 40 registros de sessão, 42 perguntas e zero falhas técnicas. '
               'Os 19 checkpoints não vazios foram verificados após reinício; os dois checkpoints de exclusão foram '
               'verificados, com banco e RAM observados e preservação dos não alvos. O checkpoint de estado vazio '
               'foi registrado como `vazio_consistente`, fora do denominador de persistência de fatos.', '',
               '| Cenário | Aprovados P4 / 21 | Reprovados verificados | Não verificados | Tokens completos |',
               '|---|---:|---:|---:|---:|']
    contagens = {}
    for c in ('memoria_automatica', 'historico_completo'):
        rs = [r for r in perguntas if r['cenario'] == c]
        aprovados = sum(r['julgamento']['passou'] for r in rs)
        pendentes = sum(r['julgamento']['revisao_necessaria'] for r in rs)
        tokens = sum(s['tokens']['sessao']['tokens_total'] for s in p6['sessoes'] if s['cenario'] == c)
        contagens[c] = (aprovados, len(rs) - aprovados - pendentes, pendentes, tokens)
        linhas.append(f'| {c} | {aprovados} | {len(rs) - aprovados - pendentes} | {pendentes} | {tokens} |')
    t = p6['comparacoes_tokens']['sessao']['tokens_total']
    linhas += ['', f"Redução de **{t['reducao_pct']}%**, com **{t['pares_medidos']}/{t['pares_previstos']}** pares medidos. "
               'A meta de 30% continua não atingida. A avaliação automática de respostas não é completa: '
               'há onze julgamentos não verificados, que não são convertidos em acertos ou erros confirmados. '
               'As taxas apenas dos verificados não representam a taxa de todas as 21 perguntas.', '',
               'Abstenção: 4/4 correta na memória automática e 3/4 no histórico; ocorrências de fatos esquecidos '
               'nas respostas: 0/4 e 1/4, respectivamente. Isso não certifica toda a RAM, buffers externos ou conformidade jurídica.', '',
               '## Revisão textual complementar assistida por IA', '',
               'A revisão abaixo examina todas as respostas não aprovadas usando os gabaritos congelados e as respostas literais. Não altera JSONL, P4, aliases ou gabaritos, '
               'nem representa revisão humana da equipe. Além do valor solicitado, considera detalhes contraditórios '
               'inventados: dizer dois gatos e trocar Luna por Leo não é resposta integralmente correta.', '',
               '| Cenário | Pergunta | Resposta literal | Análise complementar |', '|---|---|---|---|']
    totais_revisao = {c: contagens[c][0] for c in contagens}
    csv_linhas = []
    for r in perguntas:
        chave = (r['cenario'], r['evento']['id'])
        revisao = REVISAO.get(chave)
        if not r['julgamento']['passou']:
            if revisao is None:
                raise ValueError('Falta análise explícita de ' + str(chave))
            passou, motivo = revisao
            totais_revisao[r['cenario']] += int(passou)
            revisados.append({'cenario': chave[0], 'evento_id': chave[1], 'resposta': r['resultado']['resposta'],
                              'conteudo_aprovado_revisao_ia': passou, 'motivo': motivo})
            linhas.append('| ' + ' | '.join(map(celula, [*chave, r['resultado']['resposta'], motivo])) + ' |')
        csv_linhas.append({'cenario': chave[0], 'evento_id': chave[1], 'pergunta': r['evento']['texto'],
                           'resposta': r['resultado']['resposta'], 'esperado': anotacoes[chave[1]]['esperado'],
                           'p4_passou': r['julgamento']['passou'], 'p4_revisao': r['julgamento']['revisao_necessaria'],
                           'revisao_ia': revisao[0] if revisao else '', 'motivo_revisao': revisao[1] if revisao else ''})
    linhas += ['', f"Resultado complementar: {totais_revisao['memoria_automatica']}/21 para memória automática e "
               f"{totais_revisao['historico_completo']}/21 para histórico. Esses totais incluem a análise assistida e devem "
               'ser citados com essa qualificação. A versão automática original permanece inconclusiva para onze respostas.', '',
               '## Falhas e limitações que permanecem', '',
               '1. Recuperação por palavras ainda falha para paráfrases fora das consultas reconhecidas. A melhoria '
               'por chave cobre parte do domínio; não substitui avaliação de recuperação semântica mais ampla.',
               '2. O modelo pode ignorar suporte disponível: ocorreu abstenção indevida sobre esporte no desenvolvimento.',
               '3. Na P6, a quantidade de gatos foi correta, mas a memória automática inventou Leo em vez de Luna. '
               'Isso mostra que acertar o atributo solicitado não garante fidelidade de detalhes adicionais.',
               '4. O julgador P4 não reconhece todas as paráfrases corretas. Resultados não verificados são expostos; '
               'a gramática não foi ajustada retrospectivamente para melhorar esta rodada.',
               '5. A meta de economia global não foi atingida. Redução apenas nas perguntas não substitui o custo da sessão.', '',
               'O backend Ollama foi reutilizado na mesma rede Docker da demonstração, com chamadas desta bateria sequenciais. '
               'A API e o banco eram exclusivos; não se garante ausência de carga externa no host. Latência não é uma '
               'comparação controlada de hardware. A P6 tem uma rodada e quatro usuários sintéticos, sem inferência estatística.', '',
               '## Proveniência, tentativas e reprodução', '',
               '- A primeira preparação P6 falhou antes das sessões porque o banco é criado sob demanda. '
               '`p6-r01` conserva configuração e log; o coletor foi corrigido e `p6-r02` usou novo banco e novo ID.',
               '- A primeira suíte local usou um temporário cujo diretório pai não existia; houve erros de preparação. '
               'A rodada seguinte identificou e corrigiu aplicação indevida do contexto compacto ao baseline. '
               'As verificações posteriores usam diretório próprio e incluem regressão de histórico longo.',
               '- Ver [decisão e protocolo](revisao-experimental/decisao-20261118.md), '
               '[resumo P6](../evidencias/melhorias-20261118/p6-r02/resumo.json), '
               '[JSONL original](../evidencias/melhorias-20261118/p6-r02/eventos.jsonl) e '
               '[respostas CSV](../evidencias/melhorias-20261118/respostas-p6.csv).', '',
               'Comandos utilizados (saída sempre nova; ambiente isolado e dependências instaladas):', '',
               '```powershell',
               'python -B -m src.interface.comparativo --saida SAIDA_NOVA.json --repeticoes 3',
               'python -B -m tools.executar_p6_local --saida-dir PASTA_NOVA --commit-base b912ab6 --protocolo docs/revisao-experimental/protocolo-local-20261118.json',
               'python -B -m tools.resumir_melhorias', '```', '',
               'Na execução registrada, os comandos rodaram em container descartável, com `src`, `eval` e `tools` '
               'montados somente para leitura e `OLLAMA_HOST=http://ollama:11434`. A configuração efetiva e hashes '
               'estão em `p6-r02/configuracao.json`.', '',
               '## Pendências da entrega', '',
               'Revisão humana cruzada, confirmação de dados institucionais e composição do grupo, definição de licença '
               'pelos titulares, vídeo de 3–5 minutos e CI verde na tag final `v1.0`. Esta rodada não executou publicação, '
               'merge, tag ou envio acadêmico. Os resultados técnicos não substituem essas exigências do professor.', '']
    teste_path = PASTA / 'teste-separado-r01.json'
    if teste_path.exists():
        teste = json.loads(teste_path.read_text(encoding='utf-8'))
        linhas += ['## Bateria separada de dez casos', '',
                   'Código mantido após as rodadas anteriores; três repetições por caso, 120 tentativas nos quatro cenários. '
                   'Textos e resultados esperados originais preservados em cópia anotada. Conjunto separado, acessível no '
                   'repositório, sem alegação de avaliação cega e sem ajuste do produto após observar suas respostas.', '',
                   '| Cenário | Aprovados P4 | Tentativas | Tokens completos |', '|---|---:|---:|---:|---:|']
        for c, s in teste['resumo'].items():
            linhas.append(f"| {c} | {s['aprovados']} | {s['casos']} | {s['tokens_total']} |")
        falhas = [r for r in teste['resultados'] if not r['passou']]
        linhas += ['', 'Todas as respostas não aprovadas constam do JSON original e do CSV `falhas-teste-separado.csv`. '
                   'Não foram usadas para reescrever regras ou gabaritos.', '',
                   'A automática teve 21/30 aprovações contra 24/30 do histórico: perda de 10 pontos percentuais. '
                   'Os tokens foram 27.134 contra 27.802, economia de 2,40%. Portanto, essa bateria reprova as metas '
                   'adicionais de economia mínima de 30% e perda máxima de 5 p.p. A cobertura dos julgamentos factuais '
                   'não é integral: consultar os denominadores do JSON, sem usar só os verificados para declarar sucesso.', '',
                   'TST001 não recuperou a cidade na paráfrase sobre residência e produziu cidade inventada. '
                   'TST004 manteve o carro após a frase de negação não reconhecida e retornou o valor antigo. '
                   'TST008 falhou na paráfrase sobre veículo. A falha de TST004 limita o esquecimento por linguagem '
                   'natural; não contradiz o resultado dos DELETEs e do pedido explícito de esquecimento medidos na P6. '
                   'O teste separado revelou generalização insuficiente. Uma próxima revisão deve usar novo protocolo '
                   'e novo conjunto de teste, mantendo esta rodada como resultado da versão congelada.', '']
        if falhas:
            with (PASTA / 'falhas-teste-separado.csv').open('w', encoding='utf-8', newline='') as f:
                campos = ['cenario', 'id', 'repeticao', 'resposta', 'esperado']
                w = csv.DictWriter(f, fieldnames=campos)
                w.writeheader()
                w.writerows({k: r[k] for k in campos} for r in falhas)
    (RAIZ / 'docs/melhorias-avaliacao-20261118.md').write_text('\n'.join(linhas), encoding='utf-8')
    with (PASTA / 'respostas-p6.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(csv_linhas[0]))
        w.writeheader()
        w.writerows(csv_linhas)
    (PASTA / 'revisao-textual-ia.json').write_text(json.dumps({
        'autor': 'Codex; análise assistida por IA, sem aprovação humana atribuída',
        'origem_sha256': hashlib.sha256(origem.read_bytes()).hexdigest(),
        'criterio': 'Gabaritos congelados, sem aceitar detalhes inventados ou contraditórios.',
        'revisoes': revisados, 'totais_complementares': totais_revisao}, ensure_ascii=False, indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
    nomes = ['Memória automática', 'Histórico completo']
    a.bar(nomes, [v[3] for v in contagens.values()], color=['#355e54', '#9faeaa'])
    a.set_title('Tokens da sessão completa')
    a.bar_label(a.containers[0], padding=3)
    a.set_ylim(0, 26000)
    base = [0, 0]
    for i, (rotulo, cor) in enumerate([('Aprovados P4', '#355e54'), ('Reprovados', '#b67357'), ('Não verificados', '#c5b375')]):
        valores = [v[i] for v in contagens.values()]
        b.bar(nomes, valores, bottom=base, label=rotulo, color=cor)
        base = [x + y for x, y in zip(base, valores)]
    b.set_title('Conteúdo: 21 perguntas por cenário')
    b.set_ylim(0, 27)
    b.legend(loc='upper center', fontsize=8)
    for eixo in (a, b):
        eixo.tick_params(axis='x', labelsize=9)
        eixo.spines[['top', 'right']].set_visible(False)
    fig.suptitle('P6 real - 18/11/2026: uma rodada, 20 sessões por cenário')
    fig.savefig(PASTA / 'p6-resultados.png', dpi=180)
    plt.close(fig)
    print(json.dumps({'p6': contagens, 'revisao_ia': totais_revisao, 'tokens_reducao_pct': t['reducao_pct']}))


if __name__ == '__main__':
    main()
