/* Comportamientos comunes de RespiraKids. Sin JS en línea: las plantillas declaran la intención con
   atributos data-* y este archivo la implementa (permite una CSP sin 'unsafe-inline').

   data-cambiar-tema           botón que alterna tema oscuro / claro
   data-mostrar-password="id"  botón que muestra u oculta la contraseña del campo indicado
   data-confirmar="texto"      formulario que pide confirmación antes de enviarse
   data-autoenviar             select que envía su formulario al cambiar
   data-limpiar="campo"        (con data-autoenviar) campo del formulario que se vacía antes de enviar
   data-enfocar                elemento que recibe el foco al cargar (p. ej. resumen de errores) */
(function () {
  "use strict";

  var COLOR_BARRA = { dark: "#0a1220", light: "#f2f6fa" };

  function aplicarTema(tema) {
    var raiz = document.documentElement;
    raiz.setAttribute("data-theme", tema);
    raiz.setAttribute("data-bs-theme", tema);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", COLOR_BARRA[tema]);
    try {
      window.localStorage.setItem("rk-tema", tema);
    } catch (e) {
      /* sin almacenamiento: el cambio dura hasta recargar */
    }
    document.dispatchEvent(new CustomEvent("rk:tema", { detail: tema }));
  }

  document.addEventListener("DOMContentLoaded", function () {
    var temaActual = document.documentElement.getAttribute("data-theme");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", COLOR_BARRA[temaActual] || COLOR_BARRA.dark);

    document.querySelectorAll("[data-cambiar-tema]").forEach(function (boton) {
      boton.setAttribute("aria-pressed", String(temaActual === "light"));
      boton.addEventListener("click", function () {
        var nuevo = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
        aplicarTema(nuevo);
        boton.setAttribute("aria-pressed", String(nuevo === "light"));
      });
    });

    document.querySelectorAll("[data-mostrar-password]").forEach(function (boton) {
      boton.addEventListener("click", function () {
        var campo = document.getElementById(boton.getAttribute("data-mostrar-password"));
        if (!campo) return;
        var mostrar = campo.type === "password";
        campo.type = mostrar ? "text" : "password";
        boton.setAttribute("aria-pressed", String(mostrar));
        boton.setAttribute("aria-label", mostrar ? "Ocultar contraseña" : "Mostrar contraseña");
      });
    });

    document.querySelectorAll("form[data-confirmar]").forEach(function (formulario) {
      formulario.addEventListener("submit", function (evento) {
        if (!window.confirm(formulario.getAttribute("data-confirmar"))) evento.preventDefault();
      });
    });

    document.querySelectorAll("select[data-autoenviar]").forEach(function (lista) {
      lista.addEventListener("change", function () {
        var limpiar = lista.getAttribute("data-limpiar");
        if (limpiar && lista.form.elements[limpiar]) lista.form.elements[limpiar].value = "";
        lista.form.submit();
      });
    });

    var enfocar = document.querySelector("[data-enfocar]");
    if (enfocar) enfocar.focus();
  });
})();
