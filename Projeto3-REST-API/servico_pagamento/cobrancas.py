# Cobrancas abertas no provedor, em memoria.

import copy
import threading

PENDENTE = "PENDENTE"
APROVADO = "APROVADO"
RECUSADO = "RECUSADO"
CANCELADO = "CANCELADO"

# resultados de decidir()
DECIDIDA = "decidida"
REPETIDA = "repetida"          # mesmo webhook de novo: responde ok sem republicar
INEXISTENTE = "inexistente"
CANCELADA = "cancelada"        # o cliente cancelou o pedido antes de pagar
JA_DECIDIDA = "ja_decidida"    # chegou o resultado oposto ao ja registrado

_lock = threading.Lock()
_por_pedido = {}     # pedido_id -> cobranca
_por_cobranca = {}   # cobranca_id -> pedido_id
# pedidos excluidos. Guardado a parte porque o pedido.excluido pode chegar antes
# do pedido.estoque_ok (vem de outro produtor, a ordem entre os dois nao e garantida)
_cancelados = set()


def cancelado(pedido_id):
    with _lock:
        return pedido_id in _cancelados


def buscar(pedido_id):
    with _lock:
        return copy.deepcopy(_por_pedido.get(pedido_id))


def registrar(evento, cobranca_id, checkout_url):
    cobranca = {
        "pedido_id": evento["pedido_id"],
        "cobranca_id": cobranca_id,
        "checkout_url": checkout_url,
        "status": PENDENTE,
        "evento": evento,
    }
    with _lock:
        _por_pedido[cobranca["pedido_id"]] = cobranca
        _por_cobranca[cobranca_id] = cobranca["pedido_id"]
        return copy.deepcopy(cobranca)


def cancelar(pedido_id):
    """Marca o pedido como excluido. Retorna a cobranca se ela estava pendente."""
    with _lock:
        _cancelados.add(pedido_id)
        cobranca = _por_pedido.get(pedido_id)
        if cobranca is None or cobranca["status"] != PENDENTE:
            return None
        cobranca["status"] = CANCELADO
        return copy.deepcopy(cobranca)


def decidir(cobranca_id, pedido_id, status):
    """Registra o resultado do webhook. Retorna (cobranca, resultado)."""
    with _lock:
        cobranca = _por_pedido.get(_por_cobranca.get(cobranca_id))
        if cobranca is None or cobranca["pedido_id"] != pedido_id:
            return None, INEXISTENTE
        if cobranca["status"] == CANCELADO:
            return copy.deepcopy(cobranca), CANCELADA
        if cobranca["status"] == status:
            return copy.deepcopy(cobranca), REPETIDA
        if cobranca["status"] != PENDENTE:
            return copy.deepcopy(cobranca), JA_DECIDIDA
        cobranca["status"] = status
        return copy.deepcopy(cobranca), DECIDIDA
