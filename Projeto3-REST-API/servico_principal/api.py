# API Gateway: a API REST consumida pelo frontend e o canal SSE.
#
# Publica : pedido.criado, pedido.excluido, interesse.promocao
# Consome : pedido.estoque_ok, estoque.indisponivel, pagamento.pendente,
#           pagamento.aprovado, pagamento.recusado, pedido.enviado (consumidor.py)
#


import asyncio
import json
import re
from contextlib import asynccontextmanager

import pika
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sse_starlette import EventSourceResponse

from comum import estoque_cliente, mensageria, publicador
from comum.config import (
    ACAO_CANCELAR,
    ACAO_INSCREVER,
    CATEGORIAS,
    RK_INTERESSE_PROMOCAO,
    RK_PEDIDO_CRIADO,
    RK_PEDIDO_EXCLUIDO,
)
from servico_principal import consumidor, pedidos
from servico_principal.sse import hub

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ciclo de vida do app: inicia o hub e o consumidor antes de aceitar pedidos, e encerra
@asynccontextmanager
async def lifespan(_app):
    hub.iniciar(asyncio.get_running_loop())
    mensageria.definir_servico("principal")
    # a fila tem que estar ligada antes de aceitar pedidos, senao a resposta do
    # Estoque ao primeiro pedido.criado poderia se perder
    await asyncio.to_thread(consumidor.iniciar)
    yield

