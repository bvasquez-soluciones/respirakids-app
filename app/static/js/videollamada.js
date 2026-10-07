/* Videollamada (WebRTC). El video va directo y cifrado entre los dos navegadores; el servidor solo intercambia
   los mensajes para conectarlos (oferta, respuesta y candidatos de red), que se consultan cada segundo.
   - El profesional llama: cuando el cuidador contesta, crea la oferta.
   - El cuidador responde a la oferta.
   - Salir de la página cuelga la llamada. Nada se graba. */
(function () {
  "use strict";
  const raiz = document.getElementById("videollamada");
  if (!raiz) return;

  const rol = raiz.dataset.rol;
  const urlEstado = raiz.dataset.estadoUrl;
  const urlSenal = raiz.dataset.senalUrl;
  const urlColgar = raiz.dataset.colgarUrl;
  const volver = raiz.dataset.volver;
  const csrf = raiz.dataset.csrf;
  let servidoresIce = [];
  try { servidoresIce = JSON.parse(raiz.dataset.ice || "[]"); } catch (e) { servidoresIce = []; }

  let estado = raiz.dataset.estado;
  const esperaEntrante = rol === "cuidador" && estado === "llamando";

  // ---------------------------------------------------------------- Llamada entrante (pantalla de consentimiento)
  // Si el profesional cancela mientras el cuidador decide, la pantalla se actualiza sola.
  if (esperaEntrante) {
    const vigilar = async function () {
      try {
        const r = await fetch(urlEstado, { credentials: "same-origin" });
        if (r.ok && (await r.json()).estado !== "llamando") { window.location.reload(); return; }
      } catch (e) { /* se reintenta */ }
      setTimeout(vigilar, 2000);
    };
    setTimeout(vigilar, 2000);
    return;
  }

  const videoLocal = document.getElementById("video-local");
  const videoRemoto = document.getElementById("video-remoto");
  const espera = document.getElementById("video-espera");
  const textoEstado = document.getElementById("video-estado");
  const tiempo = document.getElementById("video-tiempo");
  const boton = function (accion) { return raiz.querySelector('[data-accion="' + accion + '"]'); };

  let medios = null;
  let conexion = null;
  let desde = 0;
  let pendientes = [];       // candidatos que llegan antes de la descripción remota
  let terminado = false;
  let conectadoDesde = null;
  let camaraFrontal = true;
  let consulta = null;
  let reintentos = 0;
  const REINTENTOS_MAXIMOS = 2;
  const botonReproducir = document.getElementById("video-reproducir");

  function mostrarEstado(texto) { if (textoEstado) textoEstado.textContent = texto; }

  async function enviar(tipo, datos) {
    try {
      await fetch(urlSenal, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ tipo: tipo, datos: datos }),
      });
    } catch (e) { /* la consulta siguiente detecta si la llamada terminó */ }
  }

  // ---------------------------------------------------------------- Cámara y micrófono
  async function abrirMedios() {
    const video = { facingMode: camaraFrontal ? "user" : "environment", width: { ideal: 1280 }, height: { ideal: 720 } };
    try {
      medios = await navigator.mediaDevices.getUserMedia({ video: video, audio: true });
    } catch (error) {
      // Sin cámara (o sin permiso para ella): se intenta solo con audio.
      try {
        medios = await navigator.mediaDevices.getUserMedia({ audio: true });
        boton("camara").disabled = true;
        mostrarEstado("Sin cámara: la llamada sigue solo con audio.");
      } catch (e) {
        mostrarEstado("No pudimos usar tu cámara ni tu micrófono. Revisa los permisos del navegador y vuelve a intentarlo.");
        throw e;
      }
    }
    videoLocal.srcObject = medios;
    // El botón para cambiar de cámara solo tiene sentido si hay más de una (celulares).
    try {
      const dispositivos = await navigator.mediaDevices.enumerateDevices();
      boton("voltear").hidden = dispositivos.filter(function (d) { return d.kind === "videoinput"; }).length < 2;
    } catch (e) { /* sin lista de dispositivos */ }
  }

  // ---------------------------------------------------------------- Conexión entre los dos dispositivos
  function crearConexion() {
    if (conexion) conexion.close();
    // Los candidatos pendientes se conservan: pueden haber llegado antes que la oferta.
    conexion = new RTCPeerConnection({ iceServers: servidoresIce });
    medios.getTracks().forEach(function (pista) { conexion.addTrack(pista, medios); });
    conexion.ontrack = function (evento) {
      if (videoRemoto.srcObject !== evento.streams[0]) {
        videoRemoto.srcObject = evento.streams[0];
        reproducir();
      }
    };
    conexion.onicecandidate = function (evento) {
      if (evento.candidate) enviar("candidato", evento.candidate.toJSON());
    };
    conexion.onconnectionstatechange = function () {
      const s = conexion.connectionState;
      if (s === "connected") {
        espera.hidden = true;
        raiz.classList.add("rk-video--conectada");
        if (!conectadoDesde) { conectadoDesde = Date.now(); tiempo.hidden = false; }
        vigilarImagen();
      } else if (s === "disconnected") {
        espera.hidden = false;
        mostrarEstado("Conexión inestable… intentando recuperar.");
      } else if (s === "failed") {
        espera.hidden = false;
        if (!reconectar()) mostrarEstado("No fue posible conectar el video en esta red. Puedes seguir por mensajes.");
      }
    };
  }

  // Algunos navegadores no reproducen video con sonido sin un toque del usuario: se ofrece un botón.
  function reproducir() {
    const intento = videoRemoto.play();
    if (intento && intento.catch) {
      intento.then(function () { botonReproducir.hidden = true; })
        .catch(function () { botonReproducir.hidden = false; });
    }
  }
  botonReproducir.addEventListener("click", function () { botonReproducir.hidden = true; reproducir(); });

  // El profesional vuelve a negociar la conexión si falla o si, ya conectada, no llega imagen.
  function reconectar() {
    if (rol !== "profesional" || terminado || reintentos >= REINTENTOS_MAXIMOS) return false;
    reintentos += 1;
    mostrarEstado("Reconectando…");
    llamar();
    return true;
  }

  function vigilarImagen() {
    setTimeout(function () {
      const pistaVideo = videoRemoto.srcObject && videoRemoto.srcObject.getVideoTracks()[0];
      // Hay pista de video pero no llega imagen (ancho 0) aunque la conexión diga "conectada": se renegocia.
      // Sin pista de video (la otra persona no tiene cámara) la llamada sigue solo con audio.
      if (!terminado && pistaVideo && videoRemoto.videoWidth === 0) reconectar();
    }, 8000);
  }

  async function aplicarPendientes() {
    for (const c of pendientes) { try { await conexion.addIceCandidate(c); } catch (e) { /* candidato viejo */ } }
    pendientes = [];
  }

  async function llamar() {  // profesional
    crearConexion();
    const oferta = await conexion.createOffer();
    await conexion.setLocalDescription(oferta);
    enviar("oferta", { type: conexion.localDescription.type, sdp: conexion.localDescription.sdp });
    mostrarEstado("Conectando…");
  }

  async function procesar(senal) {
    if (senal.tipo === "oferta" && rol === "cuidador") {
      crearConexion();
      await conexion.setRemoteDescription(senal.datos);
      await aplicarPendientes();
      const respuesta = await conexion.createAnswer();
      await conexion.setLocalDescription(respuesta);
      enviar("respuesta", { type: conexion.localDescription.type, sdp: conexion.localDescription.sdp });
      mostrarEstado("Conectando…");
    } else if (senal.tipo === "respuesta" && rol === "profesional" && conexion
               && conexion.signalingState === "have-local-offer") {
      await conexion.setRemoteDescription(senal.datos);
      await aplicarPendientes();
    } else if (senal.tipo === "candidato") {
      if (conexion && conexion.remoteDescription) {
        try { await conexion.addIceCandidate(senal.datos); } catch (e) { /* candidato no válido */ }
      } else {
        pendientes.push(senal.datos);
      }
    }
  }

  // ---------------------------------------------------------------- Consulta del estado y las señales
  async function revisar() {
    consulta = null;
    if (terminado) return;
    try {
      const r = await fetch(urlEstado + "?desde=" + desde, { credentials: "same-origin" });
      if (r.ok) {
        const datos = await r.json();
        const anterior = estado;
        estado = datos.estado;
        if (estado !== "llamando" && estado !== "en_curso") { finalizar(); return; }
        if (rol === "profesional" && anterior === "llamando" && estado === "en_curso") await llamar();
        for (const s of datos.senales) { desde = Math.max(desde, s.id); await procesar(s); }
      }
    } catch (e) { /* sin conexión momentánea: se reintenta */ }
    const conectada = conexion && conexion.connectionState === "connected";
    consulta = setTimeout(revisar, conectada ? 3000 : 1000);
  }

  // ---------------------------------------------------------------- Fin de la llamada
  function soltarMedios() {
    if (medios) medios.getTracks().forEach(function (p) { p.stop(); });
    if (conexion) conexion.close();
  }

  function finalizar() {
    if (terminado) return;
    terminado = true;
    clearTimeout(consulta);
    soltarMedios();
    window.location.reload();  // el servidor muestra cómo terminó y la duración
  }

  async function colgar() {
    if (terminado) return;
    terminado = true;
    clearTimeout(consulta);
    soltarMedios();
    try {
      await fetch(urlColgar, { method: "POST", credentials: "same-origin",
        headers: { "X-CSRFToken": csrf, Accept: "application/json" } });
    } catch (e) { /* la llamada se cierra sola por falta de señal */ }
    window.location.href = volver;
  }

  // Cerrar la pestaña o salir de la página también cuelga (sendBeacon sobrevive a la navegación).
  window.addEventListener("pagehide", function () {
    if (terminado) return;
    const cuerpo = new FormData();
    cuerpo.append("csrf_token", csrf);
    navigator.sendBeacon(urlColgar, cuerpo);
  });

  // ---------------------------------------------------------------- Controles
  function alternar(accion, pistas, etiquetaApagar, etiquetaEncender) {
    const b = boton(accion);
    const apagado = b.getAttribute("aria-pressed") !== "true";
    pistas.forEach(function (p) { p.enabled = !apagado; });
    b.setAttribute("aria-pressed", apagado ? "true" : "false");
    b.setAttribute("aria-label", apagado ? etiquetaEncender : etiquetaApagar);
    b.querySelector("[data-icono-encendido]").hidden = apagado;
    b.querySelector("[data-icono-apagado]").hidden = !apagado;
  }

  boton("microfono").addEventListener("click", function () {
    if (medios) alternar("microfono", medios.getAudioTracks(), "Silenciar micrófono", "Activar micrófono");
  });
  boton("camara").addEventListener("click", function () {
    if (medios) alternar("camara", medios.getVideoTracks(), "Apagar cámara", "Encender cámara");
  });
  boton("voltear").addEventListener("click", async function () {
    camaraFrontal = !camaraFrontal;
    try {
      const nuevo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: camaraFrontal ? "user" : "environment" } });
      const pista = nuevo.getVideoTracks()[0];
      const anterior = medios.getVideoTracks()[0];
      if (conexion) {
        const emisor = conexion.getSenders().find(function (s) { return s.track && s.track.kind === "video"; });
        if (emisor) await emisor.replaceTrack(pista);
      }
      if (anterior) { medios.removeTrack(anterior); anterior.stop(); }
      medios.addTrack(pista);
      videoLocal.srcObject = medios;
    } catch (e) { camaraFrontal = !camaraFrontal; }
  });
  boton("colgar").addEventListener("click", colgar);

  setInterval(function () {
    if (!conectadoDesde) return;
    const s = Math.floor((Date.now() - conectadoDesde) / 1000);
    tiempo.textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
  }, 1000);

  // ---------------------------------------------------------------- Inicio
  (async function () {
    if (!window.RTCPeerConnection || !navigator.mediaDevices) {
      mostrarEstado("Este navegador no permite videollamadas. Actualízalo o usa Chrome, Edge, Firefox o Safari recientes.");
      return;
    }
    try { await abrirMedios(); } catch (e) { return; }
    if (rol === "profesional" && estado === "en_curso") await llamar();  // la página se abrió con la llamada ya aceptada
    revisar();
  })();
})();
