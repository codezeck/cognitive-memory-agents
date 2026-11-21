"""Análise adicional de valores antigos anotados na resposta final, sem LLM."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from eval.julgamento_respostas import ATRIBUTOS, julgar_resposta, normalizar

VERSAO = 'informacao-antiga-v1'
CENARIOS = {'historico_completo', 'memoria_regras_api', 'sem_memoria',
            'memoria_persistente_api', 'memoria_automatica'}


def _textos(valores):
    return (isinstance(valores, list) and len(valores) <= 32
            and all(isinstance(v, str) and v.strip() and len(v) <= 2000 for v in valores))


def avaliar_informacao_antiga(resposta, caso, *, falha=False):
    """Não confunde menção literal, afirmação atual e contraste temporal reconhecido."""
    medida = {'versao': VERSAO, 'aplicavel': None, 'status': 'nao_verificado',
              'retornou_antiga': None, 'ocorrencias_literais': [],
              'motivo': 'anotacao_ausente_ou_invalida'}
    a = caso.get('avaliacao') if isinstance(caso, dict) else None
    if not isinstance(a, dict) or a.get('tipo_resposta') not in ('factual', 'abstencao'):
        return medida
    if a['tipo_resposta'] == 'abstencao':
        return {**medida, 'aplicavel': False, 'status': 'nao_aplicavel',
                'motivo': 'abstencao_ou_esquecimento_avaliados_separadamente'}
    antigos, aliases, esperado = a.get('valores_antigos'), a.get('aliases_aceitos', []), caso.get('esperado')
    if (not _textos(antigos) or not _textos(aliases) or not isinstance(a.get('atributo'), str)
            or a['atributo'] not in ATRIBUTOS
            or not isinstance(esperado, str) or not esperado.strip()):
        return medida
    if not antigos:
        return {**medida, 'aplicavel': False, 'status': 'nao_aplicavel',
                'motivo': 'sem_valor_antigo_anotado'}
    if {normalizar(v) for v in antigos} & {normalizar(v) for v in [esperado, *aliases]}:
        return {**medida, 'motivo': 'anotacao_antiga_conflita_com_valor_atual'}
    medida['aplicavel'] = True
    if falha or not isinstance(resposta, str) or not resposta.strip() or len(resposta) > 16000:
        return {**medida, 'motivo': 'resposta_ausente_ou_trajetoria_incompleta'}
    texto = normalizar(resposta)
    ocorrencias = [v for v in antigos if re.search(r'(?<!\w)' + re.escape(normalizar(v)) + r'(?!\w)', texto)]
    medida['ocorrencias_literais'] = ocorrencias
    if not ocorrencias:
        return {**medida, 'status': 'verificado', 'retornou_antiga': False,
                'motivo': 'sem_ocorrencia_literal_dos_valores_antigos'}
    atual = julgar_resposta(resposta, caso)['acerto_factual']
    if atual['status'] == 'aprovado':
        return {**medida, 'status': 'verificado', 'retornou_antiga': False,
                'motivo': 'valor_atual_ou_contraste_temporal_reconhecido'}
    for antigo in ocorrencias:
        hipotese = {'esperado': antigo, 'informacoes_esquecidas': [],
                    'avaliacao': {'tipo_resposta': 'factual', 'atributo': a['atributo'],
                                  'aliases_aceitos': [], 'valores_antigos': [],
                                  'informacoes_proibidas': []}}
        if julgar_resposta(resposta, hipotese)['acerto_factual']['status'] == 'aprovado':
            return {**medida, 'status': 'verificado', 'retornou_antiga': True,
                    'motivo': 'valor_antigo_afirmado_como_resposta'}
    return {**medida, 'motivo': 'mencao_antiga_sem_sentido_temporal_verificado'}


def _resumir(registros):
    elegiveis = [r for r in registros if r['medida']['aplicavel'] is True]
    verificados = [r for r in elegiveis if r['medida']['status'] == 'verificado']
    n = sum(r['medida']['retornou_antiga'] is True for r in verificados)
    return {'tentativas_previstas': len(registros), 'tentativas_elegiveis': len(elegiveis),
            'julgamentos_verificados': len(verificados), 'numerador': n, 'denominador': len(verificados),
            'nao_verificados': len(elegiveis) - len(verificados),
            'nao_aplicaveis': sum(r['medida']['aplicavel'] is False for r in registros),
            'aplicabilidade_desconhecida': sum(r['medida']['aplicavel'] is None for r in registros),
            'cobertura_pct': round(100 * len(verificados) / len(elegiveis), 2) if elegiveis else None,
            'taxa_pct': round(100 * n / len(verificados), 2) if verificados else None}


def analisar_informacao_antiga(documento, *, casos=None, anotacoes=None, repeticoes=None):
    indisponivel = {'versao': VERSAO, 'disponivel': False,
                   'motivo': 'Registros ou anotações originais incompatíveis; não inferir valores antigos.'}
    if not isinstance(documento, dict):
        return indisponivel
    interface = documento.get('interface') or {}
    registros = documento.get('resultados')
    if not isinstance(interface, dict) or not isinstance(registros, list) or len(registros) > 2000:
        return indisponivel
    p6 = isinstance(documento.get('sessoes'), list)
    if p6:
        fontes = anotacoes if anotacoes is not None else interface.get('anotacoes')
        if not isinstance(fontes, dict) or not fontes or len(fontes) > 100:
            return indisponivel
    else:
        lista = casos if casos is not None else interface.get('casos')
        if (not isinstance(lista, list) or not lista or len(lista) > 100
                or any(not isinstance(c, dict) or not isinstance(c.get('id'), str) for c in lista)):
            return indisponivel
        fontes = {c['id']: c for c in lista}
        if len(fontes) != len(lista):
            return indisponivel
    if any(not isinstance(k, str) or not isinstance(v, dict) for k, v in fontes.items()):
        return indisponivel
    observados = {}
    indices = {}
    cenarios = set()
    for i, r in enumerate(registros):
        if not isinstance(r, dict):
            return indisponivel
        evento = r.get('evento')
        if p6 and (not isinstance(evento, dict) or evento.get('tipo') != 'pergunta'):
            continue
        codigo = evento.get('id') if p6 else r.get('id')
        rep = 1 if p6 else r.get('repeticao')
        cenario = r.get('cenario')
        if (not isinstance(codigo, str) or codigo not in fontes or not isinstance(cenario, str)
                or cenario not in CENARIOS or type(rep) is not int or rep not in (1, 2, 3)):
            return indisponivel
        chave = (cenario, codigo, rep)
        if chave in observados:
            return indisponivel
        observados[chave], indices[chave] = r, i
        cenarios.add(cenario)
    resumo = documento.get('metricas_resposta' if p6 else 'resumo', {})
    if isinstance(resumo, dict):
        cenarios.update(c for c in resumo if c in CENARIOS)
    reps = 1 if p6 else repeticoes if repeticoes is not None else interface.get('repeticoes')
    if reps is None:
        reps = max((k[2] for k in observados), default=1)
    if type(reps) is not int or reps not in (1, 2, 3) or any(k[2] > reps for k in observados) or not cenarios:
        return indisponivel
    resultados = []
    for cenario in sorted(cenarios):
        for codigo, caso in fontes.items():
            for rep in range(1, reps + 1):
                chave = (cenario, codigo, rep)
                r = observados.get(chave, {})
                resultado = r.get('resultado', {}) if p6 else r
                resposta = resultado.get('resposta') if isinstance(resultado, dict) else None
                falha = bool(r.get('erro')) or r.get('estado') == 'erro' or r.get('trajetoria_integra') is False
                medida = avaliar_informacao_antiga(resposta, caso, falha=falha)
                resultados.append({'indice': indices.get(chave), 'id': codigo, 'cenario': cenario,
                                   'repeticao': rep, 'medida': medida})
    try:
        serializado = json.dumps(fontes, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError):
        return indisponivel
    return {'versao': VERSAO, 'disponivel': True, 'anotacoes_sha256': hashlib.sha256(serializado).hexdigest(),
            'motivo': 'Análise adicional dos valores antigos anotados; não altera P4/P5, tokens ou respostas. Maior taxa é pior. Cobertura literal e gramatical limitada; sem revisão humana automática.',
            'resultados': resultados,
            'cenarios': {c: _resumir([r for r in resultados if r['cenario'] == c]) for c in sorted(cenarios)}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', type=Path, required=True)
    parser.add_argument('--saida', type=Path, required=True)
    args = parser.parse_args(argv)
    documento = json.loads(args.entrada.read_text(encoding='utf-8'))
    analise = analisar_informacao_antiga(documento)
    with args.saida.open('x', encoding='utf-8') as f:
        json.dump(analise, f, ensure_ascii=False, allow_nan=False, indent=2)
    return 0 if analise['disponivel'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
