from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from eval import avaliar_comparativo as comparativo
from eval.avaliar_comparativo import (
    avaliar_resposta_comparativo,
    texto_memoria,
    avaliar_resposta_controlada,
    resposta_esperada_cenario,
    resumir,
    avaliar_recuperacao_equivalente,
)
from src import agent as agente_mod
from src.api import agente_local as modulo_agente
from src.api.catalogo import SelecaoModelo
from src.armazenamento.repositorio import MemoriaSQLite
from src.memoria.gerenciador import GerenciadorMemoria


def caso_esquecimento_cidade():
    return {
        "id": "TEST-CIDADE",
        "categoria": "esquecimento",
        "mensagens": [
            "Moro em Osasco.",
            "Esqueça minha cidade.",
            "Em que cidade moro?",
        ],
        "esperado": ["não sei"],
        "informacoes_esquecidas": ["Osasco"],
        "avaliacao": {"tipo_resposta": "abstencao", "atributo": "cidade", "informacoes_proibidas": []},
    }


def caso_esquecimento_time():
    return {
        "id": "TEST-TIME",
        "categoria": "esquecimento",
        "mensagens": [
            "Torço pelo Vasco.",
            "Não torço mais pelo Vasco.",
            "Para qual time torço?",
        ],
        "esperado": ["não sei"],
        "informacoes_esquecidas": ["Vasco"],
        "avaliacao": {"tipo_resposta": "abstencao", "atributo": "time", "informacoes_proibidas": []},
    }


def test_resposta_desconhecida_explicita_e_aprovada():
    assert avaliar_resposta_comparativo(
        "Não sei.",
        caso_esquecimento_cidade(),
    )


def test_memoria_sem_informacao_e_aprovada():
    assert avaliar_resposta_comparativo(
        "A memória não contém informações sobre sua cidade.",
        caso_esquecimento_cidade(),
    )


def test_nao_aceita_desconhecimento_com_cidade_inventada():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas você mora em Osasco.",
        caso_esquecimento_cidade(),
    )


def test_nao_aceita_desconhecimento_com_time_inventado():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas você torce pelo Vasco.",
        caso_esquecimento_time(),
    )


def test_texto_de_memoria_cidade():
    assert texto_memoria("cidade", "Osasco") == "Moro em Osasco."


def test_texto_de_memoria_carro():
    assert texto_memoria("carro", "Corolla") == "Meu carro é um Corolla."

def test_rejeita_cidade_esquecida_com_ressalva():
    assert not avaliar_resposta_comparativo(
        "Não tenho informações, mas acredito que você esteja em Osasco.",
        caso_esquecimento_cidade(),
    )


def test_recusa_sem_revelar_cidade_nao_comprova_desconhecimento():
    julgamento = comparativo.julgar_resposta(
        "Não posso fornecer informações pessoais sobre a cidade onde moro.",
        caso_esquecimento_cidade(),
    )
    assert julgamento["sem_informacao_proibida"]["valor"] is True
    assert julgamento["abstencao_correta"]["status"] == "nao_verificado"
    assert julgamento["passou"] is False


def test_rejeita_desconhecimento_com_cidade_inventada():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas moro em São Paulo.",
        caso_esquecimento_cidade(),
    )


def test_rejeita_desconhecimento_com_time_inventado():
    assert not avaliar_resposta_comparativo(
        "Não sei, mas você torce pelo Santos.",
        caso_esquecimento_time(),
    )


def test_aceita_falta_de_local_fornecido():
    assert avaliar_resposta_comparativo(
        "Você não forneceu o local onde você mora.",
        caso_esquecimento_cidade(),
    )


def test_aceita_historico_sem_informacao_sobre_cidade():
    assert avaliar_resposta_comparativo(
        "Seu histórico não contém informações sobre a cidade onde você mora.",
        caso_esquecimento_cidade(),
    )


def test_aceita_impossibilidade_de_reconhecer_cidade():
    assert avaliar_resposta_comparativo(
        "Não posso reconhecer sua cidade.",
        caso_esquecimento_cidade(),
    )


def test_aceita_agente_sem_informacao_atualizada():
    assert avaliar_resposta_comparativo(
        "O agente não tem informações atualizadas "
        "sobre a localização exata do usuário.",
        caso_esquecimento_cidade(),
    )


