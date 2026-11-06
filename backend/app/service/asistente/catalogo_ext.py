"""Intenciones ampliadas del asistente (segundo bloque del catálogo): rankings, análisis y conocimiento del sistema.

Va después de las intenciones base: ante un empate gana la base, así que estas llevan pesos más altos cuando deben ganar.
Los patrones se escriben sobre el texto ya normalizado (minúsculas, sin tildes ni signos).
"""

from app.service.asistente.intencion import INV, Intencion, _i

_ALERTA_CONTRA = [(r"\balert\w+", -2.5)]

# Intenciones ampliadas cuya respuesta no depende de las sedes (no se muestra «alcance»).
SIN_ALCANCE_EXT: frozenset[str] = frozenset({
    "ranking_precio", "lista_precios", "productos_inactivos", "glosario", "como_hacer", "modulos_sistema", "asistente_funciona", "version_sistema", "no_registra",
    "comparar_entidades", "comparar_sedes", "comparar_categorias", "comparar_productos",
})

INTENCIONES_EXT: tuple[Intencion, ...] = (
    # ------------------------------------------------------------------------------------------ Inventario
    _i("ranking_stock", "Inventario", "Producto con más o menos existencias", INV,
       ("¿Qué producto tiene más existencias?", "¿Cuál es el producto con menos stock?", "¿Qué producto tiene más valor en inventario?"), [
        (r"\b(que|cual|cuales) (es |son )?(el |los |la |las )?(producto|productos|referencia|referencias|articulo|articulos|item|items)\b.*\b(mas|menos|mayor|menor|mayores|menores)\b.*\b(stock|existencias?|unidades|inventario|valor)\b", 9),
        (r"\b(producto|productos|referencia|referencias) (con|de|que tiene|que tienen|tiene|tienen) (el |la )?(mas|menos|mayor|menor)( cantidad de)? (stock|existencias?|unidades|inventario)\b", 9),
        (r"\b(top|ranking|mayores|menores) (de )?(productos )?(por )?(stock|existencias|inventario|valor en inventario)\b", 8),
        (r"\b(mayor|menor|mas|menos) (stock|existencias?)\b", 5),
        (r"\b(producto|productos)\b.*\b(mas|mayor|menos|menor)\b.*\b(plata|dinero|capital|valor)\b.*\b(inventario|invertid\w+|bodega|stock)\b", 8),
        (r"\bdonde (tengo|tenemos|esta) (mas|la mayor parte de) (la )?(plata|dinero|capital|inversion)\b", 8),
    ], ruta="/inventario", contras=[(r"\b(agotad\w+|stock bajo|bajo stock|excesiv\w+|critic\w+)\b", -3), (r"\b(vend\w+|ventas?)\b", -4)]),
    _i("stock_umbral", "Inventario", "Productos con más o menos de N unidades", INV,
       ("Productos con más de 100 unidades", "Productos con menos de 20 unidades", "Productos con entre 10 y 50 unidades"), [
        (r"\b(mas|menos|mayor|menor|superior|inferior) (de|que|a|del) \d+ (unidades|piezas|und|unds|existencias|en stock|en inventario)\b", 9),
        (r"\b(con|tengan|tienen|tiene|hay|queden) (mas|menos|mayor|menor) (de|que|a) \d+\b", 6),
        (r"\bentre \d+ y \d+ (unidades|piezas|existencias)\b", 9),
        (r"\bproductos? con (mas|menos) de \d+", 7),
    ], ruta="/inventario", contras=[(r"\b(vend\w+|ventas?|dias|meses|semanas)\b", -4)]),
    _i("capital_inmovilizado", "Inventario", "Dinero parado en inventario", INV,
       ("¿Cuánto dinero tengo parado en inventario?", "¿Cuánta plata hay en exceso?"), [
        (r"\b(capital|dinero|plata|inversion|recursos?) (inmovilizad\w+|parad\w+|estancad\w+|congelad\w+|detenid\w+|atrapad\w+|dormid\w+)\b", 9),
        (r"\b(inmovilizad\w+|parad[oa]s?|estancad\w+|congelad\w+)\b.*\b(capital|dinero|plata|inventario|stock)\b", 8),
        (r"\bcuant[oa] (dinero|plata|capital) (tengo|tenemos|hay|esta) (en |de )?(exceso|sobrestock|productos sin (ventas|rotacion|movimiento)|mercancia (parada|sin rotacion))\b", 9),
        (r"\b(plata|dinero|capital) (en|de) (exceso|sobrestock|productos sin|mercancia sin)\b", 8),
    ], ruta="/inventario"),
    _i("productos_sin_minimo", "Inventario", "Productos sin stock mínimo o máximo configurado", INV,
       ("¿Qué productos no tienen stock mínimo configurado?",), [
        (r"\b(productos?|referencias?)\b.*\bsin (stock )?(minimo|maximo)\b", 9),
        (r"\b(productos?|referencias?|articulos?)\b.*\b(no tienen?|sin|no se les ha|les falta|falta)\b.*\b(stock |nivel(es)? )?(minimo|maximo)\b.*\b(definid\w+|configurad\w+|registrad\w+|asignad\w+|fijad\w+)\b|\b(no tienen|sin) (stock )?(minimo|maximo) (definid\w+|configurad\w+)\b", 12),
        (r"\bsin (stock )?(minimo|maximo)( configurado| definido| registrado)?\b", 8),
        (r"\b(minimo|maximo) (sin|no) (configurad\w+|definid\w+|registrad\w+)\b|\bfalta(n)? (configurar|definir) (el )?(stock )?(minimo|maximo)\b|\bsin niveles\b", 8),
    ], ruta="/inventario"),
    _i("ranking_precio", "Productos", "Productos más caros o más baratos", ("productos.ver",),
       ("¿Cuál es el producto más caro?", "Productos más baratos"), [
        (r"\b(mas|menos) (caro|cara|caros|caras|costoso|costosa|costosos|costosas|barato|barata|baratos|baratas)\b", 9),
        (r"\b(mayor|menor|mas alto|mas bajo|maximo|minimo) (precio|costo)\b", 8),
        (r"\bprecio (mas )?(alto|bajo|maximo|minimo)\b", 8),
        (r"\bproductos? (de )?(mayor|menor) (precio|costo|valor)\b", 8),
    ], ruta="/productos"),
    _i("lista_precios", "Productos", "Lista de costos y precios", ("productos.ver",),
       ("Lista de precios", "Productos con su costo y precio"), [
        (r"\blista de precios\b|\bprecios? de (todos )?(los|las) (productos|articulos|referencias)\b|\bcatalogo (con|de) precios\b", 9),
        (r"\bproductos? con (su )?(costo|precio)\b|\b(costo|precio)s? (y|con) (costo|precio)s?\b", 8),
        (r"\bcuanto (cuesta|vale|cuestan|valen) cada (producto|uno|articulo)\b", 8),
        (r"\b(precios?|costos?) de (las |los )?\w+", 3.5),
    ], ruta="/productos", prefiere="categoria", contras=[(r"\bpromedio\b|\bmargen\b", -4)]),
    _i("productos_inactivos", "Productos", "Productos inactivos", ("productos.ver",),
       ("¿Qué productos están inactivos?",), [
        (r"\bproductos? (inactiv\w+|inhabilitad\w+|deshabilitad\w+|descontinuad\w+|desactivad\w+|dados? de baja|retirad\w+)\b", 8.5),
        (r"\b(que|cuales|cuantos) productos (estan|hay|quedan) (inactiv\w+|inhabilitad\w+|deshabilitad\w+|descontinuad\w+|desactivad\w+)\b", 9),
        (r"\b(inactivos|inhabilitados|descontinuados|deshabilitados)\b", 5),
    ], ruta="/productos", contras=[(r"\b(usuarios?|empleados?|sedes?)\b", -6)]),
    _i("abc_inventario", "Ventas", "Clasificación ABC (Pareto) de productos", ("ventas.ver",),
       ("Análisis ABC de productos", "¿Qué productos son clase A?"), [
        (r"\babc\b|\bpareto\b|\bclasificacion abc\b|\bclase [abc]\b", 9),
        (r"\b80 ?(20|/20)\b", 8),
        (r"\bproductos? (estrella|clave|mas importantes|que mas aportan|que generan (la )?mayor parte)\b", 7),
    ], ruta="/ventas"),
    # ------------------------------------------------------------------------------------------------- Ventas
    _i("utilidad_ventas", "Ventas", "Utilidad de las ventas", ("ventas.ver",),
       ("¿Cuánta utilidad dejaron las ventas este mes?", "¿Cuánto ganamos esta semana?"), [
        (r"\b(utilidad|ganancia|ganancias|beneficio|rentabilidad|margen)\b.*\b(ventas?|vendid\w+|mes|semana|hoy|ayer|periodo|trimestre|ano|facturacion)\b", 10),
        (r"\b(ventas?|vendimos|vendido|vendiste|facturamos)\b.*\b(utilidad|ganancia|ganancias|beneficio|rentabilidad|margen)\b", 10),
        (r"\bcuanto (ganamos|gane|ganaste|gano|hemos ganado|llevamos ganado|dejamos|dejo)\b", 8.5),
        (r"\b(utilidad|ganancia) (bruta|neta|total|del (mes|dia|periodo|ano))\b", 8.5),
    ], ruta="/ventas"),
    _i("ventas_por_hora", "Ventas", "Horas en que más se vende", ("ventas.ver",),
       ("¿A qué hora se vende más?", "Ventas por hora"), [
        (r"\bhoras?\b.*\b(vende|venden|vendemos|se vende|ventas?|vendio|pico|concurrid\w+)\b", 9),
        (r"\b(vende|venden|vendemos|ventas?)\b.*\bhoras?\b", 8),
        (r"\bhoras? (pico|punta|de mayor (venta|movimiento|afluencia)|mas (concurrida|ocupada))\b|\bhorarios? (de|con) (mas )?ventas?\b|\b(franja|jornada|turno) (horari\w+ )?(con )?(mas )?ventas?\b|\bventas por hora\b", 9),
    ], ruta="/ventas", contras=[(r"\bque hora es\b|\bhora actual\b", -8)]),
    _i("venta_mayor", "Ventas", "Venta de mayor o menor valor", ("ventas.ver",),
       ("¿Cuál fue la venta más grande del mes?", "La venta más pequeña de la semana"), [
        (r"\b(venta|factura|ticket)\b.*\b(mas (grande|alta|alto|cara|cuantiosa|pequena|baja)|mayor|maxima|menor|minima)\b", 7),
        (r"\b(mayor|mejor|maxima|mas grande|mas alta|menor|minima|mas pequena|mas baja) (venta|factura)\b", 8),
        (r"\bventa de (mayor|menor) (valor|monto|cuantia)\b|\bcual fue (la )?(venta|factura) (mas|de mayor|de menor)\b", 9),
    ], ruta="/ventas", contras=[(r"\b(promedio|total|cuantas)\b", -3)]),
    _i("ventas_promedio", "Ventas", "Promedios de venta (por día, semana o mes)", ("ventas.ver",),
       ("¿Cuál es el promedio de ventas diarias?", "¿Cuánto vendemos por día en promedio?"), [
        (r"\bpromedio (de )?(ventas?|venta) (diari\w+|por dia|semanal\w*|mensual\w*|por semana|por mes)\b", 9),
        (r"\b(venta|ventas|vendemos|vendido|facturamos) (en )?promedio\b|\bpromedio (diario|semanal|mensual) de (ventas?|facturacion)\b", 9),
        (r"\bcuanto (vendemos|vendo|facturamos|se vende|vendimos) (en promedio|por dia|al dia|diariamente|cada dia|por semana|a la semana|por mes|al mes)\b", 9),
        (r"\britmo de ventas\b|\bpromedio de ventas\b", 7),
    ], ruta="/ventas"),
    _i("mis_ventas", "Ventas", "Mis propias ventas", ("ventas.ver", "ventas.registrar"),
       ("¿Cuánto he vendido yo este mes?", "Mis ventas de hoy"), [
        (r"\bmis ventas\b|\bmi (venta|vendido|facturacion)\b", 10),
        (r"\bcuanto (he|llevo) (vendido|facturado)\b|\blo que (he )?(vendido|facturado|vendi)\b|\bcuanto (vendi|facture|vendo yo)\b", 10),
        (r"\bventas (que )?(yo )?(he )?(hecho|registrado|realizado)\b|\blas ventas (que )?(registre|hice|hecho)\b", 9),
        (r"\bmis (resultados|numeros|cifras) de ventas?\b", 9),
    ], ruta="/ventas"),
    _i("ventas_proyeccion", "Ventas", "Cómo va a cerrar el mes (proyección de ventas)", ("ventas.ver",),
       ("¿Cómo va a cerrar el mes en ventas?", "¿Cuánto vamos a vender este mes a este ritmo?"), [
        (r"\b(cierre|cerrar|cerramos|cerraria|cerraremos|terminar|terminaremos|terminamos)\b.*\b(mes|ano|semana|trimestre)\b", 8),
        (r"\b(proyeccion|proyectad\w+|proyectar)\b.*\bventas?\b|\bventas?\b.*\b(proyeccion|proyectad\w+)\b", 8),
        (r"\ba (este|ese) ritmo\b|\bsi (seguimos|mantenemos|continuamos) (asi|este ritmo|igual)\b", 8),
        (r"\bcuanto (voy a|vamos a|alcanzaremos a|llegaremos a) (vender|facturar)\b.*\b(este|el) (mes|ano|trimestre)\b", 9),
    ], ruta="/ventas", contras=[(r"\b(unidades|demanda|producto)\b", -3)]),
    _i("ultima_venta_producto", "Ventas", "Última venta de un producto", ("ventas.ver",),
       ("¿Cuándo fue la última venta de BAT-001?", "¿Desde cuándo no se vende el casco urbano?"), [
        (r"\bultima venta (de|del|de la)\b|\bpor ultima vez\b|\bultima vez que (se )?(vendio|vendimos|vendieron)\b", 9),
        (r"\bdesde cuando no (se )?(vende|vendemos|vendio)\b|\bcuanto (hace|tiempo|llevamos|lleva) (que )?(no )?(se )?(vende|vendemos|sin vender|sin ventas)\b|\bhace cuanto (no )?(se )?(vende|vendio)\b|\bdias sin (vender|ventas)\b", 16),
    ], ruta="/ventas", requiere="producto"),
    # ------------------------------------------------------------------------------------------------ Alertas
    _i("alertas_analisis", "Alertas", "Análisis de alertas (por sede, producto, antigüedad y tiempo de resolución)", ("alertas.ver",),
       ("¿Qué sede tiene más alertas?", "¿Cuáles son las alertas más antiguas?", "¿Cuánto tardan en resolverse las alertas?"), [
        (r"\balert\w+\b.*\b(por|en cada) (sede|producto|categoria)\b|\balertas por (sede|producto|categoria)\b", 9),
        (r"\b(que|cual|cuales) (sede|producto|categoria|tipo)s? (tiene|tienen|con|presenta\w*|acumula\w*|concentra\w*)\b.*\bmas\b.*\balert\w+", 9),
        (r"\balert\w+\b.*\b(antigua\w*|viej\w+|mas tiempo|abierta\w* (hace|desde)|sin atender|rezagad\w+)", 9),
        (r"\b(antigua\w*|viej\w+)\b.*\balert", 9),
        (r"\b(tiempo|demor\w+|tarda\w*)\b.*\b(resol\w+|atend\w+|cerr\w+)\b.*\balert\w+|\balert\w+\b.*\b(tiempo|demor\w+|tarda\w*)\b", 9),
        (r"\bcuanto (tardan|demoran|se demoran|tarda|demora)\b.*\balert", 9),
        (r"\bdistribucion de (las )?alertas\b|\btipo de alertas? (mas )?(comun|frecuente)\b|\bproductos? con mas alertas\b|\bmas alertas\b", 8.5),
    ], ruta="/alertas"),
    # ----------------------------------------------------------------------------------------------- Traslados
    _i("traslados_analisis", "Traslados", "Análisis de traslados (en tránsito, tiempos, rutas y sedes)", ("traslados.ver",),
       ("¿Cuántas unidades hay en tránsito?", "¿Cuánto tarda un traslado?", "¿Qué sede envía más traslados?"), [
        (r"\b(unidades|mercancia|productos|inventario|stock|cuanto|cuantas)\b.*\b(en transito|en camino|por llegar)\b", 10),
        (r"\b(tiempo|cuanto (tarda|demora|se demora)|demora|tarda)\b.*\btraslad\w+|\btraslad\w+\b.*\b(tiempo|tarda|demora|demoran|duran?)\b", 9),
        (r"\btraslad\w+\b.*\b(por sede|envia\w*|recibe\w*|manda\w*)\b|\b(que|cual) sede (envia|manda|recibe|despacha|mas traslados)\b", 9),
        (r"\b(ruta|trayecto|recorrido)\b.*\btraslad\w+|\btraslad\w+\b.*\b(ruta|trayecto)\b|\bruta de traslado\b", 9),
        (r"\b(producto|productos)\b.*\b(mas|mayor)\b.*\btraslad\w+|\bmas trasladad\w+|\btraslad\w+\b.*\bproductos? mas\b", 9),
        (r"\b(producto|productos)\b.*\b(se )?(traslada\w*|mueve\w*|envia\w*)\b.*\bmas\b", 9),
    ], ruta="/traslados"),
    # --------------------------------------------------------------------------------------------- Movimientos
    _i("movimientos_analisis", "Movimientos", "Análisis de movimientos (quién, dónde y balance de entradas y salidas)", ("movimientos.ver",),
       ("¿Quién movió más inventario este mes?", "Balance de entradas y salidas", "¿Qué producto tiene más movimientos?"), [
        (r"\bquien\w*\b.*\b(movio|mueve|registro|registra|hizo|hace|realizo)\b.*\b(movimientos?|inventario|ajustes?|entradas?|salidas?)\b", 9),
        (r"\bmovimientos? por (sede|usuario|persona|tipo|producto)\b", 9),
        (r"\bbalance (de )?(entradas|movimientos)\b|\bentradas (vs|versus|contra|y) salidas\b|\bentraron y salieron\b|\bentra y sale\b|\bflujo de (inventario|mercancia)\b", 9),
        (r"\b(producto|productos)\b.*\bmas\b.*\b(movimientos?|movido|movimiento)\b|\bmas movimientos?\b", 8),
    ], ruta="/movimientos"),
    _i("compras_resumen", "Movimientos", "Compras de mercancía (entradas por compra)", ("movimientos.ver",),
       ("¿Cuánto compramos este mes?", "Compras del mes"), [
        (r"\b(compras|compramos|comprado|compradas|comprados|adquirimos|adquirido|adquisiciones?)\b", 8),
        (r"\bcuanto (gastamos|gaste|gasto|gastado|invertimos|invertido|invierto|pagamos|pague)\b.*\b(mercancia|inventario|compras|productos|reponer|reposicion)\b", 9),
    ], ruta="/movimientos", contras=[(r"\b(recomend\w+|sugier\w+|debo|deberia)\b", -6)]),
    _i("devoluciones", "Movimientos", "Devoluciones de clientes y a proveedores", ("movimientos.ver", "ventas.ver"),
       ("¿Cuántas devoluciones hubo?",), [
        (r"\bdevoluc\w+|\bdevolvi\w+|\bdevuelt\w+", 8),
    ], ruta="/movimientos"),
    # ----------------------------------------------------------------------------------------------- General
    _i("tareas_pendientes", "General", "Qué tengo pendiente (alertas, traslados, recomendaciones…)", (),
       ("¿Qué tengo pendiente?", "¿Qué es lo más urgente?"), [
        (r"\bque (debo|tengo que|hay que|toca|deberia) hacer\b", 8),
        (r"\bque (tengo|hay|tenemos|me queda) pendiente\w*\b", 8),
        (r"\b(tareas|pendientes|prioridades) (de hoy|del dia|para hoy|urgentes|pendientes)\b|\b(mis|las) (tareas|prioridades|pendientes)\b", 8),
        (r"\bque es (lo )?(mas )?(urgente|importante|prioritario)\b|\bque atiendo primero\b|\bpor donde (empiezo|comienzo|arranco)\b|\bque (priorizo|atiendo|hago primero)\b", 9),
    ]),
    # ------------------------------------------------------------------------ Predicción y recomendaciones
    _i("inversion_reposicion", "Predicción y recomendaciones", "Cuánto cuesta reponer lo recomendado", ("recomendaciones.ver",),
       ("¿Cuánto dinero necesito para reponer lo recomendado?", "Inversión necesaria en reposición"), [
        (r"\b(inversion|presupuesto|costo|cuanto (cuesta|costaria|costara|dinero|plata|necesito|se necesita|hay que invertir|invertir))\b.*\b(reponer|reposicion|reabastec\w+|comprar|compra|pedido|recomend\w+)\b", 13),
        (r"\b(reponer|reposicion|reabastecer|comprar|pedido)\b.*\b(cuesta|costaria|costo|inversion|presupuesto|cuanto dinero|cuanta plata)\b", 13),
        (r"\binversion (necesaria|sugerida|requerida|total)\b", 13),
    ], ruta="/recomendaciones"),
    _i("consejos_inventario", "Inventario", "Consejos para reducir exceso, evitar agotados o mejorar la rotación", INV,
       ("¿Cómo reduzco el inventario?", "¿Cómo evito quedarme sin stock?", "¿Cómo mejoro la rotación?"), [
        (r"\bcomo (reduzco|bajo|disminuyo|mejoro|aumento|optimizo|evito|controlo|cuido|administro|gestiono|manejo)\b.*\b(inventario|stock|existencias|rotacion|agotados?|exceso|faltantes?|mermas?|perdidas)\b", 9),
        (r"\bque (hago|puedo hacer|debo hacer|hacer) (con|para|si)\b.*\b(exceso|sobrestock|agotad\w+|productos sin|mercancia (parada|sin)|inventario)\b", 8.5),
        (r"\b(consejos?|recomendaciones? generales?|tips?|buenas practicas|sugerencias?)\b.*\b(inventario|stock)\b", 8),
        (r"\bcomo (mejorar|optimizar|reducir|evitar|controlar)\b.*\b(inventario|stock|rotacion|agotados|exceso)\b", 9),
        (r"\bcomo (puedo |podria |podemos |hago para |logro |consigo )?(vender|vendo|aumentar|aumento|subir|subo|incrementar|incremento|mejorar|mejoro) (mas|las ventas|mis ventas|ventas|el volumen de ventas)\b|\b(aumentar|subir|incrementar|mejorar) (las |mis )?ventas\b|\bvender mas\b", 10),
    ], ruta="/inventario"),
    # --------------------------------------------------------------------------------------------- Calidad y SIG
    _i("calidad_analisis", "Calidad y SIG", "Análisis de calidad (proveedores, productos, tiempos y garantías por vencer)",
       ("calidad.ver", "calidad.reportar", "calidad.gestionar"),
       ("¿Qué proveedor tiene más problemas?", "¿Qué producto tiene más no conformidades?", "¿Qué garantías están por vencer?"), [
        (r"\bproveedor\w*\b.*\b(problemas?|defectos?|fallas?|no ?conformidad\w*|garantias?|danos?|mal estado)\b", 11),
        (r"\b(problemas?|defectos?|fallas?|no ?conformidad\w*|garantias?)\b.*\bproveedor\w*\b", 11),
        (r"\b(producto|productos|sede|sedes|tipo|tipos)\b.*\b(mas|mayor)\b.*\b(no ?conformidad\w*|defectos?|garantias?|fallas?|danos?|defectuos\w+)", 11),
        (r"\b(no ?conformidad\w*|garantias?|defectos?)\b.*\b(por|segun) (proveedor|producto|sede|tipo)\b", 11),
        (r"\bproveedor\w*\b.*\b(mas|mayor|menos|menor)\b.*\b(reportes?|reclamos?|quejas?|incidencias?|casos|devoluciones|incumplimientos?)\b", 11),
        (r"\bgarantias? (por vencer|proximas a vencer|a punto de vencer|que vencen|venciendo)\b|\bvencen? (pronto|este mes|esta semana)\b.*\bgarantia|\bgarantia\w*\b.*\b(por vencer|vencer|vencen)\b", 11.5),
        (r"\b(tiempo|tarda\w*|demor\w+|cuanto)\b.*\b(resol\w+|solucion\w+|cerr\w+)\b.*\b(no ?conformidad\w*|garantias?)\b", 11),
        (r"\bdefectos? (mas )?(comun\w*|frecuente\w*)\b|\btipos? de (defecto|no ?conformidad)\b", 11),
    ], ruta="/sig/calidad"),
    _i("pqrs_analisis", "Calidad y SIG", "Análisis de PQRS (tiempos de respuesta, antiguas, por tipo y sede)", ("pqrs.crear", "pqrs.gestionar"),
       ("¿Cuánto tardan en responderse las PQRS?", "PQRS más antiguas sin responder"), [
        (r"\bpqrs\b.*\b(tiempo|demor\w+|tarda\w*)\b|\b(tiempo|cuanto tarda\w*|cuanto demor\w+)\b.*\bpqrs\b|\b(tiempo|cuanto tarda\w*)\b.*\b(responder|respuesta)\b.*\b(queja|reclamo|pqrs)", 11),
        (r"\b(pqrs|quejas?|reclamos?)\b.*\b(antigua\w*|sin responder|sin respuesta|mas viej\w+|sin atender|mas tiempo)\b", 11),
        (r"\b(quejas?|reclamos?|pqrs)\b.*\bpor (sede|tipo)\b|\btipo de (pqrs|queja|reclamo)\w* (mas )?(comun|frecuente)\b|\b(pqrs|quejas) mas (comun|frecuente)\w*", 11),
    ], ruta="/sig/pqrs"),
    _i("ambiental_equivalencia", "Calidad y SIG", "Equivalencia del CO₂ evitado en árboles", ("ambiental.ver", "ambiental.configurar"),
       ("¿A cuántos árboles equivale el CO₂ evitado?",), [
        (r"\b(arboles?|bosques?)\b", 9),
        (r"\bequivale\w*\b.*\b(co2|carbono|arbol\w*|emisiones)\b", 9),
    ], ruta="/sig/ambiental"),
    # ------------------------------------------------------------------------------------------ Administración
    _i("usuarios_acceso", "Administración", "Últimos ingresos y usuarios bloqueados", ("usuarios.ver",),
       ("¿Quién entró hoy al sistema?", "¿Hay usuarios bloqueados?"), [
        (r"\bultimo (acceso|ingreso)\b|\bquien(es)? (entro|entraron|ingreso|ingresaron|se conecto|se conectaron|inicio sesion|accedio|accedieron)\b|\bquien(es)? (esta|estan) (conectad\w+|en linea)\b|\bultimas? conexiones?\b", 10),
        (r"\busuarios? bloquead\w+\b|\bcuentas? bloquead\w+", 9),
    ], ruta="/usuarios"),
    _i("permiso_quien", "Administración", "Quién puede hacer algo (y si yo puedo)", (),
       ("¿Quién puede anular ventas?", "¿Puedo aprobar traslados?"), [
        (r"\b(quien|quienes|que rol\w*|cual(es)? rol\w*|que perfil\w*|que usuarios?|que cargo\w*)\b.*\b(puede|pueden|podria|tiene permiso|tienen permiso|autorizad\w+|deja|permite)\b", 9),
        (r"\b(puedo|podria|me deja|me permite|me permiten|tengo permiso|tengo acceso|estoy autorizad\w+|mi rol puede|puede mi rol)\b.*\b(anular|aprobar|registrar|crear|editar|ajustar|confirmar|solicitar|ejecutar|generar|gestionar|inhabilitar|eliminar|descargar|exportar|modificar)\b", 11),
        (r"\bpermisos? (para|de) (anular|aprobar|registrar|crear|editar|ajustar|confirmar|solicitar|ejecutar|generar|gestionar|inhabilitar|descargar|exportar)\b", 10),
    ], ruta="/roles"),
    # ------------------------------------------------------------------------------------------ Comparaciones entre entidades
    *(
        _i(clave, "Comparaciones", titulo, (*INV, "ventas.ver"), ejemplos, [
            (r"\b(compara\w*|comparacion|comparativ[oa]|enfrenta\w*|cara a cara)\b", 6),
            (r"\b(vs|versus)\b", 6),
            (r"\bdiferencias? (entre|de)\b", 5),
            (r"\b(cual|cuales|que|quien|quienes)\b.*\b(mas|menos|mejor|peor|mayor|menor)\b.*\b(o|u)\b", 7.5),
            *extra,
        ], ruta=ruta, requiere=requiere, contras=[(r"\b(mes|semana|ano|trimestre|quincena|dia|hoy|ayer) (pasad[oa]|anterior)\b", -2.5)])
        for clave, titulo, ejemplos, ruta, requiere, extra in (
            ("comparar_sedes", "Comparar dos o más sedes", ("Compara la sede Norte con la sede Sur", "¿Qué sede vende más, la Norte o la Sur?"), "/sedes", "sede",
             # sin nombrar ninguna: «compara las sedes», «compara el inventario entre sedes» (se comparan todas las que la persona puede ver)
             [(r"\b(compara\w*|comparacion|comparativ[oa]|enfrenta\w*|cara a cara)\b.*\b(las |todas las |mis |nuestras )?sedes\b|\bentre (las |todas las |mis |nuestras )?sedes\b", 8)]),
            ("comparar_categorias", "Comparar categorías", ("Compara bicicletas con monopatines",), "/categorias", "categoria", []),
            ("comparar_productos", "Comparar productos", ("Compara BAT-001 con BAT-002",), "/productos", "producto", []),
        )
    ),
)
