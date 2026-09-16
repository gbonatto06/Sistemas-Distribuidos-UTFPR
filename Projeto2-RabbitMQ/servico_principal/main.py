# microservico principal
from comum import mensageria
from comum.config import (
    RK_PEDIDO_CRIADO,
    RK_PEDIDO_EXCLUIDO,
    STATUS_EXCLUIDO,
)
from servico_principal import catalogo, consumidor, pedidos
# a interface 
MENU = """
=========== E-COMMERCE ===========
1) Visualizar produtos
2) Realizar pedido
3) Excluir pedido
4) Consultar meus pedidos
0) Sair
=================================="""


# funoces auxiliares
def _perguntar(rotulo):
    return input(rotulo).strip()


def _consultar_catalogo(canal):
    # solicita o catalogo d produtos
    try:
        return catalogo.solicitar(canal)
    except catalogo.TempoEsgotado as erro:
        print(f"[aviso] {erro}; tente novamente em instantes.")
        return None


#funcao para mostrar produtos na tela, usada em varias acoes do menu
def _mostrar_produtos(produtos):
    if not produtos:
        print("Nenhum produto disponivel.")
        return
    print(f"\n{'ID':<5}{'PRODUTO':<28}{'PRECO':>10}{'ESTOQUE':>10}")
    for produto in produtos:
        # "esgotado" chama mais atencao que um 0 solto numa coluna de numeros
        estoque = "esgotado" if produto["quantidade"] == 0 else produto["quantidade"]
        print(
            f"{produto['id']:<5}{produto['nome']:<28}"
            f"{produto['preco']:>10.2f}{estoque:>10}"
        )

    
# acoes do user
def visualizar_produtos(canal, _cliente):
    catalogo_atual = _consultar_catalogo(canal)
    if catalogo_atual is not None:
        _mostrar_produtos(catalogo_atual)


def realizar_pedido(canal, cliente):
    catalogo_atual = _consultar_catalogo(canal)
    if not catalogo_atual:
        print("Sem catalogo para montar o pedido.")
        return
    produtos = {p["id"]: p for p in catalogo_atual}
    _mostrar_produtos(produtos.values())

    itens = {}  # id -> item pronto do pedido
    print("\nInforme os itens (ENTER no ID para finalizar).")
    while True:
        id_produto = _perguntar("ID do produto: ")
        if not id_produto:
            break

        # Reconsulta o Estoque a cada item escolhido: o saldo conferido e o de agora,
        # nao o da listagem acima. 
        atual = _consultar_catalogo(canal)
        if atual is None:
            print("  ! item nao adicionado: o Estoque nao respondeu")
            continue

        produto = {p["id"]: p for p in atual}.get(id_produto)
        if produto is None:
            print("Produto inexistente.")
            continue
        if produto["quantidade"] == 0:
            print(f"  ! {produto['nome']}: esgotado (saldo 0)")
            continue

        quantidade = _perguntar("Quantidade: ")
        if not quantidade.isdigit() or int(quantidade) <= 0:
            print("Quantidade invalida.")
            continue

        no_carrinho = itens[id_produto]["quantidade"] if id_produto in itens else 0
        total = no_carrinho + int(quantidade)
        if total > produto["quantidade"]:
            print(f"  ! {produto['nome']}: so ha {produto['quantidade']} em estoque")
            if no_carrinho:
                print(f"    (voce ja tem {no_carrinho} no carrinho)")
            continue

        itens[id_produto] = {
            "produto_id": id_produto,
            "nome": produto["nome"],
            "preco": produto["preco"],
            "quantidade": total,
        }
        print(f"  + {produto['nome']} x{total}")

    if not itens:
        print("Pedido cancelado: nenhum item informado.")
        return

    pedido = pedidos.criar(cliente, list(itens.values()))
    mensageria.publicar(canal, RK_PEDIDO_CRIADO, pedido)
    total = sum(i["preco"] * i["quantidade"] for i in pedido["itens"])
    print(f"\nPedido {pedido['pedido_id']} criado (total {total:.2f}).")
    print(f"Evento publicado com routing key '{RK_PEDIDO_CRIADO}'.")


def excluir_pedido(canal, cliente):
    consultar_pedidos(canal, cliente)
    pedido_id = _perguntar("\nID do pedido a excluir: ")
    pedido = pedidos.buscar(pedido_id, cliente)
    if pedido is None:
        print("Pedido nao encontrado.")
        return
    if pedido["status"] == STATUS_EXCLUIDO:
        print("Pedido ja esta excluido.")
        return

    pedidos.excluir(pedido_id)
    pedidos.publicar_exclusao(canal, pedido_id)
    print(f"Pedido {pedido_id} excluido.")
    print(f"Evento publicado com routing key '{RK_PEDIDO_EXCLUIDO}'.")


def consultar_pedidos(_canal, cliente):
    meus_pedidos = pedidos.listar(cliente)
    if not meus_pedidos:
        print("Voce ainda nao tem pedidos.")
        return
    print(f"\n{'PEDIDO':<10}{'DATA':<21}{'STATUS':<24}ITENS")
    for pedido in meus_pedidos:
        itens = ", ".join(f"{i['nome']} x{i['quantidade']}" for i in pedido["itens"])
        print(
            f"{pedido['pedido_id']:<10}{pedido['criado_em']:<21}"
            f"{pedido['status']:<24}{itens}"
        )
        if pedido["motivo"]:
            print(f"{'':<10}motivo: {pedido['motivo']}")


ACOES = {
    "1": visualizar_produtos,
    "2": realizar_pedido,
    "3": excluir_pedido,
    "4": consultar_pedidos,
}


# ---------------------------------------------------------------------- main
def main():
    mensageria.definir_servico("principal")
    # heartbeat=0: o menu passa a maior parte do tempo parado no input(), sem
    # responder heartbeat nenhum, e o broker fecharia a conexao por ociosidade.
    conexao, canal = mensageria.conectar(heartbeat=0)
    consumidor.iniciar()

    cliente = _perguntar("Identifique-se (nome do cliente): ") or "anonimo"
    print(f"Ola, {cliente}!")

    try:
        while True:
            print(MENU)
            opcao = _perguntar("Opcao: ")
            if opcao == "0":
                break
            acao = ACOES.get(opcao)
            if acao is None:
                print("Opcao invalida.")
                continue
            acao(canal, cliente)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        if conexao.is_open:
            conexao.close()
        print("\nAte logo!")


if __name__ == "__main__":
    main()