def test_aceita_nao_posso_lembrar_da_cidade():
    assert avaliar_resposta_comparativo(
        "Não posso lembrar de sua cidade.",
        caso_esquecimento_cidade(),
    )


def test_rejeita_cidade_inventada_apos_esquecimento():
    assert not avaliar_resposta_comparativo(
        "Eu souvi que você mora em São Paulo, Brasil.",
        caso_esquecimento_cidade(),
    )


def test_avaliacao_controlada_aceita_valor_exato():
    assert avaliar_resposta_controlada("Campinas.", "Campinas")


def test_avaliacao_controlada_rejeita_frase_completa():
    assert not avaliar_resposta_controlada(
        "Você mora em Campinas.",
        "Campinas",
    )


def test_avaliacao_controlada_aceita_desconhecido():
    assert avaliar_resposta_controlada(
        "DESCONHECIDO.",
        "DESCONHECIDO",
    )


def test_sem_memoria_espera_desconhecido():
    assert resposta_esperada_cenario(
        {"esperado": "Osasco"},
        "sem_memoria",
    ) == "DESCONHECIDO"


def test_esquecimento_espera_desconhecido():
    assert resposta_esperada_cenario(
        {"esperado": ["não sei"]},
        "memoria_regras_api",
    ) == "DESCONHECIDO"


def test_memoria_persistente_preserva_fato_esperado():
    assert resposta_esperada_cenario(
        {"esperado": "Osasco"},
        "memoria_persistente_api",
    ) == "Osasco"


def test_resumo_contabiliza_falhas_na_taxa_aprovacao():
    resultados = [
        {
            "cenario": "sem_memoria",
            "passou": True,
            "tokens_total": 10,
            "latencia_api_total_ms": 100,
            "metricas_completas": True,
        },
        {
            "cenario": "sem_memoria",
            "passou": False,
            "erro": "Timeout na API",
        },
    ]

    resumo = resumir(resultados)["sem_memoria"]

    assert resumo["casos"] == 2
    assert resumo["executados"] == 1
    assert resumo["falhas"] == 1
    assert resumo["aprovados"] == 1
    assert resumo["taxa_aprovacao_pct"] == 50.0

def test_recuperacao_equivalente_aceita_variantes_conhecidas():
    assert avaliar_recuperacao_equivalente(
        ["Moro em Osasco."], ["Mora em Osasco."]
    )
    assert avaliar_recuperacao_equivalente(
        ["Pratico yoga."], ["Pratica yoga"]
    )
    assert avaliar_recuperacao_equivalente(
        ["Meu carro é um Corolla."], ["Carro: Corolla."]
    )
    assert avaliar_recuperacao_equivalente(
        ["Meu nome é Ezequiel."], ["Chama-se Ezequiel."]
    )


def test_recuperacao_equivalente_rejeita_valor_incorreto():
    assert not avaliar_recuperacao_equivalente(
        ["Moro em Osasco."], ["Mora em Campinas."]
    )


def test_recuperacao_equivalente_rejeita_fato_extra():
    assert not avaliar_recuperacao_equivalente(
        ["Moro em Osasco."],
        ["Mora em Osasco.", "Pratica yoga."],
    )


def test_recuperacao_equivalente_rejeita_duplicados():
    assert not avaliar_recuperacao_equivalente(
        ["Moro em Osasco."],
        ["Mora em Osasco.", "Moro em Osasco."],
    )


def test_recuperacao_equivalente_memoria_vazia():
    assert avaliar_recuperacao_equivalente([], [])
    assert not avaliar_recuperacao_equivalente(
        [], ["Mora em Osasco."]
    )


def test_recuperacao_equivalente_preserva_fatos_desconhecidos():
    assert avaliar_recuperacao_equivalente(
        ["fato personalizado ABC"],
        ["fato personalizado ABC"],
    )
    assert not avaliar_recuperacao_equivalente(
        ["fato personalizado ABC"],
        ["fato personalizado XYZ"],
    )


