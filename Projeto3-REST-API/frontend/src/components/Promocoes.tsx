import { useState, type FormEvent } from "react";
import * as api from "../api";
import type { Produto } from "../api";
import type { Tom } from "../status";

const CHAVE_EMAIL = "loja.email";

function lerEmail() {
  try {
    return localStorage.getItem(CHAVE_EMAIL) ?? "";
  } catch {
    return "";
  }
}

type Props = {
  categorias: string[];
  produtos: Produto[];
  avisar: (tom: Tom, titulo: string, detalhe?: string) => void;
};

export function Promocoes({ categorias, produtos, avisar }: Props) {
  const [email, setEmail] = useState(lerEmail);
  const [escolhidas, setEscolhidas] = useState<string[]>([]);
  const [enviando, setEnviando] = useState<"" | "inscrever" | "cancelar">("");
  const [resultado, setResultado] = useState<{ tom: Tom; texto: string } | null>(null);

  const exemplos = (categoria: string) =>
    produtos
      .filter((p) => p.categoria === categoria)
      .map((p) => p.nome)
      .join(", ");

  function alternar(categoria: string) {
    setEscolhidas((atual) =>
      atual.includes(categoria) ? atual.filter((c) => c !== categoria) : [...atual, categoria].sort(),
    );
  }

  function lembrar(valor: string) {
    try {
      localStorage.setItem(CHAVE_EMAIL, valor);
    } catch {
      // sem storage o formulario so nao lembra o e-mail
    }
  }

  async function inscrever(evento: FormEvent) {
    evento.preventDefault();
    setEnviando("inscrever");
    setResultado(null);
    try {
      const r = await api.inscrever(email, escolhidas);
      lembrar(r.email);
      const texto = `Inscrição enviada para ${r.email} nas categorias ${r.categorias.join(", ")}. As próximas ofertas dessas categorias chegam por e-mail.`;
      setResultado({ tom: "sucesso", texto });
      avisar("sucesso", "Inscrição enviada", r.categorias.map((c) => `Categoria ${c}`).join(", "));
    } catch (erro) {
      setResultado({ tom: "erro", texto: (erro as Error).message });
    } finally {
      setEnviando("");
    }
  }

  async function cancelar() {
    setEnviando("cancelar");
    setResultado(null);
    try {
      const r = await api.cancelarInscricao(email);
      setResultado({ tom: "info", texto: `${r.email} não vai mais receber promoções.` });
      avisar("info", "Inscrição cancelada", r.email);
    } catch (erro) {
      setResultado({ tom: "erro", texto: (erro as Error).message });
    } finally {
      setEnviando("");
    }
  }

  const emailValido = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim());

  return (
    <section className="cartao promocoes">
      <h2>Promoções por e-mail</h2>
      <p className="suave">
        Escolha as categorias que te interessam. Sempre que sair uma oferta de uma delas, ela chega na sua caixa de
        entrada.
      </p>

      <form onSubmit={inscrever}>
        <label className="campo">
          <span>E-mail</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="voce@exemplo.com"
            autoComplete="email"
            required
          />
        </label>

        <fieldset className="categorias">
          <legend>Categorias de interesse</legend>
          {categorias.map((categoria) => (
            <label key={categoria} className={`opcao ${escolhidas.includes(categoria) ? "marcada" : ""}`}>
              <input
                type="checkbox"
                checked={escolhidas.includes(categoria)}
                onChange={() => alternar(categoria)}
              />
              <span>
                <strong>Categoria {categoria}</strong>
                <span className="suave">{exemplos(categoria) || "—"}</span>
              </span>
            </label>
          ))}
        </fieldset>

        <div className="acoes-form">
          <button className="botao primario" disabled={!emailValido || escolhidas.length === 0 || enviando !== ""}>
            {enviando === "inscrever" ? "Enviando…" : "Inscrever"}
          </button>
          <button
            type="button"
            className="botao secundario"
            disabled={!emailValido || enviando !== ""}
            onClick={cancelar}
          >
            {enviando === "cancelar" ? "Cancelando…" : "Cancelar inscrição"}
          </button>
        </div>
        <p className="suave pequeno-texto">
          Inscrever de novo substitui as categorias anteriores. Cancelar remove o e-mail de todas.
        </p>
      </form>

      {resultado && (
        <p className={`aviso ${resultado.tom}`} role="status">
          {resultado.texto}
        </p>
      )}
    </section>
  );
}
