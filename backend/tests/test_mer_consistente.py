"""El MER publicado (docs/modelo/mer_spec.py) describe la misma base de datos que los modelos del código.

Compara la especificación del MER (21 entidades, 50 relaciones, 25 reglas de negocio) con las llaves foráneas,
las restricciones únicas y la obligatoriedad de las columnas que declaran los modelos de SQLAlchemy. Si el código
cambia una llave sin actualizar el MER, o al revés, estas pruebas fallan (Tabla K3 del Anexo K, filas 1 a 4).
No necesitan base de datos: leen los metadatos de los modelos."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import Index, PrimaryKeyConstraint, UniqueConstraint

from app.model import Base

RUTA_SPEC = Path(__file__).resolve().parents[2] / "docs" / "modelo" / "mer_spec.py"
TABLAS = Base.metadata.tables


@pytest.fixture(scope="module")
def spec():
    definicion = importlib.util.spec_from_file_location("mer_spec", RUTA_SPEC)
    modulo = importlib.util.module_from_spec(definicion)
    definicion.loader.exec_module(modulo)
    return modulo


def _llaves_reales() -> dict[tuple[str, tuple[str, ...]], object]:
    return {
        (tabla.name, tuple(c.name for c in fk.columns)): fk for tabla in TABLAS.values() for fk in tabla.foreign_key_constraints
    }


def _es_unica(tabla, columnas: tuple[str, ...]) -> bool:
    """¿Esas columnas, juntas, identifican a lo sumo una fila (PK, UNIQUE o índice único no parcial)?"""
    conjunto = set(columnas)
    for restriccion in tabla.constraints:
        if isinstance(restriccion, UniqueConstraint | PrimaryKeyConstraint) and {c.name for c in restriccion.columns} == conjunto:
            return True
    for indice in tabla.indexes:
        parcial = indice.dialect_options["postgresql"]["where"] is not None
        if isinstance(indice, Index) and indice.unique and not parcial and {c.name for c in indice.columns} == conjunto:
            return True
    return False


def test_las_entidades_del_mer_se_corresponden_con_las_tablas_del_modelo(spec):
    tablas_del_mer = [t for _n, tablas, *_resto in spec.ENTIDADES for t in tablas]
    assert len(spec.ENTIDADES) == 21
    assert sorted(tablas_del_mer) == sorted(TABLAS), "cada tabla del modelo pertenece a una sola entidad del MER"
    assert len(TABLAS) == 22  # las 21 entidades más rol_permisos, que resuelve la relación N a M entre rol y permiso
    por_clase = {m.class_.__name__: m.class_.__tablename__ for m in Base.registry.mappers}
    for nombre, tablas, _atributos, _rf, _reglas, clase, _pantalla in spec.ENTIDADES:
        assert por_clase.get(clase) in tablas, f"{nombre}: la clase {clase} no está mapeada a {tablas}"


def test_cada_relacion_del_mer_tiene_su_llave_foranea_en_el_modelo(spec):
    reales = _llaves_reales()
    faltan = [(rid, tabla, cols) for rid, _n, _c, _r, llaves in spec.RELACIONES for tabla, cols in llaves if (tabla, cols) not in reales]
    assert len(spec.RELACIONES) == 50
    assert not faltan, f"relaciones del MER sin llave foránea en el modelo: {faltan}"


def test_toda_llave_foranea_del_modelo_es_una_relacion_del_mer_o_la_empresa_repetida(spec):
    """51 llaves de las 50 relaciones (R05 genera dos) + 8 llaves a empresas en tablas de negocio = 59."""
    reales = _llaves_reales()
    del_mer = {(tabla, cols) for *_resto, llaves in spec.RELACIONES for tabla, cols in llaves}
    sobran = sorted(set(reales) - del_mer)
    assert all(cols == ("empresa_id",) and reales[(tabla, cols)].referred_table.name == "empresas" for tabla, cols in sobran), sobran
    assert len(del_mer) == 51 and len(sobran) == 8 and len(reales) == 59


def test_la_cardinalidad_de_cada_relacion_la_impone_la_base_de_datos(spec):
    errores = []
    for rid, _nombre, cardinalidad, _regla, llaves in spec.RELACIONES:
        madre, hija = (x.strip() for x in cardinalidad.split("—"))
        if rid == "R05":  # N a M: sus dos llaves son parte de la PK compuesta de rol_permisos
            tabla = TABLAS["rol_permisos"]
            if not all(c in {x.name for x in tabla.primary_key.columns} for _t, cols in llaves for c in cols):
                errores.append((rid, "las llaves de R05 deben formar la PK de rol_permisos"))
            continue
        assert len(llaves) == 1, rid
        nombre_tabla, columnas = llaves[0]
        tabla = TABLAS[nombre_tabla]
        obligatoria = all(not tabla.c[c].nullable for c in columnas)
        if (madre == "1") != obligatoria:
            errores.append((rid, f"lado madre «{madre}» pero la llave {'es' if obligatoria else 'no es'} obligatoria"))
        unica = _es_unica(tabla, columnas)
        if (hija == "0..1") != unica:
            errores.append((rid, f"lado hija «{hija}» pero la llave {'es' if unica else 'no es'} única"))
    assert not errores, errores


def test_toda_relacion_cita_una_regla_de_negocio_que_existe(spec):
    reglas = {r[0] for r in spec.REGLAS}
    assert len(reglas) == 25
    assert [rid for rid, _n, _c, regla, _l in spec.RELACIONES if regla not in reglas] == []


def test_toda_regla_de_negocio_se_usa_en_alguna_relacion(spec):
    usadas = {regla for _rid, _n, _c, regla, _l in spec.RELACIONES}
    assert sorted(r[0] for r in spec.REGLAS if r[0] not in usadas) == []
