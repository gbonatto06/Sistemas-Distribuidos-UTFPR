from comum import mensageria

# publica um evento na exchange do sistema, com a routing_key especificada.
# cada publicacao abre a sua conexao, publica e fecha. feito por conta da
# pika nao pode ser dividido em threads
def publicar(routing_key, evento):
    conexao, canal = mensageria.conectar()
    try:
        mensageria.publicar(canal, routing_key, evento)
    finally:
        conexao.close()
