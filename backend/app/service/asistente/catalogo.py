"""Catálogo de intenciones del asistente.

Cada intención declara: el permiso que exige, las frases que la identifican (expresiones regulares sobre el texto ya
normalizado: minúsculas, sin acentos ni signos) con un peso, ejemplos reales de pregunta y la pantalla relacionada.
La intención ganadora es la de mayor puntaje; las entidades que aparecen en la frase (un producto, una sede…)
suman o restan para desempatar. Todo es puro: se prueba sin base de datos.
"""

import re
from dataclasses import dataclass

from app.service.asistente.catalogo_conocimiento import INTENCIONES_CONOCIMIENTO
from app.service.asistente.catalogo_ext import INTENCIONES_EXT
from app.service.asistente.intencion import INV as _INV
from app.service.asistente.intencion import Intencion, SenalesEntidades, _i  # noqa: F401

# Grupos que se muestran en la ayuda, en este orden.
CATEGORIAS_AYUDA = (
    "Inventario",
    "Productos",
    "Movimientos",
    "Ventas",
    "Comparaciones",
    "Traslados",
    "Alertas",
    "Predicción y recomendaciones",
    "Calidad y SIG",
    "Administración",
    "Ayuda del sistema",
    "General",
)

_ALERTA_CONTRA = [(r"\balert\w+", -2.5)]

