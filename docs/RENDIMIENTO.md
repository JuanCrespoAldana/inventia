# Rendimiento y capacidad

Resultados de las pruebas de carga y de volumen de datos. Cubren RNF-011 (tiempo de respuesta), RNF-012
(procesamiento sin afectar la operación), RNF-013 (capacidad de almacenamiento) y RNF-014 (operaciones simultáneas).
Todo lo medido se puede repetir con los scripts de `infra/carga/` (sección 7).

> **Alcance de estas cifras.** Se midieron en un solo equipo de pruebas (2 núcleos, 8 GB de memoria) donde corrían a la
> vez la API, PostgreSQL 16 y el generador de carga, con **datos sintéticos** de la demostración de movilidad eléctrica
> (3 sedes, 36 productos, 200 días de ventas). Cada escenario se ejecutó **una sola vez**: no hay intervalos de
> confianza y las diferencias de pocos milisegundos no son significativas. Describen cómo se comporta el sistema en
> ese equipo; no son una garantía de capacidad para otra infraestructura ni para datos reales.

## 1. Cómo se midió

| Elemento | Detalle |
|---|---|
| API | 1 proceso de Uvicorn (sin réplicas), `ENVIRONMENT=development`, conexión directa a PostgreSQL local |
| Base de datos | PostgreSQL 16 en la misma máquina; sin ajustes de rendimiento |
| Generador de carga | Locust 2.47.0 en la misma máquina (consume procesador, así que las cifras son prudentes) |
| Usuarios virtuales | Inician sesión una vez y repiten, con pausas de 0,5 a 2 s, lo que haría una persona: panel, existencias de su sede y consolidadas, productos, ventas, alertas, predicciones, recomendaciones, vista previa de reportes y, salvo en las pruebas de solo lectura, registro de ventas y de entradas |
| Duración | 60 s por escenario (70 s en la prueba con exportación) |
| Latencia de un solo usuario | `infra/carga/medir_latencias.py`: 15 repeticiones por consulta (la primera se descarta); 3 en las exportaciones pesadas |

## 2. Un solo usuario y volumen de datos creciente (RNF-011, RNF-013)

Para medir cómo reacciona el sistema cuando crece el historial se copió la base de demostración y se multiplicó su
historial con `infra/carga/inflar_base.sh` (las copias se desplazan hacia atrás en el tiempo, de modo que lo reciente
no cambia). Los registros copiados sirven para medir tiempos; no son consistentes con las existencias actuales.

| Escala | Ventas | Líneas de venta | Movimientos | Auditoría | Tamaño de la base |
|---|---:|---:|---:|---:|---:|
| ×1 (base de demostración) | 5 502 | 12 774 | 14 217 | 5 710 | 20 MB |
| ×10 | 55 020 | 127 740 | 142 170 | 57 100 | 90 MB |
| ×50 | 275 100 | 638 700 | 710 850 | 285 533 | 406 MB |

Mediana en milisegundos de una consulta con un solo usuario:

| Consulta | ×1 | ×10 | ×50 |
|---|---:|---:|---:|
| Panel (30 días) | 39 | 67 | 86 |
| Panel (365 días) | 64 | 97 | 122 |
| Existencias consolidadas | 13 | 16 | 12 |
| Alertas | 11 | 10 | 9 |
| Ventas, primera página | 14 | 25 | 51 |
| Ventas, última página | 11 | 33 | 141 |
| Movimientos, primera página | 15 | 28 | 70 |
| Movimientos, última página | 21 | 103 | 441 |
| Auditoría, primera página | 9 | 14 | 43 |
| Auditoría, última página | 12 | 30 | 132 |
| Reporte de ventas en pantalla (todo el historial) | 40 | 177 | 53 |
| Reporte de movimientos en pantalla (todo el historial) | 21 | 22 | 23 |

