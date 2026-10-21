# Envio de e-mail pela API externa (Resend), via REST.
#
# POST https://api.resend.com/emails com a chave no header Authorization.
# Sem RESEND_API_KEY o servico continua funcionando: o e-mail so aparece no log.

import html

import httpx

from comum.config import EMAIL_REMETENTE, RESEND_API_KEY, RESEND_URL


def ativo():
    return bool(RESEND_API_KEY)


def _reais(valor):
    return f"R$ {valor:.2f}".replace(".", ",")


def mensagem_promocao(produto, desconto, preco):
    """(assunto, html, texto) do e-mail de uma promocao."""
    assunto = f"{desconto}% off: {produto['nome']}"
    corpo = (
        "<div style=\"font-family:Arial,sans-serif;max-width:480px\">"
        f"<h2>{html.escape(produto['nome'])} com {desconto}% de desconto</h2>"
        f"<p>De <s>{_reais(produto['preco'])}</s> por <strong>{_reais(preco)}</strong>.</p>"
        f"<p style=\"color:#667085\">Categoria {html.escape(produto['categoria'])}. "
        "Para sair da lista, use a aba Promoções da loja.</p></div>"
    )
    texto = f"{produto['nome']} com {desconto}% de desconto: de {_reais(produto['preco'])} por {_reais(preco)}."
    return assunto, corpo, texto


def enviar(para, assunto, corpo, texto):
    """Envia um e-mail (um destinatario por vez). Retorna True se foi aceito."""
    if not RESEND_API_KEY:
        print(f"[promocoes] e-mail SIMULADO para {para}: {assunto}")
        return True
    try:
        resposta = httpx.post(
            f"{RESEND_URL}/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": EMAIL_REMETENTE, "to": [para], "subject": assunto,
                  "html": corpo, "text": texto},
            timeout=10,
        )
    except httpx.HTTPError as erro:
        print(f"[promocoes] Resend inacessivel ao enviar para {para}: {erro}")
        return False
    if resposta.is_success:
        print(f"[promocoes] e-mail enviado para {para}: {assunto}")
        return True
    print(f"[promocoes] Resend recusou o e-mail para {para} ({resposta.status_code}): {resposta.text}")
    return False
