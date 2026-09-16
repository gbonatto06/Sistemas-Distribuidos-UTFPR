# Consome : pagamento.aprovado
# Publica : pedido.enviado

# Emite a nota do pedido e prepara o envio. O total sai dos precos que viajam no
# proprio evento desde o pedido.criado

import uuid
from datetime import datetime

from comum import mensageria
from comum.config import (
    FILA_ENTREGA,
    RK_PAGAMENTO_APROVADO,
    RK_PEDIDO_ENVIADO,
    STATUS_PEDIDO_ENVIADO,
)

ROUTING_KEYS = [RK_PAGAMENTO_APROVADO]

def enviar_pedido(canal, evento):
    """Emite a nota, prepara a entrega e anuncia o envio."""
    pedido_id = evento["pedido_id"]
    total = sum(item["preco"] * item["quantidade"] for item in evento["itens"])
    nota = f"NF{uuid.uuid4().hex[:8].upper()}"

    print(f"[entrega] pedido {pedido_id}: nota {nota} emitida, total {total:.2f}")
    print(f"[entrega] pedido {pedido_id}: enviado -> {RK_PEDIDO_ENVIADO}")
    mensageria.publicar(
        canal,
        RK_PEDIDO_ENVIADO,
        {
            **evento,
            "status": STATUS_PEDIDO_ENVIADO,
            "nota_fiscal": nota,
            "total": round(total, 2),
            "enviado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


TRATADORES = {
    RK_PAGAMENTO_APROVADO: enviar_pedido,
}
# verifica se a routing key do evento recebido tem um tratador definido, e chama ele com o canal e o evento.
def tratar(canal, routing_key, evento):
    tratador = TRATADORES.get(routing_key)
    if tratador:
        tratador(canal, evento)


def main():
    print("[entrega] aguardando eventos:", ", ".join(ROUTING_KEYS))
    print("[entrega] Ctrl+C para encerrar")
    try:
        # define o id do servico e a chave privada para assinar os eventos publicados
        mensageria.definir_servico("entrega")
        # consome a fila de eventos do servico, chamando tratar() para cada evento
        mensageria.consumir(FILA_ENTREGA, ROUTING_KEYS, tratar)
    except KeyboardInterrupt:
        print("\n[entrega] encerrado")


if __name__ == "__main__":
    main()
