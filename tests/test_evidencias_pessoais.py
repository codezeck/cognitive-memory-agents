"""Politica local; geracao verdadeira e coberta pela bateria Docker opt-in."""
import pytest

from src import agent


@pytest.fixture
def modelo():
    agent.historicos_por_usuario.clear()

    class Modelo:
        def __init__(self):
            self.chamadas = []

        def gerar(self, mensagens):
            self.chamadas.append([dict(m) for m in mensagens])
            # Adversarial: nao respeita a orientacao para admitir desconhecimento.
            return 'Resposta do modelo sem garantia de fidelidade.'

    modelo = Modelo()
    yield modelo
    agent.historicos_por_usuario.clear()


@pytest.mark.parametrize('pergunta', [
    'Onde eu moro?', 'Em que cidade moro?', 'Em qual cidade eu moro?', 'Qual e a minha cidade de residencia?',
    'Qual e o meu nome?', 'Qual e o meu telefone?', 'Como me chamo?',
])
def test_fato_nunca_informado_nao_depende_de_obediencia_do_modelo(modelo, pergunta):
    resultado = agent.responder(pergunta, 'u1', adaptador=modelo, retornar_detalhes=True)
    assert resultado == {'resposta': 'DESCONHECIDO', 'tokens_entrada': None, 'tokens_saida': None,
                         'origem_uso':'politica_local', 'chamadas_modelo_observadas':0}
    assert modelo.chamadas == []


@pytest.mark.parametrize('memoria', [
    'Mora em Niteroi.', {'texto': 'Mora em Niteroi.'}, {'content': 'Mora em Niteroi.'},
])
def test_suporte_real_na_memoria_continua_no_modelo(modelo, memoria):
    resposta = agent.responder('Em que cidade moro?', 'u1', [memoria], modelo)
    assert resposta == 'Resposta do modelo sem garantia de fidelidade.'
    assert len(modelo.chamadas) == 1
    assert any('Mora em Niteroi.' in m['content'] for m in modelo.chamadas[0])


@pytest.mark.parametrize('pergunta,memoria', [
    ('Qual e o meu nome?', 'Chama-se Larissa.'),
    ('Qual e o meu esporte?', 'Pratica corrida.'),
    ('Qual e o meu time?', 'Torce para Fluminense.'),
    ('Qual e a minha cor favorita?', 'Favorito (cor): lilas.'),
    ('Qual e o meu apelido?', 'Prefere ser chamado de Lari.'),
    ('Qual e a minha viagem?', 'Planeja viajar para Curitiba.'),
    ('Qual e o meu projeto?', 'O projeto se chama Laboratorio.'),
    ('Qual e a minha cidade?', 'Mora em Nao-Me-Toque.'),
])
def test_formas_canonicas_ja_usadas_pelo_produto_continuam_com_suporte(modelo, pergunta, memoria):
    assert agent.responder(pergunta, 'u1', [memoria], modelo) != 'DESCONHECIDO'
    assert len(modelo.chamadas) == 1


def test_memoria_irrelevante_ou_resposta_antiga_do_assistente_nao_da_suporte(modelo):
    agent.obter_historico('u1').extend([
        {'role': 'user', 'content': 'Em que cidade moro?'},
        {'role': 'assistant', 'content': 'Voce mora em Sao Paulo.'},
    ])
    resposta = agent.responder('Onde moro?', 'u1',
                              ['A cidade preferida para turismo e Natal.'], modelo)
    assert resposta == 'DESCONHECIDO'
    assert modelo.chamadas == []


@pytest.mark.parametrize('mensagem', [
    'Qual e a capital da Franca?', 'Como posso organizar meus estudos?',
    'Qual e a minha melhor opcao para estudar?',
    'Minha palavra de exemplo e NEVOA. Qual e a minha palavra de exemplo?',
    'Moro em Niteroi. Em que cidade eu moro?',
    'Na cidade onde eu moro faz frio.',
])
def test_conversa_comum_e_suporte_na_mensagem_atual_preservados(modelo, mensagem):
    assert agent.responder(mensagem, 'u1', adaptador=modelo) == (
        'Resposta do modelo sem garantia de fidelidade.')
    assert modelo.chamadas[-1][-1]['content'] == mensagem


