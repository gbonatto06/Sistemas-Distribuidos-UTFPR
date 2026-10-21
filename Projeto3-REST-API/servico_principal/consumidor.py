# Consumidor de eventos do Principal: atualiza o status dos pedidos, avisa o
# dono pelo SSE e publica a exclusao quando o pedido nao vai adiante.

from comum import mensageria, publicador
from comum.config import (
    FILA_PRINCIPAL,
    RK_ESTOQUE_INDISPONIVEL,
    RK_PAGAMENTO_APROVADO,
    RK_PAGAMENTO_PENDENTE,
    RK_PAGAMENTO_RECUSADO,
    RK_PEDIDO_ENVIADO,
    RK_PEDIDO_ESTOQUE_OK,
    RK_PEDIDO_EXCLUIDO,
    STATUS_AGUARDANDO_PAGAMENTO,
    STATUS_ESTOQUE_INDISPONIVEL,
    STATUS_ESTOQUE_OK,
    STATUS_PAGAMENTO_APROVADO,
    STATUS_PAGAMENTO_RECUSADO,
    STATUS_PEDIDO_ENVIADO,
)
from servico_principal import pedidos
from servico_principal.sse import hub

# routing key -> novo status do pedido
TRANSICOES = {
    RK_PEDIDO_ESTOQUE_OK: STATUS_ESTOQUE_OK,
    RK_ESTOQUE_INDISPONIVEL: STATUS_ESTOQUE_INDISPONIVEL,
    RK_PAGAMENTO_PENDENTE: STATUS_AGUARDANDO_PAGAMENTO,
    RK_PAGAMENTO_APROVADO: STATUS_PAGAMENTO_APROVADO,
    RK_PAGAMENTO_RECUSADO: STATUS_PAGAMENTO_RECUSADO,
    RK_PEDIDO_ENVIADO: STATUS_PEDIDO_ENVIADO,
}

ROUTING_KEYS = list(TRANSICOES)

# depois destes a reserva precisa voltar ao estoque
DEVOLVEM_ESTOQUE = {RK_ESTOQUE_INDISPONIVEL, RK_PAGAMENTO_RECUSADO}


def _campos(routing_key, evento):
    """Campos do evento que o pedido guarda junto com o novo status."""
    if routing_key in (RK_ESTOQUE_INDISPONIVEL, RK_PAGAMENTO_RECUSADO):
        return {"motivo": evento.get("motivo", "")}
    if routing_key == RK_PAGAMENTO_PENDENTE:
        return {"checkout_url": evento.get("checkout_url")}
    if routing_key == RK_PEDIDO_ENVIADO:
        return {"nota_fiscal": evento.get("nota_fiscal")}
    return {}


def publicar_exclusao(pedido_id):
    publicador.publicar(RK_PEDIDO_EXCLUIDO, {"pedido_id": pedido_id})


def tratar(_canal, routing_key, evento):
    status = TRANSICOES.get(routing_key)
    if status is None:
        return
    pedido_id = evento["pedido_id"]
    pedido = pedidos.atualizar_status(pedido_id, status, **_campos(routing_key, evento))
    if pedido is None:
        print(f"[principal] {routing_key} ignorado: pedido {pedido_id} "
              "desconhecido ou ja finalizado")
        return

    print(f"[principal] pedido {pedido_id}: {status} "
          f"({hub.conexoes(pedido['cliente'])} conexao(oes) SSE de {pedido['cliente']})")
    hub.notificar(pedido)

    if routing_key in DEVOLVEM_ESTOQUE:
        publicar_exclusao(pedido_id)


def iniciar():
    """Sobe a thread que consome os eventos do Principal."""
    return mensageria.consumir_em_segundo_plano(FILA_PRINCIPAL, ROUTING_KEYS, tratar)
