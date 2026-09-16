# modulo de consumidor de eventos do Principal, que atualiza o status dos pedidos e publica exclusao quando necessario.

import threading

from comum import mensageria
from comum.config import (
    FILA_PRINCIPAL,
    RK_ESTOQUE_INDISPONIVEL,
    RK_PEDIDO_ESTOQUE_OK,
    rk_catalogo_para,
    RK_PAGAMENTO_APROVADO,
    RK_PAGAMENTO_RECUSADO,
    STATUS_ESTOQUE_INDISPONIVEL,
    STATUS_ESTOQUE_OK,
    STATUS_PAGAMENTO_APROVADO,
    STATUS_PAGAMENTO_RECUSADO,
    RK_PEDIDO_ENVIADO,
    STATUS_PEDIDO_ENVIADO,
)
from servico_principal import catalogo, pedidos


RK_CATALOGO = rk_catalogo_para("principal")

ROUTING_KEYS = [
    RK_PEDIDO_ESTOQUE_OK,
    RK_ESTOQUE_INDISPONIVEL,
    RK_CATALOGO,
    RK_PAGAMENTO_APROVADO,
    RK_PAGAMENTO_RECUSADO,
    RK_PEDIDO_ENVIADO,
]


def tratar(canal, routing_key, evento):
    if routing_key == RK_CATALOGO:
        catalogo.receber(evento)
        return

    pedido_id = evento["pedido_id"]
    if routing_key == RK_PEDIDO_ESTOQUE_OK:
        pedidos.atualizar_status(pedido_id, STATUS_ESTOQUE_OK)
        print(f"\n[evento] pedido {pedido_id}: estoque reservado, segue para pagamento")
    elif routing_key == RK_ESTOQUE_INDISPONIVEL:
        motivo = evento.get("motivo", "")
        pedidos.atualizar_status(pedido_id, STATUS_ESTOQUE_INDISPONIVEL, motivo)
        print(f"\n[evento] pedido {pedido_id}: estoque indisponivel ({motivo})")
        pedidos.publicar_exclusao(canal, pedido_id)
    elif routing_key == RK_PAGAMENTO_APROVADO:
        pedidos.atualizar_status(pedido_id, STATUS_PAGAMENTO_APROVADO)
        print(f"\n[evento] pedido {pedido_id}: pagamento aprovado")
    elif routing_key == RK_PAGAMENTO_RECUSADO:
        pedidos.atualizar_status(pedido_id, STATUS_PAGAMENTO_RECUSADO)
        print(f"\n[evento] pedido {pedido_id}: pagamento recusado")
        pedidos.publicar_exclusao(canal, pedido_id)
    elif routing_key == RK_PEDIDO_ENVIADO:
        pedidos.atualizar_status(pedido_id, STATUS_PEDIDO_ENVIADO)
        nota = evento.get("nota_fiscal", "sem nota")
        print(f"\n[evento] pedido {pedido_id}: enviado (nota {nota})")

def iniciar(espera=30):
    """aqui esta subindo a thread que consome os eventos do Principal e chama tratar() para cada um.

    """
    pronto = threading.Event()
    thread = threading.Thread(
        target=mensageria.consumir,
        args=(FILA_PRINCIPAL, ROUTING_KEYS, tratar),
        kwargs={"pronto": pronto},
        daemon=True,
    )
    thread.start()
    if not pronto.wait(timeout=espera):
        print(f"[aviso] a fila do Principal nao ficou pronta em {espera}s; "
              "as respostas do Estoque podem se perder.")
    return thread
