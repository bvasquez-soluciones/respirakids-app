/* Actualización sin recargar: contadores de la barra (notificaciones, alertas, solicitudes) cada 10 s, y el aviso
   de videollamada entrante para el cuidador (con vibración y un timbre suave si el navegador lo permite).
   - Se pausa con la pestaña oculta y se detiene tras 30 min sin actividad del usuario (no mantiene viva una
     sesión desatendida: el cierre por inactividad sigue funcionando).
   - Si llega algo nuevo muestra un aviso discreto; en "Solicitudes" recarga la lista cuando cambia. */
(function () {
  "use strict";
  const url = document.body.getAttribute("data-estado-url");
  if (!url) return;
  const pagina = document.body.getAttribute("data-pagina");
  const INTERVALO = 10000;
  const INACTIVIDAD_MAXIMA = 30 * 60 * 1000;
  let ultimaActividad = Date.now();
  let anterior = null;
  let temporizador = null;

  ["pointerdown", "keydown", "scroll", "touchstart"].forEach(function (evento) {
    window.addEventListener(evento, function () { ultimaActividad = Date.now(); }, { passive: true });
  });

  function pintar(nombre, valor) {
    document.querySelectorAll('[data-contador="' + nombre + '"]').forEach(function (enlace) {
      const clase = enlace.getAttribute("data-clase-contador") || "rk-bell-badge";
      let insignia = enlace.querySelector("." + clase);
      if (!valor) {
        if (insignia) insignia.remove();
        return;
      }
      if (!insignia) {
        insignia = document.createElement("span");
        insignia.className = clase;
        enlace.appendChild(insignia);
      }
      insignia.textContent = valor;
    });
  }

  function avisar(texto) {
    const aviso = document.getElementById("aviso-flotante");
    if (!aviso) return;
    aviso.textContent = texto;
    aviso.hidden = false;
    clearTimeout(aviso._ocultar);
    aviso._ocultar = setTimeout(function () { aviso.hidden = true; }, 6000);
  }

  // ---------------------------------------------------------------- Videollamada entrante (cuidador)
  const avisoLlamada = document.getElementById("llamada-entrante");
  let timbre = null;

  function sonar() {
    try {
      const Contexto = window.AudioContext || window.webkitAudioContext;
      if (!Contexto) return;
      const ctx = new Contexto();
      [0, 0.45].forEach(function (inicio) {
        const osc = ctx.createOscillator();
        const vol = ctx.createGain();
        osc.frequency.value = 660;
        vol.gain.setValueAtTime(0.0001, ctx.currentTime + inicio);
        vol.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + inicio + 0.05);
        vol.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + inicio + 0.35);
        osc.connect(vol).connect(ctx.destination);
        osc.start(ctx.currentTime + inicio);
        osc.stop(ctx.currentTime + inicio + 0.4);
      });
      setTimeout(function () { ctx.close(); }, 1200);
    } catch (e) { /* el navegador puede bloquear el sonido sin interacción previa */ }
    if (navigator.vibrate) navigator.vibrate([300, 150, 300]);
  }

  function llamadaEntrante(llamada) {
    if (!avisoLlamada || pagina === "videollamadas.sala") return;
    if (!llamada) {
      avisoLlamada.hidden = true;
      clearInterval(timbre);
      timbre = null;
      return;
    }
    document.getElementById("llamada-entrante-texto").textContent = "📹 " + llamada.texto;
    document.getElementById("llamada-entrante-ir").href = llamada.url;
    if (avisoLlamada.hidden) {
      avisoLlamada.hidden = false;
      sonar();
      timbre = setInterval(sonar, 3000);
    }
  }

  async function revisar() {
    temporizador = null;
    if (Date.now() - ultimaActividad > INACTIVIDAD_MAXIMA) return;  // se reanuda con la próxima actividad
    try {
      const respuesta = await fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (respuesta.ok) {
        const datos = await respuesta.json();
        pintar("notificaciones", datos.notificaciones);
        pintar("alertas", datos.alertas);
        pintar("solicitudes", datos.solicitudes);
        llamadaEntrante(datos.llamada);
        if (anterior) {
          if (datos.notificaciones > anterior.notificaciones) avisar("Tienes una notificación nueva.");
          if (datos.solicitudes > anterior.solicitudes) avisar("Llegó una nueva solicitud de atención.");
          if (pagina === "mensajes.solicitudes" && datos.solicitudes !== anterior.solicitudes) window.location.reload();
        }
        anterior = datos;
      }
    } catch (e) {
      /* sin conexión: se reintenta en la próxima vuelta */
    }
    programar();
  }

  function programar() {
    if (!temporizador && !document.hidden) temporizador = setTimeout(revisar, INTERVALO);
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) { clearTimeout(temporizador); temporizador = null; revisar(); }
  });
  ["pointerdown", "keydown"].forEach(function (evento) {
    window.addEventListener(evento, programar, { passive: true });
  });
  revisar();
})();
