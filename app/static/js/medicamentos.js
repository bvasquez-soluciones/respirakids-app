/* Formulario de indicación: agregar y quitar medicamentos (máximo 5) renumerando los campos. */
(function () {
  const MAXIMO = 5;
  const lista = document.getElementById("lista-medicamentos");
  const agregar = document.getElementById("agregar-medicamento");

  function renumerar() {
    const bloques = lista.querySelectorAll(".rk-medicamento");
    bloques.forEach((bloque, i) => {
      bloque.querySelector(".rk-medicamento__numero").textContent = i + 1;
      bloque.querySelectorAll("[id], [name], [for], [aria-describedby]").forEach((el) => {
        ["id", "name", "for", "aria-describedby"].forEach((atr) => {
          const valor = el.getAttribute(atr);
          if (valor) el.setAttribute(atr, valor.replace(/medicamentos-\d+-/g, "medicamentos-" + i + "-"));
        });
      });
      bloque.querySelector(".rk-quitar-medicamento").hidden = bloques.length === 1;
    });
    agregar.hidden = bloques.length >= MAXIMO;
  }

  agregar.addEventListener("click", () => {
    const copia = lista.querySelector(".rk-medicamento:last-child").cloneNode(true);
    copia.querySelectorAll("input, textarea").forEach((el) => { el.value = ""; el.removeAttribute("aria-invalid"); el.classList.remove("is-invalid"); });
    copia.querySelectorAll(".rk-campo-error").forEach((el) => el.remove());
    lista.appendChild(copia);
    renumerar();
    copia.querySelector("input").focus();
  });

  lista.addEventListener("click", (evento) => {
    if (!evento.target.classList.contains("rk-quitar-medicamento")) return;
    evento.target.closest(".rk-medicamento").remove();
    renumerar();
  });

  renumerar();
})();