def caso_historico():
    return {
        "id": "TEST-HISTORICO",
        "categoria": "recuperacao",
        "mensagens": ["Moro em Osasco.", "Em que cidade moro?"],
        "memorias": ["Moro em Osasco."],
        "esperado": "Osasco",
        "estado_regras_esperado": {"cidade": "Osasco"},
        "avaliacao": {"tipo_resposta": "factual", "atributo": "cidade", "informacoes_proibidas": []},
    }


@pytest.fixture
def historico_simulado(monkeypatch):
    estado = SimpleNamespace(
        chamadas=[], entradas=[], adaptadores=[], falhar_na_chamada=None,
        cliente=Mock(spec=httpx.Client),
    )
    monkeypatch.setattr(agente_mod, "historicos_por_usuario", {})
    # Estes testes verificam a P1 no mesmo processo; spawn é testado separadamente.
    monkeypatch.setattr(
        comparativo, "executar_historico_em_processo",
        lambda caso, provedor, modelo, timeout=None:
            comparativo.executar_historico(caso, provedor, modelo),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "chave-simulada")

    class AdaptadorSimulado:
        def gerar_com_detalhes(self, mensagens):
            estado.chamadas.append([dict(m) for m in mensagens])
            if len(estado.chamadas) == estado.falhar_na_chamada:
                raise RuntimeError("falha simulada do modelo")
            return {
                "resposta": "Osasco", "tokens_entrada": 11, "tokens_saida": 3,
            }

    def fabrica(provedor):
        def criar(modelo, api_key=None):
            estado.adaptadores.append((provedor, modelo, api_key))
            return AdaptadorSimulado()
        return criar

    monkeypatch.setattr(modulo_agente, "OllamaAdapter", fabrica("ollama"))
    monkeypatch.setattr(modulo_agente, "OpenAIAdapter", fabrica("openai"))
    responder_original = modulo_agente.AgenteLocal.responder

    def observar(self, usuario_id, mensagem, memorias, selecao):
        estado.entradas.append((usuario_id, mensagem, list(memorias), selecao))
        return responder_original(self, usuario_id, mensagem, memorias, selecao)

    monkeypatch.setattr(modulo_agente.AgenteLocal, "responder", observar)

    def proibir_memoria(*args, **kwargs):
        pytest.fail("O controle de histórico não deve acessar a API ou memória.")

    monkeypatch.setattr(comparativo, "conversar", proibir_memoria)
    monkeypatch.setattr(comparativo, "limpar_usuario", proibir_memoria)
    monkeypatch.setattr(MemoriaSQLite, "__init__", proibir_memoria)
    monkeypatch.setattr(GerenciadorMemoria, "processar", proibir_memoria)
    return estado


@pytest.mark.parametrize(
    "provedor,modelo,chave",
    [("ollama", "modelo-local-teste", None),
     ("openai", "modelo-hospedado-teste", "chave-simulada")],
)
def test_historico_isola_memoria_e_preserva_agente_e_avaliador(
    monkeypatch, historico_simulado, provedor, modelo, chave,
):
    estado = historico_simulado
    caso = caso_historico()
    agente_mod.obter_historico(comparativo.USUARIO_HISTORICO).append(
        {"role": "user", "content": "Texto de outro caso"}
    )
    outro = agente_mod.obter_historico("outro_usuario")
    outro.append({"role": "user", "content": "Conversa preservada"})
    avaliar = Mock(wraps=comparativo.julgar_resposta)
    monkeypatch.setattr(comparativo, "julgar_resposta", avaliar)

    resultado = comparativo.executar_cenario(
        estado.cliente, caso, "historico_completo", provedor, modelo,
    )

    sistema = {"role": "system", "content": agente_mod.SYSTEM_PROMPT}
    assert estado.chamadas == [
        [sistema, {"role": "user", "content": caso["mensagens"][0]}],
        [sistema, {"role": "user", "content": caso["mensagens"][0]},
         {"role": "assistant", "content": "Osasco"},
         {"role": "user", "content": caso["mensagens"][1]}],
    ]
    assert estado.entradas == [
        (comparativo.USUARIO_HISTORICO, m, [], SelecaoModelo(provedor, modelo))
        for m in caso["mensagens"]
    ]
    assert estado.adaptadores == [(provedor, modelo, chave)]
    avaliar.assert_called_once_with("Osasco", caso)
    assert resultado["passou"] is True
    assert resultado["via"] == "agente_local"
    assert resultado["memorias_usadas"] == []
    assert resultado["tokens_entrada"] == 22
    assert resultado["tokens_saida"] == 6
    assert resultado["tokens_total"] == 28
    assert resultado["chamadas_modelo"] == 2
    assert agente_mod.obter_historico(comparativo.USUARIO_HISTORICO) == [sistema]
    assert agente_mod.obter_historico("outro_usuario") is outro
    assert outro[-1]["content"] == "Conversa preservada"
    assert estado.cliente.mock_calls == []


