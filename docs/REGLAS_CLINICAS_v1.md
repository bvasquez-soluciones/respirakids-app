# Reglas clínicas v1-aiepi — documento de validación

> **Estado: PENDIENTE DE VALIDACIÓN POR UN PROFESIONAL DE SALUD.** Este documento se genera automáticamente desde `app/clinica/reglas_v1.py` con `flask reglas documentar`; no editarlo a mano.

**Fuente clínica principal:** Herramienta Clínica para el abordaje inicial de las condiciones prevalentes en la primera infancia (AIEPI clínico), Ministerio de Salud y Protección Social de Colombia.

## 1. Convención de semaforización (decisión principal a validar)

La fuente **no define** una semaforización verde/amarillo/rojo (documento maestro, sección 15). RespiraKids aplica esta convención única:

| Nivel | Se asigna cuando la fuente describe el hallazgo como… |
|---|---|
| 🔴 Rojo | signo de alarma, de gravedad o de máxima gravedad, o indica hospitalización o remisión hospitalaria |
| 🟡 Amarillo | criterio para consultar o canalizar, o una clasificación no grave (p. ej. "Neumonía", "Tos ferina") |
| 🟢 Verde | no se identificó ninguno de los criterios anteriores (no significa "sano") |

El nivel final es el mayor de las reglas que se cumplen. Las reglas marcadas como **salvaguarda** no provienen de la fuente.

## 2. Reglas implementadas

### R01 · 🔴 Rojo · Tiraje subcostal (hundimiento debajo de las costillas al respirar)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Neumonía](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/neumonia/)
- **Criterio:** Neumonía: "se confiere gravedad cuando presenta tiraje subcostal independientemente de la frecuencia respiratoria". Listado también como signo de alarma en Neumonía y Bronquiolitis.
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R02 · 🔴 Rojo · Coloración azulada de labios o piel (cianosis)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Neumonía](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/neumonia/)
- **Criterio:** Neumonía: "Signos de máxima gravedad o predictivos de muerte: cianosis, incapacidad de ingerir líquidos, quejido, aleteo nasal y desnutrición aguda." También es signo de alarma en Bronquiolitis y CRUP.
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R03 · 🔴 Rojo · No puede beber líquidos

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Neumonía](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/neumonia/)
- **Criterio:** Neumonía: "Signos de máxima gravedad o predictivos de muerte: cianosis, incapacidad de ingerir líquidos, quejido, aleteo nasal y desnutrición aguda."
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R04 · 🔴 Rojo · Quejido al respirar

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Neumonía](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/neumonia/)
- **Criterio:** Neumonía: "Signos de máxima gravedad o predictivos de muerte: cianosis, incapacidad de ingerir líquidos, quejido, aleteo nasal y desnutrición aguda."
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R05 · 🔴 Rojo · Aleteo nasal

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Neumonía](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/neumonia/)
- **Criterio:** Neumonía: "Signos de máxima gravedad o predictivos de muerte: cianosis, incapacidad de ingerir líquidos, quejido, aleteo nasal y desnutrición aguda."
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R06 · 🔴 Rojo · Pausas en la respiración (apnea)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Bronquiolitis](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/bronquiolitis/)
- **Criterio:** Bronquiolitis, signos de alarma: "Tiraje subcostal, respiración rápida, apneas, cianosis, saturación de oxígeno baja según edad y altura. Factores de BAR."
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R07 · 🔴 Rojo · Saturación de oxígeno baja para la altitud (hipoxemia)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Neumonía](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/neumonia/)
- **Criterio:** Neumonía: "Oximetría según altitud (hipoxemia): 0-1500 msnm ≤94%; 1501-2000 ≤92%; 2001-2500 ≤90%; 2501-3000 ≤88%; 3500-4000 ≤83%." La hipoxemia según altitud está en sus signos de alarma.
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] La fuente no da umbral para 3001-3499 msnm ni para más de 4000 msnm; en esos casos la regla no se aplica y se muestra un aviso.
  - [ ] Confirmar si la medición con oxímetro doméstico por parte del cuidador es aceptable.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R08 · 🔴 Rojo · Estridor en reposo (ruido agudo al inhalar estando tranquilo/a)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Laringotraqueitis / CRUP](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/laringotraqueitis-crup/)
