import asyncio
import threading
from collections import defaultdict

from comum.config import (
    STATUS_AGUARDANDO_PAGAMENTO,
    STATUS_CRIADO,
    STATUS_ESTOQUE_INDISPONIVEL,
    STATUS_ESTOQUE_OK,
    STATUS_EXCLUIDO,
    STATUS_PAGAMENTO_APROVADO,
    STATUS_PAGAMENTO_RECUSADO,
    STATUS_PEDIDO_ENVIADO,
)

# texto pronto para o frontend mostrar na notificacao
MENSAGENS = {
    STATUS_CRIADO: "Pedido criado, aguardando o estoque",
    STATUS_ESTOQUE_OK: "Estoque confirmado",
    STATUS_ESTOQUE_INDISPONIVEL: "Estoque indisponivel",
    STATUS_AGUARDANDO_PAGAMENTO: "Aguardando pagamento",
    STATUS_PAGAMENTO_APROVADO: "Pagamento aprovado",
    STATUS_PAGAMENTO_RECUSADO: "Pagamento recusado",
    STATUS_PEDIDO_ENVIADO: "Pedido enviado",
    STATUS_EXCLUIDO: "Pedido cancelado",
}


# Conexoes SSE abertas, agrupadas por cliente.
#
# Cada aba conectada em GET /eventos ganha uma asyncio.Queue que vive no event
# loop do servidor. Os eventos chegam por outra thread (o consumidor do RabbitMQ
# ou um handler HTTP), e asyncio.
class Hub:
    def __init__(self):
        self._lock = threading.Lock()
        self._filas = defaultdict(set)  # cliente -> {asyncio.Queue}
        self._loop = None

    def iniciar(self, loop):
        self._loop = loop

    def conectar(self, cliente):
        """Chamado dentro do event loop, ao abrir o GET /eventos."""
        fila = asyncio.Queue()
        with self._lock:
            self._filas[cliente].add(fila)
        return fila

    def desconectar(self, cliente, fila):
        with self._lock:
            filas = self._filas.get(cliente)
            if filas is not None:
                filas.discard(fila)
                if not filas:
                    del self._filas[cliente]

    def conexoes(self, cliente):
        with self._lock:
            return len(self._filas.get(cliente, ()))

    def notificar(self, pedido):
        """envia o pedido atualizado a todas as abas do dono."""
        if self._loop is None:
            return
        notificacao = {
            "pedido": pedido,
            "mensagem": MENSAGENS.get(pedido["status"], pedido["status"]),
        }
        with self._lock:
            filas = list(self._filas.get(pedido["cliente"], ()))
        for fila in filas:
            self._loop.call_soon_threadsafe(fila.put_nowait, notificacao)


hub = Hub()
