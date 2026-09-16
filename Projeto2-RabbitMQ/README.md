## Estrutura

```
comum/                  código compartilhado
  config.py             broker, exchange, routing keys, filas, estoque inicial, chaves
  mensageria.py         conectar / publicar / consumir
  cripto.py             assina e verifica os eventos
  autorizacao.py        quem pode publicar cada routing key
  rastro.py             mostra no terminal cada evento que sai e entra
  requisicao.py         pergunta/resposta casada por id de correlação

servico_estoque/
  estoque.py            reservar, devolver, catálogo
  main.py               consumidor de eventos

servico_pagamento/
  main.py               cobrança simulada dos pedidos reservados

servico_entrega/
  main.py               despacho simulado dos pedidos pagos

servico_promocoes/
  main.py               sorteia produtos e publica promoções por categoria

consumidor_promocoes/
  main.py               processo que só escuta promoções (C1, C2)

servico_principal/
  main.py               menu do terminal
  pedidos.py            pedidos em memória e seus status
  catalogo.py           consulta o catálogo por evento
  consumidor.py         escuta eventos em thread separada

scripts/
  gerar_chaves.py       gera os pares Ed25519 dos serviços

chaves/                 nunca versionado
  privadas/<servico>     só o próprio serviço tem a sua
  publicas/<servico>.pub o keyring, igual para todos
```

## Como rodar com Docker

```bash
python scripts/gerar_chaves.py         # uma vez
docker compose up -d --build rabbitmq estoque pagamento entrega
docker compose run --rm c1
docker compose run --rm c2
docker compose up -d --build promocoes
docker compose run --rm principal
```
