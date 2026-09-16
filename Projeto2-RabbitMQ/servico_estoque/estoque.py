import re
from comum.config import PRODUTOS

_produtos = {}  # id -> {"id","nome","preco","quantidade"}
_reservas = {}  # pedido_id -> itens                         


# produtos
def iniciar():
    #Semeia o estoque a partir da env PRODUTOS e devolve quantos produtos entraram.
    _produtos.clear()
    _reservas.clear()
    for linha in re.split(r"[;\r\n]+", PRODUTOS):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        try:
            id_produto, nome, preco, quantidade, categoria = [
                campo.strip() for campo in linha.split("|")
            ]
            _produtos[id_produto] = {
                "id": id_produto,
                "nome": nome,
                "preco": float(preco),
                "quantidade": int(quantidade),
                "categoria": categoria, # o Promocoes usa para montar a routing key promocao.categoria.X
            }
        except ValueError:
            raise ValueError(
                f"linha {linha!r} (esperado id|nome|preco|quantidade|categoria)"
            ) from None
    return len(_produtos)


def catalogo():
    # devolve o catalogo de produtos
    return [dict(produto) for produto in _produtos.values()]


# operacoes
def verificar(itens, produtos):
    """Retorna o motivo da indisponibilidade, ou None se tudo esta disponivel."""
    for item in itens:
        produto = produtos.get(item["produto_id"])
        if produto is None:
            return f"produto {item['produto_id']} inexistente"
        if produto["quantidade"] < item["quantidade"]:
            return (
                f"produto {produto['nome']}: pedido {item['quantidade']}, "
                f"disponivel {produto['quantidade']}"
            )
    return None


def reservar(pedido_id, itens):
    """Da baixa no estoque e registra a reserva.

    Retorna (True, None) em caso de sucesso ou (False, motivo) se algum
    produto nao esta disponivel.
    """
    if pedido_id in _reservas:
        return True, None  # evento repetido: nao reserva duas vezes

    motivo = verificar(itens, _produtos)
    if motivo:
        return False, motivo

    for item in itens:
        _produtos[item["produto_id"]]["quantidade"] -= item["quantidade"]
    _reservas[pedido_id] = itens
    return True, None


def devolver(pedido_id):
    # Devolve ao estoque os itens reservados para o pedido.
    # Retorna a lista de itens devolvidos.
    
    itens = _reservas.pop(pedido_id, None)
    if not itens:
        return []

    for item in itens:
        if item["produto_id"] in _produtos:
            _produtos[item["produto_id"]]["quantidade"] += item["quantidade"]
    return itens