**Lectura.** Con 50 veces más datos, las consultas del uso diario (panel, existencias, alertas, listas) siguen por
debajo de 0,15 s, muy por debajo del límite de 3 s de RNF-011. Lo que crece es el costo de **paginar hasta el final**
de listas muy largas (la última página de movimientos pasa de 21 ms a 441 ms) porque la base debe recorrer y descartar
las filas anteriores; en el uso real casi nadie llega a esa página, pero es la consulta que primero se degradaría. El
tiempo del reporte de ventas en pantalla no crece de forma regular (177 ms en ×10, 53 ms en ×50): depende del plan que
elige PostgreSQL y no se investigó más.

Exportaciones y PDF (un solo usuario, mediana en milisegundos):

| Exportación (todo el historial) | ×1 | ×10 | ×50 |
|---|---:|---:|---:|
| PDF de ventas (tope de 1 000 filas) | 1 902 | 2 079 | 1 969 |
| CSV de ventas | 928 | 3 780 | 3 965 |
| Excel de ventas | 3 819 | 16 207 | 16 258 |

En ×10 y ×50 el CSV y el Excel ya alcanzan el tope de 50 000 filas (por eso son iguales), de modo que el tiempo deja
de crecer, pero **una exportación de 50 000 filas a Excel tarda unos 16 s y supera el objetivo de 3 s** de RNF-011. El
PDF se limita a 1 000 filas y tarda unos 2 s. Se prefirió documentar este límite a ocultarlo (sección 6).

## 3. Usuarios simultáneos (RNF-011, RNF-014)

Escenario completo (consultas, ventas y entradas de mercancía) sobre la base ×1:

| Usuarios | Peticiones | Fallidas | Peticiones/s | Mediana (ms) | p95 (ms) | p99 (ms) | Máx. (ms) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 234 | 0 | 4,0 | 16 | 45 | 52 | 92 |
| 20 | 932 | 0 | 15,8 | 18 | 56 | 620 | 667 |
| 50 | 2 255 | 0 | 38,2 | 23 | 100 | 750 | 942 |

Con 50 usuarios, el registro de una venta tuvo mediana de 47 ms y p95 de 150 ms; el de una entrada, 44 ms y 160 ms.
Ninguna petición falló. Las primeras peticiones de cada escenario (conexiones nuevas y cachés frías) tardan entre 0,7 y
1,0 s, lo que explica el p99; después el percentil 95 acumulado baja.

**Consistencia de los datos tras la carga (RNF-014).** Después de cada escenario se ejecutó
`infra/carga/verificar_consistencia.py`, que comprueba directamente en la base que no hubo actualizaciones perdidas:
sin existencias negativas, `saldo_posterior = saldo_anterior + variación` en cada movimiento, cada movimiento parte del
saldo en que terminó el anterior, el último saldo coincide con la existencia actual y no hay consecutivos de venta
repetidos. Las cinco comprobaciones dieron **0 violaciones** tras los tres escenarios (hasta 5 502 ventas y 14 217
movimientos con 50 usuarios escribiendo a la vez).

## 4. Predicción mientras otras personas consultan (RNF-012)

La predicción corre en un hilo aparte dentro del mismo proceso que la API.

| Situación (base ×1, 20 usuarios de solo lectura, 60 s) | Mediana (ms) | p95 (ms) | p99 (ms) | Máx. (ms) | Fallidas |
|---|---:|---:|---:|---:|---:|
| Sin predicción | 16 | 54 | 500 | 573 | 0 |
| Con una predicción lanzada a los 15 s | 71 | 380 | 510 | 574 | 0 |

La predicción de las 108 series de la demostración terminó en estado `completada` en **61,8 s** con esa carga, y en
**54,7 s** sin usuarios. Mientras corre, las consultas siguen respondiendo (ninguna falló y el máximo no cambió), pero
la mediana se multiplica por 4 y el p95 por 7: **la operación no se interrumpe, pero se vuelve más lenta**. Por eso se
recomienda programar la predicción fuera del horario de operación (`python -m app.cli predecir`).

Con la base ×50 la misma predicción tardó **76,2 s** (+39 %): la historia que usa el modelo está limitada a 200 días, de
modo que el trabajo de cálculo no crece con el historial total; el aumento se debe probablemente a la lectura de las
ventas (no se midió por separado).

