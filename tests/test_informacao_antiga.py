import copy
import json

import pytest

from eval.informacao_antiga import analisar_informacao_antiga, avaliar_informacao_antiga, main
from eval.julgamento_respostas import julgar_resposta

CASO = {'id': 'A', 'categoria': 'atualizacao', 'esperado': 'Campinas',
        'informacoes_esquecidas': [], 'avaliacao': {'tipo_resposta': 'factual', 'atributo': 'cidade',
        'aliases_aceitos': [], 'valores_antigos': ['Osasco'], 'informacoes_proibidas': []}}


@pytest.mark.parametrize('resposta,antiga,status', [
    ('Osasco', True, 'verificado'), ('Você mora em Osasco.', True, 'verificado'),
    ('Certamente Osasco', True, 'verificado'), ('Campinas', False, 'verificado'),
    ('Recife', False, 'verificado'), ('DESCONHECIDO', False, 'verificado'),
    ('Não é Osasco; é Campinas', False, 'verificado'),
    ('Antes Osasco; agora Campinas', False, 'verificado'),
    ('Antes eu morava em Osasco; agora eu moro em Campinas.', False, 'verificado'),
    ('Não moro em Osasco; moro em Campinas', False, 'verificado'),
    ('Não é Osasco', None, 'nao_verificado'), ('Talvez Osasco', None, 'nao_verificado'),
    ('"Osasco"', None, 'nao_verificado'), ('Osasco ou Campinas', None, 'nao_verificado'),
    ('Antes eu morava em Osasco.', None, 'nao_verificado'),
    ('Osascópolis', False, 'verificado'), (None, None, 'nao_verificado'),
    ('', None, 'nao_verificado'),
])
def test_antigo_afirmado_nao_e_mencao_temporal_negacao_ou_falha(resposta, antiga, status):
    caso=copy.deepcopy(CASO);antes=copy.deepcopy(caso);original=julgar_resposta(resposta,caso)
    medida=avaliar_informacao_antiga(resposta,caso)
    assert medida['retornou_antiga'] is antiga and medida['status']==status
    assert medida['aplicavel'] is True
    assert caso==antes and julgar_resposta(resposta,caso)==original


def doc(respostas=('Osasco','Campinas','Não é Osasco'), repeticoes=1):
    return {'interface':{'casos':[copy.deepcopy(CASO)],'repeticoes':repeticoes},
            'resumo':{c:{} for c in ['historico_completo','memoria_regras_api','sem_memoria']},
            'resultados':[{'id':'A','cenario':c,'repeticao':1,'resposta':r,'tokens_total':7,
                           'julgamento':julgar_resposta(r,CASO)}
                          for c,r in zip(['historico_completo','memoria_regras_api','sem_memoria'],respostas)]}


def test_taxa_cobertura_e_original_preservado_sem_modelo(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('Sem processos/modelos'))
    d=doc();antes=json.dumps(d,sort_keys=True);a=analisar_informacao_antiga(d)
    assert a['disponivel'] and json.dumps(d,sort_keys=True)==antes
    assert a['cenarios']['historico_completo']['taxa_pct']==100
    assert a['cenarios']['memoria_regras_api']['taxa_pct']==0
    assert a['cenarios']['sem_memoria']['taxa_pct'] is None
    assert a['cenarios']['sem_memoria']['nao_verificados']==1
    assert a['cenarios']['sem_memoria']['cobertura_pct']==0


def test_tentativas_ausentes_e_trajetoria_quebrada_nao_somem_do_denominador():
    d=doc(repeticoes=3);d['resultados'][0]['erro']='falha simulada'
    d['resultados'][1]['trajetoria_integra']=False
    a=analisar_informacao_antiga(d)
    for m in a['cenarios'].values():
        assert m['tentativas_elegiveis']==3 and m['nao_verificados']==3
        assert m['denominador']==0 and m['taxa_pct'] is None
    assert sum(r['indice'] is None for r in a['resultados'])==6


