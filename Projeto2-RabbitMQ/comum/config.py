# configuracao para os microservicos
import os
from pathlib import Path

# url da fila do rabbitmq
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")

# exchange tipo direct para eventos de eCommerce, tipo topic para Promocoes
EXCHANGE_ECOMMERCE = "eCommerce"
EXCHANGE_PROMOCOES = "Promocoes"

TIPOS_EXCHANGE = {
    EXCHANGE_ECOMMERCE: "direct",
    EXCHANGE_PROMOCOES: "topic",
}

# o prefixo promocao utilizado para identificar a exchange de Promocoes, que e do tipo topic
PREFIXO_PROMOCAO = "promocao."


def exchange_de(routing_key):
    # retorna a exchange que deve ser usada para publicar a routing key
    if routing_key.startswith(PREFIXO_PROMOCAO):
        return EXCHANGE_PROMOCOES
    return EXCHANGE_ECOMMERCE


# Routing keys
RK_PEDIDO_CRIADO = "pedido.criado"
RK_PEDIDO_EXCLUIDO = "pedido.excluido"
RK_PEDIDO_ESTOQUE_OK = "pedido.estoque_ok"
RK_ESTOQUE_INDISPONIVEL = "estoque.indisponivel"
RK_PRODUTOS_CONSULTA = "produtos.consulta"
RK_PRODUTOS_CATALOGO = "produtos.catalogo"
RK_PAGAMENTO_APROVADO = "pagamento.aprovado"
RK_PAGAMENTO_RECUSADO = "pagamento.recusado"
RK_PEDIDO_ENVIADO = "pedido.enviado"
# Quem pode consultar o catalogo.
SOLICITANTES_CATALOGO = ("principal", "promocoes")

def rk_consulta_catalogo(servico):
    return f"{RK_PRODUTOS_CONSULTA}.{servico}"


def rk_catalogo_para(servico):
    return f"{RK_PRODUTOS_CATALOGO}.{servico}"

# Promocoes: a routing key e hierarquica e carrega a categoria do produto, para o
# consumidor escolher no binding o que quer receber 
CATEGORIAS = ("A", "B", "C")


def rk_promocao(categoria):
    """Routing key da promocao de um produto daquela categoria"""
    return f"{PREFIXO_PROMOCAO}categoria.{categoria}"


PADRAO_TODAS_PROMOCOES = f"{PREFIXO_PROMOCAO}#"

# Filas dos microservicos
FILA_ESTOQUE = "estoque.eventos"
FILA_PRINCIPAL = "principal.eventos"
FILA_PAGAMENTO = "pagamento.eventos"
FILA_ENTREGA = "entrega.eventos"
FILA_PROMOCOES = "promocoes.eventos"
# variavel para definir se os eventos publicados devem ser visiveis 
EVENTOS_VISIVEIS = os.environ.get("EVENTOS_VISIVEIS", "1").strip().lower() not in (
    "0",
    "nao",
    "false",
    "",
)

RAIZ = Path(__file__).resolve().parent.parent

# configuracao inicial do estoque
PRODUTOS_PADRAO = """
1|Teclado Mecanico|349.90|9|A
2|Mouse Gamer|189.50|15|A
3|Monitor 24 polegadas|899.00|5|B
4|Headset Bluetooth|259.90|8|B
5|Webcam Full HD|179.00|0|C
"""

PRODUTOS = os.environ.get("PRODUTOS", PRODUTOS_PADRAO)

# status do pedido
STATUS_CRIADO = "CRIADO"
STATUS_ESTOQUE_OK = "ESTOQUE_OK"
STATUS_ESTOQUE_INDISPONIVEL = "ESTOQUE_INDISPONIVEL"
STATUS_EXCLUIDO = "EXCLUIDO"
STATUS_PAGAMENTO_APROVADO = "PAGAMENTO_APROVADO"
STATUS_PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
STATUS_PEDIDO_ENVIADO = "PEDIDO_ENVIADO"

# Promocoes
# Segundos entre uma promocao e a seguinte.
PROMOCAO_INTERVALO = int(os.environ.get("PROMOCAO_INTERVALO", "15"))

# Chaves
# As publicas formam um keyring unico, igual para todos os servicos
# Cada servico possui apenas a sua privada.
# Em Docker, CHAVE_PRIVADA aponta para o secret e CHAVES_PUBLICAS para o volume :ro.
DIR_CHAVES = RAIZ / "chaves"
CHAVES_PUBLICAS = Path(os.environ.get("CHAVES_PUBLICAS", DIR_CHAVES / "publicas"))
_PRIVADA_ENV = os.environ.get("CHAVE_PRIVADA")

def caminho_chave_privada(servico):
    return Path(_PRIVADA_ENV) if _PRIVADA_ENV else DIR_CHAVES / "privadas" / servico
