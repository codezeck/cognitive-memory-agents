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

    

class MemoriaNaoEncontrada(ErroDominio):
    codigo, status_http = "memoria_nao_encontrada", 404
    

class NaoAutenticado(ErroDominio):
    codigo, status_http = "nao_autenticado", 401

class AcessoNegado(ErroDominio):
    codigo, status_http = "acesso_negado", 403