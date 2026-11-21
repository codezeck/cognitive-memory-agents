import copy
import json

import pytest

from src.interface.analise import analisar_tarefa
from src.interface.protocolos import fonte_v3


def documento(resposta='DESCONHECIDO', cenario='sem_memoria'):
    caso = copy.deepcopy(fonte_v3()[0])
    return {'interface': {'casos': [caso]}, 'resultados': [
        {'id': caso['id'], 'cenario': cenario, 'repeticao': 1, 'resposta': resposta,
         'julgamento': {'passou': True, 'tipo_resposta': 'abstencao'}}]}


def test_gabarito_comum_nao_confunde_abstencao_com_acerto_factual():
    doc = documento()
    original = json.dumps(doc, sort_keys=True)
    analise = analisar_tarefa(doc)
    j = analise['resultados'][0]['julgamento']
    assert analise['versao'] == 'tarefa-comum-p4-v1'
    assert j['tipo_resposta'] == 'factual' and j['passou'] is False
    assert json.dumps(doc, sort_keys=True) == original


def test_sem_memoria_pode_acertar_e_automatica_pode_errar():
    correto = fonte_v3()[0]['esperado']
    assert analisar_tarefa(documento(correto))['resultados'][0]['julgamento']['passou']
    assert not analisar_tarefa(documento('Inventado', 'memoria_regras_api'))['resultados'][0]['julgamento']['passou']


def test_abstencao_necessaria_continua_correta_na_mesma_tarefa():
    caso = next(c for c in fonte_v3() if c['avaliacao']['tipo_resposta'] == 'abstencao')
    doc = {'interface': {'casos': [caso]}, 'resultados': [
        {'id': caso['id'], 'cenario': c, 'repeticao': 1, 'resposta': 'DESCONHECIDO'}
        for c in ('sem_memoria', 'historico_completo', 'memoria_regras_api', 'memoria_persistente_api')]}
    assert all(r['julgamento']['passou'] for r in analisar_tarefa(doc)['resultados'])


@pytest.mark.parametrize('mudanca', ['sem_casos', 'duplicado', 'metadado_invalido', 'cenario_invalido', 'repeticao_invalida'])
def test_incompativeis_nao_ganham_julgamento_inferido(mudanca):
    doc = documento()
    if mudanca == 'sem_casos': doc['interface'].pop('casos')
    elif mudanca == 'duplicado': doc['resultados'] *= 2
    elif mudanca == 'metadado_invalido': doc['interface']['casos'][0]['avaliacao'] = {}
    elif mudanca == 'cenario_invalido': doc['resultados'][0]['cenario'] = ['sem_memoria']
    else: doc['resultados'][0]['repeticao'] = True
    assert analisar_tarefa(doc)['disponivel'] is False


def test_p6_nao_tem_seu_gabarito_alterado_e_sem_modelo(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Análise não cria processos'))
    assert analisar_tarefa({'sessoes': [], 'interface': {}})['disponivel'] is False
    assert analisar_tarefa(documento())['disponivel']