_BASE: tuple[Intencion, ...] = (
    # ------------------------------------------------------------------------------------------ General
    _i("saludo", "General", "Saludar", (), ("Hola",), [
        (r"^(hola|ola|buen[oa]s?( dias| tardes| noches)?|saludos|hey|que tal|buen dia|que mas|quiubo|quihubo|epa)\b", 2.6),
    ]),
    _i("despedida", "General", "Despedirse", (), ("Chao",), [(r"\b(chao|adios|hasta luego|nos vemos|hasta pronto|bye)\b", 4)]),
    _i("gracias", "General", "Agradecer", (), ("Gracias",), [
        (r"\b(gracias|te agradezco|muy amable|mil gracias)\b", 4),
        (r"^(genial|perfecto|excelente|listo|vale|ok|okay|de acuerdo|entendido|super|buenisimo)\b", 2.8),
        (r"\b(felicitaciones|felicidades|bien hecho|buen trabajo|eres (genial|el mejor|un crack|muy bueno|buenisimo)|me sirvio|muy util|excelente trabajo|que bueno)\b", 4),
    ]),
    _i("quien_eres", "General", "Saber qué es el asistente", (), ("¿Quién eres?", "¿Eres una inteligencia artificial?"), [
        (r"\b(quien|que) eres\b|\bcomo te llamas\b|\btu nombre\b|\bquien te (creo|hizo|programo)\b", 4.5),
        (r"\beres (una? )?(ia|inteligencia|bot|robot|persona|humano|claude|chatgpt)\b|\bque (es|significa) inventia\b", 4.5),
    ]),
    _i("ayuda", "General", "Ver qué puedo preguntar", (), ("¿Qué puedes hacer?", "Ayuda"), [
        (r"\bayuda\b|\bayudame\b|\bhelp\b|\bmenu\b", 4),
        (r"\bque (puedes|sabes|haces)( hacer| responder| consultar)?\b|\bque puedo (preguntar|consultar|pedir)\b", 5),
        (r"\bpara que (sirves|sirve)\b|\bcomo (funcionas|te uso|se usa|funciona esto)\b", 5),
        (r"\bque (cosas|tipo de preguntas|preguntas|temas) (puedo|se pueden|te puedo|manejas|sabes)\b", 5.5),
        (r"\bejemplos?\b|\bcomandos?\b|\bopciones\b|\bque me puedes (decir|ayudar|mostrar)\b|\bno se (que|como) (preguntar|hacer)\b", 4),
    ]),
    _i("fecha_hoy", "General", "Saber la fecha de hoy", (), ("¿Qué día es hoy?",), [
        (r"\bque (dia|fecha|hora) (es|son|estamos)( hoy)?\b|\bfecha (de )?hoy\b|\ben que fecha estamos\b|\bque dia es hoy\b", 6),
    ]),
    _i("mi_perfil", "General", "Ver mi rol y mis permisos", (), ("¿Quién soy?", "¿Qué puedo hacer en el sistema?", "¿Cuáles son mis permisos?"), [
        (r"\bquien soy\b|\bcon que (rol|usuario|cuenta) (estoy|entre|ingrese)\b|\ben que sede estoy\b", 9),
        (r"\bmi (perfil|rol|sede|cuenta|usuario|correo|email|nombre)\b", 6.5),
        (r"\bque (rol|cargo|perfil|permisos|acceso|sede|usuario) (tengo|soy|es el mio|me corresponde|me asignaron|me dieron)\b|\b(a|en) que sede (pertenezco|estoy|trabajo|me corresponde|opero)\b|\bcual es mi (rol|sede|cargo)\b", 8.5),
        (r"\b(que|cuales) (puedo|no puedo|podria|se me permite) hacer\b|\b(mis )?permisos\b", 7),
        (r"\ba que (tengo|puedo) acceso\b|\bque (modulos|pantallas|opciones|secciones) (puedo|tengo)\b|\bque (acceso|accesos) tengo\b", 8),
    ], ruta="/perfil"),
    _i("navegacion", "General", "Encontrar una pantalla", (), ("¿Dónde registro una venta?", "¿Cómo llego a las alertas?"), [
        (r"\bdonde (veo|encuentro|esta|puedo ver|se ve|registro|creo|hago|se hace|puedo hacer|puedo crear|puedo registrar|miro|consulto)\b", 6.5),
        (r"\bcomo (llego|entro|accedo|voy|ingreso|abro|encuentro|veo|hago para ver)\b", 6.5),
        (r"\b(abre|abrir|abreme|llevame|ir a|ve a|vamos a|navega\w*|muestrame la (pantalla|pagina|seccion))\b", 6.5),
        (r"\b(pantalla|pagina|modulo|seccion|enlace)\b", 4.5),
    ]),
    _i("accion_no_soportada", "General", "Pedir un cambio (solo consulto)", (), ("Registra una venta",), [
        (r"^(por favor |porfa |favor )?(registra|registrame|crea|creame|agrega|agregame|anade|elimina|borra|anula|aprueba|rechaza|cancela|modifica|edita|cambia|"
         r"actualiza|ajusta|confirma|inhabilita|deshabilita|desactiva|habilita|restablece)\b", 11),
        (r"^(por favor |porfa |favor )?(registra|registrame|crea|creame|agrega|agregame|anade|elimina|borra|anula|aprueba|rechaza|cancela|"
         r"modifica|edita|cambia|actualiza|ajusta|solicita|confirma|inhabilita|deshabilita|desactiva|habilita|restablece|ejecuta|recalcula|"
         r"carga|importa|sube|envia|manda|pide|hazme|haz|genera)\b", 8),
        (r"\b(quiero|necesito|deseo|me gustaria|voy a|vamos a|puedes|podrias|podria|ayudame a|ayudame con)\s+(registrar|crear|agregar|anadir|"
         r"eliminar|borrar|anular|aprobar|rechazar|cancelar|modificar|editar|cambiar|actualizar|ajustar|solicitar|confirmar|inhabilitar|"
         r"deshabilitar|desactivar|habilitar|restablecer|ejecutar|recalcular|cargar|importar|subir|enviar|mandar|pedir|hacer una|generar)\b", 8),
    ]),
    _i("fuera_de_alcance", "General", "Temas que Inventia no maneja", (), ("¿Cuánto me deben los clientes?",), [
        (r"\b(cartera|cuentas? por (cobrar|pagar)|nomina|salarios?|sueldos?|impuestos?|iva|dian|bancos?|deudas?|prestamos?|"
         r"estado de resultados|balance general|contabilidad|facturacion electronica|pedidos de clientes|flujo de caja|caja menor)\b", 7),
        (r"\b(clientes?|proveedores?)\b", 3),
        # Temas que Inventia no guarda (la respuesta explica por qué y qué sí se puede preguntar).
        (r"\b(descuentos?|promocion(es)?|cupon(es)?|rebajas?|bonificacion(es)?)\b", 10),
        (r"\bmetas?\b|\bobjetivos? de ventas?\b|\bpresupuestos?\b|\bcumplimiento (de|del) (la |el )?(meta|objetivo|presupuesto)\b|\bcuotas? de ventas?\b", 10),
        (r"\b(que|cuales|cuantos|mejores|principales|nuevos|frecuentes|top) clientes\b|\bclientes? (que|con|frecuentes?|nuevos?|mas)\b|\bquienes? (nos |le )?(compro|compraron|compra|compran)\b|\b(ventas?|compras?|historial) (por|de cada|del) cliente\b|\bpor cliente\b|\bfidelizacion\b", 10),
        (r"\b(medios?|metodos?|formas?) de pago\b|\bpagos? (en|con|por) (efectivo|tarjeta|transferencia)\b|\b(efectivo|tarjeta de credito|tarjeta debito|nequi|daviplata|fiado)\b", 10),
        (r"\b(lotes?|caducidad|fechas? de (vencimiento|caducidad)|numeros? de serie|productos? (\w+ )?(vencidos?|por vencer|que vencen|proximos a vencer|caducad\w+)|vencimientos? de (productos|mercancia|inventario))\b", 10),
        (r"\b(estantes?|estanterias?|pasillos?|racks?)\b|\bubicacion(es)? (en|dentro de|exacta en) (la )?(bodega|almacen)\b|\b(ubicacion(es)?|ubicar|ubicado) (del |de los |de la |de cada )?(producto|productos|articulo|mercancia|referencia)s?\b", 10),
        (r"\b(orden(es)? de compra|cuentas? por pagar|cotizacion(es)?|catalogo de proveedores|lista de proveedores|facturas? de compra)\b", 10),
        (r"\b(domicilios?|transportadora|guias? de envio|rutas? de entrega|tracking|despachos? a clientes|pedidos? de clientes)\b", 10),
        (r"\b(codigos? de barras?|qr|escaner|escanear|lector de codigos?)\b", 10),
        (r"\b(clima|lluvia|temporada alta|festivos?|dia de la madre|navidad|black friday)\b.*\b(ventas?|demanda|prediccion)\b|\b(ventas?|demanda|prediccion)\b.*\b(clima|lluvia|festivos?|navidad|black friday|temporada alta|dia de la madre)\b", 10),
    ], contras=[(r"\b(quejas?|reclamos?|pqrs|peticion\w*|sugerencias?|garantia\w*|no ?conformidad\w*|defect\w*|calidad)\b", -8)]),
    _i("charla", "General", "Conversación fuera de tema", (), ("Cuéntame un chiste",), [
        (r"\b(chiste|cuentame algo|que opinas|clima|futbol|noticias|quien gano|receta|poema|cancion|horoscopo|capital de|presidente)\b", 6),
    ]),
    # ------------------------------------------------------------------------------------------ Inventario
    _i("resumen_general", "General", "Resumen general del negocio", (), ("Dame un resumen general", "¿Cómo va el negocio?"), [
        (r"\bresumen( general| ejecutivo)?\b", 2.5),
        (r"\bpanorama\b|\bvista general\b|\bestado general\b|\bsituacion (general|actual)\b|\bindicadores\b|\bkpis?\b|\bdashboard\b|\bpanel( de control)?\b|\binforme ejecutivo\b", 4.5),
        (r"\bcomo (esta|va|vamos|andamos|anda|nos va|marcha) (el |la |mi |nuestro |nuestra )?(negocio|empresa|todo|operacion|compania|tienda)\b", 6),
        (r"\bcomo (va|vamos|andamos) (todo|las cosas)\b|\bdame un (resumen|panorama)\b", 6),
        (r"^como (vamos|andamos|nos va|nos esta yendo|va el dia|vamos hoy)( hoy| ahora| este mes| esta semana)?$", 6),
        (r"\bresumen\b.*\b(negocio|empresa|dia|semana|mes|operacion)\b", 4),
    ], ruta="/"),
    _i("resumen_inventario", "Inventario", "Estado general del inventario", _INV, ("¿Cómo está el inventario?", "¿Cuántas unidades tenemos en total?", "Resumen del inventario"), [
        (r"\b(resumen|estado|situacion|panorama|salud|balance|radiografia) (general )?(del|de) (mi |nuestro )?inventario\b", 6),
        (r"\bcomo (esta|va|andamos|estamos|anda|vamos) (el |con el |de )?(inventario|stock|existencias|bodega|mercancia)\b", 6),
        (r"\binventario (general|total|actual|completo|global)\b|\bsalud del inventario\b", 4.5),
        (r"\bque tan (bien|mal) (esta|va|anda|andamos|vamos|estamos) (mi |el |nuestro |con el |con mi )?(inventario|stock|bodega|existencias)\b", 9),
        (r"\b(cuantas?|total de) (unidades|existencias|productos en inventario) (hay|tenemos|tiene|en total|totales|en inventario|en stock)?\b", 3.5),
        (r"\bunidades (totales|en total|en inventario)\b|\bexistencias totales\b|\bstock total\b|\bcuanto (inventario|stock) (hay|tenemos|tengo)\b|\bcuanto (llevo|llevamos|manejo|manejamos) (en )?(bodega|almacen|inventario|stock)\b", 5),
        (r"\binventario (de )?hoy\b|\bque hay en (el |la )?(almacen|bodega|inventario|stock)\b|\bcuanto hay (disponible|en total|de todo)\b|\bdisponibilidad (general|total)\b|\bque tengo (en|de) (inventario|stock|bodega)\b|\bque tenemos (en|de) (inventario|stock|bodega)\b", 6.5),
    ], ruta="/inventario"),
    _i("valor_inventario", "Inventario", "Valor del inventario", _INV, ("¿Cuánto vale el inventario?", "Valor del inventario por sede"), [
        (r"\bvalor\w* (del |de |total del |total de |de la |de las )?(inventario|mercancia|stock|existencias|bodega|almacen|inversion)\b", 7),
        (r"\b(inventario|mercancia|stock|existencias|bodega) (esta )?(valorizad\w*|valorado)\b", 7),
        (r"\bcuant[oa] (vale|valen|cuesta|cuestan|dinero|plata|capital|hay invertido|tenemos invertido|tengo invertido|esta invertido|hay en|tenemos en) "
         r"(el |la |mi |nuestro |en )?(inventario|mercancia|stock|bodega|existencias)\b", 7),
        (r"\bcapital (inmovilizado|invertido|parado|de trabajo)\b|\bdinero (invertido|parado|en (inventario|mercancia|stock))\b|\binversion en (inventario|mercancia)\b", 5.5),
        (r"\bvalor\w* (del |de )?(inventario|mercancia|stock|existencias) (por|de cada|en cada) (sede|bodega|tienda|categoria)\w*\b", 11),
        (r"\bcuant[oa] (plata|dinero|capital|valor|billete)( \w+){0,3} (inventario|mercancia|stock|bodega|existencias)\b", 7),
        (r"\bvalorizacion\b|\bvalorizar\b|\bcosto (total )?del inventario\b|\bcuanto (nos )?cuesta (el )?inventario\b", 5.5),
    ], ruta="/inventario"),
    _i("stock_producto", "Inventario", "Existencias de un producto", _INV, ("¿Cuánto hay de casco urbano?", "¿Hay stock de BAT-004?", "¿Dónde hay baterías de 48 V?"), [
        (r"\bcuant[oa]s?\b.*\b(hay|tenemos|tengo|tiene|queda\w*|existen?|disponibles?|stock|inventario|unidades|quedan)\b", 3),
        (r"\b(stock|existencias?|inventario|unidades|disponibilidad|disponible\w*) (de|del|de la|de los|de las)\b", 4.5),
        (r"\b(hay|tenemos|tengo|queda\w*|quedan|existen?) (de|del|de la|de los|de las)\b", 4.5),
        (r"\bhay\b.*\b(stock|existencias?|disponibilidad|unidades)\b", 3),
        (r"\b(en que|donde|que) sedes? (hay|tienen|tiene|esta|estan|queda|tenemos)\b|\bdonde (hay|esta|estan|tenemos|queda)\b", 4.5),
        (r"\bdisponib\w*\b|\b(tenemos|tienen|manejamos|hay|queda|quedan|existe|existen|tengo)\b", 1.5),
        (r"\b(queda|quedan|hay|tenemos|tengo|existe|existen|tienen) (alguna?|algun|algunos|algunas|unidades?|stock|existencias|disponibilidad)\b", 4.5),
    ], ruta="/inventario", requiere="producto"),
    _i("listar_agotados", "Inventario", "Productos agotados", _INV, ("¿Qué productos están agotados?", "¿Qué está agotado en la Sede Norte?"), [
        (r"\bagotad\w*", 5.5),
        (r"\bsin (stock|existencias?|unidades|inventario|disponibilidad)\b|\ben cero\b|\bstock (cero|0)\b|\bcantidad (cero|0)\b", 5.5),
        (r"\bquebrad\w*|\bquiebres? de stock\b|\bstock ?out\b", 5.5),
        (r"\b(se )?(acabo|acabaron|acabado|agoto|agotaron|termino|terminaron)\b", 3.5),
        (r"\bno (hay|queda\w*|tenemos|tengo|quedan) (nada|ninguna|ningun|stock|existencias|unidades|productos)\b", 4.5),
        (r"\bque (productos?|articulos?|referencias?|cosas) (no hay|faltan|nos faltan|hacen falta|estan en cero)\b|\bfaltantes?\b|\bhacen falta\b|\bnos falta\b", 5),
    ], ruta="/inventario", contras=_ALERTA_CONTRA),
    _i("listar_bajos", "Inventario", "Productos con stock bajo", _INV, ("¿Qué productos tienen stock bajo?", "¿Qué está por debajo del mínimo?"), [
        (r"\b(stock|inventario|existencias?|nivel(es)?|cantidad(es)?) (bajo|bajos|minimo|minimos|critico|criticos|insuficiente|insuficientes|escaso|escasos)\b", 6),
        (r"\bbajos? (stock|inventario|nivel)\b|\bpor debajo (del|de su|de) (minimo|nivel|stock)\b|\bdebajo del minimo\b", 6),
        (r"\b(poco|poca|pocos|pocas) (stock|inventario|existencias?|unidades)\b|\bqueda\w* (pocas?|pocos)\b|\bpocas? unidades\b", 5.5),
        (r"\bescas\w*\b", 5.5),
        (r"\bcasi (agotad\w*|sin|se acab\w*|se agot\w*|acabandose|en cero)\b", 6),
        (r"\ba punto de (agotar\w*|acabarse|quedar\w*)\b|\bpor agotar\w*\b|\bproximos? a agotar\w*\b", 6),
        (r"\bproductos? (con )?(bajo|poco)\b|\bnivel minimo\b|\bstock minimo\b|\bminimo permitido\b", 3),
        (r"\bbajo\b", 2.5),
    ], ruta="/inventario", contras=_ALERTA_CONTRA),
    _i("listar_excesivos", "Inventario", "Productos con exceso de stock", _INV, ("¿Qué productos tienen exceso de stock?", "¿Dónde tengo sobrestock?"), [
        (r"\bexces\w*\b", 5.5),
        (r"\bsobre ?stock\b|\bsobre ?inventario\b|\bsobreabastec\w*\b|\bsobrante\w*\b", 6.5),
        (r"\b(sobre|por encima d(el|e)) (el )?maximo\b|\bsupera\w* (el )?maximo\b|\bpasa\w* (el )?maximo\b|\bpor encima del tope\b", 6.5),
        (r"\bdemasiad[oa]s?\b", 3.5),
        (r"\b(mercancia|inventario|stock|productos?|unidades) (de mas|que sobra\w*|sobrante\w*|en exceso)\b|\bsobra(n)?\b", 5.5),
        (r"\b(mucho|mucha|muchos|muchas) (stock|inventario|unidades|existencias|mercancia|producto)\b", 5),
        (r"\bstock (muerto|parado|inmovil\w*)\b|\bcapital (parado|inmovil\w*)\b|\binmovilizad\w*", 4.5),
    ], ruta="/inventario", contras=_ALERTA_CONTRA),
    _i("niveles_producto", "Inventario", "Stock mínimo y máximo de un producto", _INV, ("¿Cuál es el stock mínimo de BAT-004?",), [
        (r"\b(stock|nivel|niveles|cantidad) (minim[oa]s?|maxim[oa]s?)\b", 5.5),
        (r"\bniveles? de (stock|inventario|existencias)\b", 5.5),
        (r"\b(minimo|maximo) (de|del|para)\b|\bpunto de (reorden|pedido)\b|\bstock de seguridad\b|\bumbral\w*\b", 4.5),
    ], ruta="/inventario", requiere="producto"),
    _i("inventario_por_sede", "Inventario", "Inventario por sede", _INV, ("¿Qué hay en la Sede Norte?", "Compara el inventario entre sedes"), [
        (r"\b(inventario|existencias?|stock|mercancia|productos|unidades) (de|en|por|de la|en la|de todas las|en todas las|en cada|por cada) (cada )?(sedes?|bodegas?|tiendas?|sucursal\w*|puntos? de venta)\b", 5.5),
        (r"\bque (hay|tenemos|tiene|tienen|queda) en (la |el |cada |todas las )?(sedes?|bodegas?|tiendas?|sucursal\w*)\b", 5.5),
        (r"\bdistribucion (del |de )?(inventario|stock)\b|\bque sede (tiene|tienen|concentra)\b", 5),
        (r"\b(por|cada|todas las) sedes?\b|\bcomparar? (las )?sedes\b|\bentre sedes\b|\bcomparativo\b", 2.8),
        (r"\bsede\b", 1.5),
    ], ruta="/inventario", prefiere="sede", contras=[(r"\b(ventas?|vendi\w*|vendio|vendimos|vendemos|facturaci\w*|facturad\w*|facturamos|ingresos?)\b", -1.5)]),  # «ventas de la sede norte» son ventas
    _i("inventario_categoria", "Inventario", "Inventario por categoría", _INV, ("¿Cuánto hay en la categoría baterías?", "Inventario por categoría"), [
        (r"\bcategori\w*\b", 2.8),
        (r"\bque (porcentaje|parte|proporcion|participacion|peso) (del |de |en el )?(inventario|stock|existencias|mercancia)\b", 8),
        (r"\b(por|cada|todas las) categori\w*\b|\binventario (de|por) (la )?categori\w*\b", 5),
        (r"\bcuant[oa]s?\b.*\b(hay|tenemos|tengo|tiene|queda\w*|existen?|disponibles?|quedan)\b|\b(stock|existencias?|inventario|unidades) (de|del|de la|de los|de las)\b", 1.5),
    ], ruta="/inventario/consolidado", prefiere="categoria"),
    _i("producto_info", "Productos", "Ficha de un producto", ("productos.ver",), ("¿Cuánto cuesta la bicicleta plegable?", "¿En qué categoría está BAT-004?", "Datos del producto REP-010"), [
        (r"\b(precio|precios|cuanto (cuesta|cuestan|vale|valen|sale|salen|costo)|costo|costos|pvp)\b", 3.5),
        (r"\b(codigo|referencia|sku)\b", 3),
        (r"\b(categoria|unidad de medida|descripcion|ficha|detalles?|datos|informacion|info|caracteristicas?) (de|del|de la)\b", 4.5),
        (r"\ben que categoria\b|\bde que categoria\b|\bque es (el|la|un|una)\b", 5),
        (r"\ba cuanto (lo |la |los |las )?(vendemos|se vende|sale|salen|esta|estan|cobramos|ofrecemos|vale|valen)\b", 9),
    ], ruta="/productos", requiere="producto"),
    _i("margen_productos", "Productos", "Margen de ganancia", ("productos.ver",), ("¿Qué productos tienen mayor margen?", "¿Cuál es el margen del casco urbano?"), [
        (r"\bmargen(es)?\b|\bganancia\w*|\butilidad(es)?\b|\brentabilidad\b|\bmarkup\b|\bcuanto (gano|ganamos|se gana|dejamos|deja)\b", 6),
        (r"\brentable\w*\b|\bdeja\w* (mas )?(utilidad|ganancia|margen|plata|dinero)\b|\b(mas|menos) (plata|dinero|utilidad) (deja|dejan)\b", 6.5),
    ], ruta="/productos"),
    _i("catalogo_conteo", "Productos", "Cuántos productos y categorías hay", ("productos.ver", "categorias.ver"), ("¿Cuántos productos manejamos?", "Productos sin costo registrado"), [
        (r"\bproductos?\b.*\b(sin|no tienen?|falta) (el )?(precio|costo)\b|\b(sin|no tienen?) (precio|costo)( registrado| definido| asignado)?\b", 9),
        (r"\bcuant[oa]s? (productos|articulos|referencias|items|categorias|skus|codigos)\b", 6),
        (r"\b(numero|total|cantidad) de (productos|articulos|referencias|categorias)\b", 5.5),
        (r"\bproductos? (activos|inactivos|inhabilitad\w*|desactivad\w*|descontinuad\w*)\b", 5.5),
        (r"\bproductos? sin (costo|precio|categoria)\b|\bsin (costo|precio) registrad\w*\b|\bcosto (faltante|sin registrar)\b", 6),
        (r"\bcatalogo\b", 3.5),
        (r"\bcuantos? (sku|skus)\b|\bsku\b|\bnumero de (sku|skus)\b", 6.5),
    ], ruta="/productos"),
    _i("buscar_producto", "Productos", "Buscar productos", ("productos.ver",), ("Busca productos de luz", "¿Qué productos manejamos?"), [
        (r"\b(busca\w*|buscar|encuentra\w*|localiza\w*|muestrame|dame|lista\w*|listame|enumera\w*|ver|mostrar|muestra) (los |las |el |la |todos los |todas las )?(productos|articulos|referencias|items)\b", 5),
        (r"\bque (productos|articulos|referencias) (hay|tenemos|manejamos|vendemos|tiene|tienen|son|ofrecemos)\b", 5),
        (r"\bproductos (de|del|de la|que (contengan|incluyan|tengan|se llamen|empiecen))\b|\bcatalogo de\b", 3.5),
        (r"\b(existe|tenemos|manejamos|vendemos|hay) (algun|alguna|un|una)? ?(producto|articulo|referencia)\b", 4),
        (r"\b(lista|listado) (de |del )?(los |mis |nuestros |todos los )?(productos|articulos|referencias|items|catalogo)\b", 6),
        (r"\b(muestrame|muestra|mostrar|dame|damelos|damelas|ver|busca|buscame|buscar|listame|lista)\b", 2.5),
    ], ruta="/productos", prefiere="producto"),
    # ------------------------------------------------------------------------------------------ Movimientos
    _i("entradas_mercancia", "Movimientos", "Entradas de mercancía", ("movimientos.ver",), ("¿Qué mercancía entró esta semana?", "Últimas entradas de inventario"), [
        (r"\bentradas?\b", 4.5),
        (r"\brecepci\w+\b|\brecibimos\b|\brecibid[oa]s?\b|\bllegaron?\b|\bllego\b|\bingresaron?\b|\bingreso de (mercancia|productos|inventario)\b", 4.5),
        (r"\bque (entro|ingreso|llego|recibimos)\b|\bmercancia (recibida|que llego|ingresada)\b", 6),
        (r"\b(que|cuanta|cuantas|cuantos|cual) (mercancia|productos?|articulos?|inventario|referencias?|unidades|cosas|material) (entro|entraron|ingreso|ingresaron|llego|llegaron|recibimos|compramos|se recibio|se recibieron|nos llego|nos llegaron)\b", 7),
        (r"\bcompras? (recibidas?|realizadas?|de mercancia)\b|\bdevoluci\w+ (de )?clientes?\b", 4.5),
    ], ruta="/movimientos"),
    _i("salidas_mercancia", "Movimientos", "Salidas, mermas y pérdidas", ("movimientos.ver",), ("¿Cuántas pérdidas tuvimos este mes?", "Salidas de inventario de ayer"), [
        (r"\bsalidas?\b", 4.5),
        (r"\bque (salio|egreso|se fue|se retiro)\b|\begresos?\b|\bretiros? de (mercancia|inventario)\b", 5.5),
        (r"\b(mermas?|perdidas?|deterioros?|danad\w*|rotura\w*|robos?|hurtos?|desperdicios?|bajas? de inventario|consumo interno)\b", 5.5),
        (r"\bdevoluci\w+ (a )?proveedor\w*\b", 5.5),
    ], ruta="/movimientos"),
    _i("ajustes_inventario", "Movimientos", "Ajustes de inventario", ("movimientos.ver",), ("¿Qué ajustes de inventario hubo este mes?",), [
        (r"\bajustes?\b|\bajustad\w*\b", 5),
        (r"\bconteo fisico\b|\bconteos? ciclicos?\b|\binventario fisico\b|\btoma fisica\b|\bdiferencias? de inventario\b|\bdescuadres?\b|\bcorreccion\w*\b", 5.5),
    ], ruta="/movimientos"),
    _i("movimientos_inventario", "Movimientos", "Movimientos y kardex", ("movimientos.ver",), ("Últimos movimientos de inventario", "Historial de movimientos de BAT-004"), [
        (r"\bmovimient\w*\b", 5),
        (r"\bkardex\b", 6.5),
        (r"\bhistorial\b", 3),
        (r"\btrazabilidad\b|\bbitacora de inventario\b|\bque paso con\b|\bultimos? cambios\b", 4),
        (r"\b(como|que) (se ha |se )?(movido|movio)\b", 4.5),
    ], ruta="/movimientos"),
    # ------------------------------------------------------------------------------------------ Ventas
    _i("ventas_resumen", "Ventas", "Resumen de ventas", ("ventas.ver",), ("¿Cuánto vendimos hoy?", "Ventas de este mes", "¿Cuántas bicicletas vendimos esta semana?"), [
        (r"\b(ventas?|vendi\w*|vendio|vendimos|vender|vendemos|facturaci\w*|facturad\w*|facturamos|factur\w+)\b", 3.5),
        (r"\bcuant[oa]s?\b.*\b(vend\w*|ventas|facturam\w*|factur\w*|recaud\w*)\b", 5),
        (r"\b(ingresos?|recaudo|recaudamos|ticket promedio|venta promedio|promedio de (venta|ventas|compra)|monto vendido|total vendido|total de ventas)\b", 5),
        (r"\bcomo (van|andan|estan|fueron|estuvieron|nos (fue|va)|vamos) (las |en )?ventas\b", 6.5),
        (r"\bcrecimiento\b|\bcrecieron\b|\bbajaron las ventas\b|\bsubieron\b", 3.5),
        (r"\bcuanta (plata|platica|lana|billete) (hemos|han|hicimos|llevamos|facturamos|vendimos|entro|entraron|ingreso)\b|\bcuanto (hemos|llevamos) (hecho|facturado|vendido|recaudado)\b|\bcuanto (entro|entraron|ingreso|ingresaron)\b", 8),
        (r"\b(cantidad|numero|total) de (transacciones|ventas|facturas|tickets)\b|\bcuantas (transacciones|facturas|tickets)\b", 8),
    ], ruta="/ventas"),
    _i("ventas_comparar", "Ventas", "Comparar ventas entre periodos", ("ventas.ver",), ("Compara octubre con septiembre", "Compara esta semana con la semana pasada"), [
        (r"\bcompar\w+\b", 4),
        (r"\b(versus|vs|contra|frente a|respecto (a|de)|diferencia entre|cambio entre|crecimiento (de|entre))\b", 3),
        # «¿vendimos más este mes que el anterior?»
        (r"\b(mas|menos|mejor|peor|crecimos|crecieron|bajamos|bajaron|subimos|subieron|aumentamos|aumentaron|disminuimos|disminuyeron|caimos|cayeron)\b.*"
         r"\b(este|esta|el) (mes|semana|ano|trimestre)\b.*\bque (el |la )?(anterior|pasad[oa]|previo|previa|mes|semana|ano|trimestre)\b", 8),
        (r"\b(respecto|frente|comparad[oa]|comparando|en comparacion) (a|con|al|a la)\b.*\b(anterior|pasad[oa])\b", 5),
    ], ruta="/ventas", requiere="periodo", contras=[(r"\bsedes?\b", -3.5)]),
    _i("ventas_por_sede", "Ventas", "Ventas por sede", ("ventas.ver",), ("¿Qué sede vende más?", "Ventas por sede este mes"), [
        (r"\bventas? (por|de cada|en cada|de las|entre) sedes?\b", 8),
        (r"\bque sede (vende|vendio|factura|facturo|genera|es la que)\b|\b(mejor|peor) sede\b|\bsede (que )?(mas|menos) (vende|vendio|factura|ventas)\b", 8),
        (r"\branking de sedes\b|\bcomparar? (las )?sedes\b", 3),
        (r"\b(cual|que) sede (vendio|vende|vendieron|factur\w+|genero|genera|tuvo|tiene)\b.*\b(mas|menos|mejor|peor|ventas)\b|\branking de sedes (por|en) ventas\b|\bsedes? (por|en) (ventas|facturacion)\b", 8.5),
        (r"\b(cual|que) (sede|tienda|sucursal) (va|vende|esta|anda|rinde|factura) (mejor|peor|mas|menos)\b|\bsede (que )?(va|vende|rinde) (mejor|peor)\b|\bmejor (sede|tienda|sucursal)\b|\bpeor (sede|tienda|sucursal)\b", 9),
        (r"\b(sede|tienda|sucursal) que (peor|mejor|mas|menos) (vende|vendio|factura|rinde|va)\b|\ben que (sede|tienda|sucursal) (me|nos|se) (va|vende|venden|vendo|vendemos|rinde) (mejor|peor|mas|menos)\b", 9),
    ], ruta="/ventas"),
    _i("ventas_top_productos", "Ventas", "Productos más (o menos) vendidos", ("ventas.ver",), ("¿Cuáles son los productos más vendidos?", "Top 5 más vendidos del mes"), [
        (r"\b(mas|menos) vendid[oa]s?\b", 8),
        (r"\b(mejores|peores) (productos|ventas|articulos)\b", 6.5),
        (r"\btop\b", 3.5),
        (r"\bproductos? (estrella|top|lideres?|populares|exitosos?|que (mas|menos) (se )?(vend\w*|sale\w*|rota\w*))\b", 8),
        (r"\bque (es lo )?(mas|menos) (se )?(vende|vendio|vendemos|sale|rota)\b|\b(lo|los) que (mas|menos) (se )?(vende\w*|sale\w*|rota\w*)\b", 8),
        (r"\b(mayor|menor) (venta|rotacion)\b|\bbest ?seller\w*\b|\brank\w* de productos\b", 6.5),
        (r"\bque (producto|articulo|referencia|item) (se )?(vende|vendio|vendemos|vendimos|sale|rota|mas se|es el que mas|es el mas)\b", 8.5),
        (r"\bque (productos|articulos|referencias) (se )?(vend\w*|vendieron|venden)\b", 6),
        (r"\bproductos? que (mas|menos) se (mueven?|venden|rotan?)\b|\bque (se )?(vende|vendemos|mueve) (poco|mucho|bien|mal)\b|\bque (no )?(se )?(vende|mueve) (nada|casi nada)\b", 8),
    ], ruta="/ventas"),
    _i("rotacion_inventario", "Ventas", "Rotación del inventario", ("ventas.ver",), ("¿Cuál es la rotación del inventario?", "¿Qué productos rotan más lento?"), [
        (r"\brotacion\b.*\b(inventario|stock|existencias|mercancia|bodega)\b|\b(inventario|stock|existencias|mercancia|bodega)\b.*\brotacion\b", 8),
        (r"\brotacion (de|del|por|en) (producto|productos|articulo|articulos|referencia|referencias|categoria|categorias|sede|sedes)\b", 7.5),
        (r"\b(rota|rotan|giran|gira)\b.*\b(lent\w+|rapid\w+|despacio)\b", 8),
        (r"\b(cuantas veces|que tan rapido|con que rapidez|a que velocidad) (rota|rotan|gira|giran|se mueve|se mueven|se vende|se venden|sale|salen)\b", 8),
        (r"\bindice de rotacion\b|\brotacion (promedio|general|total)\b|\bdias de (inventario|rotacion)\b.*\bproducto", 7.5),
        (r"\brotacion\b", 4),
    ], ruta="/ventas"),
    _i("productos_sin_ventas", "Ventas", "Productos sin rotación", ("ventas.ver",), ("¿Qué productos no se han vendido este mes?", "Productos con baja rotación"), [
        (r"\bsin (ventas|movimiento|rotacion|salida|demanda)\b", 8),
        (r"\bno (se )?(han? )?(vend\w*|mov\w*|rot\w*|sale\w*)\b|\bque no (se )?(ha |han )?(vend\w*|movi\w*)\b", 7),
        (r"\b(baja|poca|nula|ninguna) rotacion\b", 8),
        (r"\b(estancad\w*|obsolet\w*|muert[oa]s?|dormid\w*|lento movimiento|poco movimiento|inactivos? de venta)\b", 7),
        (r"\bsin vender\b|\bsin moverse\b", 7),
        (r"\bno se (mueve\w*|esta moviendo|vende\w*|rota\w*)\b|\bque no (sale\w*|rota\w*|se mueve\w*)\b|\bquiet[oa]s?\b", 7.5),
    ], ruta="/ventas"),
    _i("ventas_por_categoria", "Ventas", "Ventas por categoría", ("ventas.ver",), ("¿Qué categoría vende más?", "Ventas por categoría del mes"), [
        (r"\bventas? (por|de cada|en cada) categori\w*\b", 8),
        (r"\b(cual|que) categoria\w* (vende|vendio|factura|facturo|genera|es la que|tiene mas ventas|deja)\b|\bcategoria (que )?(mas|menos) (vende|vendio|factura|ventas)\b|\b(mejor|peor) categoria\b", 8),
    ], ruta="/ventas"),
    _i("ventas_por_dia", "Ventas", "Tendencia y mejores días de venta", ("ventas.ver",), ("¿Qué día se vende más?", "Tendencia de ventas del mes", "Ventas por mes"), [
        (r"\b(mejor|peor) (dia|mes|semana)\b|\bdia (que )?(mas|menos) (se )?(vende|vendio|vendemos|ventas)\b|\bmes (con )?(mas|mayores) ventas\b", 8),
        (r"\b(en )?que (dia|mes|semana)\w*( de \w+)?( de \d{4})? (se |hemos |ha )?(vende|vendio|vendemos|vendimos|vendido|factura|facturo|facturamos|vendieron|hay mas|hubo mas)\b", 8.5),
        (r"\b(que )?dias? de la semana\b|\btendencia\w*\b|\bevolucion\b", 5),
        (r"\bventas? (diarias?|por dia|dia a dia|cada dia|semanales?|mensuales?|por semana|por mes|por hora)\b", 8),
        (r"\b(dia|dias) (pico|de mas ventas|de mayor venta)\b|\bpico de ventas\b|\btemporada alta\b|\bestacionalidad\b", 7),
    ], ruta="/ventas"),
    _i("ventas_por_vendedor", "Ventas", "Ventas por vendedor", ("ventas.ver",), ("¿Quién vendió más este mes?",), [
        (r"\bquien (mas |menos )?(vendio|vende|ha vendido|factura)\b|\bvendedor\w*\b|\bcajer\w*\b", 7),
        (r"\bquien (registro|hizo|realizo|hace|ha hecho|ha registrado|proceso) (mas|menos) ventas\b|\bquien (tiene|hizo|registro) (mas|menos) ventas\b", 10),
        (r"\b(mejor|peor) (vendedor|empleado|usuario|persona|asesor)\b|\bventas? por (usuario|vendedor|empleado|persona|asesor|cajero)\b", 8),
    ], ruta="/ventas"),
    _i("ventas_recientes", "Ventas", "Últimas ventas", ("ventas.ver",), ("Últimas 10 ventas", "Muéstrame las ventas de ayer"), [
        (r"\bultim[oa]s? (\d+ )?ventas?\b|\bventas? recientes?\b|\bultima venta\b|\bhistorial de ventas\b", 8),
        (r"\b(lista|listado|listame|muestrame|ver|detalle) (de )?(las |mis )?ventas\b", 6.5),
        (r"\bque (se ha |hemos )?vendido\b", 5),
    ], ruta="/ventas"),
    _i("venta_detalle", "Ventas", "Detalle de una venta", ("ventas.ver",), ("Detalle de la venta 15",), [
        (r"\b(venta|factura|ticket|comprobante|remision) (numero |n |no |nro |num |#)?\d+\b", 10),
    ], ruta="/ventas"),
    _i("ventas_anuladas", "Ventas", "Ventas anuladas", ("ventas.ver",), ("¿Cuántas ventas anuladas hubo este mes?",), [
        (r"\bventas? (anuladas?|canceladas?|devueltas?)\b|\b(devoluciones|devueltas?) de ventas?\b", 9),
        (r"\banulacion\w*\b|\banuladas?\b", 6),
    ], ruta="/ventas"),
    # ------------------------------------------------------------------------------------------ Traslados
    _i("traslado_detalle", "Traslados", "Detalle de un traslado", ("traslados.ver",), ("Detalle del traslado 3",), [
        (r"\btraslado (numero |n |no |nro |num |#)?\d+\b", 10),
    ], ruta="/traslados"),
    _i("traslados_pendientes", "Traslados", "Traslados pendientes", ("traslados.ver",), ("¿Qué traslados están pendientes?", "Traslados por aprobar"), [
        (r"\btraslados? (pendientes?|por (aprobar|confirmar|recibir|revisar)|solicitados?|abiertos?|sin (aprobar|confirmar)|en (transito|camino|proceso|curso)|esperando)\b", 11),
        (r"\b(pendientes?|por aprobar|por confirmar|en transito) .*traslados?\b|\bque traslados (hay|tengo|debo|faltan?)\b", 7),
        (r"\btraslados? (que )?(estan?|hay|quedan|siguen|faltan?)( \w+)? (pendientes?|por (aprobar|confirmar|recibir|revisar)|en (transito|camino|proceso)|sin (aprobar|confirmar))\b", 9),
    ], ruta="/traslados"),
    _i("traslados_lista", "Traslados", "Consultar traslados", ("traslados.ver",), ("Traslados de este mes", "¿Cuántos traslados se confirmaron?"), [
        (r"\btraslad\w+\b", 4.5),
        (r"\btraslados? (que |de |desde |hacia |a |para )?(llegaron|llegan|salieron|salen|recibimos|enviamos|se hicieron|se hizo|hubo|hay|se confirmaron|se aprobaron|se rechazaron|se cancelaron)\b", 9),
        (r"\b(envi\w+|movimos|mandamos|transferim\w+|transferid\w+) (de |entre )?(una )?sede\w*\b", 5),
        (r"\bhistorial de traslados\b|\b(cuantos|cuantas|ultimos?) traslados\b", 6),
        (r"\btransferencias?\b", 4),
    ], ruta="/traslados"),
    # ------------------------------------------------------------------------------------------ Alertas
    _i("alertas_resumen", "Alertas", "Cuántas alertas hay", ("alertas.ver",), ("¿Cuántas alertas hay?", "Resumen de alertas"), [
        (r"\bcuant[oa]s? alertas?\b|\b(resumen|conteo|total|numero|cantidad) de alertas\b", 9),
        (r"\balertas? (activas?|abiertas?|pendientes?)? ?(hay|tengo|tenemos|existen)\b|\balertas? por (tipo|prioridad)\b|\bhay alertas?\b", 7),
        (r"\b(hay|tengo|tenemos|ves|detectas|encuentras) algo (raro|extrano|anormal|inusual|preocupante|grave|malo|mal|fuera de lo normal)\b|\balgo (raro|extrano|anormal|inusual|preocupante)\b", 8),
        (r"\bhay (algun |algunos )?(problemas?|novedad\w*|inconvenientes?|anomalias?|irregularidades?) (en|con) (el |la |los |las |mi |mis )?(inventario|stock|existencias|bodega|productos)\b", 8),
    ], ruta="/alertas"),
    _i("alertas_lista", "Alertas", "Alertas de inventario", ("alertas.ver",), ("Alertas críticas", "¿Qué debo revisar hoy?", "Alertas de inventario bajo"), [
        (r"\balert\w+\b", 4.5),
        (r"\balertas? (de |por |del |con )?(stock|inventario|existencias?|exceso|sobre ?stock|riesgo|agotamiento|desabastecimiento|quiebre|bajo|baja|excesivo|sobrante|faltantes?|revision)\b", 10.5),
        (r"\balertas? (ya )?(resuelt\w+|cerrad\w+|solucionad\w+|atendid\w+)|\bhistorial de alertas\b", 10),
        (r"\b(avisos?|advertencias?|notificaciones|banderas? rojas?|focos? rojos?|alarmas?)\b", 4),
        (r"\bproblemas? (de |en )?(inventario|stock)\b", 5),
        (r"\bque (debo|tengo que|hay que|toca|necesito|conviene|deberia) (revisar|atender|resolver|vigilar|mirar|ver)\b", 6),
        (r"\bque (esta|estan) (mal|fallando|critico\w*)\b|\ben que (debo|tengo que|hay que) (enfocarme|concentrarme|fijarme)\b", 5.5),
        (r"\b(criticos?|criticas?|urgentes?|prioritari\w+)\b", 3.5),
    ], ruta="/alertas"),
    _i("riesgo_desabastecimiento", "Alertas", "Riesgo de desabastecimiento y cobertura", ("prediccion.ver", "alertas.ver"), ("¿Qué productos se van a agotar pronto?", "¿Cuántos días me dura la batería 48 V?"), [
        (r"\brie?sgo de (desabastec\w*|quiebre|agotamiento|faltante|ruptura)\b", 9),
        (r"\bque (se )?(va a |vamos a |podria |puede )?(agotar\w*|acabar\w*|quedar\w* sin|faltar|terminar\w*)\b", 7.5),
        (r"\b(se agotaran|se acabaran|va a faltar|van a faltar|faltaran|se terminara\w*|nos quedaremos sin|quedaremos sin)\b", 7.5),
        (r"\b(van|va|vamos|podrian|pueden|podria|puede|iran|ira) a (agotar\w*|acabar\w*|quedar\w* sin|faltar|terminar\w*)\b|\b(a punto de|por|proximos? a) (agotar\w*|acabar\w*)\b|\bse (me |nos |le |les )?(esta|estan) (agotando|acabando|terminando)\b|\bpor agotarse\b", 8.5),
        (r"\bque (pasa|pasaria|ocurre|ocurriria|sucede|sucederia) si no (repongo|reponemos|repone|compro|compramos|pido|pedimos|reabastezco|reabastecemos|hago pedido)\b", 9),
        (r"\bcobertura\b|\bdias de (cobertura|inventario|stock|autonomia|duracion)\b", 7),
        (r"\bcuant[oa]s? (dias|tiempo|semanas) (me |nos |le |les )?(dura\w*|alcanza\w*|aguanta\w*|nos queda\w*|queda\w*|tenemos de)\b|\bcuanto (me |nos )?(dura\w*|alcanza\w*|duran|aguanta\w*)\b", 7.5),
        (r"\bdesabastec\w*\b|\bproxim\w+ a (agotar\w*|acabar\w*)\b", 4.5),
    ], ruta="/alertas", prefiere="producto"),
    # ------------------------------------------------------------------------------------------ Predicción y recomendaciones
    _i("prediccion_demanda", "Predicción y recomendaciones", "Demanda estimada (predicción)", ("prediccion.ver",), ("¿Cuánto se venderá de casco urbano las próximas 2 semanas?", "¿Qué productos tendrán más demanda?"), [
        (r"\bpredic\w+\b", 4.5),
        (r"\bpronostic\w+\b|\bforecast\b|\bprevision\b|\bprever\b|\bprevisto\b", 5),
        (r"\bproyecc\w+\b|\bproyect\w+\b", 4),
        (r"\bestim\w+\b", 3.5),
        (r"\bdemanda\b", 4),
        (r"\bcuant[oa]s? (se )?(va a |vamos a |voy a |podria |podriamos |se espera |esperamos |esperas |calculas |estimas |proyectas |prevees |predices )?"
         r"(vender|venderse|venderemos|vendera|demandar|necesitar|pedir|consumir|salir)\b", 8),
        (r"\b(se vendera|venderemos|vamos a vender|voy a vender|vendera|venderan|se demandara|se espera vender|esperamos vender)\b", 7),
        (r"\bque (tanto|cuanto) (se )?(va a )?vender\w*\b|\bdemanda (esperada|futura|estimada|proyectada|prevista|proxima)\b", 7),
        (r"\bque (se )?(va|van|vamos|vas|podemos|podriamos|podria) a (vender|venderse|demandar)\w*\b|\bque (venderemos|vendera|venderan|se vendera|se vendera)\b", 8),
        (r"\bventas? (esperad\w+|futur\w+|proyectad\w+|estimad\w+|previst\w+)\b|\b(proxim[oa]s?|siguientes?|venider[oa]s?) .{0,20}\bventas?\b|\bventas? .{0,20}\b(proxim[oa]s?|siguientes?|venider[oa]s?)\b", 7),
        (r"\b(mayor|menor|mas|menos) demanda\b", 6.5),
        (r"\bque productos? (tendra|tendran|va a tener|van a tener|tendria|tienen) (mas |mayor )?demanda\b", 8),
    ], ruta="/predicciones", prefiere="producto"),
    _i("prediccion_estado", "Predicción y recomendaciones", "Estado y precisión de la predicción", ("prediccion.ver",), ("¿Cuándo se generó la última predicción?", "¿Qué tan precisa es la predicción?"), [
        (r"\b(ultima|ultimo|actual) (prediccion|ejecucion|corrida|pronostico|modelo)\b", 7.5),
        (r"\b(estado|situacion|resumen|informacion|info) (de |sobre )?(la |las )?(prediccion|predicciones|pronosticos?|ejecucion)\b", 9),
        (r"\bcuando (fue|se hizo|se corrio|se genero|corrio) (la )?(ultima )?(prediccion|ejecucion|corrida)\b", 9),
        (r"\bcuando se (genero|ejecuto|calculo|corrio|actualizo|hizo) (la |el )?(ultim\w+ )?(prediccion|pronostico|modelo)\b", 9),
        (r"\b(precision|exactitud|confiabilidad|confianza|acierto|error)\b.*\b(modelo|prediccion|pronostico|predicciones)\b", 9),
        (r"\bque tan (bueno|buena|preciso|precisa|confiable|exacto|exacta|bien)\b", 6),
        (r"\b(wape|mae|rmse|mape|smape|metricas?|linea base)\b", 7),
        (r"\bque (modelos?|algoritmos?|metodos?|tecnicas?) (usan|usas|utilizan|emplean|se usan|se utilizan|hay)\b|\bcomo (se )?(predice|predices|pronostican|pronostica|pronosticas)\b", 8),
        (r"\bmodelos? (usado|usados|utiliz\w+|empleado|de prediccion|predictivo\w*|estadisticos?|entrenado\w*)\b", 7.5),
        (r"\bcomo (predices|predice|calculas|calcula|funciona la prediccion|se calcula la (demanda|prediccion)|estimas)\b", 7.5),
        (r"\b(prediccion|predicciones) (esta )?(desactualizad\w+|vencid\w+|actualizad\w+|vigente\w*)\b", 9),
        (r"\bhorizonte\b", 4),
    ], ruta="/predicciones"),
    _i("recomendaciones", "Predicción y recomendaciones", "Qué reponer, comprar o trasladar", ("recomendaciones.ver",), ("¿Qué debo reponer esta semana?", "¿Qué debo trasladar entre sedes?", "Recomendaciones pendientes"), [
        (r"\brecomend\w+\b", 5),
        (r"\bque (me )?(recomiendas|sugieres|aconsejas|propones)\b", 8),
        (r"\bsugerenc\w+\b|\bsugerid\w+\b|\bsugier\w+\b", 4),
        (r"\bque (debo|deberia|tengo que|hay que|toca|conviene|necesito|necesitamos|debemos|deberiamos|me toca|nos toca|puedo|podemos|tocaria) "
         r"(reponer|comprar|pedir|reabastecer|surtir|resurtir|reordenar|ordenar|trasladar|mandar|enviar|mover|adquirir|encargar)\b", 8.5),
        (r"\b(reponer|reposicion|reabastec\w+|resurtir|surtir|reordenar)\b", 5.5),
        (r"\bque (compro|pido|ordeno|encargo|compramos|pedimos|ordenamos|surto)\b", 8.5),
        (r"\b(lista|orden|ordenes|pedido|pedidos) (de |para )?(compras?|compra|reposicion|reabastecimiento|pedidos?)\b|\bnecesito (comprar|pedir|reponer|surtir)\b", 7.5),
        (r"\bpor comprar\b|\bpor pedir\b|\ba comprar\b|\ba pedir\b", 5),
        (r"\bcuant[oa]s? (debo|deberia|tengo que|conviene|necesito|necesitamos|debemos|hay que) (comprar|pedir|reponer|ordenar|trasladar|encargar)\b", 8.5),
        (r"\bcuantas? recomendaciones\b|\bestado de las recomendaciones\b|\bhistorial de recomendaciones\b", 9),
        (r"\bque (recomienda|sugiere|aconseja|propone) (el )?(sistema|inventia|la herramienta)\b|\bque me (recomienda|sugiere|aconseja) (el )?(sistema|inventia)\b", 9),
    ], ruta="/recomendaciones"),
    _i("reportes_ayuda", "General", "Cómo sacar un reporte", (), ("¿Cómo descargo un reporte de ventas?",), [
        (r"\breport\w+\b", 5),
        (r"\b(exportar|descargar|exporta\w*|descarga\w*|imprimir|sacar un)\b", 5),
        (r"\b(excel|xlsx|csv|pdf)\b", 5),
        (r"\binforme\w*\b", 4.5),
    ], ruta="/reportes"),
    # ------------------------------------------------------------------------------------------ Calidad y SIG
    _i("pqrs_resumen", "Calidad y SIG", "PQRS (peticiones, quejas, reclamos y sugerencias)", ("pqrs.crear", "pqrs.gestionar"), ("¿Cuántas PQRS hay pendientes?", "Mis quejas y reclamos"), [
        (r"\bpqrs\b", 9),
        (r"\bcuant[oa]s? (pqrs|quejas|reclamos|peticiones)\b.*\b(sin responder|sin respuesta|pendientes|abiertas|sin atender|sin resolver)\b", 12),
        (r"\b(quejas?|reclamos?|peticion\w+|buzon|radicado\w*)\b", 6.5),
        (r"\bsugerencias? (de |del )?(los )?(clientes?|usuarios?|empleados?)\b|\bmis (quejas|reclamos|peticiones|solicitudes|pqrs)\b", 8),
    ], ruta="/sig/pqrs"),
    _i("calidad_resumen", "Calidad y SIG", "Calidad: no conformidades y garantías", ("calidad.ver", "calidad.reportar", "calidad.gestionar"), ("¿Cuántas no conformidades hay abiertas?", "Resumen de calidad"), [
        (r"\bno ?conformidad\w*\b", 9),
        (r"\bcalidad\b", 6),
        (r"\bacciones? (correctivas?|preventivas?|de mejora)\b|\bcapa\b|\bmejora continua\b|\bcausa raiz\b|\breclamos? de calidad\b", 8),
        (r"\bdefect\w+\b|\bdefectuos\w+\b|\bhallazgos?\b", 6),
        (r"\bproductos? (danados?|equivocados?|con (defecto|falla|problema))\b|\bproveedor\w* (con )?(problemas?|fallas?|incumpl\w+)\b", 7),
    ], ruta="/sig/calidad"),
    _i("garantias", "Calidad y SIG", "Garantías", ("calidad.ver", "calidad.reportar", "calidad.gestionar"), ("¿Qué garantías están abiertas?",), [
        (r"\bgarantia\w*\b", 9.5),
    ], ruta="/sig/calidad"),
    _i("sst", "Calidad y SIG", "Seguridad y salud en el trabajo (pausas activas)", ("sst.ver", "sst.gestionar"), ("¿Cómo va el cumplimiento de las pausas activas?",), [
        (r"\bpausas? activas?\b|\bcumplimiento de (las )?pausas\b", 9),
        (r"\b(sst|seguridad y salud|salud ocupacional|salud en el trabajo)\b", 9),
        (r"\b(ergonomi\w+|postura\w*|estiramient\w+|descansos? activos?|ejercicios? (de|para) (pausa|descanso)|bienestar laboral)\b", 6),
        (r"\bcuantas pausas\b|\bpausas (se )?(hicieron|realizaron|hechas|realizadas|activas hechas)\b", 8),
    ], ruta="/sig/sst"),
    _i("ambiental", "Calidad y SIG", "Gestión ambiental (CO₂ evitado)", ("ambiental.ver", "ambiental.configurar"), ("¿Cuánto CO₂ evitamos este año?",), [
        (r"\b(ambiental\w*|co2|dioxido de carbono|carbono|huella de carbono|emision\w*|ecologic\w+|sostenib\w+|medio ?ambiente|contamin\w+)\b", 8),
        (r"\b(toneladas?|kg) de co2\b|\bevit\w+ (emitir|emisiones)\b|\bimpacto (ambiental|verde)\b", 9),
        (r"\bvehiculos? electricos? (vendid\w+|que vendimos)\b", 5),
    ], ruta="/sig/ambiental"),
    # ------------------------------------------------------------------------------------------ Administración
    _i("sedes_info", "Administración", "Sedes de la empresa", ("sedes.ver",), ("¿Cuántas sedes tenemos?", "¿Dónde queda la Sede Norte?"), [
        (r"\bcuantas sedes\b|\bque sedes (tenemos|hay|existen|tiene|manejamos|estan|activas)\b", 9),
        (r"\b(lista|listado|nombres?) de (las )?sedes\b|\bnuestras sedes\b|\bmis sedes\b", 8),
        (r"\bsedes? (activas?|inactivas?|inhabilitadas?|abiertas?|cerradas?)\b", 7),
        (r"\b(informacion|info|datos|detalles?|ficha|perfil) (de|sobre|acerca de) (la )?(sede|tienda|bodega)\b", 8.5),
        (r"\bdonde (esta|queda|se ubica|estan|quedan) (la |las )?(sede|sedes|tienda|bodega)\b|\b(direccion|ubicacion|ciudad|telefono) de (la )?(sede|tienda|bodega)\b", 7.5),
        (r"\b(ciudad|ciudades|direccion|direcciones|telefono|ubicacion|ubicaciones) de (las |los )?(sedes|tiendas|bodegas|puntos)\b|\ben que ciudad\w* (estan|queda|quedan|tenemos|hay)\b", 8),
        (r"\b(en que|a que|que|cual es la) (ciudad|direccion|barrio|zona)\b.*\b(sede|sedes|tienda|bodega)\b", 9),
        (r"\b(sede|sedes|tienda|bodega)\b.*\b(en que|a que|que) (ciudad|direccion|barrio|zona)\b", 9),
    ], ruta="/sedes"),
    _i("usuarios_info", "Administración", "Usuarios y equipo", ("usuarios.ver",), ("¿Cuántos usuarios hay?", "¿Quién es el administrador?"), [
        (r"\bcuant[oa]s? (usuarios|empleados|trabajadores|personas|colaboradores|vendedores|administradores|gerentes|encargados|analistas)\b", 9),
        (r"\busuarios?( activos| inactivos| registrados| habilitados| inhabilitados| del sistema)?\b", 4.5),
        (r"\b(lista|listado) de (usuarios|empleados|personal)\b|\busuarios? por rol\b", 9),
        (r"\b(empleados|personal|equipo de trabajo|trabajadores|colaboradores)\b", 5),
        (r"\bquien(es)? (es|son|esta|estan|administra|maneja|encargado|trabaja\w*) (el |la |los |las |de )?(administrador|gerente|encargad\w+|analista|usuari\w+|equipo|personal)\b|\bquien es el (administrador|gerente|encargado|analista)\b", 8),
        (r"\b(que|cual) rol (tiene|cumple|ocupa|desempena) (el |la |los |las )?(gerente|administrador|encargad\w+|analista|usuari\w+)\b|\bcomo se (llama|llaman) (el |la |los |las )?(administrador|gerente|encargad\w+|analista|dueno|usuari\w+)\b|\bquien es (el |la )?dueno\b", 9),
        (r"\bquienes (son|es) (los |las |el |la )?(administrador\w*|gerente\w*|encargad\w+|analista\w*|vendedor\w*|usuario\w*)\b", 10),
    ], ruta="/usuarios"),
    _i("roles_info", "Administración", "Roles y permisos", ("roles.ver", "usuarios.ver"), ("¿Qué roles hay?", "¿Qué puede hacer el gerente?"), [
        (r"\broles?\b", 5.5),
        (r"\b(que )?(hace|puede hacer|permite) (el |un |la )?(rol |perfil )?(de )?(administrador|gerente|encargado|analista|usuario de inventario)\b", 8),
        (r"\bdiferencia\w* entre (los )?roles\b|\bperfiles? de usuario\b", 8),
        (r"\b(permisos|funciones|alcance|accesos?|que puede hacer|que hace) (del|de la|de los|de las|que tiene el|que tiene la) (rol |perfil )?(administrador|gerente|encargad\w+|analista|usuario)\b", 10),
    ], ruta="/roles"),
    _i("auditoria", "Administración", "Auditoría (quién hizo qué)", ("auditoria.ver", "auditoria.operaciones"), ("¿Quién anuló ventas esta semana?", "Actividad reciente de los usuarios"), [
        (r"\bauditoria\b|\bbitacora\b", 9),
        (r"\bquien (cambio|modifico|elimino|borro|anulo|creo|registro|aprobo|toco|hizo|edito|ajusto|cancelo|actualizo|agrego)\b", 8),
        (r"\bque (hizo|hicieron|cambio|cambiaron|modifico|paso con)\b", 4.5),
        (r"\bactividad (reciente|de (los )?usuarios?|del sistema)\b|\bhistorial de (acciones|actividad|cambios|accesos)\b", 8),
        (r"\bintentos (de )?(acceso|ingreso|login)\b|\baccesos? fallidos?\b|\binicios? de sesion\b", 8),
        (r"\blogs?\b", 4),
        (r"\b(acciones|cambios|eventos|operaciones) (de hoy|del dia|recientes|de la semana)\b|\bregistro de (actividad|acciones|cambios|eventos)\b|\bultimos cambios\b|\bcambios recientes\b", 8),
    ], ruta="/auditoria"),
    _i("empresa_info", "Administración", "Datos y parámetros de la empresa", ("empresa.ver",), ("¿Cuál es el plazo de entrega configurado?", "Datos de la empresa"), [
        (r"\b(datos|informacion|info|perfil) de (la |mi |nuestra )?empresa\b|\b(nit|razon social|nombre de la empresa)\b|\bcomo se llama (la |mi |nuestra )?empresa\b", 8),
        (r"\bparametros? (de |del )?(la )?(empresa|reposicion|reabastecimiento|recomendacion\w*)\b", 8),
        (r"\b(plazo de entrega|lead ?time|dias de seguridad|cobertura objetivo|dias de cobertura objetivo)\b", 8),
        (r"\bzona horaria\b|\bmoneda\b", 6),
        (r"\bempresa\b", 2.5),
    ], ruta="/empresa"),
    _i("agentes_ia", "Administración", "Agentes de IA y llaves de acceso", ("agentes.gestionar",), ("¿Cómo conecto un agente de IA?",), [
        (r"\bagentes? (de )?(ia|inteligencia)\b", 8),
        (r"\b(api ?key|llave\w*|token de acceso)\b", 6.5),
        (r"\bintegraci\w+\b", 5.5),
        (r"\b(claude|mcp|chatgpt|gpt|openai)\b", 5),
        (r"\bconectar\w*\b|\bapi\b", 4),
    ], ruta="/integraciones"),
)

