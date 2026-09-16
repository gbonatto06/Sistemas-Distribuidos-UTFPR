# microservico de pagamento
import random

from comum import mensageria
from comum.config import (
    FILA_PAGAMENTO,
    RK_PAGAMENTO_APROVADO,
    RK_PAGAMENTO_RECUSADO,
    RK_PEDIDO_ESTOQUE_OK,
)

ROUTING_KEYS = [RK_PEDIDO_ESTOQUE_OK]


def _pedido_estoque_ok(canal, evento):
    # simulacao aleatoria de pagamento aprovado ou recusado
    pedido_id = evento["pedido_id"]
    if random.choice([True, False]):
        print(f"[pagamento] pedido {pedido_id}: aprovado -> {RK_PAGAMENTO_APROVADO}")
        mensageria.publicar(canal, RK_PAGAMENTO_APROVADO, evento)
    else:
        print(f"[pagamento] pedido {pedido_id}: recusado -> {RK_PAGAMENTO_RECUSADO}")
        mensageria.publicar(canal, RK_PAGAMENTO_RECUSADO, evento)


TRATADORES = {
    RK_PEDIDO_ESTOQUE_OK: _pedido_estoque_ok,
}


def tratar(canal, routing_key, evento):
    tratador = TRATADORES.get(routing_key)
    if tratador:
        tratador(canal, evento)


def main():
    print("[pagamento] aguardando eventos:", ", ".join(ROUTING_KEYS))
    print("[pagamento] Ctrl+C para encerrar")
    try:
        mensageria.definir_servico("pagamento")
        mensageria.consumir(FILA_PAGAMENTO, ROUTING_KEYS, tratar)
    except KeyboardInterrupt:
        print("\n[pagamento] encerrado")


if __name__ == "__main__":
    main()