def test_historico_isola_casos_e_nao_reinicia_por_pedido_de_esquecimento(
    historico_simulado,
):
    estado = historico_simulado
    caso = caso_esquecimento_cidade()
    for _ in range(2):
        comparativo.executar_cenario(
            estado.cliente, caso, "historico_completo", "ollama", "modelo-teste",
        )

    for inicio in (0, 3):
        assert len(estado.chamadas[inicio]) == 2
        assert [m["content"] for m in estado.chamadas[inicio + 2]
                if m["role"] == "user"] == caso["mensagens"]
    assert len(agente_mod.obter_historico(comparativo.USUARIO_HISTORICO)) == 1
    assert estado.cliente.mock_calls == []


@pytest.mark.parametrize("origem", ["modelo", "avaliacao"])
def test_historico_limpa_contexto_mesmo_em_erro(
    monkeypatch, historico_simulado, origem,
):
    estado = historico_simulado
    if origem == "modelo":
        estado.falhar_na_chamada = 2
    else:
        def falhar(*args):
            raise RuntimeError("falha simulada da avaliação")
        monkeypatch.setattr(comparativo, "julgar_resposta", falhar)

    with pytest.raises(RuntimeError, match="falha simulada"):
        comparativo.executar_cenario(
            estado.cliente, caso_historico(), "historico_completo",
            "ollama", "modelo-teste",
        )

    assert agente_mod.obter_historico(comparativo.USUARIO_HISTORICO) == [
        {"role": "system", "content": agente_mod.SYSTEM_PROMPT},
    ]
    assert estado.cliente.mock_calls == []


@pytest.mark.parametrize(
    "cenario,conversas,memorias,sessoes",
    [("sem_memoria", 1, 0, 2), ("memoria_persistente_api", 1, 1, 2),
     ("memoria_regras_api", 2, 0, 3)],
)
def test_demais_cenarios_continuam_pela_api(
    monkeypatch, cenario, conversas, memorias, sessoes,
):
    caso = caso_historico()
    pedidos = []

    def proibir_agente_local():
        pytest.fail("Os demais cenários devem continuar usando a API.")

    monkeypatch.setattr(comparativo, "AgenteLocal", proibir_agente_local)

    def responder(request):
        caminho = request.url.path
        pedidos.append((request.method, caminho))
        if request.method == "DELETE":
            return httpx.Response(200, json={"removidas": 0})
        if caminho.endswith("/sessoes"):
            return httpx.Response(204)
        if caminho.endswith("/memorias"):
            return httpx.Response(201, json={"id": "memoria-simulada"})
        if caminho.endswith("/estado-regras"):
            return httpx.Response(200, json=caso["estado_regras_esperado"])
        assert caminho == "/conversas"
        return httpx.Response(200, json={
            "resposta": "DESCONHECIDO" if cenario == "sem_memoria" else "Osasco",
            "memorias_usadas": [] if cenario == "sem_memoria" else caso["memorias"],
            "tokens_entrada": 11, "tokens_saida": 3, "latencia_ms": 1,
        })

    with httpx.Client(transport=httpx.MockTransport(responder),
                      base_url="http://teste") as cliente:
        resultado = comparativo.executar_cenario(
            cliente, caso, cenario, "ollama", "modelo-teste",
        )

    caminho = f"/usuarios/{comparativo.USUARIO_ID}"
    assert pedidos.count(("POST", "/conversas")) == conversas
    assert pedidos.count(("POST", f"{caminho}/memorias")) == memorias
    assert pedidos.count(("POST", f"{caminho}/sessoes")) == sessoes
    assert pedidos.count(("DELETE", f"{caminho}/memorias")) == 2
    assert resultado["via"] == "api"
    assert resultado["passou"] is True
