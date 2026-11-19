"""Reprodução entre SOs sem afrouxar o congelamento de conteúdo."""
import hashlib
import json

import pytest

from tools import reproduzir_p6 as modulo


@pytest.mark.parametrize('origem,checkout', [(b'\r\n', b'\n'), (b'\n', b'\r\n')])
def test_mesmo_conteudo_entre_windows_linux(origem, checkout):
    texto = b'{\n  "valor": "Santos"\n}\n'
    congelado = texto.replace(b'\n', origem)
    atual = texto.replace(b'\n', checkout)
    assert modulo.conferir_fonte(atual, hashlib.sha256(congelado).hexdigest()) == hashlib.sha256(atual).hexdigest()


@pytest.mark.parametrize('novo', [b'{\n  "valor": "Campinas"\n}\n',
                                 b'{\n"valor": "Santos"\n}\n'])
def test_mudanca_de_gabarito_ou_formatacao_extra_e_rejeitada(novo):
    congelado = b'{\r\n  "valor": "Santos"\r\n}\r\n'
    with pytest.raises(ValueError, match='além dos finais de linha'):
        modulo.conferir_fonte(novo, hashlib.sha256(congelado).hexdigest())


def test_protocolo_novo_preserva_original_e_usa_bytes_reais(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo, 'RAIZ', tmp_path)
    monkeypatch.setattr(modulo, 'PROTOCOLO', modulo.Path('original.json'))
    monkeypatch.setattr(modulo, 'FONTES', {'dataset_sha256': modulo.Path('dados.json')})
    fonte = b'{\n  "fato": 1\n}\n'
    (tmp_path/'dados.json').write_bytes(fonte)
    p = {'execucao_autorizada': True, 'referencia': 'decisão do usuário',
         'dataset_sha256': hashlib.sha256(fonte.replace(b'\n', b'\r\n')).hexdigest()}
    original = json.dumps(p).encode()
    (tmp_path/'original.json').write_bytes(original)
    destino = tmp_path/'novo.json'
    modulo.preparar_protocolo(destino)
    novo = json.loads(destino.read_text(encoding='utf-8'))
    assert (tmp_path/'original.json').read_bytes() == original
    assert novo['dataset_sha256'] == hashlib.sha256(fonte).hexdigest()
    assert novo['reproducao']['hashes_originais']['dataset_sha256'] == p['dataset_sha256']
    assert novo['reproducao']['revisao_humana_adicional'] is False
    with pytest.raises(FileExistsError):
        modulo.preparar_protocolo(destino)


def test_rodada_existente_e_recusada_antes_de_preparo_e_modelo(tmp_path, monkeypatch):
    def nao_preparar(*args):
        pytest.fail('não deve preparar protocolo para uma saída existente')
    monkeypatch.setattr(modulo, 'preparar_protocolo', nao_preparar)
    with pytest.raises(SystemExit) as erro:
        modulo.main(['--saida-dir', str(tmp_path), '--commit-base', 'teste'])
    assert erro.value.code == 2
