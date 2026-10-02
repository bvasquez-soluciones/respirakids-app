/* Pantalla "Conectando con un profesional...": consulta el estado de la solicitud cada pocos segundos y
   recarga la página cuando un profesional la acepta (o si se cancela). */
(function () {
  "use strict";
  const contenedor = document.querySelector("[data-estado-url]");
  if (!contenedor) return;
  const url = contenedor.getAttribute("data-estado-url");

  async function revisar() {
    try {
      const respuesta = await fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (respuesta.ok) {
        const datos = await respuesta.json();
        if (datos.estado !== "pendiente") {
          window.location.reload();
          return;
        }
      }
    } catch (e) {
      /* sin conexión: se reintenta en la próxima vuelta */
    }
    setTimeout(revisar, 8000);
  }
  setTimeout(revisar, 8000);
})();