def test_esquecido_outro_usuario_e_categoria_nao_inferem_valor_antigo():
    caso=copy.deepcopy(CASO);caso['avaliacao']['valores_antigos']=[]
    caso['informacoes_esquecidas']=['Osasco'];caso['avaliacao']['informacoes_proibidas']=['Osasco']
    assert avaliar_informacao_antiga('Osasco',caso)['status']=='nao_aplicavel'
    caso['avaliacao']['tipo_resposta']='abstencao'
    caso['avaliacao']['valores_antigos']=['Osasco']
    assert avaliar_informacao_antiga('Osasco',caso)['status']=='nao_aplicavel'


@pytest.mark.parametrize('campo,valor', [('valores_antigos',None),('valores_antigos','Osasco'),
    ('atributo',[]),('atributo','atributo_inexistente'),('aliases_aceitos',[12])])
def test_anotacoes_invalidas_nao_viram_taxa_zero(campo,valor):
    caso=copy.deepcopy(CASO);caso['avaliacao'][campo]=valor
    assert avaliar_informacao_antiga('Campinas',caso)['aplicavel'] is None


def test_conflito_com_atual_e_acentos_ou_limites_de_palavra():
    caso=copy.deepcopy(CASO);caso['avaliacao']['valores_antigos']=['São José']
    assert avaliar_informacao_antiga('sao jose',caso)['retornou_antiga'] is True
    caso['avaliacao']['aliases_aceitos']=['São José']
    assert avaliar_informacao_antiga('São José',caso)['aplicavel'] is None


@pytest.mark.parametrize('mudanca',['duplicado','cenario','id','repeticao','sem_casos'])
def test_documentos_incompativeis_fecham_sem_inferencia(mudanca):
    d=doc()
    if mudanca=='duplicado':d['resultados']*=2
    elif mudanca=='cenario':d['resultados'][0]['cenario']=['historico_completo']
    elif mudanca=='id':d['resultados'][0]['id']='outro'
    elif mudanca=='repeticao':d['interface']['repeticoes']=True
    else:d['interface'].pop('casos')
    assert not analisar_informacao_antiga(d)['disponivel']


def test_p6_com_anotacoes_originais_e_sem_modificar_julgamentos():
    d={'sessoes':[],'interface':{'anotacoes':{'u/s2/pergunta1':copy.deepcopy(CASO)}},
       'metricas_resposta':{'historico_completo':{},'memoria_automatica':{}},
       'resultados':[{'cenario':'historico_completo','evento':{'tipo':'pergunta','id':'u/s2/pergunta1'},
                      'trajetoria_integra':True,'resultado':{'resposta':'Osasco'}}]}
    a=analisar_informacao_antiga(d)
    assert a['cenarios']['historico_completo']['numerador']==1
    assert a['cenarios']['memoria_automatica']['nao_verificados']==1


def test_api_analise_tarefa_inclui_medida_sem_mudar_versao_p4():
    from src.interface.analise import analisar_tarefa
    from src.interface.protocolos import fonte_v3
    caso=copy.deepcopy(next(c for c in fonte_v3() if c['avaliacao']['valores_antigos']))
    d={'interface':{'casos':[caso]},'resultados':[{'id':caso['id'],'cenario':'historico_completo',
        'repeticao':1,'resposta':caso['avaliacao']['valores_antigos'][0]}]}
    a=analisar_tarefa(d)
    assert a['versao']=='tarefa-comum-p4-v1' and a['informacao_antiga']['disponivel']
    assert a['informacao_antiga']['cenarios']['historico_completo']['numerador']==1


def test_cli_derivado_e_exclusivo_sem_sobrescrever_original(tmp_path):
    entrada=tmp_path/'original.json';saida=tmp_path/'analise.json'
    raw=json.dumps(doc()).encode();entrada.write_bytes(raw)
    assert main(['--entrada',str(entrada),'--saida',str(saida)])==0
    assert entrada.read_bytes()==raw
    with pytest.raises(FileExistsError):main(['--entrada',str(entrada),'--saida',str(saida)])
