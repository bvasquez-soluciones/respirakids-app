/* Adjuntar fotos o PDF y grabar notas de voz en una conversación.
   - La nota de voz se graba con MediaRecorder (requiere HTTPS y permiso del micrófono) y dura máximo 2 minutos.
   - El archivo se valida otra vez en el servidor (services/adjuntos.py): aquí solo se orienta al usuario. */
(function () {
  "use strict";
  const form = document.getElementById("form-mensaje");
  if (!form) return;
  const entrada = document.getElementById("adjunto-archivo");
  const vista = document.getElementById("adjunto-vista");
  const nombre = document.getElementById("adjunto-nombre");
  const audioVista = document.getElementById("adjunto-audio");
  const quitar = document.getElementById("adjunto-quitar");
  const grabar = document.getElementById("btn-grabar");
  const estado = document.getElementById("estado-grabacion");
  const maxBytes = parseFloat(form.getAttribute("data-max-mb") || "5") * 1024 * 1024;
  const DURACION_MAXIMA = 120; // segundos
  let notaDeVoz = null;
  let grabador = null;
  let cronometro = null;

  function limpiar() {
    entrada.value = "";
    notaDeVoz = null;
    audioVista.hidden = true;
    audioVista.removeAttribute("src");
    nombre.textContent = "";
    vista.hidden = true;
  }

  entrada.addEventListener("change", function () {
    const archivo = entrada.files[0];
    if (!archivo) return limpiar();
    if (archivo.size > maxBytes) {
      window.alert("El archivo no puede superar " + (maxBytes / 1024 / 1024) + " MB.");
      return limpiar();
    }
    notaDeVoz = null;
    audioVista.hidden = true;
    nombre.textContent = "📎 " + archivo.name;
    vista.hidden = false;
  });
  quitar.addEventListener("click", limpiar);

  // Notas de voz: solo si el navegador puede grabar.
  if (window.MediaRecorder && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    grabar.hidden = false;
    grabar.addEventListener("click", async function () {
      if (grabador && grabador.state === "recording") { grabador.stop(); return; }
      let flujo;
      try {
        flujo = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        window.alert("No se pudo usar el micrófono. Revisa el permiso del navegador.");
        return;
      }
      const partes = [];
      grabador = new MediaRecorder(flujo);
      grabador.addEventListener("dataavailable", function (e) { if (e.data.size) partes.push(e.data); });
      grabador.addEventListener("stop", function () {
        flujo.getTracks().forEach(function (pista) { pista.stop(); });
        clearInterval(cronometro);
        grabar.setAttribute("aria-pressed", "false");
        grabar.classList.remove("is-grabando");
        estado.hidden = true;
        notaDeVoz = new Blob(partes, { type: grabador.mimeType || "audio/webm" });
        entrada.value = "";
        nombre.textContent = "🎤 Nota de voz";
        audioVista.src = URL.createObjectURL(notaDeVoz);
        audioVista.hidden = false;
        vista.hidden = false;
      });
      grabador.start();
      grabar.setAttribute("aria-pressed", "true");
      grabar.classList.add("is-grabando");
      let segundos = 0;
      estado.hidden = false;
      estado.textContent = "● Grabando… 0:00 (toca el micrófono para terminar)";
      cronometro = setInterval(function () {
        segundos += 1;
        estado.textContent = "● Grabando… " + Math.floor(segundos / 60) + ":" + String(segundos % 60).padStart(2, "0") +
          " (toca el micrófono para terminar)";
        if (segundos >= DURACION_MAXIMA) grabador.stop();
      }, 1000);
    });
  }

  // Con nota de voz, el formulario se envía con fetch para incluir la grabación.
  form.addEventListener("submit", async function (evento) {
    if (!notaDeVoz) return;
    evento.preventDefault();
    const datos = new FormData(form);
    const extension = (notaDeVoz.type.indexOf("mp4") >= 0) ? "m4a" : (notaDeVoz.type.indexOf("ogg") >= 0 ? "ogg" : "webm");
    datos.set("adjunto", notaDeVoz, "nota-de-voz." + extension);
    try {
      await fetch(form.action || window.location.href, { method: "POST", body: datos, credentials: "same-origin" });
    } finally {
      window.location.reload();
    }
  });
})();