## 5. Capacidad de almacenamiento (RNF-013)

Se probó con una base de **406 MB** y cerca de **1,9 millones de filas** en las cuatro tablas de mayor crecimiento
(ventas, líneas, movimientos y auditoría); con 20 usuarios simultáneos de solo lectura la mediana fue de 25 ms y el
p95 de 160 ms (frente a 20 ms y 68 ms en ×1), sin errores:

| Base | Peticiones | Fallidas | Peticiones/s | Mediana (ms) | p95 (ms) | p99 (ms) |
|---|---:|---:|---:|---:|---:|---:|
| ×1 | 910 | 0 | 15,5 | 20 | 68 | 680 |
| ×10 | 922 | 0 | 15,6 | 21 | 100 | 700 |
| ×50 | 899 | 0 | 15,2 | 25 | 160 | 780 |

En volumen, esto equivale a unas 1 500 ventas al día durante seis meses, una cifra holgada para una pyme.
**No se probó** con decenas de millones de filas ni con datos reales; para esos volúmenes habría que considerar partición
de las tablas de movimientos y auditoría y archivado de datos antiguos.

## 6. Hallazgo: las exportaciones grandes frenan a los demás usuarios

Se lanzó una exportación de Excel de todo el historial mientras 20 usuarios consultaban (70 s):

| Base | Filas exportadas | Duración de la exportación | Mediana (ms) | p95 (ms) | p99 (ms) | Máx. (ms) | Peticiones/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| ×1 | ≈12 800 | 4,7 s | 19 | 190 | 2 800 | 3 705 | 14,9 |
| ×50 | 50 000 (tope) | 20,4 s | 31 | 2 500 | 11 000 | 15 096 | 11,8 |

Ninguna petición falló, pero durante una exportación de 50 000 filas algunas consultas de otras personas tardaron hasta
15 s. La generación del Excel es código de Python puro y se ejecuta en un hilo de la misma API; lo más probable es que
compita con el servidor por el procesador (no se comprobó esa causa). Para comparar, generar el CSV de 50 000 filas
cuesta unos 0,4 s de cálculo (medido aparte); su efecto sobre otros usuarios no se midió.

**Mitigaciones posibles (no implementadas):** reducir el tope de filas del Excel (hoy 50 000), generar las
exportaciones grandes en un trabajo en segundo plano con un enlace de descarga, usar una librería de escritura de
Excel más rápida, o recomendar el CSV para volúmenes grandes. Mientras tanto, conviene pedir las exportaciones grandes fuera del
horario de operación o acotar las fechas.

## 7. Cómo repetir las pruebas

Todo en una **base de pruebas** (nunca con datos reales). Detalles en los encabezados de cada script.

```bash
# Dependencias del generador de carga
pip install -r infra/carga/requirements.txt

# 1) Latencia de un solo usuario
export INVENTIA_EMAIL=admin@... INVENTIA_PASSWORD=...        # administrador de la base de pruebas
python infra/carga/medir_latencias.py http://127.0.0.1:8000 resultados/latencias_x1.json

# 2) Usuarios simultáneos (use INVENTIA_SOLO_LECTURA=1 para no escribir; INVENTIA_PDF=1 incluye PDF)
cd infra/carga
locust -f locustfile.py --headless --host http://127.0.0.1:8000 -u 20 -r 20 -t 60s --csv resultados/u20

# 3) Consistencia de los datos después de una prueba con escrituras
cd backend && DATABASE_URL=postgresql+asyncpg://... python ../infra/carga/verificar_consistencia.py

# 4) Más volumen: copiar la base de pruebas y multiplicar su historial (9 copias = ×10, 49 = ×50)
PGHOST=localhost PGUSER=... PGPASSWORD=... infra/carga/inflar_base.sh mi_base_de_pruebas_copia 9
```

`inflar_base.sh` se niega a trabajar sobre bases cuyo nombre contenga «prod» o «real».
