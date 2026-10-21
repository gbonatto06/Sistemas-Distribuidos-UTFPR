import type { Pedido, StatusPedido } from "./api";

export type Tom = "neutro" | "info" | "sucesso" | "alerta" | "erro";

export const ROTULOS: Record<StatusPedido, string> = {
  CRIADO: "Criado",
  ESTOQUE_OK: "Estoque confirmado",
  ESTOQUE_INDISPONIVEL: "Estoque indisponível",
  AGUARDANDO_PAGAMENTO: "Aguardando pagamento",
  PAGAMENTO_APROVADO: "Pagamento aprovado",
  PAGAMENTO_RECUSADO: "Pagamento recusado",
  PEDIDO_ENVIADO: "Enviado",
  EXCLUIDO: "Cancelado",
};

export const TONS: Record<StatusPedido, Tom> = {
  CRIADO: "neutro",
  ESTOQUE_OK: "info",
  ESTOQUE_INDISPONIVEL: "erro",
  AGUARDANDO_PAGAMENTO: "alerta",
  PAGAMENTO_APROVADO: "sucesso",
  PAGAMENTO_RECUSADO: "erro",
  PEDIDO_ENVIADO: "sucesso",
  EXCLUIDO: "neutro",
};

// depois destes o pedido nao muda mais (igual ao STATUS_FINAIS do backend)
export const FINAIS = new Set<StatusPedido>([
  "ESTOQUE_INDISPONIVEL",
  "PAGAMENTO_RECUSADO",
  "PEDIDO_ENVIADO",
  "EXCLUIDO",
]);

// o cliente so cancela antes de pagar (igual ao STATUS_CANCELAVEIS do backend)
export const CANCELAVEIS = new Set<StatusPedido>(["CRIADO", "ESTOQUE_OK", "AGUARDANDO_PAGAMENTO"]);

export type EstadoEtapa = "feita" | "atual" | "falhou" | "pendente";
export type Etapa = { rotulo: string; estado: EstadoEtapa };

/** As quatro etapas da linha do tempo, a partir do historico do pedido. */
export function etapas(pedido: Pedido): Etapa[] {
  const passou = new Set(pedido.historico.map((h) => h.status));
  const cancelado = pedido.status === "EXCLUIDO";

  const estoque: EstadoEtapa = passou.has("ESTOQUE_OK")
    ? "feita"
    : passou.has("ESTOQUE_INDISPONIVEL")
      ? "falhou"
      : cancelado
        ? "pendente"
        : "atual";

  let pagamento: EstadoEtapa = "pendente";
  if (passou.has("PAGAMENTO_APROVADO")) pagamento = "feita";
  else if (passou.has("PAGAMENTO_RECUSADO")) pagamento = "falhou";
  else if (estoque === "feita" && !cancelado) pagamento = "atual";

  let envio: EstadoEtapa = "pendente";
  if (passou.has("PEDIDO_ENVIADO")) envio = "feita";
  else if (pagamento === "feita") envio = "atual";

  return [
    { rotulo: "Pedido criado", estado: "feita" },
    { rotulo: "Estoque", estado: estoque },
    { rotulo: "Pagamento", estado: pagamento },
    { rotulo: "Envio", estado: envio },
  ];
}

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
export const reais = (valor: number) => moeda.format(valor);

/** "2026-10-16 15:19:57" -> "16/10 15:19" */
export function dataCurta(texto: string) {
  const [data, hora = ""] = texto.split(" ");
  const [, mes, dia] = data.split("-");
  return `${dia}/${mes} ${hora.slice(0, 5)}`;
}
