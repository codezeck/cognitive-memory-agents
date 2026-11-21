import httpx

from eval.sessoes_transporte import Credencial, Evento
from tools.executar_p6_local import APIIsolada, ColetorLocal, snapshot


def test_coletor_cria_esquema_por_api_e_observa_reinicio_real_sem_modelo(tmp_path):
    usuarios = {'u1': Credencial('p6_teste_isolado', 'token-sintetico-de-teste')}
    db = tmp_path / 'dados' / 'novo.db'
    api = APIIsolada(tmp_path, db, usuarios, 'modelo-nao-consultado')
    config = {'agente_real': True, 'provedor': 'ollama', 'modelo': 'modelo-nao-consultado',
              'backend_id': 'sintetico', 'backend_historico_id': 'sintetico', 'commit_api': 'teste'}
    try:
        api.iniciar()
        assert not db.exists()  # /saude não materializa o banco.
        coletor = ColetorLocal(tmp_path, api, 'execucao-teste', config, {})
        coletor.preparar_iniciais()
        assert snapshot(db) == []
        coletor.preparar(execucao_id='execucao-teste', api_url=api.url,
                         usuarios={'u1': 'p6_teste_isolado'}, provedor='ollama', modelo='modelo-nao-consultado')
        with httpx.Client(base_url=api.url, headers={
                'Authorization': 'Bearer token-sintetico-de-teste'}, timeout=10) as c:
            resposta = c.post('/usuarios/p6_teste_isolado/memorias',
                              json={'texto': 'Profissão: artista.', 'chave': 'profissao'})
            resposta.raise_for_status()
        evento = Evento('u1/s1/checkpoint_persistencia', 'u1', 1, 'checkpoint_persistencia')
        medicao = coletor(evento)
        assert medicao['reinicio_confirmado'] is True
        assert medicao['estado_antes'] == medicao['estado_depois']
        assert len(medicao['estado_depois']) == 1
        assert medicao['evidencia_status'] == 'compativel'
    finally:
        api.parar()
        api.log.close()
