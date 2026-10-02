/* Guía interactiva para cuidadores nuevos.
   Los pasos los decide el servidor (app/services/guia.py) según lo que el cuidador ya hizo; aquí solo se muestran:
   se oscurece la pantalla, se ilumina el elemento [data-guia] de cada paso y una burbuja explica qué hacer.
   El oscurecido es solo visual: la página sigue funcionando (se puede escribir y presionar botones). */
(function () {
  "use strict";
  const nodoDatos = document.getElementById("rk-guia-datos");
  if (!nodoDatos) return;
  let datos;
  try { datos = JSON.parse(nodoDatos.textContent); } catch (e) { return; }

  const CLAVE_OCULTA = "rk-guia-oculta-" + datos.usuario;
  const CLAVE_BIENVENIDA = "rk-guia-bienvenida-" + datos.usuario;
  const CLAVE_HECHA = "rk-guia-hecha-" + datos.usuario + "-" + datos.etapa;
  const reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function leer(clave) { try { return window.localStorage.getItem(clave); } catch (e) { return null; } }
  function guardar(clave) { try { window.localStorage.setItem(clave, "1"); } catch (e) { /* sin almacenamiento */ } }
  function borrar(clave) { try { window.localStorage.removeItem(clave); } catch (e) { /* sin almacenamiento */ } }

  if (datos.forzada) { borrar(CLAVE_OCULTA); borrar(CLAVE_HECHA); }
  if (leer(CLAVE_OCULTA) || leer(CLAVE_HECHA)) return;

  // Solo los pasos cuyo elemento está en la página y visible.
  function objetivoDe(paso) {
    let selector = '[data-guia="' + paso.objetivo + '"]';
    if (paso.nino) selector += '[data-guia-nino="' + paso.nino + '"]';
    return Array.prototype.find.call(document.querySelectorAll(selector), function (el) {
      return el.getClientRects().length > 0;
    }) || null;
  }
  const pasos = datos.pasos.map(function (p) { return Object.assign({}, p, { el: objetivoDe(p) }); })
    .filter(function (p) { return p.el; });
  if (!pasos.length) return;

  // ---------------------------------------------------------------- Elementos de la guía
  function crear(etiqueta, clase, texto) {
    const el = document.createElement(etiqueta);
    if (clase) el.className = clase;
    if (texto) el.textContent = texto;
    return el;
  }

  const foco = crear("div", "rk-guia-foco");
  foco.setAttribute("aria-hidden", "true");
  const burbuja = crear("div", "rk-guia-burbuja");
  burbuja.setAttribute("role", "dialog");
  burbuja.setAttribute("aria-labelledby", "rk-guia-titulo");
  burbuja.setAttribute("aria-describedby", "rk-guia-texto");
  const contador = crear("p", "rk-guia-burbuja__contador");
  const titulo = crear("h2", "rk-guia-burbuja__titulo");
  titulo.id = "rk-guia-titulo";
  titulo.tabIndex = -1;
  const texto = crear("p", "rk-guia-burbuja__texto");
  texto.id = "rk-guia-texto";
  const acciones = crear("div", "rk-guia-burbuja__acciones");
  const botonSaltar = crear("button", "btn btn-link btn-sm rk-guia-burbuja__saltar", "Saltar guía");
  const botonAnterior = crear("button", "btn btn-outline-secondary btn-sm", "Anterior");
  const botonSiguiente = crear("button", "btn btn-primary btn-sm", "Siguiente");
  const pista = crear("span", "rk-guia-burbuja__pista", "Presiona el botón iluminado 👆");
  [botonSaltar, botonAnterior, botonSiguiente].forEach(function (b) { b.type = "button"; });
  acciones.append(botonSaltar, botonAnterior, pista, botonSiguiente);
  burbuja.append(contador, titulo, texto, acciones);

  let indice = 0;
  let activo = false;

  function colocar() {
    if (!activo) return;
    const paso = pasos[indice];
    const r = paso.el.getBoundingClientRect();
    const margen = 8;
    const anchoVisible = document.documentElement.clientWidth;  // sin la barra de desplazamiento
    const altoVisible = document.documentElement.clientHeight;
    // El recuadro no se sale de la pantalla (p. ej. el último botón de la barra inferior).
    const izquierda = Math.max(2, r.left - margen);
    const derecha = Math.min(anchoVisible - 2, r.right + margen);
    foco.style.top = (r.top + window.scrollY - margen) + "px";
    foco.style.left = (izquierda + window.scrollX) + "px";
    foco.style.width = (derecha - izquierda) + "px";
    foco.style.height = (r.height + margen * 2) + "px";

    const celular = anchoVisible < 576;
    burbuja.classList.toggle("rk-guia-burbuja--celular", celular);
    if (celular) {
      // En el celular la burbuja va abajo; si el comienzo del elemento iluminado queda abajo, va arriba.
      const arriba = r.top > altoVisible * 0.5;
      burbuja.classList.toggle("rk-guia-burbuja--arriba", arriba);
      burbuja.style.top = burbuja.style.left = "";
      return;
    }
    const ancho = burbuja.offsetWidth;
    const alto = burbuja.offsetHeight;
    let top = r.bottom + 14;
    if (top + alto > altoVisible - 16 && r.top - alto - 14 > 16) top = r.top - alto - 14;
    top = Math.max(16, Math.min(top, altoVisible - alto - 16));
    // Centrada respecto al elemento, sin salirse de la pantalla.
    const left = Math.max(16, Math.min(r.left + r.width / 2 - ancho / 2, anchoVisible - ancho - 16));
    burbuja.style.top = top + "px";
    burbuja.style.left = left + "px";
  }

  let pendiente = false;
  function recolocar() {
    if (pendiente) return;
    pendiente = true;
    window.requestAnimationFrame(function () { pendiente = false; colocar(); });
  }

  function mostrar(i) {
    indice = i;
    const paso = pasos[i];
    contador.textContent = pasos.length > 1 ? "Paso " + (i + 1) + " de " + pasos.length : "";
    titulo.textContent = paso.titulo;
    texto.textContent = paso.texto;
    botonAnterior.hidden = i === 0;
    const ultimo = i === pasos.length - 1;
    botonSiguiente.hidden = paso.accion;
    botonSiguiente.textContent = ultimo ? "Terminar" : "Siguiente";
    pista.hidden = !paso.accion;
    foco.classList.toggle("rk-guia-foco--accion", paso.accion);
    // Elementos altos (p. ej. la autorización): se muestra su comienzo, donde está lo que hay que hacer.
    const r = paso.el.getBoundingClientRect();
    const altoVisible = document.documentElement.clientHeight;
    const destino = r.height > altoVisible * 0.45
      ? r.top + window.scrollY - 110
      : r.top + window.scrollY - (altoVisible - r.height) / 2;
    window.scrollTo({ top: Math.max(0, destino), behavior: reducirMovimiento ? "auto" : "smooth" });
    colocar();
    window.setTimeout(colocar, reducirMovimiento ? 0 : 350);
    titulo.focus({ preventScroll: true });
  }

  function cerrar() {
    activo = false;
    foco.remove();
    burbuja.remove();
    window.removeEventListener("resize", recolocar);
    window.removeEventListener("scroll", recolocar);
    document.removeEventListener("keydown", teclado);
  }

  function avisar(mensaje) {
    const aviso = document.getElementById("aviso-flotante");
    if (!aviso) return;
    aviso.textContent = mensaje;
    aviso.hidden = false;
    window.setTimeout(function () { aviso.hidden = true; }, 5000);
  }

  function teclado(e) {
    if (e.key === "Escape") { cerrar(); }
  }

  botonSiguiente.addEventListener("click", function () {
    if (indice < pasos.length - 1) { mostrar(indice + 1); return; }
    guardar(CLAVE_HECHA);
    cerrar();
  });
  botonAnterior.addEventListener("click", function () { if (indice > 0) mostrar(indice - 1); });
  botonSaltar.addEventListener("click", function () {
    guardar(CLAVE_OCULTA);
    cerrar();
    avisar("Guía cerrada. Puedes volver a verla en Ayuda.");
  });
  // Al presionar el elemento iluminado de un paso de acción, la guía se aparta (la página continúa sola).
  pasos.forEach(function (p) {
    if (p.accion) p.el.addEventListener("click", function () { if (activo) cerrar(); });
  });

  function iniciar() {
    activo = true;
    document.body.append(foco, burbuja);
    window.addEventListener("resize", recolocar);
    window.addEventListener("scroll", recolocar, { passive: true });
    document.addEventListener("keydown", teclado);
    mostrar(0);
  }

  // ---------------------------------------------------------------- Bienvenida (solo la primera vez)
  function bienvenida() {
    const fondo = crear("div", "rk-guia-bienvenida");
    const caja = crear("div", "rk-guia-bienvenida__caja");
    caja.setAttribute("role", "dialog");
    caja.setAttribute("aria-modal", "true");
    caja.setAttribute("aria-labelledby", "rk-guia-bienvenida-titulo");
    const t = crear("h2", "rk-guia-bienvenida__titulo", datos.bienvenida.titulo);
    t.id = "rk-guia-bienvenida-titulo";
    const p = crear("p", "rk-guia-bienvenida__texto", datos.bienvenida.texto);
    const fila = crear("div", "rk-guia-bienvenida__acciones");
    const comenzar = crear("button", "btn btn-primary", "Comenzar");
    const ahoraNo = crear("button", "btn btn-link", "Ahora no");
    comenzar.type = ahoraNo.type = "button";
    fila.append(ahoraNo, comenzar);
    caja.append(t, p, fila);
    fondo.append(caja);
    document.body.append(fondo);
    comenzar.focus();

    function quitar() { fondo.remove(); document.removeEventListener("keydown", tecladoBienvenida); }
    function tecladoBienvenida(e) {
      if (e.key === "Escape") { ahoraNo.click(); }
      if (e.key === "Tab") { // el foco no sale de la bienvenida
        e.preventDefault();
        (document.activeElement === comenzar ? ahoraNo : comenzar).focus();
      }
    }
    document.addEventListener("keydown", tecladoBienvenida);
    comenzar.addEventListener("click", function () { guardar(CLAVE_BIENVENIDA); quitar(); iniciar(); });
    ahoraNo.addEventListener("click", function () {
      guardar(CLAVE_BIENVENIDA);
      guardar(CLAVE_OCULTA);
      quitar();
      avisar("Cuando quieras, abre la guía desde Ayuda.");
    });
  }

  if (datos.bienvenida && !leer(CLAVE_BIENVENIDA)) bienvenida();
  else iniciar();
})();
