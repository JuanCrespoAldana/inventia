# Verificación de seguridad

Dos herramientas propias que apoyan el mapeo a OWASP Top 10:2025 de [`docs/SEGURIDAD.md`](../../docs/SEGURIDAD.md). Las dos
envían peticiones reales: **úselas solo contra una API de pruebas con una base desechable**.

| Archivo | Para qué sirve |
|---|---|
| `sonda_seguridad.py` | 16 comprobaciones contra una API en ejecución: rutas sin token, token alterado o con algoritmo `none`, rol limitado y aislamiento por sede, CORS y cabeceras, entradas maliciosas, cuerpos malformados, bloqueo por intentos y auditoría |
| `fuzz_api.sh` | Fuzzing con [Schemathesis](https://schemathesis.readthedocs.io) a partir del contrato OpenAPI: exige que ninguna entrada produzca error 5xx y que las respuestas cumplan lo documentado |

```bash
# Sonda (los archivos contienen solo la contraseña; no la escriba en la línea de comandos)
python sonda_seguridad.py http://127.0.0.1:8000 admin@... ruta/clave_admin.txt encargado@... ruta/clave_encargado.txt salida.json
# Aviso: bloquea la cuenta del usuario limitado (prueba de bloqueo por intentos) y espera 62 s para no chocar con el
# límite de 10 inicios de sesión por minuto. Desbloquee la cuenta después, o use una de pruebas.

# Fuzzing (instale antes: pip install schemathesis). Requiere un JWT de administrador en un archivo.
./fuzz_api.sh http://127.0.0.1:8002 ruta/token.txt
```

No sustituyen una prueba de penetración independiente ni un escáner dinámico como OWASP ZAP.
