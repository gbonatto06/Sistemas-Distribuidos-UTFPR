# microservico de estoque
# Consome : pedido.criado, pedido.excluido
# Publica : pedido.estoque_ok, estoque.indisponivel
# HTTP    : GET /produtos (o Gateway e o Promocoes consultam o catalogo por aqui)

import uvicorn

from comum import mensageria
from comum.config import (
    ESTOQUE_PORTA,
    FILA_ESTOQUE,
    RK_ESTOQUE_INDISPONIVEL,
    RK_PEDIDO_CRIADO,
    RK_PEDIDO_ESTOQUE_OK,
    RK_PEDIDO_EXCLUIDO,
)
from servico_estoque import api, estoque

ROUTING_KEYS = [RK_PEDIDO_CRIADO, RK_PEDIDO_EXCLUIDO]


def _pedido_criado(canal, evento):
    # reserva o estoque para o pedido, e publica pedido.estoque_ok ou estoque.indisponivel
    pedido_id = evento["pedido_id"]
    ok, motivo = estoque.reservar(pedido_id, evento["itens"])

    if ok:
        print(f"[estoque] pedido {pedido_id}: reserva efetuada -> {RK_PEDIDO_ESTOQUE_OK}")
        mensageria.publicar(canal, RK_PEDIDO_ESTOQUE_OK, evento)
    else:
        print(f"[estoque] pedido {pedido_id}: indisponivel ({motivo})")
        mensageria.publicar(
            canal,
            RK_ESTOQUE_INDISPONIVEL,
            {**evento, "motivo": motivo},
        )


def _pedido_excluido(canal, evento):
    # devolve ao estoque os itens reservados para o pedido
    pedido_id = evento["pedido_id"]
    itens = estoque.devolver(pedido_id)
    if itens:
        print(f"[estoque] pedido {pedido_id}: {len(itens)} item(ns) devolvido(s) ao estoque")
    else:
        print(f"[estoque] pedido {pedido_id}: nenhuma reserva a devolver")


TRATADORES = {
    RK_PEDIDO_CRIADO: _pedido_criado,
    RK_PEDIDO_EXCLUIDO: _pedido_excluido,
}


def tratar(canal, routing_key, evento):
    tratador = TRATADORES.get(routing_key)
    if tratador:
        tratador(canal, evento)


def main():
    # inicia o microservico de estoque: sobe o HTTP e consome eventos do RabbitMQ
    
    try:
        total, semeado = estoque.iniciar()
    except ValueError as erro:
        print(f"[estoque] env PRODUTOS invalida: {erro}")
        return
    origem = "semeados da env PRODUTOS" if semeado else "lidos do banco"
    print(f"[estoque] {total} produto(s) {origem} ({estoque.ESTOQUE_DB})")
    print("[estoque] aguardando eventos:", ", ".join(ROUTING_KEYS))

    mensageria.definir_servico("estoque")
    mensageria.consumir_em_segundo_plano(FILA_ESTOQUE, ROUTING_KEYS, tratar)

    print(f"[estoque] HTTP em :{ESTOQUE_PORTA}  (Ctrl+C para encerrar)")
    uvicorn.run(api.app, host="0.0.0.0", port=ESTOQUE_PORTA)
    print("[estoque] encerrado")


if __name__ == "__main__":
    main()