INTENCIONES: tuple[Intencion, ...] = _BASE + INTENCIONES_EXT + INTENCIONES_CONOCIMIENTO

INTENCION_POR_CLAVE: dict[str, Intencion] = {i.clave: i for i in INTENCIONES}

# Intenciones que no consultan datos de negocio (se pueden responder sin permisos específicos).
SOCIALES = frozenset({"saludo", "despedida", "gracias", "quien_eres", "ayuda", "fecha_hoy", "charla", "fuera_de_alcance"})

UMBRAL = 2.5  # por debajo de este puntaje la pregunta no se considera entendida


def alcanza_umbral(puntos: float) -> bool:
    """El desempate de `puntuar` resta una millonésima por posición: no debe dejar a una intención justo en el umbral por debajo de él."""
    return puntos >= UMBRAL - 0.001


def puntuar(texto: str, entidades: SenalesEntidades) -> list[tuple[Intencion, float]]:
    """Puntaje de cada intención para la frase (texto normalizado), de mayor a menor; solo las que suman."""
    resultado: list[tuple[Intencion, float]] = []
    for orden, intencion in enumerate(INTENCIONES):
        puntos = sum(peso for patron, peso in intencion.senales if patron.search(texto))
        if puntos <= 0:
            continue
        puntos += sum(peso for patron, peso in intencion.contras if patron.search(texto))
        if intencion.requiere:
            puntos += 2.5 if getattr(entidades, intencion.requiere) else -3.0
        if intencion.prefiere and getattr(entidades, intencion.prefiere):
            puntos += 2.0
        if puntos > 0:
            resultado.append((intencion, puntos - orden * 1e-6))
    resultado.sort(key=lambda par: par[1], reverse=True)
    return resultado


