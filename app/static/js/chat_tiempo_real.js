/* Conversación: muestra los mensajes nuevos sin recargar (consulta cada 5 s mientras la pestaña está visible).
   El contenido se inserta como texto (textContent), nunca como HTML. */
(function () {
  "use strict";
  const lista = document.querySelector("[data-nuevos-url]");
  if (!lista) return;
  const url = lista.getAttribute("data-nuevos-url");
  let ultimo = parseInt(lista.getAttribute("data-ultimo") || "0", 10);
  const INTERVALO = 5000;

  function cercaDelFinal() {
    return lista.scrollHeight - lista.scrollTop - lista.clientHeight < 120;
  }

  function agregar(mensaje) {
    const vacio = lista.querySelector("[data-sin-mensajes]");
    if (vacio) vacio.remove();
    const fila = document.createElement("div");
    fila.className = "rk-msg-row" + (mensaje.propio ? " user" : "");
    const burbuja = document.createElement("div");
    burbuja.className = "rk-msg-bubble";
    function texto(clase, valor) {
      const div = document.createElement("div");
      if (clase) div.className = clase;
      div.textContent = valor;
      burbuja.appendChild(div);
    }
    texto("rk-msg-autor", mensaje.propio ? "Tú" : mensaje.autor);
    (mensaje.adjuntos || []).forEach(function (adjunto) {
      if (adjunto.tipo === "imagen") {
        const enlace = document.createElement("a");
        enlace.href = adjunto.url; enlace.target = "_blank"; enlace.rel = "noopener"; enlace.className = "rk-adjunto-imagen";
        const img = document.createElement("img");
        img.src = adjunto.url; img.alt = "Foto enviada: " + adjunto.nombre; img.loading = "lazy";
        enlace.appendChild(img);
        burbuja.appendChild(enlace);
      } else if (adjunto.tipo === "audio") {
        const audio = document.createElement("audio");
        audio.controls = true; audio.preload = "none"; audio.src = adjunto.url; audio.className = "rk-adjunto-audio";
        audio.setAttribute("aria-label", "Nota de voz");
        burbuja.appendChild(audio);
      } else {
        const enlace = document.createElement("a");
        enlace.href = adjunto.url; enlace.className = "rk-adjunto-doc";
        enlace.textContent = "📄 " + adjunto.nombre + " (" + adjunto.tamano + ")";
        burbuja.appendChild(enlace);
      }
    });
    if (mensaje.contenido) texto("", mensaje.contenido);
    texto("rk-msg-fecha", mensaje.fecha);
    fila.appendChild(burbuja);
    lista.appendChild(fila);
  }

  let temporizador = null;

  async function revisar() {
    clearTimeout(temporizador);
    if (!document.hidden) {
      try {
        const respuesta = await fetch(url + "?desde=" + ultimo, { credentials: "same-origin" });
        if (respuesta.ok) {
          const datos = await respuesta.json();
          if (datos.mensajes.length) {
            const bajar = cercaDelFinal();
            datos.mensajes.forEach(agregar);
            ultimo = datos.mensajes[datos.mensajes.length - 1].id;
            if (bajar) lista.scrollTop = lista.scrollHeight;
          }
        }
      } catch (e) {
        /* sin conexión: se reintenta */
      }
    }
    temporizador = setTimeout(revisar, INTERVALO);
  }
  // Al volver a la pestaña se revisa de inmediato (mientras estuvo oculta no se consultó).
  document.addEventListener("visibilitychange", function () { if (!document.hidden) revisar(); });
  lista.scrollTop = lista.scrollHeight;
  temporizador = setTimeout(revisar, INTERVALO);
})();
