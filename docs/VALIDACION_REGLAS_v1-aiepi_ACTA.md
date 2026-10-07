# Acta de validación de las reglas clínicas v1-aiepi

Registro de la validación que habilita `REGLAS_CLINICAS_VALIDADAS=v1-aiepi` en producción
(ver `docs/REGLAS_CLINICAS_v1.md` y `docs/DESPLIEGUE.md`, sección 7).

## Datos de la validación

| Campo | Valor |
|---|---|
| Versión validada | `v1-aiepi` (26 reglas y convención de semaforización) |
| Documento revisado | `docs/REGLAS_CLINICAS_v1.md` · SHA-256 `762a63dd6a1cd8b239a829040c8d1348ba49749570098951366646e5a4278a6a` |
| Profesional que firma | Alex Pájaro |
| Profesión | Médico general |
| Registro profesional (ReTHUS / tarjeta profesional) | **PENDIENTE** |
| Fecha de la firma | 2026-10-07 |
| Documento firmado | `VALIDACION_REGLAS_CLINICAS_v1-aiepi_FIRMADA_2026-10-07.pdf` · SHA-256 `5b3fff9224f88ae4a7a984c41510a0503c2082dfecf1e30df76fb7502d8c072a` (se conserva fuera del repositorio porque contiene la firma) |

## Alcance de lo recibido

- El profesional **firmó la hoja de validación** (sección 5) con su nombre y la fecha.
- En el documento firmado **las casillas de decisión de cada regla quedaron sin marcar** y el campo de registro
  profesional quedó en blanco.
- La **aprobación de las 26 reglas sin cambios** fue comunicada **verbalmente** por el profesional al responsable del
  proyecto, **Bayron de Jesús Vásquez Castillo**, quien la confirma y autoriza la activación en producción el
  2026-10-07, asumiendo la responsabilidad de completar esta acta.

## Pendientes para completar el acta

- [ ] Número de registro profesional (ReTHUS o tarjeta profesional) del profesional que firma.
- [ ] Confirmación **escrita** del profesional de que aprueba las 26 reglas sin cambios (mensaje o documento con las
      casillas marcadas).

Si el profesional pide cambiar alguna regla, se ajusta el código, se genera una nueva versión de las reglas y se
repite la validación antes de usarla en producción.
