import pytest

from src.armazenamento.repositorio import MemoriaSQLite
from src.memoria.store_mem import MemoriaEmRam


@pytest.fixture(params=['ram', 'sqlite'])
def memoria(request, tmp_path):
    resultado = (MemoriaEmRam() if request.param == 'ram' else
                 MemoriaSQLite(str(tmp_path / 'teste.db')))
    yield resultado
    if hasattr(resultado, '_con'):
        resultado._con.close()


def test_cargo_recupera_profissao_atual_sem_depender_de_palavras_iguais(memoria):
    memoria.salvar('a', 'Profissão: ilustradora.', chave='profissao')
    atual = memoria.salvar('a', 'Profissão: editora.', chave='profissao')
    memoria.salvar('a', 'Meu cargo favorito é cozinheira.', chave='outro')
    memoria.salvar('b', 'Profissão: engenheira.', chave='profissao')
    assert memoria.buscar('a', 'Qual é meu cargo?') == [
        {'id': atual, 'texto': 'Profissão: editora.', 'score': 1.0}]
    assert memoria.buscar('a', 'Qual é meu cargo?', k=0) == []


def test_sem_chave_e_conversa_geral_preservam_busca_vetorial(memoria):
    memoria.salvar('a', 'O projeto Aurora usa Python.')
    assert memoria.buscar('a', 'Aurora Python')[0]['texto'] == 'O projeto Aurora usa Python.'
    memoria.salvar('a', 'Meu cargo é editora.')
    assert any(r['texto'] == 'Meu cargo é editora.'
               for r in memoria.buscar('a', 'Qual é meu cargo?'))


def test_esquecimento_remove_suporte_estruturado_sem_afetar_outro_usuario(memoria):
    memoria.salvar('a', 'Profissão: editora.', chave='profissao')
    memoria.salvar('b', 'Profissão: artista.', chave='profissao')
    memoria.esquecer_usuario('a')
    assert memoria.buscar('a', 'Qual é minha profissão?') == []
    assert memoria.buscar('b', 'Qual é meu cargo?')[0]['texto'] == 'Profissão: artista.'
