import { useState, type FormEvent } from "react";

export function Identificacao({ onEntrar }: { onEntrar: (cliente: string) => void }) {
  const [nome, setNome] = useState("");

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (nome.trim()) onEntrar(nome.trim());
  }

  return (
    <main className="entrada">
      <form className="cartao entrada-cartao" onSubmit={enviar}>
        <p className="marca">Loja UTFPR</p>
        <h1>Como podemos te chamar?</h1>
        <p className="suave">
          O nome identifica os seus pedidos e o canal de notificações em tempo real.
        </p>
        <label className="campo">
          <span>Seu nome</span>
          <input
            autoFocus
            maxLength={60}
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="ex.: ana"
          />
        </label>
        <button className="botao primario largo" disabled={!nome.trim()}>
          Entrar na loja
        </button>
      </form>
    </main>
  );
}
