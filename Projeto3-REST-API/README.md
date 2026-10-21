# Projeto 3: E-commerce com microsserviços, REST, SSE e RabbitMQ

Frontend web (React + TypeScript) → API Gateway (REST + SSE) → microsserviços em Python
conversando pelo RabbitMQ, com todos os eventos assinados (Ed25519). Integrações externas:
Mock de Pagamento (REST + Webhook) e Resend (e-mail).

## Como rodar com Docker

```bash
python scripts/gerar_chaves.py      # uma vez (ou .venv\Scripts\python no Windows)
cp .env.example .env                # segredos: chave do Resend e do webhook (ver Segredos)
docker compose up -d --build
docker compose logs -f principal estoque pagamento mock-pagamento entrega promocoes
```

| Onde | Endereço |
|---|---|
| Loja (frontend) | http://localhost:8080 |
| Gateway (Swagger) | http://localhost:8000/docs |
| Estoque | http://localhost:8001/produtos |
| Mock de Pagamento | http://localhost:8003/checkout/{id} (a URL vem no pedido) |
| RabbitMQ (guest/guest) | http://localhost:15672 |

`docker compose down -v` apaga o volume do Estoque e ele volta ao inicial. Cobranças (Pagamento) e inscritos
(Promoções) ficam em memória: reiniciar esses serviços os zera.

### Segredos

Assim como as chaves privadas, os segredos chegam aos containers como **Docker secrets**
(arquivo em `/run/secrets/`), nunca como variável de ambiente nem dentro da imagem:

| Segredo | Vem de | Quem recebe |
|---|---|---|
| `chave_<servico>` | `chaves/privadas/<servico>` | só o próprio serviço |
| `webhook_segredo` | `WEBHOOK_SEGREDO` no `.env` | pagamento, mock-pagamento |
| `resend_api_key` | `RESEND_API_KEY` no `.env` | promocoes |

O `.env` e `chaves/` estão no `.gitignore`. O código lê o segredo de `/run/secrets/<nome>`
(`segredo()` em `comum/config.py`), então os serviços só rodam pelo Docker. Sem
`WEBHOOK_SEGREDO` todo webhook é recusado (o Pagamento avisa no log).

O compose não recria o container quando só o valor de um segredo muda: depois de editar
o `.env`, suba com `docker compose up -d --force-recreate`.

### E-mail (Resend)

Sem `RESEND_API_KEY` os e-mails só aparecem no log do `promocoes` ("e-mail SIMULADO").
Com a chave, mas sem domínio verificado, o remetente `onboarding@resend.dev` **só entrega no
e-mail dono da conta Resend**. Na demonstração, inscreva esse e-mail.

### Frontend sem Docker

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, falando com o Gateway em localhost:8000
```

## Arquitetura

```
Frontend ──REST──▶ Gateway ──pedido.criado──▶ Estoque (SQLite)
   ▲                  │                           │
   └──────SSE─────────┤◀──pedido.estoque_ok / estoque.indisponivel
                      │                           │
                      │                      Pagamento ──REST──▶ Mock de Pagamento
                      │◀──pagamento.pendente──────┤   ◀──Webhook (HMAC)──┘
                      │◀──pagamento.aprovado/recusado
                      │◀──pedido.enviado──── Entrega
                      │
                      └──interesse.promocao──▶ Promoções ───────REST──▶ Resend
                                                 └──REST──▶ Estoque (catálogo)
