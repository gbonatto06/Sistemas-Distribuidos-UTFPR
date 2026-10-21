# Pedidos do servico principal, mantidos em memoria.

import copy
import itertools
import threading
import uuid
from datetime import datetime

from comum.config import (
    STATUS_CANCELAVEIS,
    STATUS_CRIADO,
    STATUS_EXCLUIDO,
    STATUS_FINAIS,
)

_lock = threading.Lock()
_pedidos = {}  # pedido_id -> pedido
# ordem de criacao: criado_em so tem segundos, e dois pedidos no mesmo segundo
# precisam continuar em ordem na tela
_sequencia = itertools.count(1)


def horario_atual():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def criar(cliente, itens):
    """Cria o pedido com status CRIADO e o devolve."""
    agora = horario_atual()
    pedido = {
        "pedido_id": uuid.uuid4().hex[:8],
        "cliente": cliente,
        "itens": itens,
        "total": round(sum(i["preco"] * i["quantidade"] for i in itens), 2),
        "status": STATUS_CRIADO,
        "motivo": "",
        "checkout_url": None,
        "nota_fiscal": None,
        "criado_em": agora,
        "atualizado_em": agora,
        "historico": [{"status": STATUS_CRIADO, "em": agora}],
    }
    with _lock:
        pedido["sequencia"] = next(_sequencia)
        _pedidos[pedido["pedido_id"]] = pedido
        return copy.deepcopy(pedido)


def evento_criado(pedido):
    """O que viaja no pedido.criado: so o que os outros servicos usam."""
    return {
        chave: pedido[chave]
        for chave in ("pedido_id", "cliente", "itens", "total", "criado_em")
    }


def descartar(pedido_id):
    """Remove um pedido que nem chegou a ser anunciado."""
    with _lock:
        _pedidos.pop(pedido_id, None)


def listar(cliente):
    """Pedidos de um cliente, do mais antigo para o mais novo."""
    with _lock:
        return [copy.deepcopy(p) for p in _pedidos.values() if p["cliente"] == cliente]


def buscar(pedido_id, cliente=None):
    with _lock:
        pedido = _pedidos.get(pedido_id)
        if pedido is None or cliente not in (None, pedido["cliente"]):
            return None
        return copy.deepcopy(pedido)


def atualizar_status(pedido_id, status, permitidos=None, **campos):
    """
    funcao que muda o status de um pedido, com lock para evitar que dois eventos concorrentes
    muda o status e campos variaveis de um pedido

    Pedido desconhecido ou ja finalizado nao muda: um pagamento.aprovado que
    chega depois do cliente cancelar nao ressuscita o pedido. Com permitidos,
    so muda se o status atual estiver entre eles, a checagem e a escrita ficam
    sob o mesmo lock.
    Retorna o pedido atualizado ou None.
    """
    with _lock:
        pedido = _pedidos.get(pedido_id)
        if pedido is None or pedido["status"] in STATUS_FINAIS:
            return None
        if permitidos is not None and pedido["status"] not in permitidos:
            return None
        agora = horario_atual()
        pedido.update(campos)
        pedido["status"] = status
        pedido["atualizado_em"] = agora
        pedido["historico"].append({"status": status, "em": agora})
        return copy.deepcopy(pedido)


def excluir(pedido_id):
    """Marca o pedido como EXCLUIDO, se ele ainda nao foi pago."""
    return atualizar_status(pedido_id, STATUS_EXCLUIDO, permitidos=STATUS_CANCELAVEIS)
