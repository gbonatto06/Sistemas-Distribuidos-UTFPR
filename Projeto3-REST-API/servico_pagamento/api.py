# Endpoint que recebe o webhook do provedor de pagamento.
#
# O corpo vem assinado com HMAC-SHA256 usando o segredo


import hashlib
import hmac
from typing import Literal

import pika
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ValidationError

from comum import publicador
from comum.config import RK_PAGAMENTO_APROVADO, RK_PAGAMENTO_RECUSADO, WEBHOOK_SEGREDO
from servico_pagamento import cobrancas

app = FastAPI(title="MS Pagamento")


class Webhook(BaseModel):
    cobranca_id: str
    pedido_id: str
    status: Literal["APROVADO", "RECUSADO"]


def _assinatura_valida(corpo, assinatura):
    # compara a assinatura recebida com a esperada, usando o segredo do webhook
    # sem segredo nao ha como conferir, entao recusa
    if not WEBHOOK_SEGREDO:
        return False
    esperada = hmac.new(WEBHOOK_SEGREDO.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, assinatura or "")


def _processar(dados):
    """
    processa o webhook do provedor, decide a cobranca
    se a cobranca nao existe, devolve 404
    se a cobranca ja foi decidida, devolve 409
    se a cobranca foi cancelada, devolve 409
    se a cobranca foi decidida com sucesso, publica pagamento.aprovado ou pagamento.rec
    """
    cobranca, resultado = cobrancas.decidir(dados.cobranca_id, dados.pedido_id, dados.status)
    if resultado == cobrancas.INEXISTENTE:
        raise HTTPException(404, "cobranca desconhecida")
    if resultado == cobrancas.CANCELADA:
        print(f"[pagamento] webhook de {dados.pedido_id} recusado: pedido cancelado")
        raise HTTPException(409, "pedido cancelado pelo cliente")
    if resultado == cobrancas.JA_DECIDIDA:
        raise HTTPException(409, f"cobranca ja esta {cobranca['status']}")
    if resultado == cobrancas.REPETIDA:
        return {"ok": True, "repetido": True}

    pedido_id = dados.pedido_id
    evento = {**cobranca["evento"], "cobranca_id": dados.cobranca_id}
    if dados.status == cobrancas.APROVADO:
        routing_key = RK_PAGAMENTO_APROVADO
        print(f"[pagamento] pedido {pedido_id}: aprovado -> {routing_key}")
    else:
        routing_key = RK_PAGAMENTO_RECUSADO
        evento["motivo"] = "recusado pelo provedor de pagamento"
        print(f"[pagamento] pedido {pedido_id}: recusado -> {routing_key}")

    try:
        publicador.publicar(routing_key, evento)
    except pika.exceptions.AMQPError as erro:
        raise HTTPException(503, f"RabbitMQ indisponivel ({erro!r})") from None
    return {"ok": True}


@app.post("/webhook")
async def webhook(request: Request, x_assinatura: str | None = Header(None)):
    corpo = await request.body()
    if not _assinatura_valida(corpo, x_assinatura):
        print("[seguranca] webhook com assinatura invalida: descartado")
        raise HTTPException(401, "assinatura invalida")
    try:
        dados = Webhook.model_validate_json(corpo)
    except ValidationError as erro:
        raise HTTPException(422, erro.errors(include_url=False)) from None
    # publicar e bloqueante (pika): sai do event loop
    return await run_in_threadpool(_processar, dados)
