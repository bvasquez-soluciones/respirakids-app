/* Reportes del profesional: distribución por nivel y síntomas más reportados.
   Datos en <script id="datos-reportes" type="application/json">. Requiere graficos.js. */
(function () {
  "use strict";
  const fuente = document.getElementById("datos-reportes");
  if (!fuente || !window.RespiraGraficos) return;
  const datos = JSON.parse(fuente.textContent);

  RespiraGraficos.crear(document.getElementById("grafico-riesgo"), function (c) {
    return {
      type: "doughnut",
      data: {
        labels: datos.niveles.map((n) => n.nombre),
        datasets: [{
          data: datos.niveles.map((n) => n.total),
          backgroundColor: datos.niveles.map((n) => c.nivel[n.nivel]),
          borderColor: c.superficie,
          borderWidth: 3,
          hoverOffset: 6,
        }],
      },
      options: {
        cutout: "62%",
        plugins: { legend: { position: "bottom" } },
      },
    };
  });

  if (datos.sintomas.length) {
    RespiraGraficos.crear(document.getElementById("grafico-sintomas"), function (c) {
      return {
        type: "bar",
        data: {
          labels: datos.sintomas.map((s) => s.etiqueta),
          datasets: [{
            label: "Registros",
            data: datos.sintomas.map((s) => s.total),
            backgroundColor: c.primario,
            borderRadius: 6,
            maxBarThickness: 22,
          }],
        },
        options: {
          indexAxis: "y",
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { stepSize: 1, precision: 0 }, grid: { color: c.borde } },
            y: { grid: { display: false }, ticks: { color: c.secundario } },
          },
        },
      };
    });
  }
})();
