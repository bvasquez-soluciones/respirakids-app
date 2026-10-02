/* Chat del asistente fundamentado. La URL y el token CSRF llegan como data-* del formulario. */
(function () {
  "use strict";
  const chatBox = document.getElementById("chat-box");
  const form = document.getElementById("form-chat");
  const input = document.getElementById("input-pregunta");
  const btnEnviar = document.getElementById("btn-enviar");
  const quickWrap = document.getElementById("quick-suggestions-wrap");

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function formatearRespuesta(texto) {
    const lineas = texto
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    let html = "";
    let dentroLista = false;

    lineas.forEach((linea) => {
      if (linea.startsWith("⚠️ Atención:") || linea.startsWith("⚠️Atención:")) {
        if (dentroLista) {
          html += "</ul>";
          dentroLista = false;
        }
        const contenido = escapeHtml(linea.replace(/^⚠️\s*Atención:\s*/, ""));
        html += `<div class="rk-msg-attention"><strong>⚠️ Atención:</strong> ${contenido}</div>`;
      } else if (linea.startsWith("- ")) {
        if (!dentroLista) {
          html += "<ul>";
          dentroLista = true;
        }
        html += `<li>${negritas(escapeHtml(linea.slice(2)))}</li>`;
      } else {
        if (dentroLista) {
          html += "</ul>";
          dentroLista = false;
        }
        html += `<p class="mb-1">${negritas(escapeHtml(linea))}</p>`;
      }
    });
    if (dentroLista) html += "</ul>";
    return html;
  }

  function negritas(texto) {
    return texto.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function agregarFuentes(bubble, fuentes) {
    if (!fuentes || !fuentes.length) return;
    const lista = document.createElement("div");
    lista.className = "rk-msg-fuentes";
    lista.innerHTML = "<strong>Fuentes:</strong>";
    const ul = document.createElement("ol");
    fuentes.forEach((f) => {
      const li = document.createElement("li");
      li.value = f.n;
      if (f.url) {
        const a = document.createElement("a");
        a.href = f.url; a.target = "_blank"; a.rel = "noopener";
        a.textContent = f.titulo;
        li.appendChild(a);
      } else {
        li.textContent = f.titulo;
      }
      ul.appendChild(li);
    });
    lista.appendChild(ul);
    bubble.appendChild(lista);
  }

  function agregarMensaje(texto, esUsuario, fuentes) {
    const row = document.createElement("div");
    row.className = "rk-msg-row" + (esUsuario ? " user" : "");

    const avatar = document.createElement("div");
    avatar.className = "rk-msg-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = esUsuario ? "🧑" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "rk-msg-bubble";
    bubble.innerHTML = esUsuario
      ? escapeHtml(texto)
      : formatearRespuesta(texto);

    if (!esUsuario) agregarFuentes(bubble, fuentes);
    row.appendChild(avatar);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function mostrarEscribiendo() {
    const row = document.createElement("div");
    row.className = "rk-msg-row";
    row.id = "typing-row";
    row.innerHTML = `<div class="rk-msg-avatar" aria-hidden="true">🤖</div><div class="rk-msg-bubble rk-typing-dots"><span class="visually-hidden">El asistente está escribiendo</span><span aria-hidden="true"></span><span aria-hidden="true"></span><span aria-hidden="true"></span></div>`;
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
  }
  function quitarEscribiendo() {
    const row = document.getElementById("typing-row");
    if (row) row.remove();
  }

  async function enviarPregunta(pregunta) {
    agregarMensaje(pregunta, true);
    quickWrap.hidden = true;
    btnEnviar.disabled = true;
    mostrarEscribiendo();

    try {
      const res = await fetch(form.dataset.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": form.dataset.csrf,
        },
        body: JSON.stringify({ pregunta: pregunta }),
      });
      quitarEscribiendo();
      if (res.status === 429) {
        agregarMensaje("⚠️ Has hecho muchas preguntas seguidas. Espera un momento e inténtalo de nuevo.", false);
        btnEnviar.disabled = false;
        return;
      }
      const data = await res.json();

      if (data.error) {
        agregarMensaje("⚠️ " + data.error, false);
      } else {
        agregarMensaje(data.respuesta, false, data.fuentes);
      }
    } catch (err) {
      quitarEscribiendo();
      agregarMensaje("⚠️ Error de conexión. Intenta de nuevo.", false);
    }

    btnEnviar.disabled = false;
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const pregunta = input.value.trim();
    if (!pregunta) return;
    input.value = "";
    enviarPregunta(pregunta);
  });

  document.querySelectorAll(".rk-quick-card").forEach((card) => {
    card.addEventListener("click", () => {
      enviarPregunta(card.dataset.pregunta);
    });
  });
})();
