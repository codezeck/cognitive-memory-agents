import pytest

from src import agent
from src.api.agente_local import AgenteLocal
from src.api.catalogo import SelecaoModelo
from src.api.servico import Conversador
from src.memoria.store_mem import MemoriaEmRam
from src.memoria.gerenciador import GerenciadorMemoria


@pytest.fixture
def ambiente(monkeypatch):
    agent.historicos_por_usuario.clear()
    memoria = MemoriaEmRam()
    gerenciador = GerenciadorMemoria(memoria)
    modelo = type('Modelo', (), {'gerar': lambda self, ms: 'Resposta gerada'})()
    chamadas = []
    def gerar(ms):
        chamadas.append(ms)
        return 'Resposta gerada'
    monkeypatch.setattr(modelo, 'gerar', gerar)
    agente = AgenteLocal()
    monkeypatch.setattr(agente, '_adaptador', lambda *args: modelo)
    yield Conversador(agente, memoria, gerenciador=gerenciador), memoria, chamadas
    agent.historicos_por_usuario.clear()


def conversar(ambiente, mensagem, uid='a'):
    return ambiente[0].conversar(uid, mensagem, SelecaoModelo('ollama', 'teste'))


def test_fato_puro_e_confirmado_localmente_mas_pergunta_continua_no_modelo(ambiente):
    r = conversar(ambiente, 'Moro em Sorocaba.')
    assert r.origem_uso == 'politica_local' and r.chamadas_modelo_observadas == 0
    assert ambiente[2] == []
    assert agent.obter_historico('a')[-2]['content'] == 'Moro em Sorocaba.'
    r = conversar(ambiente, 'Em qual município resido?')
    assert r.origem_uso == 'provedor' and len(ambiente[2]) == 1
    assert 'Sorocaba' in str(ambiente[2][-1])


@pytest.mark.parametrize('mensagem', [
    'Moro em Sorocaba. Explique o clima local.',
    'Meu carro é um Fox. Quanto custa manter um carro?',
    'Moro em Sorocaba e explique o clima.',
    'Talvez eu moro em Sorocaba.',
    'Esqueça minha cidade e conte uma piada.',
])
def test_pedido_misto_ou_hipotese_nao_vira_confirmacao_local(ambiente, mensagem):
    conversar(ambiente, mensagem)
    assert len(ambiente[2]) == 1


def test_negacao_por_valor_remove_todas_versoes_e_nao_reintroduz_alvo_na_ram(ambiente):
    conversar(ambiente, 'Meu carro é um Fox.')
    conversar(ambiente, 'Meu carro agora é um Sandero.')
    conversar(ambiente, 'Meu carro é um Fox.', 'b')
    conversar(ambiente, 'Não tenho mais o Sandero.')
    assert ambiente[1].listar_por_usuario('a') == []
    assert ambiente[1].listar_por_usuario('b')
    assert 'Sandero' not in str(agent.obter_historico('a'))
    r = conversar(ambiente, 'Que veículo uso atualmente?')
    assert r.resposta == 'DESCONHECIDO'


def test_negacao_antiga_ou_ambigua_nao_remove_fato_atual(ambiente):
    conversar(ambiente, 'Meu carro é um Fox.')
    conversar(ambiente, 'Meu carro agora é um Sandero.')
    conversar(ambiente, 'Não tenho mais o Fox.')
    assert ambiente[0].gerenciador.estado('a')['carro'] == 'Sandero'
    # Mesma palavra em duas chaves não permite escolher silenciosamente uma.
    ambiente[1].salvar('a', 'Nome: Atlas.', chave='nome', metadados={'valor': 'Atlas'})
    ambiente[1].salvar('a', 'Carro: Atlas.', chave='carro', metadados={'valor': 'Atlas'})
    conversar(ambiente, 'Não tenho mais o Atlas.')
    assert ambiente[0].gerenciador.estado('a')['carro'] == 'Atlas'


