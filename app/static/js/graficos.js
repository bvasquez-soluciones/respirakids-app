/* Gráficos de RespiraKids sobre Chart.js con los colores del sistema de diseño (tokens.css).
   Uso: RespiraGraficos.crear(lienzo, (c) => configuracion)  — `c` trae los colores del tema actual.
   Al cambiar de tema (evento rk:tema) los gráficos se reconstruyen con la nueva paleta. */
window.RespiraGraficos = (function () {
  "use strict";
  const graficos = [];

  function token(nombre) {
    return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
  }

  function colores() {
    return {
      texto: token("--rk-text"),
      secundario: token("--rk-text-2"),
      tenue: token("--rk-muted"),
      borde: token("--rk-border"),
      superficie: token("--rk-surface-solid"),
      primario: token("--rk-primary"),
      ia: token("--rk-ia"),
      nivel: {
        rojo: token("--rk-sem-rojo"),
        amarillo: token("--rk-sem-amarillo"),
        verde: token("--rk-sem-verde"),
        neutro: token("--rk-sem-neutro"),
      },
    };
  }

  function aplicarEstilosBase() {
    const c = colores();
    Chart.defaults.color = c.tenue;
    Chart.defaults.borderColor = c.borde;
    Chart.defaults.font.family = token("--rk-font") || "system-ui";
    Chart.defaults.font.size = 12;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.tooltip.backgroundColor = c.superficie;
    Chart.defaults.plugins.tooltip.titleColor = c.texto;
    Chart.defaults.plugins.tooltip.bodyColor = c.secundario;
    Chart.defaults.plugins.tooltip.borderColor = c.borde;
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 10;
  }

  function crear(lienzo, construir) {
    if (!lienzo || typeof Chart === "undefined") return null;
    aplicarEstilosBase();
    const grafico = new Chart(lienzo, construir(colores()));
    graficos.push({ grafico: grafico, construir: construir });
    return grafico;
  }

  document.addEventListener("rk:tema", function () {
    if (typeof Chart === "undefined") return;
    aplicarEstilosBase();
    graficos.forEach(function (item) {
      const config = item.construir(colores());
      item.grafico.data = config.data;
      item.grafico.options = config.options || {};
      item.grafico.update();
    });
  });

  return { crear: crear, colores: colores };
})();
