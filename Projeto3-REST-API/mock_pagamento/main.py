# Mock de um provedor de pagamentos 

import hashlib
import hmac
import html
import json
import os
import threading
import uuid

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

PORTA = int(os.environ.get("MOCK_PORTA", "8003"))
# endereco que o NAVEGADOR usa para abrir o checkout
URL_PUBLICA = os.environ.get("URL_PUBLICA", f"http://localhost:{PORTA}").rstrip("/")
# le o segredo do arquivo do secret, em /run/secrets/webhook_segredo
def _ler_segredo():
    try:
        with open("/run/secrets/webhook_segredo", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


# segredo compartilhado com o MS Pagamento para assinar o webhook (HMAC-SHA256)
WEBHOOK_SEGREDO = _ler_segredo()

PENDENTE = "PENDENTE"
CANCELADA = "CANCELADA"
DECISOES = {"aprovar": "APROVADO", "recusar": "RECUSADO"}

app = FastAPI(title="Mock de Pagamento (provedor externo)")

_lock = threading.Lock()
_cobrancas = {}  # cobranca_id -> cobranca


class NovaCobranca(BaseModel):
    pedido_id: str = Field(min_length=1)
    valor: float = Field(gt=0)
    webhook_url: str = Field(min_length=1)
    descricao: str = ""


@app.post("/cobrancas", status_code=201)
def criar_cobranca(nova: NovaCobranca):
    # cria o id da cobranca, guarda em memoria e retorna o checkout_url
    cobranca_id = uuid.uuid4().hex[:12]
    cobranca = {
        "cobranca_id": cobranca_id,
        "pedido_id": nova.pedido_id,
        "valor": round(nova.valor, 2),
        "descricao": nova.descricao,
        "webhook_url": nova.webhook_url,
        "status": PENDENTE,
        "checkout_url": f"{URL_PUBLICA}/checkout/{cobranca_id}",
        "erro": "",
    }
    with _lock:
        _cobrancas[cobranca_id] = cobranca
    print(f"[mock] cobranca {cobranca_id}: pedido {nova.pedido_id}, R$ {nova.valor:.2f}")
    return {"cobranca_id": cobranca_id, "checkout_url": cobranca["checkout_url"]}


@app.get("/cobrancas/{cobranca_id}")
def buscar_cobranca(cobranca_id: str):
    # busca a cobranca em memoria e retorna o status e checkout_url
    with _lock:
        cobranca = _cobrancas.get(cobranca_id)
        if cobranca is None:
            raise HTTPException(404, "cobranca inexistente")
        return {k: v for k, v in cobranca.items() if k != "webhook_url"}


@app.post("/cobrancas/{cobranca_id}/cancelamento")
def cancelar_cobranca(cobranca_id: str):
    # cancela a cobranca em memoria, se ainda estiver pendente. Retorna o status atual.
    with _lock:
        cobranca = _cobrancas.get(cobranca_id)
        if cobranca is None:
            raise HTTPException(404, "cobranca inexistente")
        if cobranca["status"] == PENDENTE:
            cobranca["status"] = CANCELADA
            print(f"[mock] cobranca {cobranca_id}: cancelada pelo lojista")
        return {"status": cobranca["status"]}


def _enviar_webhook(cobranca, status):
    """
    post no webhook do lojista. Retorna a mensagem de erro, ou "" se deu certo.
    """
    corpo = json.dumps({
        "cobranca_id": cobranca["cobranca_id"],
        "pedido_id": cobranca["pedido_id"],
        "status": status,
    }).encode()
    cabecalhos = {"content-type": "application/json"}
    if WEBHOOK_SEGREDO:
        cabecalhos["x-assinatura"] = hmac.new(
            WEBHOOK_SEGREDO.encode(), corpo, hashlib.sha256
        ).hexdigest()
    try:
        resposta = httpx.post(cobranca["webhook_url"], content=corpo, headers=cabecalhos, timeout=5)
    except httpx.HTTPError as erro:
        return f"o lojista nao respondeu ({erro.__class__.__name__})"
    if resposta.is_success:
        return ""
    return f"o lojista respondeu {resposta.status_code}: {resposta.text}"


@app.post("/checkout/{cobranca_id}/{decisao}")
def decidir(cobranca_id: str, decisao: str):
    # pega o status da decisao, busca a cobranca, decide e chama o webhook do lojista
    status = DECISOES.get(decisao)
    if status is None:
        raise HTTPException(404, "decisao invalida")
    with _lock:
        cobranca = _cobrancas.get(cobranca_id)
        if cobranca is None:
            raise HTTPException(404, "cobranca inexistente")
        if cobranca["status"] != PENDENTE:
            # clique duplo ou aba antiga: so mostra o resultado
            return RedirectResponse(f"/checkout/{cobranca_id}", status_code=303)
        # decide antes de chamar o webhook: um segundo clique ja cai no if acima
        cobranca["status"] = status
        alvo = dict(cobranca)

    print(f"[mock] cobranca {cobranca_id}: {status} -> webhook {alvo['webhook_url']}")
    erro = _enviar_webhook(alvo, status)
    if erro:
        print(f"[mock] cobranca {cobranca_id}: webhook falhou: {erro}")
    with _lock:
        cobranca["erro"] = erro
    return RedirectResponse(f"/checkout/{cobranca_id}", status_code=303)

# a aba do checkout mostra o status da cobranca e permite aprovar ou recusar
_ESTILO = """
body { margin:0; min-height:100vh; display:grid; place-items:center; padding:16px;
       font:16px/1.5 system-ui,sans-serif; background:#f4f5f7; color:#1d2330; }
main { width:100%; max-width:420px; background:#fff; border:1px solid #e3e6eb;
       border-radius:14px; padding:28px; box-sizing:border-box; }
.suave { color:#667085; font-size:14px; margin:0; }
.valor { font-size:32px; font-weight:700; margin:12px 0; }
button { font:inherit; font-weight:600; border:0; border-radius:10px; padding:13px;
         cursor:pointer; color:#fff; width:100%; margin-top:10px; }
.aprovar { background:#12805c; } .recusar { background:#c0362c; }
.resultado { margin-top:20px; font-weight:600; }
.erro { margin-top:16px; color:#c0362c; font-size:14px; }
"""

_RESULTADOS = {
    "APROVADO": "Pagamento aprovado. Você já pode fechar esta aba.",
    "RECUSADO": "Pagamento recusado. Você já pode fechar esta aba.",
    CANCELADA: "Esta cobrança foi cancelada.",
}


@app.get("/checkout/{cobranca_id}", response_class=HTMLResponse)
def checkout(cobranca_id: str):
    # mostra o status da cobranca e permite aprovar ou recusar
    with _lock:
        cobranca = dict(_cobrancas.get(cobranca_id) or {})
    if not cobranca:
        corpo = "<h1>Cobrança não encontrada</h1>"
    else:
        e = html.escape
        valor = f"{cobranca['valor']:.2f}".replace(".", ",")
        corpo = (
            "<p class='suave'>MOCKPAY · provedor de pagamento</p>"
            f"<h1>Pedido {e(cobranca['pedido_id'])}</h1>"
            f"<p class='suave'>{e(cobranca['descricao'])}</p>"
            f"<p class='valor'>R$ {valor}</p>"
        )
        if cobranca["status"] == PENDENTE:
            corpo += (
                f"<form method='post' action='/checkout/{e(cobranca_id)}/aprovar'>"
                "<button class='aprovar'>Pagamento Aprovado</button></form>"
                f"<form method='post' action='/checkout/{e(cobranca_id)}/recusar'>"
                "<button class='recusar'>Pagamento Recusado</button></form>"
            )
        else:
            corpo += f"<p class='resultado'>{_RESULTADOS[cobranca['status']]}</p>"
        if cobranca["erro"]:
            corpo += f"<p class='erro'>{e(cobranca['erro'])}</p>"
    return (
        "<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Pagamento</title><style>{_ESTILO}</style></head>"
        f"<body><main>{corpo}</main></body></html>"
    )


def main():
    print(f"[mock] provedor de pagamento em :{PORTA} (checkout publico em {URL_PUBLICA})")
    uvicorn.run(app, host="0.0.0.0", port=PORTA)


if __name__ == "__main__":
    main()
