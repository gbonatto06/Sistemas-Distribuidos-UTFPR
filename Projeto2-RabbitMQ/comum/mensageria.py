import json

import pika

from comum.config import RABBITMQ_URL, TIPOS_EXCHANGE, exchange_de
from comum import autorizacao, cripto, rastro
id_servico = None

# definicao do id do servico, que sera usado para assinar os eventos publicados e verificar a autorizacao
def definir_servico(nome):
    global id_servico
    id_servico = nome

# conecta no broker e declara as exchanges do sistema. Retorna (conexao, canal)
# heartbeat=0 desliga o keepalive do AMQP
# o menu esta parado no input() e nao responde os heartbeats, entao o broker derrubaria a conexao por ociosidade.
def conectar(heartbeat=None):
    parametros = pika.URLParameters(RABBITMQ_URL)
    if heartbeat is not None:
        parametros.heartbeat = heartbeat

    conexao = pika.BlockingConnection(parametros)
    canal = conexao.channel()
    # as duas exchanges sao declaradas por todo servico: qualquer um pode ser o
    # primeiro a subir, e declarar e idempotente.
    for exchange, tipo in TIPOS_EXCHANGE.items():
        canal.exchange_declare(exchange=exchange, exchange_type=tipo, durable=True)
    return conexao, canal

# verifica o id do servico
# e ve se tem autorizacao p publicar esse evento
# cria um  envelope com o conteudo e a assinatura
# e publica no broker
def publicar(canal, routing_key, evento):
    """Publica um dicionario como evento JSON na exchange."""
    if not id_servico:
        raise RuntimeError("definir_servico() deve ser chamado antes de publicar()")
    # Serve para o erro aparecer aqui, com mensagem clara, em
    # vez de virar descarte silencioso do outro lado.
    if not autorizacao.permitido(id_servico, routing_key):
        raise PermissionError(
            f"{id_servico} nao publica {routing_key} (ver comum/autorizacao.py)"
        )
    conteudo = json.dumps(evento, ensure_ascii=False, sort_keys=True)
    envelope = {
        "produtor": id_servico,
        "conteudo": conteudo,
        "Signature": cripto.assinar_conteudo(id_servico, conteudo),
    }
    canal.basic_publish(
        exchange=exchange_de(routing_key),
        routing_key=routing_key,
        body=json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,  # persistente
        ),
    )
    rastro.publicado(routing_key, evento)

# consome a fila toda hora, e tratando cada evento
def consumir(fila, routing_keys, tratar, pronto=None, exclusiva=False):

    if not id_servico:
        raise RuntimeError("definir_servico() deve ser chamado antes de consumir()")

    conexao, canal = conectar()
    # para caso haja mais de um consumidor do mesmo servico, cada um com sua fila exclusiva, para nao perder eventos.
    if exclusiva:
        canal.queue_declare(queue=fila, exclusive=True, auto_delete=True)
    else:
        canal.queue_declare(queue=fila, durable=True)
    for routing_key in routing_keys:
        canal.queue_bind(
            exchange=exchange_de(routing_key), queue=fila, routing_key=routing_key
        )

    if pronto is not None:
        pronto.set()

    canal.basic_qos(prefetch_count=1)

    def _callback(ch, method, propriedades, corpo):
        try:
            # recebe o envelope, verifica a assinatura e a autorizacao, e chama tratar() com o conteudo
            envelope = json.loads(corpo.decode("utf-8"))
            produtor = envelope["produtor"]
            # verifica a assinatura e a autorizacao antes de chamar tratar()
            if not cripto.verificar(
                produtor, envelope["conteudo"], envelope["Signature"]
            ):
                print(
                    f"[seguranca] Signature invalida em {method.routing_key}: descartado"
                )
            # somente o produtor autorizado pode publicar a routing key: descarta o evento
            elif not autorizacao.permitido(produtor, method.routing_key):
                print(
                    f"[seguranca] {produtor} nao pode publicar "
                    f"{method.routing_key}: descartado"
                )
            else:
                conteudo = json.loads(envelope["conteudo"])
                rastro.recebido(method.routing_key, produtor, conteudo)
                tratar(ch, method.routing_key, conteudo)
        except Exception as erro:
            print(f"[erro] falha ao tratar {method.routing_key}: {erro}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    # consome a fila, chamando _callback para cada evento
    canal.basic_consume(queue=fila, on_message_callback=_callback)
    try:
        canal.start_consuming()
    finally:
        conexao.close()