- **Criterio:** CRUP, signos de alarma: "Estridor en reposo, tirajes moderados o graves, ventilación disminuida o muy disminuida, cianosis (con agitación o en reposo), alteración del nivel de conciencia."
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
  - [ ] El formulario pregunta específicamente por estridor EN REPOSO.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R09 · 🔴 Rojo · Alteración de la conciencia (muy somnoliento/a o difícil de despertar)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Laringotraqueitis / CRUP](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/laringotraqueitis-crup/)
- **Criterio:** CRUP, signos de alarma: "alteración del nivel de conciencia". Enfermedad febril, signos de alarma: "alteración de conciencia".
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R10 · 🔴 Rojo · Convulsión

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 5 · Enfermedad febril](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-5/enfermedad-febril/)
- **Criterio:** Enfermedad febril, signos de alarma: "convulsiones a repetición". Tos ferina, complicaciones: "convulsiones".
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] La fuente dice "convulsiones a repetición"; el formulario registra cualquier convulsión. Confirmar si un único episodio debe clasificarse en rojo.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R11 · 🔴 Rojo · Temperatura mayor de 40 °C

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 5 · Enfermedad febril](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-5/enfermedad-febril/)
- **Criterio:** Enfermedad febril, signos de alarma: "temperatura >40°C".
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R12 · 🔴 Rojo · Rigidez de cuello

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 5 · Enfermedad febril](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-5/enfermedad-febril/)
- **Criterio:** Enfermedad febril, signos de alarma (signos de localización graves): "rigidez de cuello".
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R13 · 🔴 Rojo · Fontanela abombada (la "mollera" levantada)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 5 · Enfermedad febril](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-5/enfermedad-febril/)
- **Criterio:** Enfermedad febril, signos de alarma (signos de localización graves): "abombamiento de fontanela".
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R14 · 🔴 Rojo · Manchas rojas o moradas en la piel (púrpura o petequias)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 5 · Enfermedad febril](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-5/enfermedad-febril/)
- **Criterio:** Enfermedad febril, signos de alarma (signos de localización graves): "púrpura/petequias".
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R15 · 🔴 Rojo · Hinchazón y enrojecimiento detrás de la oreja

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Otitis media aguda](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/otitis-media-aguda/)
- **Criterio:** Otitis media aguda: "Edema y eritema retroauricular deben hacer sospechar mastoiditis." "Mastoiditis se clasifica como enfermedad grave." "Mastoiditis debe ser remitida para manejo hospitalario."
- **Orientación mostrada:** La fuente indica que este hallazgo debe hacer sospechar una complicación que requiere manejo hospitalario. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R16 · 🔴 Rojo · Signos compatibles con la definición de caso probable de tos ferina en menor de 6 meses

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Tos ferina](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/tos-ferina/)
- **Criterio:** Tos ferina: definición de caso probable según edad (Protocolo INS) y "Se sugiere hospitalización en todos los menores de seis meses y en cualquier edad con enfermedad severa."
- **Orientación mostrada:** La fuente sugiere hospitalización en todos los menores de seis meses con este cuadro. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] La definición de caso probable la aplica normalmente un profesional; aquí se usa con datos reportados por el cuidador.
  - [ ] Para menores de 3 meses, "todas las IRA" se interpreta como cualquier registro con síntomas respiratorios.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### R17 · 🔴 Rojo · Sibilancias en menor de 2 años con factores de alto riesgo

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Bronquiolitis](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/bronquiolitis/)
- **Criterio:** Bronquiolitis: BAR cuando en niños <2 años con sospecha de bronquiolitis se asocian "<2 meses; prematuridad (peso <2000 g al nacer) en <6 meses; enfermedades congénitas cardiovasculares...; presencia de apneas; desnutrición aguda grave". Signos de alarma: "... Factores de BAR."
- **Orientación mostrada:** La fuente describe este hallazgo como signo de alarma o de gravedad. Busca atención en un servicio de salud de inmediato.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] La fuente define bronquiolitis como el PRIMER episodio de sibilancias; el formulario no distingue si es el primero.
  - [ ] Los factores de BAR se preguntan en una sola casilla que lista los de la fuente.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A01 · 🟡 Amarillo · Respiración rápida para la edad (frecuencia respiratoria medida)

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Neumonía](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/neumonia/)
- **Criterio:** Neumonía: "Taquipnea es el mejor signo único predictor de neumonía (OMS)." "Valores de frecuencia respiratoria (taquipnea): <2 meses >60; 3-12 meses >50; 1-5 años >40. Medir por 1 minuto, niño despierto sin llorar." Clasificación de la fuente: "Neumonía grave – Neumonía".
- **Orientación mostrada:** La fuente indica que la respiración rápida para la edad debe ser valorada por un profesional de salud. Consulta pronto.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Sin tiraje ni signos de máxima gravedad se asigna amarillo (clasificación "Neumonía", no "Neumonía grave"). En Bronquiolitis la fuente lista la respiración rápida entre los signos de alarma: confirmar el nivel.
  - [ ] La fuente no da umbral entre 2 y 3 meses; ahí la regla no se aplica y se muestra un aviso.
  - [ ] A los 12 meses exactos las bandas "3-12 meses" y "1-5 años" se solapan; se usa >40.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A02 · 🟡 Amarillo · Signos compatibles con la definición de caso probable de tos ferina

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Tos ferina](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/tos-ferina/)
- **Criterio:** Tos ferina: definición de caso probable según edad (Protocolo INS). Clasificación de la fuente: "Tos ferina grave – Tos ferina". "Notificar caso probable". "Canalizar a especialista en pediatría".
- **Orientación mostrada:** La fuente indica que estos casos deben ser valorados y notificados por un profesional de salud. Consulta pronto a un servicio de salud.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A03 · 🟡 Amarillo · Tos por más de 15 días

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Tuberculosis](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/tuberculosis/)
- **Criterio:** Tuberculosis, cuándo consultar: "Ante tos de más de 15 días con o sin expectoración, fiebre >8 días, pérdida o no ganancia de peso, disminución de la actividad o juego, y contacto con un caso de tuberculosis."
- **Orientación mostrada:** La fuente indica consultar a un profesional de salud ante este hallazgo.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] La fuente enumera los criterios unidos por "y"; RespiraKids aplica cada uno por separado (más sensible). Confirmar si deben exigirse combinados.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A04 · 🟡 Amarillo · Fiebre por más de 7 días

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 5 · Enfermedad febril](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-5/enfermedad-febril/)
- **Criterio:** Enfermedad febril, cuándo consultar: "Ante signos de enfermedad grave, signos de localización, fiebre prolongada (>7 días) o condiciones de riesgo." Tuberculosis: "fiebre >8 días".
- **Orientación mostrada:** La fuente indica consultar a un profesional de salud ante fiebre prolongada.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A05 · 🟡 Amarillo · Contacto con una persona con tuberculosis

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Tuberculosis](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/tuberculosis/)
- **Criterio:** Tuberculosis, cuándo consultar: "... y contacto con un caso de tuberculosis." Factores de riesgo: "Contacto domiciliario o estrecho con caso de tuberculosis pulmonar; niños y niñas menores de 5 años".
- **Orientación mostrada:** La fuente indica consultar a un profesional de salud ante este antecedente.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Mismo punto de A03 sobre criterios combinados.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A06 · 🟡 Amarillo · Pérdida de peso o no ganancia de peso

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Tuberculosis](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/tuberculosis/)
- **Criterio:** Tuberculosis, cuándo consultar: "pérdida o no ganancia de peso".
- **Orientación mostrada:** La fuente indica consultar a un profesional de salud ante este hallazgo.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Mismo punto de A03 sobre criterios combinados.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A07 · 🟡 Amarillo · Disminución de la actividad o del juego

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Tuberculosis](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/tuberculosis/)
- **Criterio:** Tuberculosis, cuándo consultar: "disminución de la actividad o juego".
- **Orientación mostrada:** La fuente indica consultar a un profesional de salud ante este hallazgo.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Mismo punto de A03 sobre criterios combinados.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### A08 · 🟡 Amarillo · Sibilancias (silbido en el pecho) en menor de 2 años

