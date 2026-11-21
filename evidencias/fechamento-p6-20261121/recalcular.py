"""Recalcula os cinco relatórios congelados; não usa rede, banco ou modelo."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

PASTA = Path(__file__).resolve().parent
CENARIOS = ('historico_completo', 'memoria_automatica')


def calcular():
    inventario = json.loads((PASTA/'inventario.json').read_text(encoding='utf-8'))
    linhas, grupos = [], defaultdict(list)
    for item in inventario:
        raw = (PASTA/item['arquivo']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['arquivo']
        doc = json.loads(raw)
        assert doc['estado_orquestracao'] == 'concluida'
        analise = json.loads((PASTA/'analises'/Path(item['arquivo']).name).read_text(encoding='utf-8'))
        assert analise['versao'] == 'tarefa-p6-conteudo-v2' and analise['disponivel']
        qualidade, tokens = {}, {}
        for cenario in CENARIOS:
            sessoes = [s for s in doc['sessoes'] if s['cenario'] == cenario]
            assert len(sessoes) == len({(s['usuario_id'], s['sessao']) for s in sessoes}) == 20
            for s in sessoes:
                t = s['tokens']['sessao']
                assert t['metricas_completas'] is True
                assert all(type(t[k]) is int and t[k] >= 0 for k in ('tokens_entrada', 'tokens_saida', 'tokens_total'))
                assert t['tokens_total'] == t['tokens_entrada']+t['tokens_saida']
            tokens[cenario] = sum(s['tokens']['sessao']['tokens_total'] for s in sessoes)
            qs = [r for r in analise['resultados'] if r['cenario'] == cenario]
            assert len(qs) == len({r['id'] for r in qs}) == 21
            for r in qs:
                original = doc['resultados'][r['indice']]
                assert original['evento']['id'] == r['id'] and original['cenario'] == cenario
                assert r['julgamento']['versao'] == 'p6-conteudo-v2'
            qualidade[cenario] = {k: dict(Counter(r['julgamento'][k]['status'] for r in qs))
                                  for k in ('acerto_factual', 'abstencao_correta', 'formato_ok')}
        par = doc['comparacoes_tokens']['sessao']['tokens_total']
        assert par['pares_medidos'] == par['pares_previstos'] == 20 and par['pares_sem_medicao'] == 0
        assert tokens['historico_completo'] == par['tokens_historico'] and tokens['memoria_automatica'] == par['tokens_automaticos']
        linha = {'id': item['id'], 'gerado_em': item['gerado_em'], 'etapa': item['etapa'], 'pares': 20,
                 'historico': tokens['historico_completo'], 'automatica': tokens['memoria_automatica'],
                 'reducao_pct': 100*(1-tokens['memoria_automatica']/tokens['historico_completo']),
                 'qualidade_v2': qualidade}
        linhas.append(linha)
        grupos[item['etapa']].append(linha)
    assert len({r['id'] for r in linhas}) == len(linhas) == 5
    assert len({r['geracao_sha256'] for r in inventario}) == 1
    assert len({r['anotacoes_sha256'] for r in inventario}) == 1

    def resumir(rs):
        h, a = sum(r['historico'] for r in rs), sum(r['automatica'] for r in rs)
        qualidade = {c: {k: dict(sum((Counter(r['qualidade_v2'][c][k]) for r in rs), Counter()))
                         for k in ('acerto_factual', 'abstencao_correta', 'formato_ok')} for c in CENARIOS}
        return {'rodadas': len(rs), 'pares': 20*len(rs), 'historico': h, 'automatica': a,
                'media_historico_por_rodada': h/len(rs), 'media_automatica_por_rodada': a/len(rs),
                'media_historico_por_sessao': h/(20*len(rs)), 'media_automatica_por_sessao': a/(20*len(rs)),
                'reducao_consolidada_pct': 100*(1-a/h),
                'media_aritmetica_reducoes_pct': sum(r['reducao_pct'] for r in rs)/len(rs),
                'menor_reducao_pct': min(r['reducao_pct'] for r in rs), 'maior_reducao_pct': max(r['reducao_pct'] for r in rs),
                'qualidade_v2': qualidade}
    return {'metodo': 'soma dos tokens pareados; mesma geração e anotações por hashes; qualidade derivada v2 congelada',
            'limite': 'Etapas da análise e da interface não isolam efeito causal sobre geração; rodadas não são usuários independentes.',
            'rodadas': linhas, 'grupos': {k: resumir(v) for k, v in grupos.items()}, 'consolidado_p6': resumir(linhas)}


if __name__ == '__main__':
    resultado = calcular()
    esperado = PASTA/'consolidado.json'
    if esperado.exists():
        assert json.loads(esperado.read_text(encoding='utf-8')) == resultado
    manifesto = PASTA/'manifesto-sha256.json'
    if manifesto.exists():
        for nome, sha in json.loads(manifesto.read_text(encoding='utf-8')).items():
            assert hashlib.sha256((PASTA/nome).read_bytes()).hexdigest() == sha, nome
    print(json.dumps({'rodadas': len(resultado['rodadas']), 'pares': resultado['consolidado_p6']['pares'],
                      'reducao_pct': resultado['consolidado_p6']['reducao_consolidada_pct'], 'status': 'conferido sem modelo'}, ensure_ascii=True))
