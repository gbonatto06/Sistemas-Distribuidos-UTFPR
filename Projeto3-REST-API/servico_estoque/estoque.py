# Estoque persistido em SQLite.

import re

from comum import banco
from comum.config import ESTOQUE_DB, PRODUTOS

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    id         TEXT PRIMARY KEY,
    nome       TEXT NOT NULL,
    preco      REAL NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade >= 0),
    categoria  TEXT NOT NULL  -- o Promocoes casa com as categorias de interesse
);
CREATE TABLE IF NOT EXISTS reservas (
    pedido_id  TEXT NOT NULL,
    produto_id TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    PRIMARY KEY (pedido_id, produto_id)
);
"""


def _transacao():
    return banco.transacao(ESTOQUE_DB)


def _leitura():
    return banco.leitura(ESTOQUE_DB)


def _ler_produtos_env():
    produtos = []
    for linha in re.split(r"[;\r\n]+", PRODUTOS):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        try:
            id_produto, nome, preco, quantidade, categoria = [
                campo.strip() for campo in linha.split("|")
            ]
            produtos.append((id_produto, nome, float(preco), int(quantidade), categoria))
        except ValueError:
            raise ValueError(
                f"linha {linha!r} (esperado id|nome|preco|quantidade|categoria)"
            ) from None
    return produtos


# produtos
def iniciar():
    """Cria as tabelas e, so com o banco vazio, semeia a partir da env PRODUTOS.

    Retorna (total de produtos, se semeou agora).
    """
    banco.criar_esquema(ESTOQUE_DB, _ESQUEMA)
    with _transacao() as conexao:
        total =conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        if total:
            return total, False
        produtos = _ler_produtos_env()
        conexao.executemany(
            "INSERT INTO produtos (id, nome, preco, quantidade, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            produtos,
        )
        return len(produtos), True


def catalogo(disponiveis=False):
    # devolve o catalogo de produtos; disponiveis=True esconde os esgotados
    filtro = "WHERE quantidade > 0" if disponiveis else ""
    with _leitura() as conexao:
        linhas = conexao.execute(
            f"SELECT id, nome, preco, quantidade, categoria FROM produtos {filtro} "
            "ORDER BY CAST(id AS INTEGER), id"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def produto(id_produto):
    with _leitura() as conexao:
        linha = conexao.execute(
            "SELECT id, nome, preco, quantidade, categoria FROM produtos WHERE id = ?",
            (id_produto,),
        ).fetchone()
    return dict(linha) if linha else None


# operacoes
def _somar_itens(itens):
    """Junta itens repetidos do mesmo produto: produto_id -> quantidade."""
    total = {}
    for item in itens:
        total[item["produto_id"]] = total.get(item["produto_id"], 0) + item["quantidade"]
    return total


def verificar(pedidos, produtos):
    """Retorna o motivo da indisponibilidade, ou None se tudo esta disponivel."""
    for id_produto, quantidade in pedidos.items():
        produto = produtos.get(id_produto)
        if produto is None:
            return f"produto {id_produto} inexistente"
        if produto["quantidade"] < quantidade:
            return (
                f"produto {produto['nome']}: pedido {quantidade}, "
                f"disponivel {produto['quantidade']}"
            )
    return None


def reservar(pedido_id, itens):
    """
    em caso de reserva, devolve (True, None) e baixa o estoque e cria as reservas.
    em caso de indisponibilidade, devolve (False, motivo)

    """
    pedidos = _somar_itens(itens)
    with _transacao() as conexao:
        ja_reservado = conexao.execute(
            "SELECT 1 FROM reservas WHERE pedido_id = ? LIMIT 1", (pedido_id,)
        ).fetchone()
        if ja_reservado:
            return True, None  # evento repetido: nao reserva duas vezes

        marcadores = ",".join("?" * len(pedidos))
        produtos = {
            linha["id"]: dict(linha)
            for linha in conexao.execute(
                f"SELECT id, nome, quantidade FROM produtos WHERE id IN ({marcadores})",
                list(pedidos),
            )
        }
        motivo = verificar(pedidos, produtos)
        if motivo:
            return False, motivo

        for id_produto, quantidade in pedidos.items():
            conexao.execute(
                "UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?",
                (quantidade, id_produto),
            )
            conexao.execute(
                "INSERT INTO reservas (pedido_id, produto_id, quantidade) VALUES (?, ?, ?)",
                (pedido_id, id_produto, quantidade),
            )
        return True, None


def devolver(pedido_id):
    # Devolve ao estoque os itens reservados para o pedido.
    # Retorna a lista de itens devolvidos.
    with _transacao() as conexao:
        itens = [
            dict(linha)
            for linha in conexao.execute(
                "SELECT produto_id, quantidade FROM reservas WHERE pedido_id = ?",
                (pedido_id,),
            )
        ]
        for item in itens:
            conexao.execute(
                "UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?",
                (item["quantidade"], item["produto_id"]),
            )
        conexao.execute("DELETE FROM reservas WHERE pedido_id = ?", (pedido_id,))
        return itens
