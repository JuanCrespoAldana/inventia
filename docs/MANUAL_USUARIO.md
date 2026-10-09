# Manual de usuario

Guía de uso de Inventia para las personas que trabajan con el sistema todos los días. Está organizada por tareas
y por rol. No necesita conocimientos técnicos.

> Lo que ve en pantalla depende de su rol: el menú solo muestra las opciones que puede usar. Si no encuentra una
> opción que necesita, pídale a un administrador de su empresa que revise su rol.

## Contenido

1. [Primeros pasos](#1-primeros-pasos)
2. [Recorrido por la pantalla](#2-recorrido-por-la-pantalla)
3. [Qué puede hacer cada rol](#3-qué-puede-hacer-cada-rol)
4. [Tareas del día a día](#4-tareas-del-día-a-día)
5. [Predicción de demanda y recomendaciones](#5-predicción-de-demanda-y-recomendaciones)
6. [Reportes](#6-reportes)
7. [Administración](#7-administración)
8. [Mensajes frecuentes y qué hacer](#8-mensajes-frecuentes-y-qué-hacer)
9. [Glosario](#9-glosario)

---

## 1. Primeros pasos

### Ingresar

1. Abra la dirección que le dio su empresa.
2. Escriba su **correo electrónico** y su **contraseña** y pulse **Ingresar**.
3. Si el administrador le asignó una contraseña temporal, el sistema le pedirá crear una personal antes de continuar.

Una contraseña válida tiene entre 8 y 128 caracteres e incluye una mayúscula, una minúscula, un número y un
carácter especial. El botón del ojo permite ver lo que escribe.

Si escribe mal la contraseña **5 veces seguidas**, la cuenta se bloquea durante 15 minutos por seguridad. Un
administrador puede desbloquearla antes.

### Olvidé mi contraseña

1. En la pantalla de ingreso pulse **¿Olvidó su contraseña?**
2. Escriba su correo. Si la cuenta existe, recibirá un código de 6 dígitos.
3. Escriba el código (vale 15 minutos y sirve una sola vez; tiene 5 intentos).
4. Cree su nueva contraseña.

Por seguridad, el sistema muestra el mismo mensaje exista o no el correo. Si no llega el código, revise la
carpeta de correo no deseado y, si sigue sin llegar, pida a un administrador que le restablezca la contraseña.

### Mi perfil

En el menú de usuario (abajo a la izquierda) abra **Mi perfil**: allí ve su empresa, su rol y su sede, y puede
**cambiar su contraseña**. Al cambiarla se cierran las demás sesiones abiertas de su cuenta.

### Cerrar sesión

Use **Salir** en el menú de usuario. La sesión también se cierra sola cuando vence; el sistema se lo avisará y
volverá a pedirle el ingreso.

### Primera vez en una empresa nueva (solo quien instala el sistema)

La primera persona que configura el sistema abre la pantalla **Configuración inicial**, escribe el **token de
configuración** que le entregó quien instaló el sistema, los datos de la empresa y los de su cuenta de
administrador. Esa pantalla deja de funcionar apenas existe una empresa: nadie puede volver a usarla para
crearse un administrador.

---

## 2. Recorrido por la pantalla

| Zona | Qué contiene |
|---|---|
| Menú lateral | Las secciones a las que tiene acceso: Inventario, Operación, Inteligencia y Administración. En celular se abre con el botón de menú |
| Panel de control | Resumen de su operación (según permisos): ventas por día, productos más vendidos, inventario por sede, alertas prioritarias, resumen de la predicción de demanda y movimientos recientes |
| Encabezado de cada página | Título, descripción y el botón de la acción principal (por ejemplo **Nueva venta**) |
| Filtros | Buscador y filtros sobre cada lista. Quedan en la dirección de la página: puede copiar el enlace y compartirlo |
| Tablas | Se ordenan en páginas; abajo elige cuántos registros ver |
| Avisos | Aparecen en una esquina cuando una acción termina bien, falla o necesita corrección |

Todas las pantallas muestran un estado de **carga** mientras esperan datos, un mensaje de **lista vacía** que
indica cómo empezar y un mensaje de **error** con botón para reintentar si algo falla.

Las acciones delicadas (inhabilitar, anular, rechazar, revocar) siempre piden una **confirmación**.

---

## 3. Qué puede hacer cada rol

| Rol | Ve | Hace |
|---|---|---|
| **Administrador** | Todas las sedes y todos los módulos | Todo, incluida la configuración de la empresa, usuarios, roles y llaves de agentes |
| **Gerente** | Todas las sedes | Consulta inventario consolidado, ventas, traslados, alertas, predicciones y reportes; aprueba o rechaza recomendaciones |
| **Encargado de sede** | Solo su sede | Registra entradas, salidas, ajustes y ventas; anula ventas; solicita, aprueba y confirma traslados; define mínimos y máximos; revisa recomendaciones |
| **Usuario de inventario** | Solo su sede | Registra entradas, salidas, ajustes y ventas; solicita y confirma traslados; consulta existencias y alertas |
| **Analista de compras** | Todas las sedes | Consulta inventario consolidado, ventas y alertas; genera predicciones y recomendaciones; las aprueba o rechaza |

Su empresa puede haber creado roles propios con otras combinaciones; en **Mi perfil** ve cuántos permisos tiene
activos.

---

## 4. Tareas del día a día

### 4.1 Consultar existencias

**Inventario → Existencias.** Elija la sede (si su rol ve varias) y, si lo desea, busque por código o nombre o
filtre por categoría o estado.

| Estado | Significado |
|---|---|
| Normal | Dentro de los límites |
| Bajo | Igual o por debajo del mínimo definido |
| Agotado | Sin unidades |
| Excesivo | Por encima del máximo definido |

**Inventario → Consolidado** (administrador, gerente, analista) suma las existencias de todas las sedes y muestra
cómo se reparten. El total se calcula siempre a partir de las sedes: no se puede editar a mano.

### 4.2 Registrar una entrada (llegó mercancía)

1. **Existencias → Registrar entrada**.
2. Elija el motivo (compra, devolución de cliente, inventario inicial, producción u otro).
3. Agregue los productos y las cantidades. Puede agregar varias líneas; un producto solo puede aparecer una vez.
4. Pulse **Registrar entrada**.

### 4.3 Registrar una salida (pérdida, consumo, devolución al proveedor)

1. **Existencias → Registrar salida**.
2. Elija el motivo (pérdida, deterioro, consumo interno, devolución al proveedor u otro).
3. Agregue productos y cantidades.

Si una cantidad supera lo disponible, el sistema **no registra nada** y le dice cuánto hay y cuánto se necesita.
Las ventas no se registran como salidas: tienen su propia pantalla.

### 4.4 Ajustar existencias (conteo físico)

En la fila del producto pulse el icono de **ajuste** e indique la **cantidad real contada**, el motivo (conteo
físico, corrección u otro) y una observación (obligatoria). El sistema calcula la diferencia, la muestra antes de
aplicar y la registra como movimiento. Nada se borra: el historial conserva el saldo anterior y el nuevo.

### 4.5 Definir mínimos y máximos

En la fila del producto pulse el icono de **niveles**. El **mínimo** dispara las alertas de inventario bajo; el
**máximo** (opcional) dispara las de exceso y limita las cantidades que se recomiendan. El máximo no puede ser
menor que el mínimo.

### 4.6 Registrar una venta

1. **Ventas → Nueva venta**.
2. Busque cada producto por código o nombre y agréguelo. El precio se propone desde la ficha del producto y puede
   modificarse en esa venta.
3. Revise el total y pulse **Registrar venta**.

Las existencias se descuentan en el mismo instante. Si falta mercancía de algún producto, **toda la venta se
rechaza** y no queda a medias.

**Anular una venta.** Abra la venta, pulse **Anular venta** y escriba el motivo. Las unidades vuelven al
inventario como un movimiento nuevo (la venta queda marcada como anulada, no se borra). Solo puede anularse dentro
del plazo que defina la empresa (30 días por defecto) y una sola vez. Las ventas anuladas no cuentan en los
reportes de ventas ni en la predicción.

### 4.7 Trasladar mercancía entre sedes

Un traslado pasa por tres etapas:

```
Solicitado ──▶ Aprobado ──▶ Confirmado
 (cualquier      (sede de        (sede de destino
  sede)          origen)         recibe)
```

1. **Traslados → Solicitar traslado**: elija sede de origen, sede de destino, productos y cantidades. Solo puede
   solicitar traslados que salgan de su sede o lleguen a ella.
2. **La sede de origen aprueba** (o rechaza con un motivo) desde la página del traslado.
3. Cuando la mercancía llega, **la sede de destino pulsa Confirmar recepción**. Solo en ese momento las
   existencias se mueven: se descuentan del origen y se suman al destino en una sola operación.

Un traslado pendiente puede **cancelarse** con un motivo. Una sede o un producto con traslados pendientes no puede
inhabilitarse.

### 4.8 Alertas

**Operación → Alertas** muestra lo que requiere atención, ordenado por prioridad (crítica, alta, media, baja):

| Tipo | Cuándo aparece |
|---|---|
| Inventario bajo | Existencias en o por debajo del mínimo, o agotadas |
| Inventario excesivo | Existencias por encima del máximo |
| Riesgo de desabastecimiento | Las existencias no alcanzan para cubrir el plazo de entrega según la demanda prevista |
| Requiere revisión | Hay existencias pero no ha habido movimiento en mucho tiempo |

Las alertas **se abren y se cierran solas** al cambiar las existencias. El botón **Recalcular alertas** vuelve a
evaluar todo de una vez (útil después de cambiar los mínimos o los parámetros de la empresa).

### 4.9 Historial de movimientos

**Inventario → Movimientos** lista cada cambio de existencias: entradas, salidas, ajustes, ventas, anulaciones y
traslados, con quién lo hizo, cuándo y el saldo antes y después. No se puede editar ni eliminar. Puede filtrar por
sede, producto, tipo y fechas.

### 4.10 Catálogo: productos y categorías

**Inventario → Productos** y **Categorías** (según permisos). Cada producto tiene código, nombre, categoría,
unidad de medida, costo y precio de venta.

- El **código no se puede cambiar** una vez creado: identifica al producto en todo el historial.
- Un producto **inhabilitado** deja de aparecer para operar, pero conserva su historial. Puede reactivarse.
- Un producto sin **costo** no se incluye en la valoración del inventario de los reportes (el reporte lo advierte).

---

## 5. Predicción de demanda y recomendaciones

> Una predicción es una **estimación**, no una venta ni una promesa. Siempre se muestra junto a su margen de error
> y su nivel de confianza. Las recomendaciones **nunca** mueven inventario ni hacen compras por sí solas.

### 5.1 Generar una predicción

**Inteligencia → Predicción de demanda → Generar predicción de demanda.** Elija el horizonte (cuántos días hacia
adelante) y confirme. El cálculo se hace en segundo plano; la pantalla muestra el avance y puede seguir trabajando.

### 5.2 Leer los resultados

Para cada producto y sede verá:

- **Demanda estimada** del periodo, con su rango probable (intervalo de 80 %).
- **Confianza**: alta, media o baja. Con confianza baja, tómela solo como orientación.
- **Modelo** utilizado y cuánto mejora frente al promedio simple.
- **Advertencias**: por ejemplo, historial corto o días en los que el producto estuvo agotado.

La gráfica compara las ventas reales (línea sólida) con el pronóstico (línea punteada con banda).

La pestaña **Series sin pronóstico** lista lo que **no** se pudo calcular y por qué (por ejemplo, «Historial
insuficiente: 12 días (se requieren al menos 28)»). Es normal para productos nuevos: el sistema prefiere no dar
número antes que inventarlo.

La pestaña **Cómo se calcula** resume los modelos y reglas utilizados. El detalle técnico está en
[PREDICCION.md](PREDICCION.md).

### 5.3 Recomendaciones

**Inteligencia → Recomendaciones → Generar recomendaciones** compara la predicción con las existencias y propone:

- **Traslado**: otra sede tiene de sobra y esta necesita. Se sugiere antes que comprar.
- **Reabastecimiento**: hay que pedir al proveedor.

Cada recomendación explica en palabras por qué se sugiere, cuántas unidades y con qué prioridad. Las acciones:

| Acción | Efecto |
|---|---|
| **Aprobar** (traslado) | Crea una **solicitud de traslado**; todavía debe aprobarla la sede de origen y confirmarla la de destino |
| **Aprobar** (reabastecimiento) | Deja constancia de que se decidió comprar |
| **Registrar compra realizada** | Deja constancia de que el pedido ya se hizo fuera del sistema |
| **Rechazar** | Descarta la sugerencia; puede escribir el motivo |

Inventia no emite órdenes de compra: el pedido al proveedor se hace como lo hace hoy su empresa.

Al volver a generar recomendaciones, las pendientes anteriores se marcan como **reemplazadas** (quedan en el
historial) y las ya aprobadas no se duplican.

---

## 6. Reportes

**Inteligencia → Reportes.** Seleccione el tipo de reporte, aplique filtros (sede, fechas y otros según el tipo) y
verá una **vista previa**. Luego descargue en **CSV** o **Excel**.

| Reporte | Contenido |
|---|---|
| Inventario por sede | Existencias, estado y valoración por producto y sede |
| Ventas | Ventas por producto, sede y periodo (sin anuladas) |
| Movimientos de inventario | Historial filtrado |
| Traslados entre sedes | Solicitudes y su estado |
| Alertas de inventario | Activas y resueltas |
| Predicción de demanda | Valores estimados, modelo, error y confianza |
| Recomendaciones | Reabastecimiento y traslado con su estado |

Solo ve los reportes que su rol permite. Cada descarga queda registrada en la auditoría. Los CSV usan coma como
separador y se abren bien en Excel; los Excel incluyen una hoja de resumen con los criterios del reporte.

---

## 7. Administración

(Según permisos; normalmente solo administradores.)

### 7.1 Empresa

**Administración → Empresa** permite editar los datos generales y los **parámetros de inventario y predicción**:
plazo de entrega, días de seguridad, cobertura objetivo, horizonte, umbral de alerta, días sin rotación y plazo
de anulación. Estos valores gobiernan las alertas y las recomendaciones; si no los conoce, deje los
predeterminados y ajústelos con la experiencia.

### 7.2 Sedes

**Administración → Sedes**: crear, editar e inhabilitar sedes. Dos sedes de la misma empresa no pueden llamarse
igual (sin importar mayúsculas).

### 7.3 Usuarios

**Administración → Usuarios**: crear, buscar (por nombre, correo, rol, sede o estado), editar, inhabilitar y
reactivar.

- Al **crear** un usuario se le asigna rol y, si el rol es «de sede», una sede. El botón **Generar contraseña
  segura** crea una contraseña temporal; **cópiela y entréguela por un canal seguro**. El usuario deberá cambiarla
  al ingresar.
- **Restablecer contraseña**: asigna otra contraseña temporal y cierra las sesiones abiertas de esa persona.
- **Desbloquear**: quita el bloqueo por intentos fallidos.
- **Inhabilitar**: la persona pierde el acceso de inmediato, pero su historial se conserva.
- No puede inhabilitar su propia cuenta ni dejar a la empresa sin administradores activos.
- No puede asignar un rol con más permisos de los que usted tiene.

### 7.4 Roles y permisos

**Administración → Roles y permisos**: los cinco roles del sistema se pueden consultar pero no modificar. Puede
**crear roles propios** (por ejemplo «Auxiliar de consulta»), elegir su alcance (toda la empresa o una sola sede) y
marcar los permisos agrupados por módulo. Solo puede conceder permisos que usted mismo tiene.

### 7.5 Auditoría

**Administración → Auditoría** muestra quién hizo qué y cuándo: ingresos exitosos y fallidos, altas, cambios,
anulaciones, descargas de reportes. Se puede filtrar por módulo, acción, usuario, resultado y fechas. Los registros
no se pueden editar ni borrar. Los gerentes ven el historial de operaciones, pero no los accesos de otras personas.

### 7.6 Agentes de IA

**Administración → Agentes de IA** (administrador): crea **llaves de acceso** para que un asistente externo
consulte inventario, alertas, predicciones o recomendaciones. Los agentes **solo pueden leer**; nunca modifican
nada.

1. **Nueva llave**: nombre, qué puede consultar, sede (opcional) y vigencia.
2. El sistema muestra la llave **una sola vez**: cópiela y guárdela. No se puede volver a ver.
3. Si una llave se pierde o se filtra, **revóquela** y cree otra.

---

## 8. Mensajes frecuentes y qué hacer

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| «Correo o contraseña incorrectos» | Los datos no coinciden | Revise mayúsculas; use la recuperación si olvidó la contraseña |
| «Tu cuenta está bloqueada temporalmente» | Demasiados intentos fallidos | Espere el tiempo indicado o pida a un administrador que la desbloquee |
| «Existencias insuficientes de … hay X y se necesitan Y» | La operación pedía más de lo disponible | Corrija la cantidad; si cree que el saldo es erróneo, haga un ajuste por conteo físico |
| «No tienes permiso para realizar esta acción» | Su rol no incluye la acción | Pida a un administrador que revise su rol |
| «Su sesión terminó» | La sesión venció o cambió su contraseña | Vuelva a ingresar |
| «No se pudo conectar con el servidor» | Sin red o servicio detenido | Revise su conexión y reintente; si persiste, avise a quien administra el sistema |
| «Historial insuficiente» (predicción) | El producto tiene pocos días de ventas | Es esperado en productos nuevos; se calculará cuando haya al menos 28 días y 5 con ventas |
| «Solo se pueden confirmar traslados aprobados» | El traslado no está en la etapa correcta o ya lo confirmó otra persona | Actualice la página para ver su estado actual |

---

## 9. Glosario

| Término | Significado |
|---|---|
| **Sede** | Una ubicación física de la empresa con su propio inventario |
| **Existencias** | Unidades disponibles de un producto en una sede |
| **Consolidado** | Suma de las existencias de todas las sedes |
| **Stock mínimo / máximo** | Límites que definen cuándo hay poco o demasiado inventario |
| **Movimiento** | Cualquier cambio de existencias (entrada, salida, ajuste, venta, anulación, traslado) |
| **Cobertura** | Cuántos días alcanzan las existencias al ritmo de ventas previsto |
| **Plazo de entrega** | Días que tarda en llegar un pedido desde que se hace |
| **Demanda estimada** | Unidades que el sistema espera vender en un periodo. Es una estimación |
| **Intervalo de 80 %** | Rango en el que se espera que caiga la demanda en 8 de cada 10 casos |
| **WAPE** | Error relativo del pronóstico: 20 % significa que, en promedio, se equivocó en una quinta parte de lo vendido |
| **Línea base** | Pronóstico simple (promedio de 28 días) contra el que debe ganar cualquier modelo más complejo |
| **Recomendación** | Sugerencia calculada por el sistema que una persona debe aprobar o rechazar |
