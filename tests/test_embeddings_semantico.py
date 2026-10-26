import os

import pytest

pytest.importorskip("fastembed")

if not os.getenv("TESTAR_EMBEDDER_SEMANTICO"):
    pytest.skip(
        "defina TESTAR_EMBEDDER_SEMANTICO=1 (baixa o modelo na primeira vez)",
        allow_module_level=True,
    )

from src.memoria.embeddings_semantico import EmbedderFastembed  # noqa: E402


@pytest.fixture(scope="module")
def embedder():
    return EmbedderFastembed()


def test_vetores_tem_a_dimensao_e_norma_um(embedder):
    vetor = embedder.embed(["Eu moro em Osasco"])[0]
    assert len(vetor) == embedder.dimensao
    assert abs(sum(v * v for v in vetor) - 1.0) < 1e-3


def test_frase_parecida_fica_mais_perto_que_frase_sem_relacao(embedder):
    fato, parecida, outra = embedder.embed(
        ["Trabalho como enfermeira", "Qual é a minha profissão?", "A lasanha estava ótima"]
    )

    def sim(a, b):
        return sum(x * y for x, y in zip(a, b))

    assert sim(fato, parecida) > sim(fato, outra)