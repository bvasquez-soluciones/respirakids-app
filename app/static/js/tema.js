/* Aplica el tema guardado (oscuro por defecto) antes de pintar la página.
   Se carga sin defer en <head>; el cambio de tema lo maneja app.js. */
(function () {
  var guardado = null;
  try {
    guardado = window.localStorage.getItem("rk-tema");
  } catch (e) {
    /* almacenamiento bloqueado: se usa el tema por defecto */
  }
  var tema = guardado === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", tema);
  document.documentElement.setAttribute("data-bs-theme", tema);
})();
