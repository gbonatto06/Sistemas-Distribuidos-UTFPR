# configuracao para os microservicos
import os
from pathlib import Path


# le o segredo do arquivo do secret, em /run/secrets/<nome>
def segredo(nome):
    try:
        return Path("/run/secrets", nome).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


# url da fila do rabbitmq
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")

# exchange tipo direct para todos os eventos do backend
EXCHANGE_ECOMMERCE = "eCommerce"

# Routing keys
RK_PEDIDO_CRIADO = "pedido.criado"
RK_PEDIDO_EXCLUIDO = "pedido.excluido"
RK_PEDIDO_ESTOQUE_OK = "pedido.estoque_ok"
RK_ESTOQUE_INDISPONIVEL = "estoque.indisponivel"
RK_PAGAMENTO_PENDENTE = "pagamento.pendente"  # cobranca criada, leva a checkout_url
RK_PAGAMENTO_APROVADO = "pagamento.aprovado"
RK_PAGAMENTO_RECUSADO = "pagamento.recusado"
RK_PEDIDO_ENVIADO = "pedido.enviado"
RK_INTERESSE_PROMOCAO = "interesse.promocao"

# acao carregada no interesse.promocao
ACAO_INSCREVER = "inscrever"
ACAO_CANCELAR = "cancelar"

# categorias dos produtos; o consumidor escolhe de quais quer receber promocao
CATEGORIAS = ("A", "B", "C")

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

#armazenamento dos dados
# banco SQLite do Estoque
ESTOQUE_DB = Path(os.environ.get("ESTOQUE_DB", RAIZ / "dados" / "estoque.db"))

# definicao das portas dos microservicos
PRINCIPAL_PORTA = int(os.environ.get("PRINCIPAL_PORTA", "8000"))
ESTOQUE_PORTA = int(os.environ.get("ESTOQUE_PORTA", "8001"))
PAGAMENTO_PORTA = int(os.environ.get("PAGAMENTO_PORTA", "8002"))
ESTOQUE_URL = os.environ.get("ESTOQUE_URL", f"http://localhost:{ESTOQUE_PORTA}")
# provedor externo onde o Pagamento cria as cobrancas
MOCK_PAGAMENTO_URL = os.environ.get("MOCK_PAGAMENTO_URL", "http://localhost:8003")
# para onde o provedor manda o resultado do pagamento (webhook)
PAGAMENTO_WEBHOOK_URL = os.environ.get(
    "PAGAMENTO_WEBHOOK_URL", f"http://localhost:{PAGAMENTO_PORTA}/webhook"
)
# segredo compartilhado com o Mock, ele assina o corpo do webhook com SHA256
# e o Pagamento so aceita o que bater.
WEBHOOK_SEGREDO = segredo("webhook_segredo")

# status do pedido
STATUS_CRIADO = "CRIADO"
STATUS_ESTOQUE_OK = "ESTOQUE_OK"
STATUS_ESTOQUE_INDISPONIVEL = "ESTOQUE_INDISPONIVEL"
STATUS_AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
STATUS_EXCLUIDO = "EXCLUIDO"
STATUS_PAGAMENTO_APROVADO = "PAGAMENTO_APROVADO"
STATUS_PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
STATUS_PEDIDO_ENVIADO = "PEDIDO_ENVIADO"

# depois destes o pedido nao muda mais
STATUS_FINAIS = frozenset({
    STATUS_ESTOQUE_INDISPONIVEL,
    STATUS_EXCLUIDO,
    STATUS_PAGAMENTO_RECUSADO,
    STATUS_PEDIDO_ENVIADO,
})
# o cliente so cancela enquanto o pedido nao foi pago
STATUS_CANCELAVEIS = frozenset({
    STATUS_CRIADO,
    STATUS_ESTOQUE_OK,
    STATUS_AGUARDANDO_PAGAMENTO,
})

# Promocoes
# Segundos entre uma promocao e a seguinte.
PROMOCAO_INTERVALO = int(os.environ.get("PROMOCAO_INTERVALO", "60"))

# api do resend
RESEND_API_KEY = segredo("resend_api_key")
RESEND_URL = os.environ.get("RESEND_URL", "https://api.resend.com")
# como nao temos dominio, devemos usar a conta do dono que criou a chave
EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE", "Loja UTFPR <onboarding@resend.dev>")

# Chaves
# As publicas formam um keyring unico, igual para todos os servicos
# Cada servico possui apenas a sua privada.
# Em Docker, CHAVE_PRIVADA aponta para o secret e CHAVES_PUBLICAS para o volume :ro.
DIR_CHAVES = RAIZ / "chaves"
CHAVES_PUBLICAS = Path(os.environ.get("CHAVES_PUBLICAS", DIR_CHAVES / "publicas"))
_PRIVADA_ENV = os.environ.get("CHAVE_PRIVADA")

def caminho_chave_privada(servico):
    return Path(_PRIVADA_ENV) if _PRIVADA_ENV else DIR_CHAVES / "privadas" / servico
