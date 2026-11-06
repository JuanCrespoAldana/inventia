"""Conocimiento del sistema que usa el asistente: glosario, guías paso a paso y temas que Inventia no registra.

Son datos puros (sin consultas): salen del manual de usuario y de las reglas reales del código (alertas, recomendaciones,
predicción). Los patrones se escriben sobre el texto ya normalizado (minúsculas, sin tildes ni signos).
"""

import re
from dataclasses import dataclass


# Formas de los verbos con que se pregunta «cómo se hace» una tarea (primera persona, tercera persona e infinitivo).
VERBOS_TAREAS: frozenset[str] = frozenset(
    """registro registra registrar creo crea crear anulo anula anular apruebo aprueba aprobar rechazo rechaza rechazar solicito solicita solicitar confirmo confirma confirmar
    cancelo cancela cancelar ajusto ajusta ajustar cambio cambia cambiar genero genera generar envio envia enviar reporto reporta reportar configuro configura configurar
    defino define definir restablezco restablece restablecer recupero recupera recuperar desbloqueo desbloquea desbloquear inhabilito inhabilita inhabilitar activo activa activar
    elimino elimina eliminar saco saca sacar agrego agrega agregar anado anade anadir ingreso ingresa ingresar cierro cierra cerrar cargo carga cargar muevo mueve mover
    resuelvo resuelve resolver respondo responde responder pido pide pedir compro compra comprar vendo vende vender devuelvo devuelve devolver reactivo reactiva reactivar
    edito edita editar modifico modifica modificar actualizo actualiza actualizar pongo pone poner habilito habilita habilitar borro borra borrar hago hace hacer
    recalculo recalcula recalcular quito quita quitar reviso revisar reclamo reclama reclamar radico radica radicar presento presenta presentar descargo descarga descargar
    importo importa importar subo sube subir recibo recibe recibir reabastezco reabastece reabastecer facturo factura facturar cuadro cuadra cuadrar corrijo corrige corregir
    inicio inicia iniciar mando manda mandar traslado traslada trasladar entro entra entrar salgo sale salir accedo accede acceder desactivo desactiva desactivar
    bloqueo bloquea bloquear asigno asigna asignar fijo fija fijar establezco establece establecer llevo lleva llevar doy da dar realizo realiza realizar emito emite emitir""".split()
)

VERSION_SISTEMA = "1.1.0"  # debe coincidir con la versión de la API (hay una prueba que lo verifica)


def _r(patron: str) -> re.Pattern:
    return re.compile(patron)


# ================================================================================================== glosario
@dataclass(frozen=True)
class Termino:
    clave: str
    nombre: str
    patron: re.Pattern
    definicion: str
    detalle: tuple[str, ...] = ()
    ruta: str | None = None
    parametro: str | None = None  # clave del parámetro de la empresa cuyo valor se muestra
    sugerencias: tuple[str, ...] = ()


def _t(clave: str, nombre: str, patron: str, definicion: str, detalle: tuple[str, ...] = (), ruta: str | None = None,
       parametro: str | None = None, sugerencias: tuple[str, ...] = ()) -> Termino:
    return Termino(clave, nombre, _r(patron), definicion, detalle, ruta, parametro, sugerencias)


