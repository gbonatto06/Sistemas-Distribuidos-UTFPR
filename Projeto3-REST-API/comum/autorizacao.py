# Quem pode publicar o que.

# A assinatura define se o serviço e mesmo quem diz ser
# A autorizacao define seesse servico pode emitir esse evento

from comum.config import (
    RK_ESTOQUE_INDISPONIVEL,
    RK_INTERESSE_PROMOCAO,
    RK_PAGAMENTO_APROVADO,
    RK_PAGAMENTO_PENDENTE,
    RK_PAGAMENTO_RECUSADO,
    RK_PEDIDO_CRIADO,
    RK_PEDIDO_ESTOQUE_OK,
    RK_PEDIDO_EXCLUIDO,
    RK_PEDIDO_ENVIADO,
)

# routing key -> servicos que podem publica-la.
# Quem nao esta na tabela nao publica. entao um evento novo
# nasce bloqueado ate alguem decidir explicitamente quem pode emitir
PRODUTORES = {
    RK_PEDIDO_CRIADO: {"principal"},
    RK_PEDIDO_EXCLUIDO: {"principal"},
    RK_INTERESSE_PROMOCAO: {"principal"},
    RK_PEDIDO_ESTOQUE_OK: {"estoque"},
    RK_ESTOQUE_INDISPONIVEL: {"estoque"},
    RK_PAGAMENTO_PENDENTE: {"pagamento"},
    RK_PAGAMENTO_APROVADO: {"pagamento"},
    RK_PAGAMENTO_RECUSADO: {"pagamento"},
    RK_PEDIDO_ENVIADO: {"entrega"},
}


def permitido(produtor, routing_key):
    # verifica se o produtor (servico) tem permissao para publicar a routing key
    return produtor in PRODUTORES.get(routing_key, frozenset())
