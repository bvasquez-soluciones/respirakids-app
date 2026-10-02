/* Registro de síntomas: aviso inmediato de signos de alarma y contador de respiraciones de 60 s. */
(function () {
  // Aviso inmediato si se marca cualquier signo de alarma.
  const aviso = document.getElementById("aviso-alarma");
  const alarmas = document.querySelectorAll("#grupo-alarma input[type=checkbox]");
  const revisar = () => { aviso.hidden = ![...alarmas].some((c) => c.checked); };
  alarmas.forEach((c) => c.addEventListener("change", revisar));
  revisar();

  // Contador de 60 segundos: la fuente indica medir la frecuencia respiratoria durante 1 minuto.
  const boton = document.getElementById("btn-contador");
  const estado = document.getElementById("estado-contador");
  const campo = document.getElementById("frecuencia_respiratoria");
  let intervalo = null;
  boton.addEventListener("click", () => {
    if (intervalo) {
      clearInterval(intervalo); intervalo = null;
      boton.textContent = "⏱️ Contar respiraciones durante 1 minuto";
      estado.textContent = "Conteo cancelado.";
      return;
    }
    let restantes = 60;
    boton.textContent = "Cancelar conteo";
    estado.textContent = "Cuenta cada vez que el pecho sube. Quedan 60 s.";
    intervalo = setInterval(() => {
      restantes -= 1;
      if (restantes > 0) {
        estado.textContent = "Cuenta cada vez que el pecho sube. Quedan " + restantes + " s.";
        return;
      }
      clearInterval(intervalo); intervalo = null;
      boton.textContent = "⏱️ Contar de nuevo";
      estado.textContent = "¡Tiempo! Escribe cuántas respiraciones contaste.";
      campo.focus();
    }, 1000);
  });
})();
