#Pedidos do servico principal, mantidos na memoria do processo.
#A lista e lida e escrita pela thread do menu e pela thread do consumidor,
# por isso todo acesso passa por um lock.

import threading
import uuid
from datetime import datetime
from comum import mensageria
from comum.config import STATUS_CRIADO, STATUS_EXCLUIDO, RK_PEDIDO_EXCLUIDO

_lock = threading.Lock()
_pedidos = [] 


def criar(cliente, itens):
    """Cria o pedido com status CRIADO e o devolve."""
    pedido = {
        "pedido_id": uuid.uuid4().hex[:8],
        "cliente": cliente,
        "itens": itens,
        "status": STATUS_CRIADO,
        "motivo": "",
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with _lock:
        _pedidos.append(pedido)
    return dict(pedido)


def listar(cliente):
    """Pedidos de um cliente, do mais antigo para o mais novo."""
    with _lock:
        return [dict(p) for p in _pedidos if p["cliente"] == cliente]


def buscar(pedido_id, cliente=None):
    with _lock:
        for pedido in _pedidos:
            if pedido["pedido_id"] == pedido_id and cliente in (None, pedido["cliente"]):
                return dict(pedido)
    return None


def atualizar_status(pedido_id, status, motivo=""):
    """Atualiza o status de um pedido. Retorna o pedido atualizado ou None."""
    with _lock:
        for pedido in _pedidos:
            if pedido["pedido_id"] == pedido_id:
                pedido["status"] = status
                pedido["motivo"] = motivo
                return dict(pedido)
    return None


def excluir(pedido_id):
    """Marca o pedido como EXCLUIDO."""
    return atualizar_status(pedido_id, STATUS_EXCLUIDO)

def publicar_exclusao(canal,pedido_id):
    pedido=buscar(pedido_id)
    if pedido:
        mensageria.publicar(canal, RK_PEDIDO_EXCLUIDO, {"pedido_id": pedido_id})
    else:
        print(f"\n[erro] pedido {pedido_id} nao encontrado para publicar exclusao")