# define o app FastAPI e habilita CORS para qualquer origem (frontend)
app = FastAPI(title="MS Principal / API Gateway", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# validacao de campos de entrada: normaliza e valida categorias e e-mail
def _normalizar_categorias(categorias):
    normalizadas = sorted({c.strip().upper() for c in categorias if c.strip()})
    invalidas = [c for c in normalizadas if c not in CATEGORIAS]
    if invalidas:
        raise ValueError(f"categorias invalidas {invalidas}; validas: {list(CATEGORIAS)}")
    return normalizadas


def _validar_email(email):
    email = email.strip().lower()
    if not _EMAIL.match(email):
        raise ValueError("e-mail invalido")
    return email


class ItemPedido(BaseModel):
    produto_id: str = Field(min_length=1)
    quantidade: int = Field(gt=0)


class NovoPedido(BaseModel):
    cliente: str = Field(min_length=1, max_length=60)
    itens: list[ItemPedido] = Field(min_length=1)

    @field_validator("cliente")
    @classmethod
    def _cliente(cls, valor):
        valor = valor.strip()
        if not valor:
            raise ValueError("cliente vazio")
        return valor


class Interesse(BaseModel):
    email: str
    categorias: list[str] = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _email(cls, valor):
        return _validar_email(valor)

    @field_validator("categorias")
    @classmethod
    def _categorias(cls, valor):
        valor = _normalizar_categorias(valor)
        if not valor:
            raise ValueError("informe ao menos uma categoria")
        return valor


# auxiliares
def _publicar(routing_key, evento):
    try:
        publicador.publicar(routing_key, evento)
    except pika.exceptions.AMQPError as erro:
        raise HTTPException(503, f"RabbitMQ indisponivel ({erro!r})") from None


def _catalogo(disponiveis=False):
    try:
        return estoque_cliente.produtos(disponiveis)
    except estoque_cliente.EstoqueIndisponivel as erro:
        raise HTTPException(503, str(erro)) from None


# endpoint de catalogo: lista produtos em estoque, consultados no MS Estoque via REST
@app.get("/produtos")
def listar_produtos(disponiveis: bool = True):
    """
    Produtos em estoque, consultados no MS Estoque via REST.
    """
    return _catalogo(disponiveis)


# pedidos
@app.post("/pedidos", status_code=201)
def criar_pedido(novo: NovoPedido):
    """Cria o pedido e publica pedido.criado.
    O MS Estoque reserva os produtos e publica pedido.estoque_ok ou estoque.indisponivel
    o MS Pagamento publica pedido.pendente, pagamento.aprovado ou pagamento.recusado

    """
    catalogo = {produto["id"]: produto for produto in _catalogo()}

    quantidades = {}
    for item in novo.itens:
        quantidades[item.produto_id] = quantidades.get(item.produto_id, 0) + item.quantidade

    itens = []
    for id_produto, quantidade in quantidades.items():
        produto = catalogo.get(id_produto)
        if produto is None:
            raise HTTPException(404, f"produto {id_produto} inexistente")
        if quantidade > produto["quantidade"]:
            raise HTTPException(
                409, f"{produto['nome']}: pedido {quantidade}, em estoque {produto['quantidade']}"
            )
        itens.append({
            "produto_id": id_produto,
            "nome": produto["nome"],
            "preco": produto["preco"],
            "quantidade": quantidade,
        })

    # o pedido entra na lista antes de publicar: a resposta do Estoque pode chegar
    # antes deste handler terminar
    pedido = pedidos.criar(novo.cliente, itens)
    try:
        _publicar(RK_PEDIDO_CRIADO, pedidos.evento_criado(pedido))
    except HTTPException:
        pedidos.descartar(pedido["pedido_id"])
        raise
    print(f"[principal] pedido {pedido['pedido_id']} de {pedido['cliente']}: "
          f"{len(itens)} item(ns), total {pedido['total']:.2f}")
    return pedido


@app.get("/pedidos")
def listar_pedidos(cliente: str = Query(min_length=1)):
    return pedidos.listar(cliente)


@app.delete("/pedidos/{pedido_id}")
def cancelar_pedido(pedido_id: str, cliente: str = Query(min_length=1)):
    """
    busca o pedido, se existir
    notifica o hub SSE, publica pedido.excluido e retorna o pedido cancelado.
    """
    atual = pedidos.buscar(pedido_id, cliente)
    if atual is None:
        raise HTTPException(404, "pedido nao encontrado")
    pedido = pedidos.excluir(pedido_id)
    if pedido is None:
        raise HTTPException(409, f"pedido em {atual['status']} nao pode mais ser cancelado")
    hub.notificar(pedido)
    _publicar(RK_PEDIDO_EXCLUIDO, {"pedido_id": pedido_id})
    print(f"[principal] pedido {pedido_id}: cancelado pelo cliente")
    return pedido


# promocoes
@app.post("/interesses", status_code=202)
def registrar_interesse(interesse: Interesse):
    """
    cria o pacote de interesse e publica interesse.promocao, que o MS Promocao envia por e-mail.
    """
    evento = {
        "email": interesse.email,
        "categorias": interesse.categorias,
        "acao": ACAO_INSCREVER,
    }
    _publicar(RK_INTERESSE_PROMOCAO, evento)
    return evento


@app.delete("/interesses/{email}", status_code=202)
def cancelar_interesse(email: str, categorias: list[str] | None = Query(None)):
    """
    Cancela as categorias informadas, sem categorias, cancela todas.
    """
    try:
        evento = {
            "email": _validar_email(email),
            "categorias": _normalizar_categorias(categorias or []),
            "acao": ACAO_CANCELAR,
        }
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from None
    _publicar(RK_INTERESSE_PROMOCAO, evento)
    return evento


# SSE
@app.get("/eventos")
async def eventos(cliente: str = Query(min_length=1)):
    """Canal SSE do cliente.

    Ao conectar, o cliente recebe a lista dos seus pedidos (evento "pedidos") e
    depois um evento "pedido" a cada mudanca de status. Notificacoes enviadas
    enquanto ele esta desconectado se perdem, mas a lista enviada na reconexao
    traz o estado atual. O ping a cada 15s mantem a conexao viva em proxies e
    revela quando o cliente ja foi embora.
    """
    # conecta antes de tirar a foto: um evento entre os dois chega repetido, nunca perdido
    fila = hub.conectar(cliente)

    async def gerar():
        try:
            yield {"event": "pedidos", "data": json.dumps(pedidos.listar(cliente))}
            while True:
                notificacao = await fila.get()
                yield {"event": "pedido", "data": json.dumps(notificacao)}
        finally:
            hub.desconectar(cliente, fila)

    return EventSourceResponse(gerar(), ping=15)
