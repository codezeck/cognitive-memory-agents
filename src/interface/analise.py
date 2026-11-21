"""Leitura adicional com a mesma tarefa; não reescreve os julgamentos da execução."""
from __future__ import annotations

import hashlib
import json

from eval.julgamento_respostas import julgar_resposta
from eval.informacao_antiga import analisar_informacao_antiga
from src.interface.protocolos import validar_casos
from src.interface.analise_p6 import analisar_p6

VERSAO = 'tarefa-comum-p4-v1'
CENARIOS = {'sem_memoria', 'historico_completo', 'memoria_persistente_api', 'memoria_regras_api'}


def analisar_tarefa(documento):
    antiga = analisar_informacao_antiga(documento)
    indisponivel = {'versao': VERSAO, 'disponivel': False, 'informacao_antiga': antiga,
                   'motivo': 'Gabarito original completo ou registros compatíveis não incorporados. Julgamentos originais preservados.'}
    if not isinstance(documento, dict):
        return indisponivel
    if isinstance(documento.get('sessoes'), list):
        return analisar_p6(documento, antiga)
    interface = documento.get('interface')
    if not isinstance(interface, dict):
        return indisponivel
    casos = interface.get('casos')
    try:
        validar_casos(casos)
    except (ValueError, TypeError):
        return indisponivel
    registros = documento.get('resultados')
    if not isinstance(registros, list) or len(registros) > 240:
        return indisponivel
    por_id = {caso['id']: caso for caso in casos}
    resultados = []
    identidades = set()
    for indice, registro in enumerate(registros):
        if not isinstance(registro, dict):
            return indisponivel
        codigo, cenario, repeticao = registro.get('id'), registro.get('cenario'), registro.get('repeticao')
        if not isinstance(codigo, str) or codigo not in por_id or not isinstance(cenario, str) or cenario not in CENARIOS:
            return indisponivel
        if type(repeticao) is not int or repeticao not in (1, 2, 3):
            return indisponivel
        identidade = (codigo, cenario, repeticao)
        if identidade in identidades:
            return indisponivel
        identidades.add(identidade)
        caso = por_id[codigo]
        resposta = registro.get('resposta')
        if resposta is not None and (not isinstance(resposta, str) or len(resposta) > 16000):
            return indisponivel
        julgamento = julgar_resposta(resposta, caso)
        esperado = 'DESCONHECIDO' if caso['avaliacao']['tipo_resposta'] == 'abstencao' else caso['esperado']
        resultados.append({'indice': indice, 'id': codigo, 'cenario': cenario, 'repeticao': repeticao,
                           'esperado': esperado, 'julgamento': julgamento})
    serializado = json.dumps(casos, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')
    return {'versao': VERSAO, 'disponivel': True, 'casos_sha256': hashlib.sha256(serializado).hexdigest(),
            'motivo': 'Mesmas perguntas e gabarito original em todos os cenários. Não é uma nova execução nem aprovação humana.',
            'resultados': resultados, 'informacao_antiga': antiga}
