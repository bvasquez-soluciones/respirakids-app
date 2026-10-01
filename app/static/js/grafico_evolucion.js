/* Gráfico de evolución: nivel de riesgo (eje izquierdo) y temperatura (eje derecho).
   Uso: <canvas id="grafico-evolucion"> + <script id="datos-evolucion" type="application/json">{...}</script> */
(function () {
  const lienzo = document.getElementById("grafico-evolucion");
  const fuente = document.getElementById("datos-evolucion");
  if (!lienzo || !fuente || typeof Chart === "undefined") return;

  const datos = JSON.parse(fuente.textContent);
  const nombresNivel = { 1: "Verde", 2: "Amarillo", 3: "Rojo" };
  const coloresNivel = { 1: "#2f9e5b", 2: "#d39b00", 3: "#d64545" };

  new Chart(lienzo, {
    type: "line",
    data: {
      labels: datos.etiquetas,
      datasets: [
        {
          label: "Nivel de riesgo", data: datos.niveles, yAxisID: "nivel", stepped: true,
          borderColor: "#1b4b43", pointRadius: 5, spanGaps: true,
          pointBackgroundColor: datos.niveles.map((n) => coloresNivel[n] || "#8a96a3"),
        },
        {
          label: "Temperatura (°C)", data: datos.temperaturas, yAxisID: "temperatura",
          borderColor: "#f2765a", borderDash: [5, 4], pointRadius: 3, spanGaps: true,
        },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: {
        nivel: {
          type: "linear", position: "left", min: 0.5, max: 3.5,
          title: { display: true, text: "Nivel de riesgo" },
          // Una marca por nivel (1 = Verde, 2 = Amarillo, 3 = Rojo).
          afterBuildTicks: (eje) => { eje.ticks = [1, 2, 3].map((value) => ({ value })); },
          ticks: { callback: (v) => nombresNivel[v] || "" },
        },
        temperatura: {
          type: "linear", position: "right", suggestedMin: 36, suggestedMax: 40,
          title: { display: true, text: "Temperatura (°C)" }, grid: { drawOnChartArea: false },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (c) => c.dataset.yAxisID === "nivel"
              ? "Nivel: " + (nombresNivel[c.parsed.y] || "sin evaluación")
              : "Temperatura: " + c.parsed.y + " °C",
          },
        },
      },
    },
  });
})();
