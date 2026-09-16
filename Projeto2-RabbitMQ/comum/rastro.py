# modulo para rastrear eventos publicados e recebidos

from comum.config import EVENTOS_VISIVEIS

_COLUNA = 28  # largura da routing key


def _correlacao(evento):
    """corr=abcd1234, quando o evento carrega id de correlacao."""
    correlacao = evento.get("correlacao")
    return f"corr={correlacao[:8]}  " if correlacao else ""


def _resumo(evento):
    """Resumo de uma linha do conteudo, sem despejar o JSON inteiro."""
    partes = []
    for chave, valor in evento.items():
        if chave == "correlacao":
            continue  # ja sai no _correlacao
        if isinstance(valor, (list, dict)):
            partes.append(f"{chave}={len(valor)}")
        elif isinstance(valor, str) and len(valor) > 32:
            partes.append(f"{chave}={valor[:29]}...")
        else:
            partes.append(f"{chave}={valor}")
    return " ".join(partes)


def publicado(routing_key, evento):
    if not EVENTOS_VISIVEIS:
        return
    print(f"  -> {routing_key:<{_COLUNA}} {_correlacao(evento)}{_resumo(evento)}")


def recebido(routing_key, produtor, evento):
    if not EVENTOS_VISIVEIS:
        return
    print(
        f"  <- {routing_key:<{_COLUNA}} {_correlacao(evento)}"
        f"de={produtor} ok  {_resumo(evento)}"
    )