```

## Eventos

| Routing key | Produtor | Consumidores | Conteúdo principal |
|---|---|---|---|
| `pedido.criado` | principal | estoque | `pedido_id, cliente, itens, total` |
| `pedido.excluido` | principal | estoque, pagamento | `pedido_id` |
| `pedido.estoque_ok` | estoque | principal, pagamento | evento do pedido |
| `estoque.indisponivel` | estoque | principal | evento do pedido + `motivo` |
| `pagamento.pendente` | pagamento | principal | `pedido_id, checkout_url` |
| `pagamento.aprovado` | pagamento | principal, entrega | evento do pedido |
| `pagamento.recusado` | pagamento | principal | evento do pedido + `motivo` |
| `pedido.enviado` | entrega | principal | evento + `nota_fiscal` |
| `interesse.promocao` | principal | promocoes | `email, categorias, acao (inscrever/cancelar)` |

Todos passam por uma única exchange `direct` (`eCommerce`). Cada mensagem vai num envelope
`{produtor, conteudo, Signature}`. Quem recebe confere a assinatura com a chave pública do produtor
e a tabela de `comum/autorizacao.py` (quem pode publicar cada routing key), e descarta o que não bate.

## Fluxo do pedido

1. O frontend faz `POST /pedidos`. O Gateway pega nome e preço no Estoque (REST) e publica `pedido.criado`.
2. O Estoque reserva em transação (SQLite) e publica `pedido.estoque_ok` ou `estoque.indisponivel`.
3. O Pagamento faz `POST mock/cobrancas` com o valor e a sua `webhook_url`, recebe a `checkout_url` e publica `pagamento.pendente`.
4. O Gateway repassa tudo pelo SSE. A aba que o frontend abriu no clique de "Finalizar" vai para o checkout.
5. O cliente clica em Aprovado/Recusado no Mock, que faz `POST pagamento:8002/webhook` assinado com HMAC.
6. O Pagamento publica `pagamento.aprovado`, e aí a Entrega emite a NF e publica `pedido.enviado`. Se publicar `pagamento.recusado`, o Gateway publica `pedido.excluido` e o Estoque devolve a reserva.

Cancelar antes de pagar publica `pedido.excluido`. O Estoque devolve a reserva e o Pagamento cancela a
cobrança, inclusive no Mock: clicar depois mostra "cobrança cancelada" e nada é despachado.

## API do Gateway

| Método | Rota | O que faz |
|---|---|---|
| GET | `/produtos?disponiveis=true` | catálogo, consultado no Estoque via REST |
| POST | `/pedidos` | `{cliente, itens:[{produto_id, quantidade}]}` → publica `pedido.criado` |
| GET | `/pedidos?cliente=` | pedidos do cliente |
| GET | `/pedidos/{id}?cliente=` | um pedido |
| DELETE | `/pedidos/{id}?cliente=` | cancela (antes do pagamento) → publica `pedido.excluido` |
| POST | `/interesses` | `{email, categorias}` → publica `interesse.promocao` (`acao=inscrever`) |
| DELETE | `/interesses/{email}?categorias=` | publica `interesse.promocao` (`acao=cancelar`); sem categorias cancela todas |
| GET | `/eventos?cliente=` | SSE: evento `pedidos` (lista atual) ao conectar e `pedido` a cada mudança de status |
s
Acompanhar um cliente pelo terminal (no PowerShell use `curl.exe`):

```bash
curl -N "localhost:8000/eventos?cliente=ana"
```

## Estrutura

```
comum/                  código compartilhado pelos microsserviços
  config.py             broker, routing keys, filas, portas, URLs, status
  mensageria.py         conectar / publicar / consumir (inclusive em thread, com reconexão)
  publicador.py         publicação thread-safe para os handlers HTTP
  cripto.py             assina e verifica os eventos
  autorizacao.py        quem pode publicar cada routing key
  banco.py              transações SQLite do Estoque
  estoque_cliente.py    GET /produtos no Estoque (Gateway e Promoções)
  rastro.py             mostra no log cada evento que sai e entra

servico_principal/      API Gateway
  api.py                rotas REST e o canal SSE (GET /eventos)
  sse.py                conexões SSE abertas por cliente
  pedidos.py            pedidos em memória, status e histórico
  consumidor.py         escuta os eventos e notifica pelo SSE

servico_estoque/
  estoque.py            reservar, devolver, catálogo (SQLite)
  api.py                GET /produtos

servico_pagamento/
  main.py               cria a cobrança ao receber pedido.estoque_ok; cancela no pedido.excluido
  cobrancas.py          cobranças em aberto (memória)
  mock_cliente.py       chamadas REST ao Mock
  api.py                POST /webhook (HMAC) → pagamento.aprovado/recusado

servico_entrega/
  main.py               emite a NF e despacha os pedidos pagos

servico_promocoes/
  main.py               inscritos em memória (interesse.promocao); sorteia e dispara promoções
  correio.py            e-mail da promoção e envio pelo Resend (REST)

mock_pagamento/         provedor EXTERNO: imagem própria, sem RabbitMQ nem chaves
  main.py               POST /cobrancas, página de checkout, webhook ao clicar

frontend/               React + TypeScript (Vite), servido pelo nginx
  src/App.tsx           abas, carrinho, aba de pagamento
  src/usePedidos.ts     pedidos ao vivo pelo EventSource (SSE)
  src/api.ts            cliente REST do Gateway

scripts/
  gerar_chaves.py       gera os pares Ed25519 dos serviços

chaves/                 nunca versionado
  privadas/<servico>     só o próprio serviço tem a sua
  publicas/<servico>.pub o keyring, igual para todos
```
