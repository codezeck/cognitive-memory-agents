"""Seleção de turnos recentes; não apaga histórico nem memórias persistentes."""

VERSAO_CONTEXTO = "memoria-contexto-v3"
MAX_TURNOS_RECENTES = 3
MAX_CARACTERES_HISTORICO = 6000


def selecionar_historico(historico: list[dict]) -> list[dict]:
    """Preserva pares completos e contíguos, do mais recente para o antigo.

    O orçamento em caracteres vale apenas para o histórico. Sistema, memórias
    recuperadas e pergunta atual são preservados pelo chamador. Não é uma
    contagem de tokens nem uma garantia sobre a janela total do modelo.
    """
    selecionados = []
    tamanho = 0
    for fim in range(len(historico), 1, -2):
        turno = historico[fim - 2:fim]
        if [m['role'] for m in turno] != ['user', 'assistant']:
            break
        custo = sum(len(m['content']) for m in turno)
        if tamanho + custo > MAX_CARACTERES_HISTORICO:
            break
        selecionados[0:0] = turno
        tamanho += custo
        if len(selecionados) == MAX_TURNOS_RECENTES * 2:
            break
    return selecionados
