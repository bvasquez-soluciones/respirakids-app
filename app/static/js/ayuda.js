/* Manual de uso: buscador de preguntas, explorador del semáforo e impresión con todo desplegado.
   Sin JavaScript la guía sigue completa: todas las preguntas se pueden abrir y el semáforo muestra el primer nivel. */
(function () {
  "use strict";

  // ---------------------------------------------------------------- Buscador
  const buscador = document.getElementById("buscar-ayuda");
  const preguntas = Array.prototype.slice.call(document.querySelectorAll(".rk-pregunta"));
  const temas = document.querySelectorAll("[data-tema]");
  const sinResultados = document.getElementById("sin-resultados");
  const resultado = document.getElementById("resultado-busqueda");
  // Mientras se busca, las secciones de presentación se ocultan para que las respuestas queden bajo el buscador.
  const secciones = document.querySelectorAll("[data-seccion]");

  // Quita tildes para que «fiebre» encuentre «Fiebre» y «contrasena» encuentre «contraseña».
  function normalizar(texto) {
    return texto.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }
  preguntas.forEach(function (p) {
    p.dataset.indice = normalizar(p.getAttribute("data-buscar") + " " + p.textContent);
  });

  function filtrar() {
    const consulta = normalizar(buscador.value.trim());
    const palabras = consulta.split(/\s+/).filter(Boolean);
    let visibles = 0;
    preguntas.forEach(function (p) {
      const coincide = palabras.every(function (w) { return p.dataset.indice.indexOf(w) !== -1; });
      p.hidden = !coincide;
      if (coincide) visibles++;
      // Al buscar se abren las coincidencias para leer la respuesta sin un toque más.
      if (palabras.length) p.open = coincide;
    });
    temas.forEach(function (t) { t.hidden = !t.querySelector(".rk-pregunta:not([hidden])"); });
    secciones.forEach(function (s) { s.hidden = palabras.length > 0; });
    sinResultados.hidden = visibles !== 0;
    resultado.textContent = !palabras.length ? ""
      : visibles === 0 ? "Sin resultados."
      : visibles + (visibles === 1 ? " respuesta encontrada." : " respuestas encontradas.");
  }

  if (buscador) {
    let espera;
    buscador.addEventListener("input", function () { clearTimeout(espera); espera = setTimeout(filtrar, 150); });
    buscador.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { buscador.value = ""; filtrar(); preguntas.forEach(function (p) { p.open = false; }); }
    });
  }

  // Un enlace con #pregunta abre esa respuesta.
  function abrirAncla() {
    const destino = location.hash && document.getElementById(location.hash.slice(1));
    if (destino && destino.tagName === "DETAILS") destino.open = true;
  }
  window.addEventListener("hashchange", abrirAncla);
  abrirAncla();

  // ---------------------------------------------------------------- Explorador del semáforo (pestañas accesibles)
  document.querySelectorAll("[data-explorador]").forEach(function (explorador) {
    const pestanas = Array.prototype.slice.call(explorador.querySelectorAll("[role=tab]"));

    function seleccionar(pestana, enfocar) {
      pestanas.forEach(function (p) {
        const activa = p === pestana;
        p.setAttribute("aria-selected", activa ? "true" : "false");
        p.tabIndex = activa ? 0 : -1;
        document.getElementById(p.getAttribute("aria-controls")).hidden = !activa;
      });
      if (enfocar) pestana.focus();
    }

    pestanas.forEach(function (p, i) {
      p.tabIndex = i === 0 ? 0 : -1;
      p.addEventListener("click", function () { seleccionar(p, false); });
      p.addEventListener("keydown", function (e) {
        let j = null;
        if (e.key === "ArrowRight") j = (i + 1) % pestanas.length;
        else if (e.key === "ArrowLeft") j = (i - 1 + pestanas.length) % pestanas.length;
        else if (e.key === "Home") j = 0;
        else if (e.key === "End") j = pestanas.length - 1;
        if (j !== null) { e.preventDefault(); seleccionar(pestanas[j], true); }
      });
    });
  });

  // ---------------------------------------------------------------- Impresión
  let abiertas = [];
  window.addEventListener("beforeprint", function () {
    abiertas = preguntas.filter(function (p) { return p.open; });
    preguntas.forEach(function (p) { p.open = true; });
  });
  window.addEventListener("afterprint", function () {
    preguntas.forEach(function (p) { p.open = abiertas.indexOf(p) !== -1; });
  });
  document.querySelectorAll("[data-imprimir]").forEach(function (b) {
    b.addEventListener("click", function () { window.print(); });
  });
})();
