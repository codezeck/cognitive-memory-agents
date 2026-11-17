import pytest

from src import agent
from eval.avaliar_comparativo import tokens_etapa, _tokens_comparaveis


@pytest.fixture(autouse=True)
def historico():
    agent.historicos_por_usuario.clear()
    yield
    agent.historicos_por_usuario.clear()


def test_zero_derivado_so_de_contagem_local_explicita():
    local={'resposta':'DESCONHECIDO','tokens_entrada':None,'tokens_saida':None,
           'origem_uso':'politica_local','chamadas_modelo_observadas':0}
    t=tokens_etapa([local])
    assert t['tokens_total']==0 and t['metricas_completas']
    assert t['chamadas_modelo']==0 and t['respostas_locais_confirmadas']==1
    assert _tokens_comparaveis(t,'tokens_total')
    assert local['tokens_entrada'] is None  # Nao reescreve a resposta original.


def test_sessao_mista_soma_ingestao_real_e_zero_local():
    t=tokens_etapa([
        {'tokens_entrada':31,'tokens_saida':4,'origem_uso':'provedor','chamadas_modelo_observadas':1},
        {'tokens_entrada':None,'tokens_saida':None,'origem_uso':'politica_local','chamadas_modelo_observadas':0},
    ])
    assert t['tokens_total']==35 and t['chamadas_modelo']==1
    assert t['chamadas_com_entrada']==2 and t['chamadas_com_tokens_zero']==0
    assert _tokens_comparaveis(t,'tokens_total')


@pytest.mark.parametrize('entrada',[
    {'tokens_entrada':None,'tokens_saida':None},
    {'tokens_entrada':0,'tokens_saida':0},
    {'tokens_entrada':0,'tokens_saida':0,'origem_uso':'provedor','chamadas_modelo_observadas':1},
    {'origem_uso':'politica_local','chamadas_modelo_observadas':False},
    {'origem_uso':'politica_local','chamadas_modelo_observadas':1},
    {'origem_uso':'politica_local','chamadas_modelo_observadas':0,'tokens_entrada':5},
    {'origem_uso':'desconhecida','chamadas_modelo_observadas':0},
    {'chamadas_modelo_observadas':0},
])
def test_falta_ou_inconsistencia_nao_vira_zero(entrada):
    t=tokens_etapa([entrada])
    assert not t['metricas_completas']
    assert not _tokens_comparaveis(t,'tokens_total')


def test_modelo_diz_desconhecido_continua_sendo_chamada_de_modelo():
    class Modelo:
        def gerar_com_detalhes(self,mensagens):
            return {'resposta':'DESCONHECIDO','tokens_entrada':7,'tokens_saida':3}
    r=agent.responder('Explique um conceito geral desconhecido.', 'u1',
                      adaptador=Modelo(),retornar_detalhes=True)
    assert r['origem_uso']=='provedor' and r['chamadas_modelo_observadas']==1
    assert tokens_etapa([r])['tokens_total']==10


def test_caminho_local_nao_invoca_adaptador_e_preserva_nulos():
    class NaoChamar:
        def gerar(self,*args): raise AssertionError('Modelo foi chamado sem suporte.')
    r=agent.responder('Onde eu moro?','u1',adaptador=NaoChamar(),retornar_detalhes=True)
    assert r['origem_uso']=='politica_local' and r['chamadas_modelo_observadas']==0
    assert r['tokens_entrada'] is None and r['tokens_saida'] is None


def test_parte_geral_de_pergunta_mista_mantem_uso_real():
    class Modelo:
        def gerar_com_detalhes(self,mensagens):
            return {'resposta':'5','tokens_entrada':12,'tokens_saida':2}
    r=agent.responder('Onde eu moro? Quanto e 2 + 3?','u1',
                      adaptador=Modelo(),retornar_detalhes=True)
    assert r['origem_uso']=='provedor_com_abstencao_local'
    assert r['chamadas_modelo_observadas']==1 and tokens_etapa([r])['tokens_total']==14