- **Origen:** Fuente clínica
- **Fuente:** [Módulo 6 · Bronquiolitis](https://herramientaclinicaprimerainfancia.minsalud.gov.co/modulo-6/bronquiolitis/)
- **Criterio:** Bronquiolitis: "primer episodio de sibilancias en un lactante menor de 2 años precedido de cuadro gripal". Clasificación de la fuente: "Bronquiolitis – Bronquiolitis Grave – Síndrome sibilante recurrente". "Canalizar a especialista en pediatría según disponibilidad cuando haya factores de riesgo o complicaciones."
- **Orientación mostrada:** Consulta a un profesional de salud para que valore las sibilancias.
- **Puntos a validar:**
  - [ ] La asignación de color es una convención de RespiraKids (la fuente no define semaforización): confirmar que el nivel asignado es adecuado.
  - [ ] Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

### S01 · 🟡 Amarillo · Dificultad para respirar o respiración rápida reportada por el cuidador (sin medir)

- **Origen:** ⚠️ Salvaguarda de RespiraKids (NO proviene de la fuente)
- **Fuente:** Regla de salvaguarda de RespiraKids (no proviene de la fuente)
- **Criterio:** NO PROVIENE DE LA FUENTE. La fuente menciona la dificultad respiratoria como componente de Bronquiolitis, CRUP y Asma, y exige MEDIR la frecuencia respiratoria durante 1 minuto; no clasifica la percepción del cuidador por sí sola.
- **Orientación mostrada:** Indicaste dificultad para respirar o respiración rápida. Si puedes, cuenta las respiraciones durante 1 minuto, revisa los signos de alarma y consulta a un profesional de salud.
- **Puntos a validar:**
  - [ ] Regla de salvaguarda: decidir si se conserva, se cambia de nivel o se elimina.
- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______

## 3. Umbrales usados (copiados de la fuente)

**Respiración rápida (Módulo 6 · Neumonía):** <2 meses >60; 3-12 meses >50; 1-5 años >40 respiraciones por minuto, medidas durante 1 minuto con el niño despierto y sin llorar.

**Hipoxemia según altitud (Módulo 6 · Neumonía):** 0-1500 msnm ≤94 %; 1501-2000 ≤92 %; 2001-2500 ≤90 %; 2501-3000 ≤88 %; 3500-4000 ≤83 %.

## 4. Criterios de la fuente que no se implementaron

| Criterio | Motivo |
|---|---|
| Desnutrición aguda (Neumonía, Bronquiolitis) | Requiere valoración antropométrica por un profesional. |
| Mal estado clínico / triángulo de aproximación pediátrica alterado (Fiebre) | Requiere examen por un profesional. |
| Hipotermia en niño pequeño o desnutrido (Fiebre) | La fuente no especifica umbral de temperatura ni de edad. |
| Edad como factor de riesgo de bacteriemia oculta (Fiebre) | La fuente no especifica umbral de edad. |
| Choque (Fiebre) | Requiere examen por un profesional. |
| Escala de Westley para CRUP (tirajes, ventilación, cianosis, conciencia) | Requiere auscultación con fonendoscopio. |
| Tirajes moderados o graves y ventilación disminuida (CRUP) | Requiere examen por un profesional. |
| Crépitos y signos de consolidación (Neumonía) | Requiere auscultación. |
| Signos de severidad de rinosinusitis y complicaciones orbitarias | Requiere examen; la fuente no define nivel. |
| Clasificación de otitis, faringoamigdalitis y asma (IPA) | Requiere examen o historia clínica completa. |
| Taquipnea entre 2 y 3 meses de edad | La fuente no especifica umbral para esa edad. |
| Hipoxemia entre 3001 y 3499 msnm o por encima de 4000 msnm | La fuente no especifica umbral para esas altitudes. |

## 5. Firma de validación

Una vez validadas todas las reglas, el profesional firma esta versión y el equipo técnico define `REGLAS_CLINICAS_VALIDADAS=v1-aiepi` en producción. Sin esa variable la aplicación no arranca en producción.

- Nombre del profesional: ______________________
- Profesión y registro (RETHUS / tarjeta profesional): ______________________
- Fecha: ______________________
- Firma: ______________________
