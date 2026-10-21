
import httpx

from comum.config import ESTOQUE_URL

# tratamento de erro
class EstoqueIndisponivel(Exception):
    """O MS Estoque nao respondeu."""


_cliente = httpx.Client(base_url=ESTOQUE_URL, timeout=3)

# um cliente rest para a microservico estoque
# que tem um endpoint /produtos que retorna a lista de produtos, com opcao de filtrar apenas os disponiveis.
# nao precisa mais da pergunta/resposta, porque o HTTP ja e requisicao-resposta. O RabbitMQ so e usado para eventos.
def produtos(disponiveis=False):
    try:
        resposta = _cliente.get("/produtos", params={"disponiveis": disponiveis})
        resposta.raise_for_status()
    except httpx.HTTPError as erro:
        raise EstoqueIndisponivel(f"MS Estoque indisponivel ({erro})") from None
    return resposta.json()