# --------------------------------------------------------------------------------------------- pantallas


@dataclass(frozen=True)
class Tema:
    patron: re.Pattern
    nombre: str
    ruta: str
    permisos: tuple[str, ...]
    ruta_crear: str | None = None
    permisos_crear: tuple[str, ...] = ()


def _t(patron: str, nombre: str, ruta: str, permisos: tuple[str, ...], ruta_crear: str | None = None, permisos_crear: tuple[str, ...] = ()) -> Tema:
    return Tema(re.compile(patron), nombre, ruta, permisos, ruta_crear, permisos_crear)


# El orden importa: el primer tema que coincide gana.
TEMAS: tuple[Tema, ...] = (
    _t(r"\bventas?\b|\bfactura\w*", "Ventas", "/ventas", ("ventas.ver", "ventas.registrar"), "/ventas/nueva", ("ventas.registrar",)),
    _t(r"\btraslad\w+|\btransferencia\w*", "Traslados", "/traslados", ("traslados.ver", "traslados.solicitar"), "/traslados/nuevo", ("traslados.solicitar",)),
    _t(r"\brecomend\w+|\bsugerenc\w+", "Recomendaciones", "/recomendaciones", ("recomendaciones.ver",)),
    _t(r"\bpredic\w+|\bpronostic\w+|\bdemanda\b", "Predicción de demanda", "/predicciones", ("prediccion.ver",)),
    _t(r"\balert\w+", "Alertas", "/alertas", ("alertas.ver",)),
    _t(r"\bconsolidad\w+", "Inventario consolidado", "/inventario/consolidado", ("inventario.consolidado",)),
    _t(r"\bmovimient\w+|\bkardex\b", "Movimientos", "/movimientos", ("movimientos.ver",)),
    _t(r"\bcategori\w+", "Categorías", "/categorias", ("categorias.ver",)),
    _t(r"\bproducto\w*|\bcatalogo\b|\breferencia\w*|\barticulo\w*", "Productos", "/productos", ("productos.ver",)),
    _t(r"\binventario\b|\bexistencias?\b|\bstock\b|\bentradas?\b|\bsalidas?\b|\bajustes?\b|\bmercancia\b", "Existencias", "/inventario", _INV),
    _t(r"\breport\w+|\bexportar\b|\bdescargar\b|\bexcel\b|\bpdf\b|\bcsv\b", "Reportes", "/reportes", (
        "reportes.inventario", "reportes.ventas", "reportes.movimientos", "reportes.traslados", "reportes.alertas", "reportes.predicciones",
        "reportes.recomendaciones")),
    _t(r"\bpqrs\b|\bqueja\w*|\breclamo\w*|\bpeticion\w*", "PQRS", "/sig/pqrs", ("pqrs.crear", "pqrs.gestionar")),
    _t(r"\bpausas?\b|\bsst\b", "Seguridad y Salud en el Trabajo", "/sig/sst", ("sst.ver", "sst.gestionar")),
    _t(r"\bno ?conformidad\w*|\bgarantia\w*|\bcalidad\b", "Calidad", "/sig/calidad", ("calidad.ver", "calidad.reportar", "calidad.gestionar")),
    _t(r"\bambiental\w*|\bco2\b", "Gestión ambiental", "/sig/ambiental", ("ambiental.ver", "ambiental.configurar")),
    _t(r"\bsedes?\b|\bsucursal\w*|\bbodega\w*", "Sedes", "/sedes", ("sedes.ver",)),
    _t(r"\busuario\w*|\bempleado\w*|\bcontrasena\b", "Usuarios", "/usuarios", ("usuarios.ver",)),
    _t(r"\brol(?:es)?\b|\bpermiso\w*", "Roles y permisos", "/roles", ("roles.ver", "usuarios.ver")),
    _t(r"\bauditoria\b|\bbitacora\b", "Auditoría", "/auditoria", ("auditoria.ver", "auditoria.operaciones")),
    _t(r"\bagente\w*|\bllave\w*|\bintegraci\w+|\bapi\b", "Agentes de IA", "/integraciones", ("agentes.gestionar",)),
    _t(r"\bempresa\b|\bparametros?\b", "Empresa", "/empresa", ("empresa.ver",)),
    _t(r"\bperfil\b|\bmi cuenta\b", "Mi perfil", "/perfil", ()),
    _t(r"\bpanel\b|\binicio\b|\bdashboard\b", "Panel de control", "/", ()),
)