# El orden importa: el primer término que coincide gana (los más específicos van antes).
GLOSARIO: tuple[Termino, ...] = (
    # ------------------------------------------------------------------------------------------ existencias
    _t("stock_minimo", "Stock mínimo", r"\b(stock|existencias?|inventario|nivel|cantidad)? ?minim[oa]s?\b",
       "Es la cantidad mínima que quieres tener de un producto en una sede. Cuando las existencias llegan a ese nivel (o quedan por debajo), el producto pasa al estado «Bajo» y se abre una alerta de inventario bajo.",
       ("Se define por producto y por sede, en Existencias, con el icono de niveles.",
        "También es el piso del punto de reposición que usan las recomendaciones de reabastecimiento.",
        "Un producto sin mínimo definido no genera alertas de inventario bajo (salvo que se agote y se venda con regularidad)."),
       "/inventario", sugerencias=("¿Qué productos no tienen stock mínimo definido?", "¿Qué productos están por debajo del mínimo?")),
    _t("stock_maximo", "Stock máximo", r"\b(stock|existencias?|inventario|nivel|cantidad)? ?maxim[oa]s?\b",
       "Es la cantidad más alta que quieres tener de un producto en una sede (es opcional). Si las existencias lo superan, el producto pasa al estado «Excesivo» y se abre una alerta de inventario excesivo.",
       ("No puede ser menor que el mínimo.", "Además limita las cantidades que el sistema recomienda al reabastecer."), "/inventario",
       sugerencias=("¿Qué productos tienen exceso de inventario?",)),
    _t("agotado", "Agotado", r"\b(producto |estado )?(agotad[oa]s?|sin existencias|sin stock|stock cero|en cero)\b",
       "Un producto está agotado cuando no le quedan unidades en una sede (existencias en cero).",
       ("Si tiene un mínimo definido, o se vende con regularidad, abre una alerta **crítica** de inventario bajo.", "Las ventas y salidas no permiten sacar más de lo que hay: el sistema rechaza la operación."),
       "/alertas", sugerencias=("¿Qué productos están agotados?",)),
    _t("excesivo", "Inventario excesivo", r"\b(exceso|excesiv[oa]s?|sobrestock|sobre ?stock|sobre ?inventario|sobreinventario|inventario de mas)\b",
       "Es cuando un producto tiene más unidades que su stock máximo. Es dinero parado en bodega.",
       ("La alerta es de prioridad **media** si las existencias superan el 150 % del máximo, y **baja** si no.", "Solo se evalúa si el producto tiene un máximo definido."),
       "/alertas", sugerencias=("¿Qué productos tienen exceso de inventario?", "¿Cuánto capital tengo inmovilizado?")),
    _t("estado_bajo", "Estado «Bajo»", r"\b(estado )?(inventario|stock) bajo\b|\bestado bajo\b|\bnivel bajo\b|\bpor debajo del minimo\b",
       "Un producto está «Bajo» cuando sus existencias son iguales o inferiores al mínimo definido, pero todavía le quedan unidades.",
       ("Abre una alerta de inventario bajo: **alta** si queda la mitad del mínimo o menos, **media** si está entre la mitad y el mínimo.",),
       "/alertas", sugerencias=("¿Qué productos están bajos de stock?",)),
    _t("estados_stock", "Estados de las existencias", r"\bestados? (de|del|de las) (stock|inventario|existencias|productos?)\b|\bniveles? de (stock|inventario)\b|\btipos? de estados?\b",
       "Cada producto, en cada sede, está en uno de cuatro estados según sus existencias frente a los límites que definiste.",
       ("**Normal**: dentro de los límites.", "**Bajo**: igual o por debajo del mínimo.", "**Agotado**: sin unidades.", "**Excesivo**: por encima del máximo."),
       "/inventario", sugerencias=("¿Cómo está el inventario?",)),
    _t("consolidado", "Inventario consolidado", r"\b(inventario )?consolidad[oa]\b",
       "Es la suma de las existencias de todas las sedes de la empresa, con el detalle de cómo se reparten.",
       ("El total siempre se calcula a partir de las sedes: no se puede editar a mano.", "Lo ven los roles con permiso de inventario consolidado (administrador, gerente, analista de compras)."),
       "/inventario/consolidado", sugerencias=("¿Cómo está el inventario por sede?",)),
    _t("valor_inventario", "Valor del inventario", r"\bvalor (del |de |total del )?(inventario|stock|mercancia|existencias)\b|\bvaloracion\b|\binventario valorizado\b",
       "Es el dinero que tienes invertido en mercancía: unidades en existencia × costo de cada producto.",
       ("Los productos sin costo registrado no se incluyen en la valoración (los reportes lo advierten).", "No es lo que obtendrías al vender: para eso se usa el precio de venta."),
       "/inventario", sugerencias=("¿Cuánto vale el inventario?", "¿Qué productos no tienen costo?")),
    _t("existencias", "Existencias", r"\b(existencias?|stock|inventario|saldo)\b",
       "Son las unidades que hay disponibles de un producto en una sede. El inventario de la empresa es el conjunto de las existencias de todas sus sedes.",
       ("Cambian con entradas, salidas, ajustes, ventas, anulaciones y traslados confirmados.", "Nunca pueden quedar en negativo: si una operación pide más de lo que hay, el sistema la rechaza."),
       "/inventario", sugerencias=("¿Cuántas unidades tenemos en total?",)),
    # ------------------------------------------------------------------------------------------ movimientos
    _t("kardex", "Kardex / movimientos", r"\b(kardex|movimientos?( de inventario)?|historial de (movimientos|inventario))\b",
       "Es el historial de cada cambio de existencias: entradas, salidas, ajustes, ventas, anulaciones y traslados, con quién lo hizo, cuándo y el saldo antes y después.",
       ("No se puede editar ni eliminar: si algo salió mal se corrige con otro movimiento (por ejemplo un ajuste).",), "/movimientos",
       sugerencias=("Últimos movimientos", "Movimientos de hoy")),
    _t("entrada", "Entrada de mercancía", r"\bentradas?( de (mercancia|inventario|productos?))?\b",
       "Es el registro de mercancía que llega a una sede: compra, devolución de cliente, inventario inicial, producción u otro motivo.",
       ("Cada entrada queda con su propio número y permite observaciones acumulativas (nadie las edita ni las borra).", "Si la mercancía llegó con un defecto se puede reportar una no conformidad desde la misma entrada."),
       "/inventario", sugerencias=("¿Cómo registro una entrada?", "Últimas entradas")),
    _t("salida", "Salida de mercancía", r"\bsalidas?( de (mercancia|inventario|productos?))?\b",
       "Es una disminución de existencias que no es una venta: pérdida, deterioro, consumo interno, devolución al proveedor u otro motivo.",
       ("Las ventas no se registran como salidas: tienen su propia pantalla.", "Si la cantidad supera lo disponible, el sistema no registra nada."),
       "/inventario", sugerencias=("¿Cómo registro una salida?",)),
    _t("ajuste", "Ajuste de inventario", r"\bajustes?( de (inventario|stock|existencias))?\b|\bconteo fisico\b|\binventario fisico\b",
       "Es la corrección de las existencias de un producto cuando lo que cuentas físicamente no coincide con lo que dice el sistema.",
       ("Indicas la cantidad real contada, el motivo y una observación obligatoria; el sistema calcula la diferencia y la registra como movimiento.", "Nada se borra: el historial conserva el saldo anterior y el nuevo."),
       "/inventario", sugerencias=("¿Cómo ajusto el inventario?", "Últimos ajustes de inventario")),
    _t("merma", "Merma o pérdida", r"\bmermas?\b|\bperdidas? de (inventario|mercancia)\b|\bdeterioro\b|\bdesperdicio\b",
       "Es la mercancía que se pierde o se daña y deja de estar disponible para vender. En Inventia se registra como una **salida** con motivo «Pérdida» o «Deterioro».",
       ("Así queda con responsable, fecha y motivo en el historial.", "Si el defecto viene del proveedor, además puede reportarse una no conformidad o una garantía."),
       "/inventario", sugerencias=("¿Cuántas mermas hubo este mes?",)),
    _t("anulacion", "Anulación de una venta", r"\banulacion(es)?\b|\bventas? anulad[oa]s?\b",
       "Anular una venta la deja marcada como anulada (no se borra) y devuelve las unidades al inventario con un movimiento nuevo.",
       ("Solo se puede anular dentro del plazo que define la empresa y una sola vez.", "Las ventas anuladas no cuentan en los reportes de ventas ni en la predicción."),
       "/ventas", parametro="dias_max_anulacion", sugerencias=("¿Cuántas ventas se anularon este mes?",)),
    # ------------------------------------------------------------------------------------------ indicadores
    _t("cobertura", "Cobertura (días de cobertura)", r"\bcobertura\b|\bdias (que|de) (dura|alcanza|duran|alcanzan)\b|\bcuanto (dura|alcanza)\b",
       "Es cuántos días alcanzan las existencias de un producto al ritmo de ventas previsto: existencias ÷ demanda diaria prevista.",
       ("Se calcula con la última predicción vigente: sin predicción no hay cobertura.", "Si la cobertura es menor que el plazo de entrega, el producto se agota antes de que llegue un pedido: por eso abre una alerta de riesgo de desabastecimiento."),
       "/alertas", sugerencias=("¿Cuántos días me dura el inventario?", "¿Qué productos se van a agotar pronto?")),
    _t("dias_inventario", "Días de inventario", r"\bdias de inventario\b|\bdias de stock\b",
       "Son los días que durarían las existencias actuales si se siguiera vendiendo al ritmo reciente: existencias ÷ promedio diario vendido.",
       ("A diferencia de la cobertura, parte de las ventas reales recientes y no de la predicción.",), "/inventario", sugerencias=("¿Cuántos días de inventario tenemos?",)),
    _t("rotacion", "Rotación de inventario", r"\brotacion\b|\brotar\b",
       "Mide qué tan rápido se vende lo que tienes: cuántas veces se vendió, en un periodo, el equivalente a tus existencias actuales (unidades vendidas ÷ existencias).",
       ("Rotación alta: el producto se mueve rápido. Rotación baja: se queda en bodega.", "Un producto con existencias y sin ventas durante el número de días configurado se marca «Requiere revisión»."),
       "/inventario", parametro="dias_sin_rotacion", sugerencias=("¿Cuál es la rotación del inventario?", "Productos de baja rotación")),
    _t("abc", "Clasificación ABC (Pareto)", r"\b(clasificacion |analisis )?abc\b|\bpareto\b|\b80 ?[-/y ] ?20\b",
       "Ordena los productos por lo que aportan a las ventas. **A**: los que suman cerca del 80 % de lo vendido. **B**: hasta el 95 %. **C**: el resto.",
       ("Sirve para decidir dónde poner más atención: pocos productos A explican la mayor parte del negocio.", "Se calcula con el valor vendido en el periodo que elijas."),
       "/ventas", sugerencias=("Clasificación ABC del inventario",)),
    _t("margen", "Margen y utilidad", r"\bmargen(es)?( bruto| de ganancia| de utilidad)?\b|\butilidad\b|\bganancia\b|\brentabilidad\b",
       "La **utilidad** es lo vendido menos lo que costó: (precio de venta − costo) × unidades. El **margen** es esa utilidad como porcentaje de lo vendido.",
       ("Los productos sin costo registrado no entran en el cálculo (se avisa cuánto se dejó por fuera).", "Es un margen bruto: no descuenta arriendo, nómina ni otros gastos que Inventia no maneja."),
       "/ventas", sugerencias=("¿Cuánta utilidad dejaron las ventas este mes?", "¿Qué productos tienen mayor margen?")),
    _t("ticket", "Ticket promedio", r"\bticket( promedio)?\b|\bventa promedio\b|\bvalor promedio (de la |por )?venta\b",
       "Es lo que vale, en promedio, cada venta: total vendido ÷ número de ventas.",
       ("Si sube, cada venta deja más; si baja, hay más ventas pequeñas.",), "/ventas", sugerencias=("¿Cuál es el ticket promedio?",)),
    _t("costo_precio", "Costo y precio de venta", r"\b(costo|precio) (de |del )?(compra|venta|producto|unitario)?\b|\bcosto\b",
       "El **costo** es lo que te cuesta cada unidad; el **precio de venta** es lo que cobras. Ambos viven en la ficha del producto.",
       ("El precio se propone en cada venta y puede cambiarse en esa venta.", "Sin costo no se puede valorar el inventario ni calcular utilidad."), "/productos",
       sugerencias=("¿Qué productos no tienen costo?", "Lista de precios")),
    _t("codigo_producto", "Código (SKU) del producto", r"\b(sku|codigo|referencia) (del |de )?(producto|articulo)?\b|\bsku\b",
       "El código es el identificador único de cada producto (por ejemplo BAT-001). Con él lo buscas en ventas, traslados y reportes.",
       ("No se puede cambiar una vez creado, porque identifica al producto en todo el historial.", "Un producto inhabilitado deja de aparecer para operar, pero conserva su historial y puede reactivarse."), "/productos"),
    # ------------------------------------------------------------------------------------------ traslados
    _t("traslado", "Traslado entre sedes", r"\btraslados?\b|\btransferencias?\b",
       "Es el movimiento de mercancía de una sede a otra. Pasa por tres etapas: **Solicitado → Aprobado → Confirmado**.",
       ("Cualquier sede involucrada puede solicitarlo; la sede de origen lo aprueba (o lo rechaza con motivo) y la de destino confirma la recepción.",
        "Las existencias solo se mueven al confirmar: se descuentan del origen y se suman al destino en una sola operación.",
        "También puede quedar **Rechazado** o **Cancelado**. Una sede o un producto con traslados pendientes no se puede inhabilitar."),
       "/traslados", sugerencias=("¿Cómo solicito un traslado?", "¿Qué traslados están pendientes?")),
    # ------------------------------------------------------------------------------------------ alertas
    _t("prioridad_alerta", "Prioridad de las alertas", r"\bprioridad(es)?\b|\b(alerta|alertas) (critica|alta|media|baja)s?\b|\bcritic[oa]s?\b",
       "Las alertas se ordenan en cuatro prioridades: **crítica**, **alta**, **media** y **baja**. Las reglas dependen del tipo de alerta.",
       ("Inventario bajo: crítica si está agotado, alta si queda la mitad del mínimo o menos, media en el resto.",
        "Riesgo de desabastecimiento: crítica si la cobertura es menor que el plazo de entrega, alta si es menor que plazo + días de seguridad, media en el resto. Si la estimación es de baja confianza, no pasa de media.",
        "Inventario excesivo: media si supera el 150 % del máximo, baja en el resto. Requiere revisión: baja."),
       "/alertas", sugerencias=("¿Qué alertas críticas hay?",)),
    _t("riesgo_desabastecimiento", "Riesgo de desabastecimiento", r"\b(riesgo de )?desabastecimiento\b|\bquiebre de stock\b",
       "Es una alerta que avisa cuando las existencias no alcanzan para cubrir el plazo de entrega según la demanda prevista: te quedarías sin producto antes de que llegue un pedido.",
       ("Se abre cuando la cobertura baja del umbral de alerta (o de plazo de entrega + días de seguridad, el mayor).", "Necesita una predicción vigente para el producto."),
       "/alertas", parametro="umbral_cobertura_alerta_dias", sugerencias=("¿Qué productos se van a agotar pronto?",)),
    _t("requiere_revision", "Requiere revisión", r"\brequiere revision\b|\bsin movimiento\b|\bproducto(s)? (parado|estancado|dormido)s?\b",
       "Es una alerta de prioridad baja: el producto tiene existencias pero no ha tenido ventas ni salidas en mucho tiempo, así que conviene revisar si sigue vigente.",
       ("El tiempo se configura en los parámetros de la empresa (días sin rotación).",), "/alertas", parametro="dias_sin_rotacion",
       sugerencias=("Productos sin ventas en los últimos 60 días",)),
    _t("alerta", "Alertas de inventario", r"\balertas?\b",
       "Son avisos automáticos de lo que requiere atención. Hay cuatro tipos: **inventario bajo**, **inventario excesivo**, **riesgo de desabastecimiento** y **requiere revisión**.",
       ("Se abren y se cierran solas cuando cambian las existencias; el botón «Recalcular alertas» las vuelve a evaluar todas (útil tras cambiar mínimos o parámetros).", "Se ordenan por prioridad: crítica, alta, media y baja."),
       "/alertas", sugerencias=("¿Qué alertas críticas hay?", "¿Qué debo revisar hoy?")),
    # ------------------------------------------------------------------------------------------ predicción
    _t("intervalo", "Intervalo de 80 %", r"\bintervalo( de confianza| de 80)?\b|\brango (probable|de la prediccion)\b|\bbanda\b",
       "Es el rango dentro del cual se espera que caiga la demanda real en cerca de 8 de cada 10 casos. Se muestra junto a la demanda estimada.",
       ("En las pruebas con datos de demostración cubrió entre 78 % y 83 %; con tus datos puede variar, así que es una guía y no una garantía.",),
       "/predicciones", sugerencias=("¿Qué se va a vender el próximo mes?",)),
    _t("wape", "WAPE", r"\bwape\b", "Es el error relativo del pronóstico: un 20 % significa que, en promedio, el modelo se equivocó en una quinta parte de lo vendido.",
       ("Es la medida principal para comparar modelos y para calcular la confianza.", "Entre más bajo, mejor."), "/predicciones"),
    _t("rmse", "RMSE", r"\brmse\b", "Es el error típico del pronóstico en unidades por día; pesa más los errores grandes.", (), "/predicciones"),
    _t("mape", "MAPE", r"\bmape\b", "Es el error porcentual medio, calculado solo en los días con ventas (con venta cero no se puede calcular).", (), "/predicciones"),
    _t("mae", "MAE", r"\bmae\b", "Es el error absoluto medio: cuántas unidades se equivoca el pronóstico por día, en promedio.", (), "/predicciones"),
    _t("linea_base", "Línea base", r"\blinea base\b|\bbaseline\b",
       "Es un pronóstico simple (el promedio de 28 días) contra el que debe ganar cualquier modelo más complejo. Si ningún modelo lo supera, se usa la línea base.",
       ("Evita que el sistema presente como «inteligente» algo que no mejora al promedio.",), "/predicciones"),
    _t("confianza", "Confianza de la predicción", r"\bconfianza\b|\bfiabilidad\b|\bconfiable\b",
       "Indica qué tan fiable es el pronóstico de un producto en una sede: **alta**, **media** o **baja**.",
       ("Alta: error (WAPE) de 35 % o menos, al menos 56 días de historia, 20 días con ventas y 2 validaciones.", "Media: error de 70 % o menos y al menos 10 días con ventas.", "Baja: el resto. Con confianza baja, tómala solo como orientación (y no genera alertas de máxima urgencia)."),
       "/predicciones", sugerencias=("¿Qué tan confiable es la predicción?",)),
    _t("modelos", "Modelos de predicción", r"\b(modelos?|algoritmos?|metodos?|tecnica)s? (de |para )?(la )?(prediccion|pronostico|demanda|ia)\b|\bque modelos?\b|\bgradient\b|\bcroston\b|\bsuavizado\b",
       "Para cada producto y sede el sistema prueba varios modelos y se queda con el que mejor acierta en datos que no vio al entrenarse.",
       ("Promedio de 7 y de 28 días, perfil semanal, demanda intermitente (Croston), suavizado exponencial estacional y gradient boosting.", "Si ninguno supera a la línea base, usa la línea base.", "Si no hay historial suficiente no inventa un número: lo lista en «Series sin pronóstico»."),
       "/predicciones", sugerencias=("¿Cómo se calcula la predicción?",)),
    _t("horizonte", "Horizonte de predicción", r"\bhorizonte\b",
       "Es cuántos días hacia adelante se calcula la predicción (por ejemplo 14 días). Se elige al generarla y la empresa tiene un valor por defecto.",
       ("A mayor horizonte, mayor incertidumbre.",), "/predicciones", parametro="horizonte_dias"),
    _t("prediccion", "Predicción de demanda", r"\bprediccion(es)?\b|\bpronostico\b|\bdemanda( estimada| prevista)?\b",
       "Es una estimación de cuántas unidades se venderán de cada producto en cada sede durante los próximos días. Es una **estimación**, no una venta ni una promesa.",
       ("Siempre se muestra con su rango probable (intervalo de 80 %) y su nivel de confianza.", "Necesita al menos 28 días de historia y 5 días con ventas por producto.", "Se genera en Inteligencia → Predicción de demanda y alimenta las alertas de desabastecimiento y las recomendaciones."),
       "/predicciones", sugerencias=("¿Qué se va a vender el próximo mes?", "¿Cómo genero una predicción?")),
    _t("punto_reposicion", "Punto de reposición y nivel objetivo", r"\bpunto de (reposicion|reorden|pedido)\b|\bnivel objetivo\b|\bcantidad sugerida\b",
       "El **punto de reposición** es el nivel en el que conviene pedir: demanda diaria × (plazo de entrega + días de seguridad), nunca menos que el stock mínimo. El **nivel objetivo** es hasta dónde reponer: demanda diaria × (plazo + seguridad + cobertura objetivo), sin pasar del máximo.",
       ("Se recomienda reabastecer cuando existencias + lo que viene en camino ≤ punto de reposición, por la diferencia hasta el nivel objetivo.",),
       "/recomendaciones", sugerencias=("¿Qué debo reponer esta semana?",)),
    _t("recomendacion", "Recomendaciones", r"\brecomendacion(es)?\b|\bsugerencias? de (compra|reposicion)\b",
       "Son sugerencias que calcula el sistema comparando la predicción con las existencias. Una persona siempre debe aprobarlas o rechazarlas: nunca mueven inventario ni compran solas.",
       ("**Traslado**: otra sede tiene de sobra y esta necesita; se sugiere antes que comprar.", "**Reabastecimiento**: hay que pedir al proveedor.",
        "Cada una trae el porqué en palabras, las unidades y la prioridad. Al volver a generarlas, las pendientes anteriores quedan como «reemplazadas»."),
       "/recomendaciones", sugerencias=("¿Qué debería comprar?", "Recomendaciones pendientes")),
    _t("reabastecimiento", "Reabastecimiento", r"\breabastec\w+|\breposicion\b|\breponer\b",
       "Es volver a surtir un producto cuando se está acabando. Inventia lo sugiere como recomendación de tipo «reabastecimiento», pero la compra al proveedor se hace fuera del sistema.",
       ("Al aprobarla dejas constancia de que se decidió comprar; «Registrar compra realizada» deja constancia de que el pedido ya se hizo.", "Cuando llega la mercancía se registra como una entrada."),
       "/recomendaciones", sugerencias=("¿Qué debo reponer esta semana?",)),
    # ------------------------------------------------------------------------------------------ parámetros
    _t("plazo_entrega", "Plazo de entrega", r"\bplazo de entrega\b|\blead ?time\b|\btiempo de entrega\b|\bplazo del proveedor\b",
       "Son los días que tarda en llegar un pedido desde que se hace. Se usa para saber con cuánta anticipación hay que reabastecer.",
       ("Se configura para toda la empresa en Administración → Empresa.",), "/empresa", parametro="plazo_entrega_dias"),
    _t("dias_seguridad", "Días de seguridad", r"\bdias de seguridad\b|\bstock de seguridad\b|\bcolchon\b|\binventario de seguridad\b",
       "Es un colchón de días que se suma al plazo de entrega para cubrir demoras o ventas por encima de lo previsto.",
       ("Se configura en Administración → Empresa.",), "/empresa", parametro="dias_seguridad"),
    _t("cobertura_objetivo", "Cobertura objetivo", r"\bcobertura objetivo\b|\bdias de cobertura objetivo\b",
       "Son los días de demanda que se quiere cubrir al reabastecer, además del plazo de entrega y los días de seguridad.",
       ("Define hasta dónde sugiere reponer el sistema (nivel objetivo).",), "/empresa", parametro="dias_cobertura_objetivo"),
    _t("umbral_alerta", "Umbral de cobertura de alerta", r"\bumbral\b",
       "Es la cobertura (en días) por debajo de la cual se abre una alerta de riesgo de desabastecimiento.",
       ("Se configura en Administración → Empresa.",), "/empresa", parametro="umbral_cobertura_alerta_dias"),
    _t("parametros", "Parámetros de la empresa", r"\bparametros?( de (la )?(empresa|inventario|prediccion|sistema))?\b|\bconfiguracion de la empresa\b",
       "Son los valores que gobiernan las alertas y las recomendaciones: plazo de entrega, días de seguridad, cobertura objetivo, horizonte, umbral de alerta, días sin rotación y plazo de anulación.",
       ("Los edita el administrador en Administración → Empresa; si no los conoces, deja los predeterminados y ajústalos con la experiencia.", "Tras cambiarlos conviene pulsar «Recalcular alertas»."),
       "/empresa", sugerencias=("¿Cuáles son los parámetros de la empresa?",)),
    # ------------------------------------------------------------------------------------------ SIG
    _t("pqrs", "PQRS", r"\bpqrs\b|\bpeticion(es)?, quejas\b",
       "Significa **Petición, Queja, Reclamo y Sugerencia**. Es el canal para que cualquier persona del sistema envíe una solicitud y vea cómo va su trámite.",
       ("Estados: pendiente → en revisión → en proceso → resuelta. Para resolverla hay que responder.", "Puedes adjuntar hasta 5 evidencias (fotos JPG, PNG o WebP, o PDF de hasta 3 MB).", "El sistema no envía correos cuando llega una: la administración debe revisar la bandeja."),
       "/sig/pqrs", sugerencias=("¿Cuántas PQRS hay pendientes?", "¿Cómo envío una PQRS?")),
    _t("sig", "SIG (Sistema Integrado de Gestión)", r"\bsig\b|\bsistema integrado( de gestion)?\b",
       "Es el conjunto de cuatro módulos de gestión de la empresa: **PQRS**, **Seguridad y Salud en el Trabajo** (pausas activas), **Calidad** (no conformidades y garantías) y **Gestión ambiental**.",
       ("Todos los roles envían PQRS y consultan los otros tres; solo el administrador gestiona.",), "/sig/pqrs", sugerencias=("¿Qué módulos tiene el sistema?",)),
    _t("sst", "SST y pausas activas", r"\bsst\b|\bseguridad y salud\b|\bpausas? activas?\b",
       "SST es **Seguridad y Salud en el Trabajo**. En Inventia se trabaja con **pausas activas**: breves descansos con un ejercicio guiado que aparecen cada cierto tiempo de uso para cuidar el cuerpo.",
       ("El intervalo lo configura el administrador (60 minutos por defecto).", "La pausa no interrumpe un formulario abierto ni una venta a medio armar; se muestra después.", "Cada pausa queda registrada (realizada u omitida)."),
       "/sig/sst", sugerencias=("¿Cuántas pausas activas se han realizado?",)),
    _t("no_conformidad", "No conformidad", r"\bno ?conformidad(es)?\b",
       "Es un producto o proceso que no cumple lo acordado o esperado: defecto de fábrica, daño en transporte, producto equivocado, cantidad incorrecta, empaque deteriorado o incumplimiento de especificación.",
       ("Estados: reportado → en revisión → en proceso de solución → resuelto → cerrado.", "Reportarla o gestionarla nunca cambia las existencias: si hay que sacar mercancía, se registra una salida aparte."),
       "/sig/calidad", sugerencias=("¿Cómo reporto una no conformidad?", "No conformidades sin cerrar")),
    _t("garantia", "Garantía", r"\bgarantias?\b",
       "Es un reclamo al proveedor por un defecto cubierto, desde que se reporta hasta que se soluciona.",
       ("Estados: reportada → pendiente de revisión → enviada al proveedor → aprobada o rechazada → solucionada → cerrada.", "Guarda el documento de respaldo, la fecha de compra y hasta cuándo cubre."),
       "/sig/calidad", sugerencias=("Garantías vigentes", "¿Hay garantías por vencer?")),
    _t("evidencia", "Evidencia", r"\bevidencias?\b|\badjuntos?\b|\barchivos? adjuntos?\b",
       "Es una foto (JPG, PNG o WebP) o un PDF que respalda una PQRS, una no conformidad o una garantía. Se permiten hasta 5 archivos de 3 MB cada uno.",
       ("Cuando el registro se cierra, ya no admite más archivos.",), "/sig/pqrs"),
    _t("co2", "CO₂ evitado", r"\bco2\b|\bhuella de carbono\b|\bemisiones?\b|\bgestion ambiental\b|\bfactor de emision\b",
       "Es una **estimación** de las emisiones que se ahorran al usar un vehículo eléctrico en lugar de uno de combustión. Se calcula por cada venta de vehículos eléctricos.",
       ("Depende de los parámetros que configure el administrador (factor de emisión de la red eléctrica y datos de cada categoría de vehículo): sin ellos el panel dice «Pendiente de parametrización».", "Los vehículos vendidos son un dato real; el CO₂ es la estimación.", "Cada registro conserva los parámetros con que se calculó: cambiarlos después no altera lo ya calculado."),
       "/sig/ambiental", sugerencias=("¿Cuánto CO₂ evitamos este año?",)),
    # ------------------------------------------------------------------------------------------ administración
    _t("rol", "Rol", r"\brol(?:es)?\b|\bperfil de acceso\b",
       "Es el conjunto de permisos que define qué puede ver y hacer una persona. Hay cinco roles del sistema: Administrador, Gerente, Encargado de sede, Usuario de inventario y Analista de compras.",
       ("Los roles del sistema no se modifican; el administrador puede crear roles propios con otras combinaciones (solo con permisos que él mismo tiene).", "El alcance puede ser toda la empresa o una sola sede."),
       "/roles", sugerencias=("¿Qué rol tengo?", "¿Qué puede hacer un encargado de sede?")),
    _t("permiso", "Permiso", r"\bpermisos?\b",
       "Es la autorización para una acción concreta (por ejemplo «Registrar ventas» o «Aprobar traslados»). Los roles agrupan permisos.",
       ("El servidor valida los permisos en cada operación, no solo la pantalla.", "En «Mi perfil» ves cuántos permisos tienes."),
       "/perfil", sugerencias=("¿Qué permisos tengo?", "¿Quién puede anular ventas?")),
    _t("alcance_sede", "Alcance por sede", r"\balcance\b|\blimitado a (la )?sede\b|\brol de sede\b",
       "Algunos roles ven toda la empresa (administrador, gerente, analista de compras) y otros solo su sede (encargado de sede, usuario de inventario).",
       ("Quien tiene alcance de sede solo consulta y opera su sede; si pregunta por otra, el asistente se lo dice.",), "/perfil"),
    _t("auditoria", "Auditoría", r"\bauditoria\b|\bbitacora\b|\btrazabilidad\b",
       "Es el registro de quién hizo qué y cuándo: ingresos exitosos y fallidos, altas, cambios, anulaciones y descargas de reportes.",
       ("No se puede editar ni borrar.", "Los gerentes ven el historial de operaciones, pero no los accesos de otras personas."),
       "/auditoria", sugerencias=("Últimos cambios en la auditoría",)),
    _t("llave_agente", "Agentes de IA y llaves de acceso", r"\bllaves?( de acceso)?\b|\bagentes? de ia\b|\bapi key\b|\bintegracion(es)?\b|\bmcp\b",
       "Son llaves que permiten a un asistente externo (un agente de IA) consultar inventario, alertas, predicciones o recomendaciones. Los agentes **solo leen**, nunca modifican nada.",
       ("La llave se muestra una sola vez al crearla; si se pierde o se filtra, se revoca y se crea otra.",), "/integraciones"),
    _t("sede", "Sede", r"\bsedes?\b|\bsucursal(es)?\b",
       "Es una ubicación física de la empresa (tienda, bodega, punto de venta) con su propio inventario.",
       ("Dos sedes de la misma empresa no pueden llamarse igual.", "No se puede inhabilitar una sede con traslados pendientes."), "/sedes", sugerencias=("¿Qué sedes tiene la empresa?",)),
    _t("categoria", "Categoría", r"\bcategorias?\b",
       "Es un grupo de productos parecidos (por ejemplo Cargadores o Baterías). Sirve para filtrar y resumir ventas e inventario.",
       (), "/categorias", sugerencias=("Ventas por categoría", "Inventario por categoría")),
    _t("inteligencia_artificial", "Inteligencia artificial en Inventia", r"\b(inteligencia artificial|ia|machine learning|aprendizaje automatico)\b",
       "Inventia usa estadística y aprendizaje automático para **predecir la demanda** de cada producto y sede, y con eso genera alertas y recomendaciones.",
       ("El asistente de consultas (este chat) no es un modelo de lenguaje: reconoce las preguntas por reglas y responde con los datos reales de tu empresa.", "Las recomendaciones siempre las aprueba una persona."),
       "/predicciones", sugerencias=("¿Cómo funciona el asistente?", "¿Cómo se calcula la predicción?")),
)


