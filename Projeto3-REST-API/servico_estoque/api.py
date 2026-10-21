# API REST do Estoque, consultada pelo Gateway

from fastapi import FastAPI, HTTPException

from servico_estoque import estoque

app = FastAPI(title="MS Estoque")


@app.get("/produtos")
def listar_produtos(disponiveis: bool = False):
    """retorna os produtos em estoque, com opcao de esconder os esgotados"""
    return estoque.catalogo(disponiveis)


@app.get("/produtos/{id_produto}")
def buscar_produto(id_produto: str):
    # busca o produto no estoque
    # se nao existir, devolve 404
    produto = estoque.produto(id_produto)
    if produto is None:
        raise HTTPException(404, f"produto {id_produto} inexistente")
    return produto
