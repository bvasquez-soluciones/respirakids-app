/* Gráfico de evolución: nivel de riesgo (eje izquierdo) y temperatura (eje derecho).
   Uso: <canvas id="grafico-evolucion"> + <script id="datos-evolucion" type="application/json">{...}</script>.
   Requiere graficos.js (colores del tema). */
(function () {
  "use strict";
  const lienzo = document.getElementById("grafico-evolucion");
  const fuente = document.getElementById("datos-evolucion");
  if (!lienzo || !fuente || !window.RespiraGraficos) return;

  const datos = JSON.parse(fuente.textContent);
  const nombresNivel = { 1: "Verde", 2: "Amarillo", 3: "Rojo" };
  const claveNivel = { 1: "verde", 2: "amarillo", 3: "rojo" };
  // Forma del punto según el nivel (además del color): círculo, triángulo, cuadrado girado.
  const formaNivel = { 1: "circle", 2: "triangle", 3: "rectRot" };

  RespiraGraficos.crear(lienzo, function (c) {
    const colorNivel = (n) => c.nivel[claveNivel[n]] || c.nivel.neutro;
    return {
      type: "line",
      data: {
        labels: datos.etiquetas,
        datasets: [
          {
            label: "Nivel de riesgo", data: datos.niveles, yAxisID: "nivel", stepped: true, spanGaps: true,
            borderColor: c.secundario, borderWidth: 2,
            pointRadius: 6, pointHoverRadius: 8,
            pointStyle: datos.niveles.map((n) => formaNivel[n] || "circle"),
            pointBackgroundColor: datos.niveles.map(colorNivel),
            pointBorderColor: c.superficie, pointBorderWidth: 2,
          },
          {
            label: "Temperatura (°C)", data: datos.temperaturas, yAxisID: "temperatura", spanGaps: true,
            borderColor: c.primario, backgroundColor: c.primario,
            borderDash: [5, 4], borderWidth: 2, pointRadius: 3,
          },
        ],
      },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { color: c.borde } },
          nivel: {
            type: "linear", position: "left", min: 0.5, max: 3.5,
            title: { display: true, text: "Nivel de riesgo" },
            grid: { color: c.borde },
            // Una marca por nivel (1 = Verde, 2 = Amarillo, 3 = Rojo).
            afterBuildTicks: (eje) => { eje.ticks = [1, 2, 3].map((value) => ({ value })); },
            ticks: { callback: (v) => nombresNivel[v] || "", color: c.secundario },
          },
          temperatura: {
            type: "linear", position: "right", suggestedMin: 36, suggestedMax: 40,
            title: { display: true, text: "Temperatura (°C)" }, grid: { drawOnChartArea: false },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => ctx.dataset.yAxisID === "nivel"
                ? "Nivel: " + (nombresNivel[ctx.parsed.y] || "sin evaluación")
                : "Temperatura: " + ctx.parsed.y + " °C",
            },
          },
        },
      },
    };
  });
})();
