# Pruebas de carga y de volumen

Scripts para medir cuánto tarda el sistema y si conserva los datos correctos cuando muchas personas lo usan a la vez o
cuando el historial crece. Los resultados obtenidos y su interpretación están en
[`docs/RENDIMIENTO.md`](../../docs/RENDIMIENTO.md).

> **Úselos solo contra una base de pruebas o de demostración.** Registran ventas y entradas reales, y `inflar_base.sh`
> inserta cientos de miles de filas.

| Archivo | Para qué sirve |
|---|---|
| `locustfile.py` | Usuarios virtuales (Locust) que miran el panel, consultan existencias, ventas, alertas, predicciones y reportes y registran ventas y entradas |
| `medir_latencias.py` | Tiempo de cada consulta con **un solo usuario**; sirve para comparar antes y después de aumentar el volumen |
| `verificar_consistencia.py` | Después de una prueba con escrituras, comprueba en la base que no hubo actualizaciones perdidas (existencias negativas, saldos encadenados, consecutivos repetidos) |
| `inflar_base.sh` | Multiplica el historial de una **copia** de la base de demostración (9 copias = ×10, 49 = ×50) |

## Receta

```bash
pip install -r requirements.txt
export INVENTIA_EMAIL=admin@...  INVENTIA_PASSWORD=...     # administrador de la base de pruebas

# 1. Un solo usuario
python medir_latencias.py http://127.0.0.1:8000 resultados/latencias_x1.json

# 2. Muchos usuarios (20 usuarios, 60 s). INVENTIA_SOLO_LECTURA=1 no escribe; INVENTIA_PDF=1 incluye reportes en PDF
locust -f locustfile.py --headless --host http://127.0.0.1:8000 -u 20 -r 20 -t 60s --csv resultados/u20

# 3. ¿Se conservaron los datos? (desde backend/, con DATABASE_URL de la misma base)
cd ../../backend && python ../infra/carga/verificar_consistencia.py

# 4. Más volumen: copie la base de demostración y multiplíquela
createdb inventia_escala && pg_dump inventia_demo --no-owner | psql -d inventia_escala
PGHOST=localhost PGUSER=postgres PGPASSWORD=... ./inflar_base.sh inventia_escala 9
```

Notas:

- El inicio de sesión se hace una sola vez al comenzar y se comparte, porque el inicio de sesión está limitado por IP
  (RNF-026) y probarlo con cientos de usuarios desde una máquina mediría solo ese límite.
- Con Locust y la API en la misma máquina, el generador de carga consume procesador; las cifras resultan prudentes.
- Las filas que crea `inflar_base.sh` llevan consecutivos de venta negativos para no chocar con los reales y no son
  consistentes con las existencias actuales: sirven para medir tiempos, no para verificar inventario.
