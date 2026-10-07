/* Panel profesional: búsqueda y filtro de pacientes por nivel, y cambio de periodo del gráfico. */
(function () {
  "use strict";
  const selectRango = document.getElementById("select-rango");
  if (selectRango) {
    selectRango.addEventListener("change", () => {
      const params = new URLSearchParams(window.location.search);
      params.set("rango", selectRango.value);
      window.location.search = params.toString();
    });
  }

  document.getElementById("btn-toggle-search").addEventListener("click", () => {
    const abierto = document.getElementById("search-bar").classList.toggle("rk-search-open");
    document.getElementById("btn-toggle-search").setAttribute("aria-expanded", String(abierto));
    if (abierto) document.getElementById("input-buscar-paciente").focus();
  });
  document.getElementById("btn-toggle-filter").addEventListener("click", () => {
    const abierto = document.getElementById("filter-bar").classList.toggle("rk-filter-open");
    document.getElementById("btn-toggle-filter").setAttribute("aria-expanded", String(abierto));
  });

  const tarjetas = document.querySelectorAll(".rk-patient-card");
  const noResults = document.getElementById("no-results");
  let filtroActivo = "todos";

  function aplicarFiltros() {
    const q = document
      .getElementById("input-buscar-paciente")
      .value.trim()
      .toLowerCase();
    let visibles = 0;
    tarjetas.forEach((card) => {
      const nombre = card.dataset.nombre || "";
      const coincideTexto = nombre.includes(q);
      const coincideFiltro =
        filtroActivo === "todos" ||
        (filtroActivo === "mios" ? card.dataset.mio === "si" : card.dataset.riesgo === filtroActivo);
      const visible = coincideTexto && coincideFiltro;
      card.classList.toggle("rk-hidden", !visible);
      if (visible) visibles++;
    });
    noResults.hidden = visibles !== 0;
  }

  document
    .getElementById("input-buscar-paciente")
    .addEventListener("input", aplicarFiltros);
  document.querySelectorAll(".rk-filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document
        .querySelectorAll(".rk-filter-chip")
        .forEach((c) => { c.classList.remove("active"); c.setAttribute("aria-pressed", "false"); });
      chip.classList.add("active");
      chip.setAttribute("aria-pressed", "true");
      filtroActivo = chip.dataset.filtro;
      aplicarFiltros();
    });
  });
})();
