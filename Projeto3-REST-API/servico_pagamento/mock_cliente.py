# Chamadas REST ao provedor de pagamento (Mock)

import httpx

from comum.config import MOCK_PAGAMENTO_URL, PAGAMENTO_WEBHOOK_URL


class ProvedorIndisponivel(Exception):
    """O provedor nao respondeu ou recusou a requisicao."""


_cliente = httpx.Client(base_url=MOCK_PAGAMENTO_URL, timeout=5)


def criar_cobranca(pedido_id, valor, descricao):
    """
    Pede a cobranca ao provedor, informando o webhook de retorno.
    Retorna o JSON do provedor (cobranca_id, checkout_url, ...).
    """
    try:
        resposta = _cliente.post("/cobrancas", json={
            "pedido_id": pedido_id,
            "valor": valor,
            "descricao": descricao,
            "webhook_url": PAGAMENTO_WEBHOOK_URL,
        })
        resposta.raise_for_status()
    except httpx.HTTPError as erro:
        raise ProvedorIndisponivel(f"provedor de pagamento indisponivel ({erro})") from None
    return resposta.json()


def cancelar_cobranca(cobranca_id):
    """
    realiza post para o endpoint de cancelamento do provedor, que cancela a cobranca
    """
    try:
        _cliente.post(f"/cobrancas/{cobranca_id}/cancelamento").raise_for_status()
        return True
    except httpx.HTTPError as erro:
        print(f"[pagamento] nao consegui cancelar a cobranca {cobranca_id} no provedor: {erro}")
        return False
