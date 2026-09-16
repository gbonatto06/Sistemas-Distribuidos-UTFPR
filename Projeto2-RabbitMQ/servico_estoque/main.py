# microservico de estoque

from comum import mensageria
from comum.config import (
    FILA_ESTOQUE,
    RK_ESTOQUE_INDISPONIVEL,
    RK_PEDIDO_CRIADO,
    RK_PEDIDO_ESTOQUE_OK,
    RK_PEDIDO_EXCLUIDO,
    RK_PRODUTOS_CONSULTA,
    SOLICITANTES_CATALOGO,
    rk_catalogo_para,
    rk_consulta_catalogo,
)
from servico_estoque import estoque

ROUTING_KEYS = [
    RK_PEDIDO_CRIADO,
    RK_PEDIDO_EXCLUIDO,
    # uma lista de routing keys para os servicos que solicitam o catalogo
    *[rk_consulta_catalogo(servico) for servico in SOLICITANTES_CATALOGO],
]


def _pedido_criado(canal, evento):
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
    pedido_id = evento["pedido_id"]
    itens = estoque.devolver(pedido_id)
    if itens:
        print(f"[estoque] pedido {pedido_id}: {len(itens)} item(ns) devolvido(s) ao estoque")
    else:
        print(f"[estoque] pedido {pedido_id}: nenhuma reserva a devolver")


def _produtos_consulta(canal, evento, quem):
    # pega o catalogo de produtos do estoque e publica para o solicitante
    produtos = estoque.catalogo()
    print(f"[estoque] catalogo para {quem}: {len(produtos)} produto(s)")
    mensageria.publicar(
        canal,
        rk_catalogo_para(quem),
        {"correlacao": evento.get("correlacao"), "produtos": produtos},
    )


TRATADORES = {
    RK_PEDIDO_CRIADO: _pedido_criado,
    RK_PEDIDO_EXCLUIDO: _pedido_excluido,
}


def tratar(canal, routing_key, evento):
    # a consulta do catalogo e a unica chave com sufixo variavel: pois
    # cada solicitante tem a sua propria routing key para receber a resposta.
    if routing_key.startswith(f"{RK_PRODUTOS_CONSULTA}."):
        _produtos_consulta(canal, evento, routing_key.rsplit(".", 1)[-1])
        return
    # dai para as demais chaves, que sao fixas, basta olhar na tabela de tratadores
    tratador = TRATADORES.get(routing_key)
    if tratador:
        tratador(canal, evento)


def main():
    try:
        total = estoque.iniciar()
    except ValueError as erro:
        print(f"[estoque] env PRODUTOS invalida: {erro}")
        return
    print(f"[estoque] {total} produto(s) carregados da env PRODUTOS")
    print("[estoque] aguardando eventos:", ", ".join(ROUTING_KEYS))
    print("[estoque] Ctrl+C para encerrar")
    try:
        mensageria.definir_servico("estoque")
        mensageria.consumir(FILA_ESTOQUE, ROUTING_KEYS, tratar)
    except KeyboardInterrupt:
        print("\n[estoque] encerrado")


if __name__ == "__main__":
    main()
