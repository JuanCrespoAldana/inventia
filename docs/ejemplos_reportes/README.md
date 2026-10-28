# Reportes de ejemplo

Reportes exportados con la propia API (módulo Reportes) el 27 de octubre de 2026, como administrador y sin filtros, sobre los **datos de demostración (sintéticos)**.
Se usan como figuras y como tabla en el Anexo J de la memoria.

| Archivo | Contenido |
|---|---|
| `reporte_inv.pdf` | Inventario por sede (PDF) |
| `reporte_ventas.pdf`, `.xlsx`, `.csv` | Ventas: el PDF se limita a las primeras 1.000 filas; el Excel y el CSV traen todas |
| `reporte_pred.pdf` | Predicción de demanda (PDF) |
| `ventas_pagina1.png`, `pred_pagina1.png` | Primera página de los dos PDF anteriores, como imagen |

Estos ejemplos se generaron **antes** de corregir el resumen del PDF de ventas: esa versión sumaba solo las filas recortadas sin decirlo. Desde la corrección (véase `CHANGELOG.md`, sección «Corregido») la vista previa, el PDF y la hoja de resumen del Excel avisan cuando el resumen suma solo las filas mostradas.