# ===================================================================================== guías «cómo se hace»
@dataclass(frozen=True)
class Tarea:
    clave: str
    nombre: str
    patron: re.Pattern
    permisos: tuple[str, ...]  # basta uno; vacío = cualquier persona
    pasos: tuple[str, ...]
    notas: tuple[str, ...] = ()
    enlaces: tuple[tuple[str, str], ...] = ()  # (etiqueta, ruta)
    sugerencias: tuple[str, ...] = ()


# Cada verbo escrito en infinitivo dentro de un patrón de guía se amplía a sus formas más usadas («registrar» cubre «registro», «registra», «registrando»…).
_FORMAS: dict[str, str] = {
    "registrar": r"registr\w+", "crear": r"crea\w*|creo|cree\b", "anular": r"anul\w+", "aprobar": r"aprob\w+|apruebo|aprueba\w*", "rechazar": r"rechaz\w+",
    "solicitar": r"solicit\w+", "confirmar": r"confirm\w+", "cancelar": r"cancel\w+", "ajustar": r"ajust(?:ar|o|e|a)\b", "cambiar": r"cambi\w+",
    "generar": r"gener\w+", "enviar": r"envi\w+", "reportar": r"report\w+", "configurar": r"configur\w+", "definir": r"defin\w+", "restablecer": r"restablec\w+|restablez\w+",
    "recuperar": r"recuper\w+", "desbloquear": r"desbloque\w+", "inhabilitar": r"inhabilit\w+", "activar": r"activ(?:ar|o|a|e)\b", "eliminar": r"elimin\w+",
    "sacar": r"sac(?:ar|o|a|an)\b", "agregar": r"agreg\w+", "anadir": r"anad\w+", "ingresar": r"ingres\w+", "cerrar": r"cierr\w+|cerr\w+", "cargar": r"carg\w+",
    "mover": r"mover|muev\w+|movi\w+", "resolver": r"resolv\w+|resuelv\w+", "responder": r"respond\w+", "pedir": r"ped(?:ir|ido)|pid\w+", "comprar": r"compr\w+",
    "vender": r"vend\w+", "devolver": r"devolv\w+|devuelv\w+", "reactivar": r"reactiv\w+", "editar": r"edit\w+", "modificar": r"modific\w+", "actualizar": r"actualiz\w+",
    "poner": r"pon(?:er|go|e|es)\b", "habilitar": r"habilit\w+", "borrar": r"borr\w+", "recalcular": r"recalcul\w+", "hacer": r"hac(?:er|e|en|emos)\b|hag(?:o|a|amos)\b",
    "realizar": r"realiz\w+", "emitir": r"emit\w+", "facturar": r"factur\w+", "gestionar": r"gestion\w+", "atender": r"atend\w+|atiend\w+", "contestar": r"contest\w+",
    "radicar": r"radic\w+", "presentar": r"present\w+", "tramitar": r"tramit\w+", "reclamar": r"reclam\w+", "mandar": r"mand\w+", "escribir": r"escrib\w+",
    "trasladar": r"traslad\w+", "recibir": r"recib\w+", "quitar": r"quit\w+", "usar": r"us(?:ar|o|a|e)\b", "aplicar": r"aplic\w+", "tomar": r"tom(?:ar|o|a|e)\b",
    "aceptar": r"acept\w+", "descartar": r"descart\w+", "ejecutar": r"ejecut\w+", "marcar": r"marc(?:ar|o|a|an)\b", "descargar": r"descarg\w+", "importar": r"import\w+",
    "subir": r"sub(?:ir|o|e)\b", "cuadrar": r"cuadr\w+", "corregir": r"correg\w+|corrij\w+", "dar": r"dar|doy|da\b|dan\b", "meter": r"met(?:er|o|e)\b", "sumar": r"sum(?:ar|o|a)\b",
    "restar": r"rest(?:ar|o|a)\b", "descontar": r"descuent\w+|descont\w+", "ingresar ": "", "abrir": r"abr(?:ir|o|e)\b", "iniciar": r"inici\w+", "entrar": r"entr(?:ar|o|a)\b",
    "loguear": r"logue\w+", "acceder": r"acced\w+", "salir": r"sal(?:ir|go|e)\b", "terminar": r"termin\w+", "bloquear": r"bloque\w+", "desactivar": r"desactiv\w+",
    "deshabilitar": r"deshabilit\w+", "asignar": r"asign\w+", "fijar": r"fij\w+", "establecer": r"establec\w+|establez\w+", "actualizar ": "", "montar": r"mont\w+", "adicionar": r"adicion\w+",
    "digitar": r"digit\w+", "levantar": r"levant\w+", "interponer": r"interpon\w+", "revocar": r"revoc\w+", "conectar": r"conect\w+", "parametrizar": r"parametriz\w+",
    "calcular": r"calcul\w+", "habilitar ": "", "refrescar": r"refresc\w+", "lanzar": r"lanz\w+", "correr": r"corr(?:er|o|e)\b", "ignorar": r"ignor\w+", "apagar": r"apag\w+",
    "solucionar": r"solucion\w+", "pasar": r"pas(?:ar|o|a)\b", "recepcionar": r"recepcion\w*",
}
_FORMAS = {k: v for k, v in _FORMAS.items() if v}
_INFINITIVOS = re.compile(r"(?:(?<=\\b)|(?<![\w\\]))(" + "|".join(sorted(_FORMAS, key=len, reverse=True)) + r")(?![\w])")


