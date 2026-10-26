from dataclasses import dataclass

from src.api.config import Configuracao
from src.api.erros import ModeloNaoPermitido, ProvedorNaoConfigurado


@dataclass(frozen=True)
class SelecaoModelo:
    provedor: str
    modelo: str


class Catalogo:
    def __init__(self, config: Configuracao):
        self.config = config

    def listar(self) -> list[dict]:
        c = self.config
        return [
            {"provedor": p, "modelo": m,
             "local": not c.exige_chave(p),
             "configurado": (not c.exige_chave(p)) or bool(c.chave_de(p)),
             "padrao": (p, m) == (c.provedor_padrao, c.modelo_padrao)}
            for p, m in c.modelos_permitidos
        ]

    def resolver(self, provedor: str | None, modelo: str | None) -> SelecaoModelo:
        c = self.config
        provedor = (provedor or c.provedor_padrao).lower()
        if modelo is None:
            if provedor == c.provedor_padrao:
                modelo = c.modelo_padrao
            else:
                modelo = next((m for p, m in c.modelos_permitidos if p == provedor), None)
        if modelo is None or (provedor, modelo) not in c.modelos_permitidos:
            raise ModeloNaoPermitido(
                f"A combinação {provedor}/{modelo} não é permitida. Veja GET /provedores.")
        if c.exige_chave(provedor) and not c.chave_de(provedor):
            raise ProvedorNaoConfigurado(
                f"O provedor '{provedor}' não está configurado neste servidor.")
        return SelecaoModelo(provedor, modelo)