@pytest.mark.parametrize('pergunta,chave,texto', [
    ('Qual é a cidade onde resido?', 'cidade', 'Mora em Sorocaba.'),
    ('Que veículo uso atualmente?', 'carro', 'Carro: Sandero.'),
    ('Em que município vivo?', 'cidade', 'Mora em Sorocaba.'),
    ('Qual atividade física eu pratico?', 'esporte', 'Pratica ciclismo.'),
    ('Qual é minha ocupação?', 'profissao', 'Profissão: arquiteta.'),
    ('Como se chama minha cachorra?', 'pet:cachorro:jade', 'Pet: cachorro chamado Jade.'),
])
def test_parafrases_recuperam_registros_atuais(ambiente, pergunta, chave, texto):
    ambiente[1].salvar('a', texto, chave=chave)
    r = conversar(ambiente, pergunta)
    assert r.memorias_usadas == [texto]
    assert len(ambiente[2]) == 1


def test_contagem_de_pets_recupera_todas_as_memorias_da_especie(ambiente):
    m = ambiente[1]
    m.salvar('a', 'Pet: gato chamado Jade.', chave='pet:gato:jade')
    m.salvar('a', 'Pet: gato chamado Paco.', chave='pet:gato:paco')
    m.salvar('a', 'Pet: cachorro chamado Sol.', chave='pet:cachorro:sol')
    r = conversar(ambiente, 'Quantos gatos tenho?')
    assert len(r.memorias_usadas) == 2
    assert all('gato chamado' in t for t in r.memorias_usadas)


def test_registro_sem_chave_com_forma_canonica_tambem_e_recuperado(ambiente):
    ambiente[1].salvar('a', 'Moro em Sorocaba.')
    r = conversar(ambiente, 'Qual é a cidade onde resido?')
    assert r.memorias_usadas == ['Moro em Sorocaba.']


def test_esquecimento_misto_nao_reintroduz_fato_antigo_no_historico(ambiente):
    conversar(ambiente, 'Moro em Sorocaba.')
    conversar(ambiente, 'Esqueça minha cidade. Explique como organizar estudos.')
    assert len(ambiente[2]) == 1
    assert len(agent.obter_historico('a')) == 1
    assert ambiente[0].gerenciador.estado('a') == {}


def test_hipotese_nao_persiste_como_fato_e_uso_local_nao_fabrica_tokens(ambiente):
    from dataclasses import asdict
    from eval.avaliar_comparativo import tokens_etapa
    conversar(ambiente, 'Talvez eu moro em Sorocaba.')
    assert ambiente[0].gerenciador.estado('a') == {}
    r = conversar(ambiente, 'Moro em Araraquara.')
    assert r.tokens_entrada is None and r.tokens_saida is None
    assert tokens_etapa([asdict(r)])['tokens_total'] == 0


def test_consulta_direta_usa_memoria_atual_sem_valor_antigo_no_prompt(ambiente):
    conversar(ambiente, 'Meu carro é um Fox.')
    conversar(ambiente, 'Meu carro agora é um Sandero.')
    conversar(ambiente, 'Qual é meu carro atual?')
    contexto = str(ambiente[2][-1])
    assert 'Sandero' in contexto and 'Fox' not in contexto
    assert 'Resposta gerada' not in contexto


@pytest.mark.parametrize('fato,pergunta', [
    ('Tenho quatro filhos.', 'Quantos filhos eu tenho?'),
    ('Sou arquiteta.', 'Qual é minha ocupação?'),
    ('Quero viajar para Natal.', 'Qual é a minha viagem?'),
])
def test_baseline_completo_nao_bloqueia_fatos_reconhecidos_pelas_regras(ambiente, fato, pergunta):
    a = ambiente[0].agente
    a.contexto_compacto = False
    selecao = SelecaoModelo('ollama', 'teste')
    a.responder('baseline', fato, [], selecao)
    r = a.responder('baseline', pergunta, [], selecao)
    assert r.origem_uso == 'provedor'
    assert len(ambiente[2]) == 2


def test_chave_personalizada_preserva_suporte_do_texto_canonico(ambiente):
    ambiente[1].salvar('a', 'Carro: Sandero.', chave='lembrete_transporte')
    r = conversar(ambiente, 'Que veículo uso atualmente?')
    assert r.memorias_usadas == ['Carro: Sandero.']
