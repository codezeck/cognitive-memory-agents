"""Reavaliação explícita da P6 com gabarito incorporado, sem persistência ou LLM."""
from __future__ import annotations

import hashlib
import json

from eval.julgamento_p6 import julgar_resposta_p6
from eval.julgamento_respostas import ATRIBUTOS

VERSAO = 'tarefa-p6-conteudo-v2'


def _textos(valores):
    return isinstance(valores, list) and len(valores) <= 32 and all(
        isinstance(v, str) and 0 < len(v.strip()) <= 2000 for v in valores)


def _anotacao(caso):
    if not isinstance(caso, dict):
        return False
    a = caso.get('avaliacao')
    if not isinstance(a, dict) or not isinstance(a.get('atributo'), str) or a['atributo'] not in ATRIBUTOS:
        return False
    modo = a.get('tipo_resposta')
    if modo not in ('factual', 'abstencao'):
        return False
    esperado = caso.get('esperado')
    if modo == 'factual' and not (isinstance(esperado, str) and 0 < len(esperado.strip()) <= 2000):
        return False
    if modo == 'abstencao' and not ((isinstance(esperado, str) and 0 < len(esperado.strip()) <= 2000) or _textos(esperado) and esperado):
        return False
    if not all(_textos(a.get(c, [])) for c in ('aliases_aceitos', 'valores_antigos', 'informacoes_proibidas')):
        return False
    proibidos = a.get('aliases_proibidos', {})
    return (_textos(caso.get('informacoes_esquecidas', [])) and isinstance(proibidos, dict)
            and len(proibidos) <= 32 and all(isinstance(k, str) and _textos(v) for k, v in proibidos.items()))


def analisar_p6(documento, antiga):
    indisponivel = {'versao': VERSAO, 'disponivel': False, 'informacao_antiga': antiga,
                   'motivo': 'P6 sem registros e anotações originais compatíveis; julgamentos preservados.'}
    interface, registros = documento.get('interface'), documento.get('resultados')
    if not isinstance(interface, dict) or not isinstance(registros, list) or not registros or len(registros) > 2000:
        return indisponivel
    anotacoes = interface.get('anotacoes')
    if (not isinstance(anotacoes, dict) or not anotacoes or len(anotacoes) > 100
            or any(not isinstance(k, str) or len(k) > 128 or not _anotacao(v) for k, v in anotacoes.items())):
        return indisponivel
    resultados, identidades = [], set()
    for indice, r in enumerate(registros):
        if not isinstance(r, dict) or not isinstance(r.get('evento'), dict):
            return indisponivel
        evento = r['evento']
        if evento.get('tipo') != 'pergunta':
            continue
        codigo, cenario, pergunta = evento.get('id'), r.get('cenario'), evento.get('texto')
        if (not isinstance(codigo, str) or codigo not in anotacoes
                or cenario not in ('historico_completo', 'memoria_automatica')
                or not isinstance(pergunta, str) or not 0 < len(pergunta) <= 2000):
            return indisponivel
        chave = (codigo, cenario)
        if chave in identidades:
            return indisponivel
        identidades.add(chave)
        saida = r.get('resultado')
        resposta = saida.get('resposta') if isinstance(saida, dict) else None
        if resposta is not None and (not isinstance(resposta, str) or len(resposta) > 16000):
            return indisponivel
        caso = {**anotacoes[codigo], 'pergunta': pergunta}
        integro = r.get('trajetoria_integra') is True and r.get('estado') == 'concluido' and not r.get('erro')
        julgamento = julgar_resposta_p6(resposta, caso, trajetoria_integra=integro)
        esperado = caso['esperado']
        if isinstance(esperado, list):
            esperado = ' / '.join(esperado)
        resultados.append({'indice': indice, 'id': codigo, 'cenario': cenario, 'repeticao': 1,
                           'esperado': esperado, 'julgamento': julgamento})
    if not resultados:
        return indisponivel
    serializado = json.dumps(anotacoes, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')
    return {'versao': VERSAO, 'disponivel': True, 'casos_sha256': hashlib.sha256(serializado).hexdigest(),
            'motivo': 'Análise P6 de conteúdo v2 com o mesmo gabarito nos dois cenários. Original preservado; sem nova geração ou aprovação humana.',
            'resultados': resultados, 'informacao_antiga': antiga}
