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
8. [Sistema Integrado de Gestión (SIG)](#8-sistema-integrado-de-gestión-sig)
9. [Mensajes frecuentes y qué hacer](#9-mensajes-frecuentes-y-qué-hacer)
10. [Glosario](#10-glosario)

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
| Menú lateral | Las secciones a las que tiene acceso: Inventario, Operación, Inteligencia, SIG y Administración. El grupo **SIG** se despliega con sus cuatro apartados. En celular se abre con el botón de menú |
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

**Sistema Integrado de Gestión (SIG).** Todos los roles envían PQRS y consultan los apartados de Seguridad y Salud en
el Trabajo, Calidad y Gestión ambiental. Solo el Administrador gestiona (responde PQRS, configura las pausas, cambia el
estado de no conformidades y garantías, configura los parámetros ambientales). El Encargado de sede y el Usuario de
inventario además **reportan** no conformidades y garantías de su sede. Los detalles están en la
[sección 8](#8-sistema-integrado-de-gestión-sig).

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
4. Si quiere, escriba una **observación** (por ejemplo, «llegaron dos cajas golpeadas»). Queda como la primera del
   historial de esa entrada.
5. Pulse **Registrar entrada**.

Cada entrada queda registrada con su propio número. Para verla después, o agregarle más observaciones, vaya a
**Movimientos → Entradas de mercancía** y pulse la entrada. Las observaciones **se acumulan**: cada una conserva quién la
escribió y cuándo, y no se pueden editar ni borrar. Agregar una observación no cambia las existencias. Si la mercancía
llegó con un defecto, desde ese mismo detalle puede pulsar **Reportar no conformidad** y el reporte nace ya enlazado con la
entrada, sin volver a escribir sus datos (ver [8.3](#83-calidad-no-conformidades-y-garantías)).

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

## 8. Sistema Integrado de Gestión (SIG)

El menú lateral tiene un grupo **SIG** con cuatro apartados. Cada uno es una pantalla con el mismo estilo que el resto
de la aplicación y muestra solo lo que su rol permite.

### 8.1 PQRS y sugerencias

Sirve para que cualquier persona del sistema envíe una **petición**, una **queja**, un **reclamo** o una **sugerencia** y
vea cómo va su trámite.

**Enviar una solicitud (todos los roles)**

1. **SIG → PQRS y sugerencias → Nueva solicitud**.
2. Elija el **tipo**, escriba el **asunto** y la **descripción**. Su nombre, su sede y la fecha se registran solos.
3. Si quiere, adjunte **evidencias** (fotos JPG, PNG o WebP, o PDF; hasta 5 archivos de 3 MB cada uno).
4. Pulse **Enviar solicitud**. Aparece una confirmación con el número de radicado.

En **Mis solicitudes** ve las que ha enviado, el estado en que están (pendiente, en revisión, en proceso o resuelta), la
respuesta de la administración y el historial de cambios. Solo usted y la administración ven sus solicitudes.

**Gestionar las solicitudes (Administrador)**

1. En **Todas las solicitudes** filtre por tipo, estado, persona o fechas, o busque por asunto o número. Arriba ve cuántas
   hay en cada estado.
2. Abra una solicitud para leerla y ver sus evidencias.
3. Cambie el **estado** y/o escriba una **respuesta** o comentario. Para marcarla como **resuelta** es obligatorio responder.
4. Cada cambio queda en el historial con quién, cuándo y el comentario; el historial no se puede alterar.

> El sistema **no envía correos** cuando llega una solicitud. La administración debe revisar la bandeja y su contador de
> pendientes con regularidad.

### 8.2 Seguridad y Salud en el Trabajo (SST): pausas activas

**Qué verá si no es administrador.** Cada cierto tiempo de uso (60 minutos por defecto; lo configura la administración) se
abre una ventana de **pausa activa** con un mensaje, un ejercicio, las instrucciones paso a paso, el tiempo sugerido y
recomendaciones de postura, cuidado de los ojos, las manos y la forma de sentarse. Al terminar pulse **Realicé la pausa**;
si no es buen momento, pulse **Omitir por ahora**.

- La pausa **no aparece mientras tiene un formulario abierto, una venta o un traslado a medio armar, un guardado en curso
  o mientras está escribiendo** (espera unos segundos tras la última tecla); espera a que termine y se muestra después. No
  se pierde nada de lo que escribía. Si vuelve a la aplicación tras una ausencia, tiene un par de minutos antes de que aparezca.
- No se repite ni se muestra dos veces a la vez, ni aunque tenga la aplicación abierta en varias pestañas o recargue la página.
- Cada pausa queda registrada (fecha, persona, actividad y si la realizó u omitió).
- En **SIG → Seguridad y Salud en el Trabajo → Ejercicios** puede repasar todos los ejercicios cuando quiera, y en **Mi
  historial** ve sus propias pausas.

**Qué puede hacer el Administrador.** No recibe pausas automáticas, pero ve todo el contenido y puede abrir una **vista
previa** de cada pausa. Además tiene tres pestañas:

| Pestaña | Para qué sirve |
|---|---|
| **Cumplimiento** | Cuántas pausas se mostraron, realizaron y omitieron, por persona y por día |
| **Frecuencia** | Activar o desactivar las pausas automáticas y fijar el intervalo (de 1 a 480 minutos) |
| **Contenido** | Crear, editar, desactivar o eliminar los ejercicios (mensaje, instrucciones, duración y recomendaciones) |

### 8.3 Calidad: no conformidades y garantías

La pantalla tiene tres pestañas: **Guía** (qué es una no conformidad y una garantía, cuándo reportarlas y cómo hacerlo
bien), **No conformidades** y **Garantías**.

**Reportar una no conformidad** (Administrador, Encargado de sede y Usuario de inventario)

1. **SIG → Calidad → No conformidades → Reportar no conformidad**, o **Reportar no conformidad** desde el detalle de una
   entrada de mercancía.
2. Elija el producto y complete la referencia (si la hay), el **tipo** (defecto de fábrica, daño en transporte, producto
   equivocado, cantidad incorrecta, empaque deteriorado, no cumple la especificación u otro), la descripción, la fecha en
   que se detectó, la **cantidad afectada** y las observaciones. Puede adjuntar evidencias.
3. Si viene de una entrada, queda enlazada con ella.

Estados: **reportado → en revisión → en proceso de solución → resuelto → cerrado**. El Administrador cambia el estado,
asigna un responsable y registra la solución. Cada cambio y cada observación quedan en el historial.

**Reportar una garantía**

1. **SIG → Calidad → Garantías → Reportar garantía**.
2. Indique el producto y la cantidad, el **documento de respaldo** (factura de compra, entrada de inventario, venta u otro)
   con su referencia, la fecha de compra, hasta cuándo cubre la garantía, el defecto y las observaciones. Puede adjuntar
   evidencias.

Estados: **reportada → pendiente de revisión → enviada al proveedor → aprobada o rechazada → solucionada → cerrada**. El
Administrador registra el proveedor, la fecha de envío, la **respuesta del proveedor**, la solución y su fecha, y asigna
un responsable.

> **Reportar o gestionar una no conformidad o una garantía nunca cambia las existencias.** Si hay que sacar la mercancía
> defectuosa del inventario, registre una **salida** (motivo «Deterioro» o «Devolución al proveedor») como siempre; así el
> movimiento queda con su propio responsable y no se descuenta dos veces.

### 8.4 Gestión ambiental

Muestra cuántos **vehículos eléctricos** se han vendido y una **estimación** del CO₂ que ayudan a evitar. Se alimenta solo:
cada venta confirmada se contabiliza automáticamente, y si se anula deja de sumar. No hay que registrar nada a mano.

Tiene cuatro pestañas:

| Pestaña | Qué muestra |
|---|---|
| **Panel** | Vehículos vendidos (dato **real**) y CO₂ evitado (**estimación**) del año elegido, acumulado por mes y por año, gráficos mensual y anual y distribución por tipo de vehículo. Se puede filtrar por año y por sede |
| **Historial** | Cada venta de vehículos contabilizada, con filtros (estado, tipo, sede, fechas, con o sin CO₂ estimado) y enlace a la venta |
| **Metodología** | La fórmula, un ejemplo con números redondos (no son datos de la empresa), los parámetros vigentes y las reglas de conteo |
| **Configuración** (solo Administrador) | Qué categorías son vehículos y con qué parámetros se estima el CO₂ |

**Importante: sin parámetros no hay cifra de CO₂.** Los vehículos vendidos se cuentan siempre, pero el CO₂ solo se calcula
cuando el Administrador configura los datos. Mientras tanto el panel muestra «Pendiente de parametrización» en vez de un
número. Para configurarlo:

1. **SIG → Gestión ambiental → Configuración**.
2. Defina el **factor de emisión de la red eléctrica** (kg de CO₂ por kWh), su año y su fuente. La pantalla ofrece como
   ayuda el valor publicado por la UPME; revíselo y confirme que sigue vigente antes de guardarlo.
3. Marque cada **categoría que sea vehículo** (por ejemplo, Bicicletas eléctricas) y complete su tipo, propulsión, recorrido
   anual estimado (km), consumo eléctrico (kWh por 100 km), la emisión del vehículo de combustión con el que se compara (g
   de CO₂ por km) y la fuente de esos datos.
4. Si ya había ventas, pulse **Incorporar ventas anteriores** para contarlas y calcular su CO₂.

Los datos de referencia deben salir de fuentes oficiales o técnicas y quedar documentados en el campo «fuente». Cada
registro conserva los parámetros con los que se calculó: cambiar la configuración después **no altera** lo ya calculado.

---

## 9. Mensajes frecuentes y qué hacer

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
| «Pendiente de parametrización» (gestión ambiental) | Faltan el factor de la red o los parámetros de la categoría | Pida al Administrador que los configure en **SIG → Gestión ambiental → Configuración** |
| «El registro está cerrado: no admite más archivos» | Una PQRS resuelta, o una no conformidad o garantía cerrada, ya no recibe evidencias | Si falta algo, registre una nueva solicitud o agregue una observación |

---

## 10. Glosario

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
| **SIG** | Sistema Integrado de Gestión: PQRS, seguridad y salud en el trabajo, calidad y gestión ambiental |
| **PQRS** | Petición, queja, reclamo o sugerencia |
| **SST** | Seguridad y Salud en el Trabajo; aquí, las pausas activas |
| **Pausa activa** | Breve descanso con un ejercicio guiado para cuidar el cuerpo durante la jornada |
| **No conformidad** | Producto o proceso que no cumple lo acordado o esperado (defecto, daño, producto equivocado…) |
| **Garantía** | Reclamo al proveedor por un defecto cubierto, desde que se reporta hasta que se soluciona |
| **Evidencia** | Foto o PDF que respalda una PQRS, una no conformidad o una garantía |
| **CO₂ evitado** | Estimación de las emisiones que se ahorran al usar un vehículo eléctrico en lugar de uno de combustión; depende de los parámetros configurados |
| **Factor de emisión de la red** | Kilogramos de CO₂ que genera la electricidad por cada kWh |
