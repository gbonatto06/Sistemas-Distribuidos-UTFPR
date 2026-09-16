# Quem pode publicar o que.

# A assinatura define se o serviço e mesmo quem diz ser
# A autorizacao define seesse servico pode emitir esse evento

from comum.config import (
    CATEGORIAS,
    SOLICITANTES_CATALOGO,
    RK_ESTOQUE_INDISPONIVEL,
    RK_PAGAMENTO_APROVADO,
    RK_PAGAMENTO_RECUSADO,
    RK_PEDIDO_CRIADO,
    RK_PEDIDO_ESTOQUE_OK,
    RK_PEDIDO_EXCLUIDO,
    RK_PRODUTOS_CATALOGO,
    RK_PRODUTOS_CONSULTA,
    RK_PEDIDO_ENVIADO,
    rk_catalogo_para,
    rk_consulta_catalogo,
    rk_promocao,
)

# routing key -> servicos que podem publica-la.
# Quem nao esta na tabela nao publica. entao um evento novo
# nasce bloqueado ate alguem decidir explicitamente quem pode emitir
PRODUTORES = {
    RK_PEDIDO_CRIADO: {"principal"},
    RK_PEDIDO_EXCLUIDO: {"principal"},
    RK_PEDIDO_ESTOQUE_OK: {"estoque"},
    RK_ESTOQUE_INDISPONIVEL: {"estoque"},
    # cada solicitante so publica a SUA pergunta, e so o Estoque
    # responde. Como a chave carrega o nome, ninguem consulta se passando por outro
    **{rk_consulta_catalogo(s): {s} for s in SOLICITANTES_CATALOGO},
    **{rk_catalogo_para(s): {"estoque"} for s in SOLICITANTES_CATALOGO},
    RK_PAGAMENTO_APROVADO: {"pagamento"},
    RK_PAGAMENTO_RECUSADO: {"pagamento"},
    RK_PEDIDO_ENVIADO: {"entrega"},
    # quem publica promocao.categoria.X e so o Promocoes.
    **{rk_promocao(categoria): {"promocoes"} for categoria in CATEGORIAS},
}


def permitido(produtor, routing_key):
    # verifica se o produtor (servico) tem permissao para publicar a routing key
    return produtor in PRODUTORES.get(routing_key, frozenset())