# Rutas de las pantallas y el permiso que exigen (para no ofrecer enlaces a pantallas vedadas).
PERMISOS_DE_RUTA: dict[str, tuple[str, ...]] = {t.ruta: t.permisos for t in TEMAS}
NOMBRE_DE_RUTA: dict[str, str] = {t.ruta: t.nombre for t in TEMAS}


def tema_de(texto: str) -> Tema | None:
    for tema in TEMAS:
        if tema.patron.search(texto):
            return tema
    return None


# Palabras del dominio que se usan para corregir errores de digitación (se suman a las de los ejemplos).
VOCABULARIO_BASE = frozenset(
    """inventario existencias existencia stock agotado agotados agotada agotadas productos producto categoria categorias sede sedes
    ventas venta vendimos vendido vendidos vendio facturacion factura traslado traslados alerta alertas prediccion predicciones
    pronostico demanda recomendacion recomendaciones reponer comprar pedir trasladar movimientos movimiento kardex entradas
    entrada salidas salida ajustes ajuste mermas perdidas margen ganancia utilidad cobertura desabastecimiento excesivo exceso
    sobrestock minimo maximo usuarios usuario empleados administrador gerente encargado analista permisos rol roles empresa
    auditoria garantia garantias calidad conformidad conformidades pausas activas ambiental carbono reporte reportes
    resumen cuantos cuantas cuanto cuanta cuales ultimos ultimas semana mes ayer manana trimestre quincena rotacion
    bateria baterias cargador cargadores bicicleta bicicletas patineta patinetas motocicleta motocicletas casco cascos
    precio costo valor total promedio semanal mensual diario tendencia comparar vendedor vendedores pendientes pendiente
    aprobado aprobados confirmado confirmados rechazado rechazados cancelado cancelados critica criticas critico criticos
    prioridad alta media baja bajo bajos normal queja quejas reclamo reclamos peticion peticiones sugerencia sugerencias clave contrasena password
    sesion llave llaves pausa pausas evidencia evidencias glosario modulos modulo""".split()
)