def _ampliar(patron: str) -> str:
    return _INFINITIVOS.sub(lambda m: "(?:" + _FORMAS[m.group(1)] + ")", patron)


def _g(clave: str, nombre: str, patron: str, permisos: tuple[str, ...], pasos: tuple[str, ...], notas: tuple[str, ...] = (),
       enlaces: tuple[tuple[str, str], ...] = (), sugerencias: tuple[str, ...] = ()) -> Tarea:
    return Tarea(clave, nombre, _r(_ampliar(patron)), permisos, pasos, notas, enlaces, sugerencias)


_V_CREAR = r"(crear|creo|crea|agregar|agrego|anadir|anado|registrar|registro|dar de alta|nuev[oa]|hacer|hago|adicionar|montar|subir)"
_V_CAMBIAR = r"(cambi\w+|edit\w+|modific\w+|actualiz\w+|corregir|correg\w+)"

GUIAS: tuple[Tarea, ...] = (
    # ------------------------------------------------------------------------------------------ ventas
    _g("anular_venta", "anular una venta", r"\banul\w+\b.*\bventas?\b|\bventas?\b.*\banul\w+|\bdevolver (una )?venta\b|\bdeshacer (una )?venta\b|\bcancelar (una )?venta\b",
       ("ventas.anular",), (
           "Abre **Ventas** y entra a la venta que quieres anular.",
           "Pulsa **Anular venta**.", "Escribe el **motivo** y confirma.",
           "Las unidades vuelven al inventario como un movimiento nuevo y la venta queda marcada como anulada (no se borra)."),
       ("Solo se puede anular dentro del plazo que define la empresa (30 días por defecto) y una sola vez.", "Las ventas anuladas no cuentan en los reportes ni en la predicción."),
       (("Ventas", "/ventas"),), ("¿Cuántas ventas se anularon este mes?",)),
    _g("registrar_venta", "registrar una venta", r"\b(registr\w+|hacer|hago|crear|creo|realizar|facturar|vender|vendo|generar|emitir|digitar|ingresar|cargar)\b.*\b(venta|ventas|factura|facturas)\b|\bvender\b|\bfacturar\b|\bcomo se vende\b",
       ("ventas.registrar",), (
           "Entra a **Ventas → Nueva venta**.",
           "Busca cada producto por código o nombre y agrégalo; el precio se propone desde la ficha y puedes cambiarlo en esa venta.",
           "Revisa el total.", "Pulsa **Registrar venta**."),
       ("Las existencias se descuentan en el mismo instante.", "Si falta mercancía de algún producto, toda la venta se rechaza y no queda a medias."),
       (("Nueva venta", "/ventas/nueva"),), ("¿Cuánto vendimos hoy?", "¿Cómo anulo una venta?")),
    # ------------------------------------------------------------------------------------------ inventario
    _g("devolucion_cliente", "registrar la devolución de un cliente", r"\bdevoluci\w+\b.*\bcliente|\bcliente\b.*\b(devolv\w+|devuelv\w+|devolucion)\b|\b(devolv\w+|devuelv\w+)\b.*\bcliente|\bme devolvieron\b|\bdevuelven\b",
       ("inventario.entrada",), (
           "Entra a **Existencias → Registrar entrada**.",
           "Elige el motivo **Devolución de cliente**.", "Agrega los productos y las cantidades que regresaron.",
           "Escribe una observación si quieres (por ejemplo, el estado en que llegaron) y pulsa **Registrar entrada**."),
       ("Si la venta original fue un error y está dentro del plazo, también puedes anularla: las unidades vuelven al inventario.",), (("Existencias", "/inventario"),)),
    _g("registrar_entrada", "registrar una entrada de mercancía", r"\b(registr\w+|dar|hacer|hago|ingres\w+|cargar|meter|agregar|agrego|sumar|anadir|recibir|recibo|ingreso|subir)\b.*\b(entradas?|mercancia|compras?|llegada|stock|inventario|existencias|unidades|productos)\b|\bllego (la )?mercancia\b|\bentrada de mercancia\b|\binventario inicial\b|\bcargar inventario\b",
       ("inventario.entrada",), (
           "Entra a **Existencias → Registrar entrada**.",
           "Elige el motivo: compra, devolución de cliente, inventario inicial, producción u otro.",
           "Agrega los productos y las cantidades (puedes poner varias líneas, un producto solo una vez).",
           "Si quieres, escribe una **observación** (por ejemplo «llegaron dos cajas golpeadas»).", "Pulsa **Registrar entrada**."),
       ("Después la ves en Movimientos → Entradas de mercancía y puedes agregarle más observaciones (se acumulan y no se editan).", "Si la mercancía llegó con un defecto, desde el detalle de la entrada puedes pulsar **Reportar no conformidad**."),
       (("Existencias", "/inventario"),), ("Últimas entradas", "¿Cómo reporto una no conformidad?")),
    _g("registrar_salida", "registrar una salida (pérdida, consumo o devolución al proveedor)", r"\b(registr\w+|dar|hacer|hago|sacar|saco|descontar|restar|baja)\b.*\b(salidas?|perdidas?|mermas?|deterioro|danos?|dano|consumo)\b|\bdar de baja\b|\bsalida de (mercancia|inventario)\b|\bdevolver al proveedor\b|\bdevolucion al proveedor\b",
       ("inventario.salida",), (
           "Entra a **Existencias → Registrar salida**.",
           "Elige el motivo: pérdida, deterioro, consumo interno, devolución al proveedor u otro.",
           "Agrega los productos y las cantidades.", "Confirma el registro."),
       ("Si una cantidad supera lo disponible, el sistema no registra nada y te dice cuánto hay y cuánto se necesita.", "Las ventas no se registran como salidas: tienen su propia pantalla."),
       (("Existencias", "/inventario"),), ("¿Cuántas mermas hubo este mes?",)),
    _g("ajustar_inventario", "ajustar las existencias (conteo físico)", r"\bajust\w+\b|\bconteo fisico\b|\binventario fisico\b|\bcuadrar\b|\bcorregir\b.*\b(stock|existencias|inventario|cantidad|saldo)\b|\bno (cuadra|coincide)\b|\bdiferencias? de inventario\b",
       ("inventario.ajustar",), (
           "Entra a **Existencias** y ubica el producto en su fila.",
           "Pulsa el icono de **ajuste**.", "Indica la **cantidad real contada**, el motivo (conteo físico, corrección u otro) y una observación (obligatoria).",
           "Revisa la diferencia que calcula el sistema y confirma."),
       ("Nada se borra: el historial conserva el saldo anterior y el nuevo.",), (("Existencias", "/inventario"),), ("Últimos ajustes de inventario",)),
    _g("definir_niveles", "definir el stock mínimo y máximo", r"\b(defin\w+|configur\w+|cambi\w+|poner|pongo|fijar|ajustar|establec\w+|modific\w+|asignar|actualizar|editar)\b.*\b(minimos?|maximos?|niveles|stock minimo|stock maximo|nivel)\b",
       ("inventario.niveles",), (
           "Entra a **Existencias** y ubica el producto en su fila.", "Pulsa el icono de **niveles**.",
           "Escribe el **mínimo** (dispara las alertas de inventario bajo) y, si quieres, el **máximo** (dispara las de exceso).", "Guarda."),
       ("El máximo no puede ser menor que el mínimo.", "Después de cambiar los niveles, el botón **Recalcular alertas** de Alertas vuelve a evaluar todo."),
       (("Existencias", "/inventario"),), ("¿Qué productos no tienen stock mínimo definido?",)),
    # ------------------------------------------------------------------------------------------ traslados
    _g("aprobar_traslado", "aprobar o rechazar un traslado", r"\b(aprob\w+|apru\w+|rechaz\w+|autoriz\w+)\b.*\btraslad\w+|\btraslad\w+\b.*\b(aprob\w+|apru\w+|rechaz\w+|autoriz\w+)",
       ("traslados.aprobar",), (
           "Entra a **Traslados** y abre el traslado en estado Solicitado.",
           "Si eres de la sede de origen, pulsa **Aprobar**; o **Rechazar** y escribe el motivo.",
           "Cuando la mercancía llegue, la sede de destino pulsa **Confirmar recepción**."),
       ("Solo la sede de origen aprueba o rechaza.", "Las existencias no se mueven hasta que el destino confirma."),
       (("Traslados", "/traslados"),), ("¿Qué traslados están pendientes?",)),
    _g("confirmar_traslado", "confirmar la recepción de un traslado", r"\b(confirm\w+|recib\w+|recepcion\w*)\b.*\b(traslad\w+|mercancia|pedido)\b|\btraslad\w+\b.*\b(confirm\w+|recib\w+|recepcion\w*)|\bllego (el|un) traslado\b",
       ("traslados.confirmar",), (
           "Entra a **Traslados** y abre el traslado aprobado.", "Verifica que la mercancía llegó.", "Pulsa **Confirmar recepción**."),
       ("Solo en ese momento se mueven las existencias: se descuentan del origen y se suman al destino en una sola operación.", "Solo se pueden confirmar traslados que ya estén aprobados."),
       (("Traslados", "/traslados"),), ("¿Qué traslados están pendientes?",)),
    _g("cancelar_traslado", "cancelar un traslado", r"\bcancel\w+\b.*\btraslad\w+|\btraslad\w+\b.*\bcancel\w+|\banular\b.*\btraslad",
       ("traslados.solicitar", "traslados.aprobar"), (
           "Entra a **Traslados** y abre el traslado pendiente.", "Pulsa **Cancelar traslado**.", "Escribe el motivo y confirma."),
       ("Solo se pueden cancelar traslados pendientes (todavía sin confirmar).",), (("Traslados", "/traslados"),)),
    _g("solicitar_traslado", "solicitar un traslado entre sedes", r"\b(solicit\w+|hacer|hago|crear|creo|pedir|pido|realizar|enviar|mover|muevo|pasar|paso|mandar|trasladar|traslado)\b.*\b(traslad\w+|mercancia|productos|unidades|inventario|stock)\b|\btrasladar\b|\bcomo (se )?traslada\b",
       ("traslados.solicitar",), (
           "Entra a **Traslados → Solicitar traslado**.", "Elige la sede de **origen** y la de **destino** (una de las dos debe ser la tuya).",
           "Agrega los productos y las cantidades.", "Envía la solicitud.",
           "La sede de origen la **aprueba** y, cuando la mercancía llega, la de destino pulsa **Confirmar recepción**."),
       ("Solo en la confirmación se mueven las existencias.", "Un traslado pendiente puede cancelarse con un motivo."),
       (("Solicitar traslado", "/traslados/nuevo"), ("Traslados", "/traslados")), ("¿Qué traslados están pendientes?",)),
    # ------------------------------------------------------------------------------------------ alertas / inteligencia
    _g("recalcular_alertas", "recalcular las alertas", r"\brecalcul\w+\b.*\balert\w+|\balert\w+\b.*\brecalcul\w+|\bactualiz\w+\b.*\balert\w+|\brefresc\w+\b.*\balert",
       ("alertas.recalcular",), ("Entra a **Alertas**.", "Pulsa **Recalcular alertas**."),
       ("Las alertas se abren y se cierran solas al cambiar las existencias; recalcular sirve después de cambiar mínimos, máximos o los parámetros de la empresa.",),
       (("Alertas", "/alertas"),), ("¿Qué alertas críticas hay?",)),
    _g("resolver_alerta", "resolver o quitar una alerta", r"\b(resolv\w+|resuelv\w+|cerrar|quitar|elimin\w+|borrar|atender|solucionar|descartar|apagar|ignorar)\b.*\balert\w+",
       (), ("No hay botón para cerrar una alerta: se cierra sola cuando la situación se corrige.",
            "Para una alerta de inventario bajo, registra una **entrada** o un **traslado** que suba las existencias por encima del mínimo.",
            "Para una de exceso, baja las existencias (venta, salida o traslado) o sube el máximo.", "Si cambiaste mínimos o parámetros, pulsa **Recalcular alertas** para que se reevalúen."),
       (), (("Alertas", "/alertas"),), ("¿Qué debo revisar hoy?",)),
    _g("generar_prediccion", "generar una predicción de demanda", r"\b(gener\w+|ejecut\w+|hacer|hago|correr|lanzar|calcular|sacar|crear|actualizar|refrescar)\b.*\b(prediccion\w*|pronostico\w*)\b|\bcomo se (calcula|hace|genera) (la |una )?prediccion\b",
       ("prediccion.ejecutar",), (
           "Entra a **Inteligencia → Predicción de demanda**.", "Pulsa **Generar predicción de demanda**.",
           "Elige el horizonte (cuántos días hacia adelante) y confirma.",
           "El cálculo se hace en segundo plano; la pantalla muestra el avance y puedes seguir trabajando."),
       ("Necesita al menos 28 días de historia y 5 días con ventas por producto; los demás aparecen en «Series sin pronóstico» con el motivo.",),
       (("Predicción de demanda", "/predicciones"),), ("¿Qué tan confiable es la predicción?",)),
    _g("generar_recomendaciones", "generar recomendaciones", r"\b(gener\w+|calcular|sacar|crear|hacer|hago|actualizar|refrescar)\b.*\brecomend\w+",
       ("recomendaciones.generar",), (
           "Primero asegúrate de tener una predicción vigente (Inteligencia → Predicción de demanda).",
           "Entra a **Inteligencia → Recomendaciones**.", "Pulsa **Generar recomendaciones**.", "Revisa cada una: trae el porqué, las unidades y la prioridad."),
       ("Al volver a generarlas, las pendientes anteriores quedan como «reemplazadas».",), (("Recomendaciones", "/recomendaciones"),), ("Recomendaciones pendientes",)),
    _g("aprobar_recomendacion", "aprobar, rechazar o registrar una recomendación", r"\b(aprob\w+|apru\w+|rechaz\w+|ejecut\w+|usar|aplicar|tomar|aceptar|descartar|marcar)\b.*\brecomend\w+|\brecomend\w+\b.*\b(aprob\w+|apru\w+|rechaz\w+|ejecut\w+|aceptar)|\bcompra realizada\b",
       ("recomendaciones.aprobar",), (
           "Entra a **Inteligencia → Recomendaciones** y abre la recomendación.",
           "**Aprobar** un traslado crea la solicitud de traslado (todavía debe aprobarla la sede de origen y confirmarla la de destino).",
           "**Aprobar** un reabastecimiento deja constancia de que se decidió comprar; **Registrar compra realizada** deja constancia de que el pedido ya se hizo.",
           "**Rechazar** la descarta; puedes escribir el motivo."),
       ("Inventia no emite órdenes de compra: el pedido al proveedor se hace como lo hace hoy tu empresa.", "Una recomendación nunca mueve inventario por sí sola."),
       (("Recomendaciones", "/recomendaciones"),), ("Recomendaciones pendientes",)),
    _g("hacer_pedido", "hacer un pedido a un proveedor", r"\b(hacer|hago|generar|crear|emitir|registrar|realizar|enviar)\b.*\b(pedido|pedidos|orden de compra|ordenes de compra|compra a proveedor|compra al proveedor)\b|\bcomo (compro|pido|reabastezco|repongo|surto)\b|\bcomo (hago|hacer) (una |la )?compra\b",
       (), (
           "Entra a **Inteligencia → Recomendaciones** para ver qué conviene reponer y en qué cantidad (si no hay, genera primero la predicción y las recomendaciones).",
           "Aprueba la recomendación de reabastecimiento para dejar constancia de la decisión.",
           "Haz el pedido al proveedor por tu canal habitual (Inventia no emite órdenes de compra).",
           "Pulsa **Registrar compra realizada** para que quede la constancia.", "Cuando llegue la mercancía, regístrala en **Existencias → Registrar entrada** con el motivo «Compra»."),
       (), (("Recomendaciones", "/recomendaciones"),), ("¿Qué debo reponer esta semana?",)),
    # ------------------------------------------------------------------------------------------ catálogo
    _g("crear_producto", "crear un producto", rf"\b{_V_CREAR}\b.*\bproductos?\b|\bproducto nuevo\b|\bdar de alta\b",
       ("productos.crear",), (
           "Entra a **Inventario → Productos**.", "Pulsa **Nuevo producto**.",
           "Completa el código, el nombre, la categoría, la unidad de medida, el costo y el precio de venta.", "Guarda."),
       ("El código no se puede cambiar después: identifica al producto en todo el historial.", "Sin costo, el producto no se incluye en la valoración del inventario.",
        "Para que tenga existencias, registra una entrada (motivo «Inventario inicial»)."),
       (("Productos", "/productos"),), ("¿Qué productos no tienen costo?",)),
    _g("editar_producto", "editar o inhabilitar un producto", rf"\b({_V_CAMBIAR}|inhabilit\w+|desactiv\w+|deshabilit\w+|reactiv\w+|habilit\w+|eliminar|borrar|quitar)\b.*\bproductos?\b|\bcambiar (el )?(precio|costo|nombre)\b",
       ("productos.editar", "productos.inhabilitar"), (
           "Entra a **Inventario → Productos** y ubica el producto.", "Para modificar nombre, categoría, costo o precio, usa la opción de **editar** de su fila.",
           "Para sacarlo de circulación, usa **Inhabilitar** (pide confirmación); puedes **reactivarlo** cuando quieras."),
       ("El código no se puede cambiar.", "Un producto inhabilitado conserva su historial; no se puede inhabilitar si tiene traslados pendientes.", "Los productos no se borran."),
       (("Productos", "/productos"),)),
    _g("crear_categoria", "crear una categoría", rf"\b{_V_CREAR}\b.*\bcategorias?\b",
       ("categorias.crear",), ("Entra a **Inventario → Categorías**.", "Pulsa **Nueva categoría**.", "Escribe el nombre y guarda."), (), (("Categorías", "/categorias"),)),
    # ------------------------------------------------------------------------------------------ administración
    _g("crear_sede", "crear una sede", rf"\b{_V_CREAR}\b.*\b(sedes?|sucursal(es)?|bodegas?)\b|\bnueva sede\b|\babrir (una )?(sede|sucursal)\b",
       ("sedes.crear",), ("Entra a **Administración → Sedes**.", "Pulsa **Nueva sede**.", "Completa el nombre y los datos de la sede y guarda."),
       ("Dos sedes de la misma empresa no pueden llamarse igual.", "Para que tenga mercancía, haz una entrada o pide traslados desde otras sedes."), (("Sedes", "/sedes"),)),
    _g("crear_usuario", "crear un usuario", rf"\b{_V_CREAR}\b.*\b(usuarios?|empleados?|cuentas?|personas?)\b|\bnuevo usuario\b|\bdar acceso\b",
       ("usuarios.crear",), (
           "Entra a **Administración → Usuarios** y pulsa **Nuevo usuario**.", "Escribe nombre y correo, y elige el **rol** (y la **sede** si el rol es de sede).",
           "Pulsa **Generar contraseña segura** y **cópiala**.", "Guarda y entrega la contraseña por un canal seguro: la persona deberá cambiarla al ingresar."),
       ("No puedes asignar un rol con más permisos de los que tú tienes.",), (("Usuarios", "/usuarios"),), ("¿Cuántos usuarios hay?",)),
    _g("restablecer_password", "restablecer o desbloquear la cuenta de otra persona", r"\b(restablec\w+|restablez\w+|resete\w+|reiniciar|recuperar|blanque\w+|cambi\w+)\b.*\b(contrasena|clave|password)\b.*\b(usuario|empleado|persona|compan\w+|otro|de el|de ella)\b|\bdesbloque\w+\b|\bcuenta bloqueada\b|\b(usuario|empleado)\b.*\b(bloquead\w+|olvido (la |su )?(contrasena|clave))",
       ("usuarios.editar",), (
           "Entra a **Administración → Usuarios** y ubica a la persona.", "Para una contraseña olvidada, usa **Restablecer contraseña**: asigna una temporal y cierra sus sesiones abiertas.",
           "Para una cuenta bloqueada por intentos fallidos, usa **Desbloquear**.", "Entrega la contraseña temporal por un canal seguro; la persona deberá cambiarla al ingresar."),
       ("La cuenta se bloquea 15 minutos tras 5 intentos fallidos; se desbloquea sola pasado ese tiempo.",), (("Usuarios", "/usuarios"),)),
    _g("inhabilitar_usuario", "inhabilitar o reactivar un usuario", r"\b(inhabilit\w+|desactiv\w+|deshabilit\w+|reactiv\w+|habilit\w+|bloque\w+|dar de baja|eliminar|borrar|quitar)\b.*\b(usuarios?|empleados?|cuentas?|personas?)\b",
       ("usuarios.inhabilitar",), ("Entra a **Administración → Usuarios** y ubica a la persona.", "Usa **Inhabilitar** (pide confirmación): pierde el acceso de inmediato y su historial se conserva.", "Para devolverle el acceso, usa **Reactivar**."),
       ("No puedes inhabilitar tu propia cuenta ni dejar a la empresa sin administradores activos.",), (("Usuarios", "/usuarios"),)),
    _g("cambiar_rol_usuario", "cambiar el rol o la sede de un usuario", r"\b(cambi\w+|asign\w+|pon\w+|mover|modific\w+|editar)\b.*\b(rol|sede|perfil|cargo)\b.*\b(usuario|empleado|persona|a [a-z]+)\b|\b(rol|sede) (de|del) (un )?(usuario|empleado)\b",
       ("usuarios.editar",), ("Entra a **Administración → Usuarios** y ubica a la persona.", "Usa la opción de **editar**.", "Cambia el **rol** o la **sede** y guarda."),
       ("No puedes asignar un rol con más permisos de los que tú tienes.",), (("Usuarios", "/usuarios"),)),
    _g("crear_rol", "crear un rol propio", rf"\b{_V_CREAR}\b.*\brol(?:es)?\b|\bnuevo rol\b|\bcrear (un )?perfil\b",
       ("roles.crear",), ("Entra a **Administración → Roles y permisos**.", "Pulsa **Nuevo rol**.", "Escribe el nombre, elige el alcance (toda la empresa o una sola sede) y marca los permisos por módulo.", "Guarda."),
       ("Solo puedes conceder permisos que tú mismo tienes.", "Los cinco roles del sistema se consultan pero no se modifican."), (("Roles y permisos", "/roles"),)),
    _g("editar_empresa", "cambiar los parámetros de la empresa", r"\b(cambi\w+|configur\w+|editar|modific\w+|ajustar|actualizar|defin\w+)\b.*\b(plazo de entrega|dias de seguridad|parametros?|cobertura objetivo|datos de la empresa|horizonte|umbral|plazo de anulacion|dias sin rotacion|empresa)\b",
       ("empresa.editar",), ("Entra a **Administración → Empresa**.", "Edita los datos generales o los parámetros: plazo de entrega, días de seguridad, cobertura objetivo, horizonte, umbral de alerta, días sin rotación y plazo de anulación.", "Guarda y pulsa **Recalcular alertas** en Alertas para aplicar los cambios."),
       ("Si no conoces los valores, deja los predeterminados y ajústalos con la experiencia.",), (("Empresa", "/empresa"),), ("¿Cuáles son los parámetros de la empresa?",)),
    _g("crear_llave", "crear o revocar una llave de agente de IA", r"\b(crear|generar|nueva|revoc\w+|quitar|eliminar|conectar)\b.*\b(llaves?|agentes?|api key|claude|integracion(es)?)\b",
       ("agentes.gestionar",), ("Entra a **Administración → Agentes de IA**.", "Pulsa **Nueva llave** y elige el nombre, qué puede consultar, la sede (opcional) y la vigencia.", "Copia la llave: se muestra **una sola vez**.", "Si se pierde o se filtra, **revócala** y crea otra."),
       ("Los agentes solo pueden leer; nunca modifican nada.",), (("Agentes de IA", "/integraciones"),)),
    # ------------------------------------------------------------------------------------------ cuenta
    _g("olvido_password", "recuperar tu contraseña", r"\b(olvid\w+|perdi|recuper\w+|no recuerdo|no me acuerdo)\b.*\b(contrasena|clave|password)\b|\b(contrasena|clave|password)\b.*\b(olvid\w+|perdi|recuper\w+)|\bno puedo (entrar|ingresar|iniciar sesion)\b",
       (), ("En la pantalla de ingreso pulsa **¿Olvidó su contraseña?**.", "Escribe tu correo: si la cuenta existe recibirás un código de 6 dígitos.", "Escribe el código (vale 15 minutos, sirve una sola vez y tienes 5 intentos).", "Crea tu nueva contraseña."),
       ("Si el código no llega, revisa la carpeta de correo no deseado; si sigue sin llegar, pide a un administrador que te restablezca la contraseña.", "Si tu cuenta está bloqueada por intentos fallidos, espera 15 minutos o pide que la desbloqueen."),
       (), ("¿Cómo cambio mi contraseña?",)),
    _g("cambiar_password", "cambiar tu contraseña", r"\b(cambi\w+|modific\w+|actualiz\w+|poner|pongo)\b.*\b(mi |la |una )?(contrasena|clave|password)\b",
       (), ("Abre el menú de usuario (abajo a la izquierda) y entra a **Mi perfil**.", "En la sección de contraseña escribe la actual y la nueva.", "Guarda: se cerrarán tus otras sesiones abiertas."),
       ("Una contraseña válida tiene entre 8 y 128 caracteres e incluye una mayúscula, una minúscula, un número y un carácter especial.",), (("Mi perfil", "/perfil"),)),
    _g("iniciar_sesion", "ingresar al sistema", r"\b(ingres\w+|entr\w+|iniciar sesion|loguear\w*|acceder|abrir)\b.*\b(sistema|cuenta|plataforma|inventia|aplicacion|app|pagina)\b|\biniciar sesion\b|\bcomo (ingreso|entro|accedo)\b$",
       (), ("Abre la dirección que te dio tu empresa.", "Escribe tu **correo electrónico** y tu **contraseña**.", "Pulsa **Ingresar**.", "Si te asignaron una contraseña temporal, el sistema te pedirá crear una personal antes de continuar."),
       ("Con 5 intentos fallidos seguidos la cuenta se bloquea 15 minutos.",), (), ("Olvidé mi contraseña",)),
    _g("cerrar_sesion", "cerrar sesión", r"\b(cerrar|salir|salgo|terminar)\b.*\b(sesion|cuenta|sistema)\b|\bsalir\b",
       (), ("Abre el menú de usuario (abajo a la izquierda).", "Pulsa **Salir**."), ("La sesión también se cierra sola cuando vence y el sistema te lo avisa.",)),
    # ------------------------------------------------------------------------------------------ SIG
    _g("enviar_pqrs", "enviar una PQRS", r"\b(enviar|hacer|radicar|crear|poner|registrar|presentar|interponer|mandar|escribir)\b.*\b(pqrs|queja|reclamo|peticion|sugerencia)\b",
       ("pqrs.crear",), ("Entra a **SIG → PQRS y sugerencias → Nueva solicitud**.", "Elige el **tipo** (petición, queja, reclamo o sugerencia), escribe el **asunto** y la **descripción**.",
                         "Si quieres, adjunta evidencias (fotos JPG, PNG o WebP, o PDF; hasta 5 archivos de 3 MB).", "Pulsa **Enviar solicitud**: verás el número de radicado.", "En **Mis solicitudes** sigues el estado y la respuesta."),
       ("Tu nombre, tu sede y la fecha se registran solos.", "Solo tú y la administración ven tus solicitudes."), (("PQRS", "/sig/pqrs"),), ("¿Cuántas PQRS hay pendientes?",)),
    _g("responder_pqrs", "responder una PQRS", r"\b(respond\w+|gestion\w+|atender|resolv\w+|contestar|cerrar|cambiar el estado de)\b.*\b(pqrs|queja|reclamo|peticion|sugerencia)\b",
       ("pqrs.gestionar",), ("Entra a **SIG → PQRS y sugerencias → Todas las solicitudes**.", "Filtra por tipo, estado, persona o fechas, o busca por asunto o número, y abre la solicitud.",
                             "Cambia el **estado** y/o escribe una **respuesta**; para marcarla como resuelta la respuesta es obligatoria.", "El cambio queda en el historial, que no se puede alterar."),
       ("El sistema no envía correos al llegar una solicitud: revisa la bandeja con regularidad.",), (("PQRS", "/sig/pqrs"),), ("PQRS abiertas",)),
    _g("reportar_no_conformidad", "reportar una no conformidad", r"\b(report\w+|registrar|registro|crear|hacer|hago|levantar|abrir|presentar)\b.*\bno ?conformidad(es)?\b",
       ("calidad.reportar", "calidad.gestionar"), ("Entra a **SIG → Calidad → No conformidades → Reportar no conformidad** (o a **Reportar no conformidad** desde el detalle de una entrada de mercancía).",
                                                  "Elige el producto, el **tipo** (defecto de fábrica, daño en transporte, producto equivocado, cantidad incorrecta, empaque deteriorado, no cumple la especificación u otro) y la descripción.",
                                                  "Indica la fecha en que se detectó y la **cantidad afectada**; adjunta evidencias si las tienes.", "Envía el reporte."),
       ("Reportarla no cambia las existencias: si hay que sacar la mercancía, registra una salida (motivo «Deterioro» o «Devolución al proveedor»).",), (("Calidad", "/sig/calidad"),), ("No conformidades sin cerrar",)),
    _g("reportar_garantia", "reportar una garantía", r"\b(report\w+|registrar|registro|crear|hacer|hago|reclamar|solicitar|abrir|presentar|tramitar)\b.*\bgarantias?\b",
       ("calidad.reportar", "calidad.gestionar"), ("Entra a **SIG → Calidad → Garantías → Reportar garantía**.", "Indica el producto y la cantidad, y el **documento de respaldo** (factura de compra, entrada de inventario, venta u otro) con su referencia.",
                                                  "Escribe la fecha de compra, hasta cuándo cubre la garantía, el defecto y las observaciones; adjunta evidencias si las tienes.", "Envía el reporte: el administrador registrará el proveedor, el envío y la respuesta."),
       ("Reportarla no cambia las existencias.",), (("Calidad", "/sig/calidad"),), ("Garantías vigentes",)),
    _g("configurar_pausas", "configurar las pausas activas", r"\b(configur\w+|cambi\w+|activar|desactivar|ajustar|modific\w+|crear|editar)\b.*\bpausas?\b",
       ("sst.gestionar",), ("Entra a **SIG → Seguridad y Salud en el Trabajo**.", "En la pestaña **Frecuencia** activa o desactiva las pausas y fija el intervalo (de 1 a 480 minutos).", "En la pestaña **Contenido** crea, edita o desactiva los ejercicios."),
       ("Las pausas no aparecen mientras la persona tiene un formulario abierto o una venta a medio armar.",), (("Seguridad y Salud", "/sig/sst"),)),
    _g("configurar_ambiental", "configurar la gestión ambiental", r"\b(configur\w+|parametriz\w+|activar|calcular|habilitar|poner)\b.*\b(ambiental|co2|carbono|huella|emisiones)\b",
       ("ambiental.configurar",), ("Entra a **SIG → Gestión ambiental → Configuración**.", "Define el **factor de emisión de la red eléctrica** (kg de CO₂ por kWh), su año y su fuente.",
                                  "Marca cada categoría que sea vehículo y completa su tipo, recorrido anual, consumo eléctrico y la emisión del vehículo de combustión con el que se compara.", "Si ya había ventas, pulsa **Incorporar ventas anteriores**."),
       ("Sin parámetros no hay cifra de CO₂: el panel dice «Pendiente de parametrización».", "Los datos de referencia deben salir de fuentes oficiales y quedar documentados en el campo «fuente»."), (("Gestión ambiental", "/sig/ambiental"),)),
    # ------------------------------------------------------------------------------------------ varias
    _g("ver_historial", "ver el historial de lo que se hizo", r"\bquien (hizo|cambio|modifico|borro|elimino)\b.*\b(como|donde)\b|\bcomo (veo|se ve|consulto|reviso) (el )?(historial|auditoria|kardex|movimientos)\b",
       ("movimientos.ver", "auditoria.ver", "auditoria.operaciones"), ("Para cambios de existencias entra a **Inventario → Movimientos**: lista cada entrada, salida, ajuste, venta, anulación y traslado con quién, cuándo y el saldo antes y después.",
                                                                       "Para ver quién hizo qué en el sistema entra a **Administración → Auditoría** y filtra por módulo, acción, usuario, resultado o fechas."),
       ("Los registros no se pueden editar ni borrar.",), (("Movimientos", "/movimientos"), ("Auditoría", "/auditoria"))),
    _g("importar_masivo", "cargar muchos datos de una vez", r"\b(import\w+|carga masiva|cargar masiv\w+|subir (un )?(excel|archivo|csv)|cargar (un )?(excel|archivo|csv)|desde excel|desde un archivo|cargar (muchos|varios|todos) (los )?(datos|productos|registros)|(muchos|varios) (datos|productos|registros) (de una vez|a la vez|al tiempo))\b",
       ("inventario.entrada", "productos.crear"), ("Hoy las altas se hacen en pantalla: **Existencias → Registrar entrada** permite varias líneas de productos en una sola entrada.", "Los productos se crean desde **Inventario → Productos → Nuevo producto**."),
       ("El manual no contempla una importación masiva desde Excel o CSV.",), (("Productos", "/productos"), ("Existencias", "/inventario"))),
)


