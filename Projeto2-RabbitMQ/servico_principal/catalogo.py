# A pergunta sai em produtos.consulta.principal e a resposta volta em
# produtos.catalogo.principal o endereco viaja na routing key, entao o Estoque nao
# precisa ler o conteudo da mensagem para saber para quem responder

from comum import requisicao
from comum.config import rk_consulta_catalogo

TempoEsgotado = requisicao.TempoEsgotado

_correlacionador = requisicao.Correlacionador()


def solicitar(canal, espera=5):
    # Publica produtos.consulta e devolve a lista de produtos respondida.

    resposta = _correlacionador.perguntar(
        canal, rk_consulta_catalogo("principal"), espera=espera
    )
    return resposta["produtos"]


def receber(evento):
    """Entrega um produtos.catalogo a consulta que o aguarda."""
    _correlacionador.responder(evento)
