class ErroDominio(Exception):
    codigo = "erro_interno"
    status_http = 500

    def __init__(self, mensagem: str = "Erro interno."):
        super().__init__(mensagem)
        self.mensagem = mensagem


class ModeloNaoPermitido(ErroDominio):
    codigo, status_http = "modelo_nao_permitido", 400

class ProvedorNaoConfigurado(ErroDominio):
    codigo, status_http = "provedor_nao_configurado", 503

class ProvedorIndisponivel(ErroDominio):
    codigo, status_http = "provedor_indisponivel", 503

class ProvedorTimeout(ErroDominio):
    codigo, status_http = "provedor_timeout", 504