def test_historico_usuario_da_suporte_mas_reset_e_outro_usuario_nao(modelo):
    agent.responder('Moro em Niteroi.', 'u1', adaptador=modelo)
    agent.responder('Onde moro?', 'u1', adaptador=modelo)
    chamadas_antes = len(modelo.chamadas)
    assert agent.responder('Onde moro?', 'u2', adaptador=modelo) == 'DESCONHECIDO'
    agent.limpar_historico('u1')
    assert agent.responder('Onde moro?', 'u1', adaptador=modelo) == 'DESCONHECIDO'
    assert len(modelo.chamadas) == chamadas_antes


def test_atualizacao_chega_ao_modelo_com_memoria_ativa_sem_substituida(modelo):
    agent.responder('Moro em Niteroi.', 'u1', adaptador=modelo)
    agent.responder('Agora moro em Vitoria.', 'u1', ['Mora em Vitoria.'], modelo)
    agent.responder('Onde moro?', 'u1', ['Mora em Vitoria.'], modelo)
    fontes = [m['content'] for m in modelo.chamadas[-1] if m['role'] == 'system']
    assert any('Mora em Vitoria.' in m for m in fontes)
    assert all('Mora em Niteroi.' not in m for m in fontes)


def test_pergunta_nao_prova_o_fato_e_negacao_nao_e_afirmacao_positiva(modelo):
    agent.responder('Eu nao moro em Niteroi.', 'u1', adaptador=modelo)
    chamadas_antes = len(modelo.chamadas)
    assert agent.responder('Onde moro?', 'u1', adaptador=modelo) == 'DESCONHECIDO'
    assert len(modelo.chamadas) == chamadas_antes


def test_pergunta_mista_separa_parte_sem_suporte_sem_bloquear_parte_geral(modelo):
    resposta = agent.responder('Qual e a minha cidade? Quanto e 2 + 3?', 'u1', adaptador=modelo)
    assert resposta == 'DESCONHECIDO (cidade).\nResposta do modelo sem garantia de fidelidade.'
    assert modelo.chamadas[-1][-1]['content'] == 'Quanto e 2 + 3?'
    assert agent.obter_historico('u1')[-2]['content'] == 'Qual e a minha cidade? Quanto e 2 + 3?'


@pytest.mark.parametrize('pergunta,memoria', [
    ('Qual é meu carro atual?', 'Carro: Corsa.'),
    ('Você lembra qual é o meu carro atualmente?', 'Meu carro é um Fit.'),
    ('Para qual time eu torço?', 'Torce para Bahia.'),
    ('Qual esporte pratico?', 'Pratica ciclismo.'),
    ('Qual é a minha profissão atual?', 'Profissão: bibliotecária.'),
])
def test_consultas_reformuladas_reconhecem_suporte_canonico(modelo, pergunta, memoria):
    assert agent.responder(pergunta, 'u1', [memoria], modelo) != 'DESCONHECIDO'
    assert len(modelo.chamadas) == 1


@pytest.mark.parametrize('pergunta', [
    'Para qual time torço?', 'Por qual time eu torço?',
    'Qual esporte eu pratico?', 'Qual é meu carro atual?',
])
def test_reformulacoes_sem_suporte_nao_inventam_valores(modelo, pergunta):
    assert agent.responder(pergunta, 'u1', ['Profissão: artista.'], modelo) == 'DESCONHECIDO'
    assert modelo.chamadas == []


@pytest.mark.parametrize('fato,pergunta', [
    ('Pratico ciclismo.', 'Qual esporte pratico?'),
    ('Torço pelo Bahia.', 'Para qual time torço?'),
    ('Meu carro agora é um Fit.', 'Qual é meu carro atual?'),
])
def test_reformulacoes_usam_fatos_do_usuario_na_sessao(modelo, fato, pergunta):
    agent.responder(fato, 'u1', adaptador=modelo)
    assert agent.responder(pergunta, 'u1', adaptador=modelo) != 'DESCONHECIDO'
    assert len(modelo.chamadas) == 2


@pytest.mark.parametrize('texto', [
    'Não torço pelo Bahia.', 'Talvez eu torça pelo Bahia.',
    'Você acha que torço pelo Bahia?',
])
def test_negacao_hipotese_e_pergunta_nao_autorizam_time(modelo, texto):
    agent.responder(texto, 'u1', adaptador=modelo)
    chamadas = len(modelo.chamadas)
    assert agent.responder('Para qual time torço?', 'u1', adaptador=modelo) == 'DESCONHECIDO'
    assert len(modelo.chamadas) == chamadas
