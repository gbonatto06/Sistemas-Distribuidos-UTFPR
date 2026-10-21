# microservico de pagamento
# Consome : pedido.estoque_ok, pedido.excluido
# Publica : pagamento.pendente, pagamento.aprovado, pagamento.recusado
# HTTP    : POST /webhook (resultado vindo do provedor de pagamento)
#
# Ao receber pedido.estoque_ok, cria a cobranca no provedor (REST) informando a
# URL do webhook, e publica pagamento.pendente com a checkout_url para o Gateway
# repassar ao cliente. O resultado chega depois, quando o cliente clica no Mock.

import uvicorn

from comum import mensageria
from comum.config import (
    FILA_PAGAMENTO,
    PAGAMENTO_PORTA,
    PAGAMENTO_WEBHOOK_URL,
    RK_PAGAMENTO_PENDENTE,
    RK_PAGAMENTO_RECUSADO,
    RK_PEDIDO_ESTOQUE_OK,
    RK_PEDIDO_EXCLUIDO,
    WEBHOOK_SEGREDO,
)
from servico_pagamento import api, cobrancas, mock_cliente

ROUTING_KEYS = [RK_PEDIDO_ESTOQUE_OK, RK_PEDIDO_EXCLUIDO]


def _descricao(evento):
    return ", ".join(f"{item['nome']} x{item['quantidade']}" for item in evento["itens"])


def _pedido_estoque_ok(canal, evento):
    # pega o id do pedido
    # verifica se ja existe cobranca ou se foi cancelado
    # se nao, cria a cobranca no provedor e publica pagamento.pendente com checkout_url

    pedido_id = evento["pedido_id"]
    if cobrancas.cancelado(pedido_id):
        print(f"[pagamento] pedido {pedido_id}: ja foi cancelado, nao cobro")
        return
    if cobrancas.buscar(pedido_id):
        print(f"[pagamento] pedido {pedido_id}: cobranca ja existe (evento repetido)")
        return

    total = round(sum(item["preco"] * item["quantidade"] for item in evento["itens"]), 2)
    try:
        resposta = mock_cliente.criar_cobranca(pedido_id, total, _descricao(evento))
    except mock_cliente.ProvedorIndisponivel as erro:
        # sem provedor nao ha como pagar: recusa, e o Gateway devolve a reserva
        print(f"[pagamento] pedido {pedido_id}: {erro} -> {RK_PAGAMENTO_RECUSADO}")
        mensageria.publicar(canal, RK_PAGAMENTO_RECUSADO, {**evento, "motivo": str(erro)})
        return

    cobranca = cobrancas.registrar(evento, resposta["cobranca_id"], resposta["checkout_url"])
    print(f"[pagamento] pedido {pedido_id}: cobranca {cobranca['cobranca_id']} "
          f"de {total:.2f} -> {RK_PAGAMENTO_PENDENTE}")
    mensageria.publicar(canal, RK_PAGAMENTO_PENDENTE, {
        "pedido_id": pedido_id,
        "cliente": evento.get("cliente"),
        "cobranca_id": cobranca["cobranca_id"],
        "checkout_url": cobranca["checkout_url"],
        "total": total,
    })


def _pedido_excluido(_canal, evento):
    # pega o id do pedido, verifica se existe cobranca, e se existir cancela no provedor
    pedido_id = evento["pedido_id"]
    cobranca = cobrancas.cancelar(pedido_id)
    if cobranca:
        print(f"[pagamento] pedido {pedido_id}: cobranca {cobranca['cobranca_id']} cancelada")
        mock_cliente.cancelar_cobranca(cobranca["cobranca_id"])


TRATADORES = {
    RK_PEDIDO_ESTOQUE_OK: _pedido_estoque_ok,
    RK_PEDIDO_EXCLUIDO: _pedido_excluido,
}


def tratar(canal, routing_key, evento):
    tratador = TRATADORES.get(routing_key)
    if tratador:
        tratador(canal, evento)


def main():
    # inicializa o microservico de pagamento: sobe o HTTP e consome eventos do RabbitMQ
    print("[pagamento] aguardando eventos:", ", ".join(ROUTING_KEYS))
    print(f"[pagamento] webhook: {PAGAMENTO_WEBHOOK_URL}")
    if not WEBHOOK_SEGREDO:
        print("[aviso] WEBHOOK_SEGREDO vazio: todo webhook sera recusado")
    mensageria.definir_servico("pagamento")
    mensageria.consumir_em_segundo_plano(FILA_PAGAMENTO, ROUTING_KEYS, tratar)

    print(f"[pagamento] HTTP em :{PAGAMENTO_PORTA}  (Ctrl+C para encerrar)")
    uvicorn.run(api.app, host="0.0.0.0", port=PAGAMENTO_PORTA)
    print("[pagamento] encerrado")


if __name__ == "__main__":
    main()