# ==================================================================================== lo que Inventia no registra
@dataclass(frozen=True)
class SinRegistro:
    clave: str
    patron: re.Pattern
    tema: str
    texto: str
    alternativas: tuple[str, ...]  # preguntas que sí puedo responder
    ruta: str | None = None


def _n(clave: str, patron: str, tema: str, texto: str, alternativas: tuple[str, ...], ruta: str | None = None) -> SinRegistro:
    return SinRegistro(clave, _r(patron), tema, texto, alternativas, ruta)


NO_REGISTRA: tuple[SinRegistro, ...] = (
    _n("descuentos", r"\bdescuentos?\b|\bpromocion(es)?\b|\bofertas?\b|\bcupon(es)?\b|\brebajas?\b|\bliquidacion(es)?\b|\bbonificacion(es)?\b",
       "descuentos y promociones",
       "Inventia no registra descuentos ni promociones como tal. Cada venta guarda el **precio unitario** con el que se vendió (que se puede modificar en esa venta), así que no puedo separar «cuánto se descontó».",
       ("¿Cuál es el precio promedio de venta de cada producto?", "¿Cuánto vendimos este mes?", "¿Cuál es el ticket promedio?"), "/ventas"),
    _n("metas", r"\bmetas?\b|\bobjetivos? de ventas?\b|\bpresupuestos?\b|\bcumplimiento (de|del) (la |el )?(meta|objetivo|presupuesto)\b|\bcuotas? de ventas?\b",
       "metas y presupuestos de ventas",
       "Inventia no guarda metas, cuotas ni presupuestos de ventas, por eso no puedo decirte si se cumplió una meta.",
       ("Compara octubre con septiembre", "¿Cómo va la proyección de ventas del mes?", "¿Qué se va a vender el próximo mes?"), "/ventas"),
    _n("clientes", r"\bclientes?\b|\bcompradores?\b|\bquien (nos )?compro\b|\bcartera\b|\bfidelizacion\b",
       "clientes",
       "Las ventas de Inventia no guardan datos del cliente (nombre, documento o historial de compras), así que no puedo decirte quién compró ni cuánto compra cada cliente. Lo que sí registra de cada venta es la sede, el vendedor, la fecha y los productos.",
       ("¿Cuánto vendió cada vendedor?", "¿Cuáles son los productos más vendidos?", "¿Cuántas PQRS hay pendientes?"), "/ventas"),
    _n("pagos", r"\b(medios?|metodos?|formas?) de pago\b|\bpagos? (en|con|por) (efectivo|tarjeta|transferencia)\b|\b(efectivo|tarjeta de credito|tarjeta debito|tarjeta|nequi|daviplata|fiado)\b",
       "medios de pago",
       "Inventia no registra cómo se pagó cada venta (efectivo, tarjeta, transferencia o crédito) ni maneja fiado o cuentas por cobrar.",
       ("¿Cuánto vendimos este mes?", "Ventas por sede", "¿Cuál es el ticket promedio?"), "/ventas"),
    _n("lotes", r"\blotes?\b|\bcaducidad\b|\bfechas? de (vencimiento|caducidad)\b|\bnumeros? de serie\b|\bproductos? (\w+ )?(vencidos?|por vencer|que vencen|proximos a vencer|caducad\w+)\b|\bvencimientos?\b",
       "lotes y fechas de vencimiento",
       "Inventia controla las existencias por producto y sede, no por lote ni por fecha de vencimiento o número de serie.",
       ("¿Cuánto hay de este producto?", "¿Qué productos no se han vendido en 60 días?", "¿Qué garantías están por vencer?"), "/inventario"),
    _n("ubicaciones", r"\b(estantes?|estanterias?|pasillos?|racks?)\b|\bubicacion(es)? (en|dentro de|exacta en) (la )?(bodega|almacen)\b|\b(ubicacion(es)?|ubicar|ubicado) (del |de los |de la |de cada )?(producto|productos|articulo|mercancia|referencia)s?\b",
       "ubicaciones dentro de la bodega",
       "El inventario se maneja por sede (cada sede tiene sus existencias), no por estante, pasillo o posición dentro de la bodega.",
       ("¿Cuánto hay de este producto por sede?", "Inventario por sede"), "/inventario"),
    _n("impuestos", r"\b(iva|impuestos?|retencion|retenciones|dian|facturacion electronica|resolucion de facturacion)\b",
       "impuestos y facturación electrónica",
       "Inventia no calcula impuestos ni emite facturas electrónicas: las ventas que registra son para controlar inventario y ventas internas.",
       ("¿Cuánto vendimos este mes?", "¿Cuánta utilidad dejaron las ventas?"), "/ventas"),
    _n("compras_ordenes", r"\b(orden(es)? de compra|compras? a proveedores?|cuentas? por pagar|proveedor(es)?|cotizacion(es)?|facturas? de compra)\b",
       "órdenes de compra y proveedores",
       "Inventia no emite órdenes de compra ni guarda un catálogo de proveedores: el pedido se hace por fuera. Lo que sí hace es sugerirte qué reponer y en qué cantidad, y registrar las compras como entradas de mercancía.",
       ("¿Qué debo reponer esta semana?", "¿Cuánto hemos comprado este mes?", "Recomendaciones pendientes"), "/recomendaciones"),
    _n("nomina", r"\b(nomina|salarios?|sueldos?|empleados? (que|con)|horas extras?|prestaciones|vacaciones)\b",
       "nómina y recursos humanos",
       "Inventia no maneja nómina ni recursos humanos. Lo único relacionado con las personas es la gestión de usuarios y las pausas activas (Seguridad y Salud en el Trabajo).",
       ("¿Cuántos usuarios hay?", "¿Cuántas pausas activas se han realizado?"), "/usuarios"),
    _n("contabilidad", r"\b(contabilidad|estado de resultados|libro diario|patrimonio|flujo de caja|caja menor|banco|bancos|gastos?|costos? fijos?|arriendo|balance general)\b",
       "contabilidad y gastos",
       "Inventia no maneja contabilidad ni gastos generales (arriendo, servicios, caja). Sí calcula la utilidad bruta de las ventas con el costo de cada producto.",
       ("¿Cuánta utilidad dejaron las ventas este mes?", "¿Cuánto vale el inventario?"), "/ventas"),
    _n("domicilios", r"\b(domicilios?|despachos?|rutas? de entrega|transportadora|guias? de envio|tracking|seguimiento de (pedido|envio)|pedidos? de clientes)\b",
       "domicilios y envíos a clientes",
       "Inventia no gestiona pedidos de clientes, domicilios ni envíos. Lo que sí controla son los **traslados entre sedes** de la empresa.",
       ("¿Qué traslados están pendientes?", "¿Qué sede envía más traslados?"), "/traslados"),
    _n("codigos_barras", r"\b(codigos? de barras?|qr|escaner|escanear|lector de codigos?)\b",
       "códigos de barras o QR",
       "Inventia identifica cada producto por su **código** (por ejemplo BAT-001), que se busca por texto al registrar ventas y movimientos. No trabaja con lector de códigos de barras ni QR.",
       ("¿Cuánto hay de BAT-001?",), "/productos"),
    _n("pronostico_clima", r"\b(clima|lluvia|temporada alta|festivos?|dia de la madre|navidad|black friday)\b.*\b(ventas?|demanda|prediccion)\b",
       "efectos externos (clima, festivos, campañas)",
       "La predicción de demanda aprende del historial de ventas de cada producto y sede (incluye el patrón semanal), pero no tiene en cuenta clima, festivos ni campañas que no estén ya reflejados en las ventas pasadas.",
       ("¿Qué se va a vender el próximo mes?", "¿Qué tan confiable es la predicción?"), "/predicciones"),
)
