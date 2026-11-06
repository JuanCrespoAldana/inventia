import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiAsistente } from "@/api/asistente";
import { apiAuth } from "@/api/auth";
import { ErrorApi } from "@/lib/errors";
import { crearSesion, renderizar } from "@/test/utilidades";
import type { RespuestaAsistente } from "@/types/api";
import AsistentePage from "./AsistentePage";

vi.mock("@/api/auth", () => ({ apiAuth: { yo: vi.fn(), logout: vi.fn() } }));
vi.mock("@/api/asistente", () => ({ apiAsistente: { preguntar: vi.fn(), ayuda: vi.fn() } }));

const contexto = { intencion: "resumen_inventario", sede_ids: [], categoria_ids: [], producto_ids: [], desde: null, hasta: null };

const respuesta = (cambios: Partial<RespuestaAsistente> = {}): RespuestaAsistente => ({
  intencion: "resumen_inventario",
  entendida: true,
  texto: "En toda la empresa hay **2.559 unidades** valoradas en **$ 1.595.887.000**.",
  bloques: [
    { tipo: "metricas", titulo: null, metricas: [{ etiqueta: "Unidades", valor: "2.559", detalle: null, tono: "neutral" }, { etiqueta: "Agotados", valor: "8", detalle: null, tono: "danger" }] },
    {
      tipo: "tabla",
      titulo: "Por sede",
      columnas: [
        { clave: "sede", etiqueta: "Sede", formato: "texto", alinear: "izq" },
        { clave: "unidades", etiqueta: "Unidades", formato: "entero", alinear: "der" },
        { clave: "estado", etiqueta: "Estado", formato: "texto", alinear: "izq" },
      ],
      filas: [{ celdas: { sede: "Sede Norte", unidades: 755, estado: "Normal" }, tonos: { estado: "success" }, ruta: "/inventario" }],
      total: 1,
      nota: null,
    },
    { tipo: "barras", titulo: "Unidades por sede", barras: [{ etiqueta: "Sede Norte", valor: 755, texto: "755" }, { etiqueta: "Sede Sur", valor: 659, texto: "659" }] },
    { tipo: "lista", titulo: "Pendientes", elementos: ["Revisar **BIC-001**"] },
  ],
  enlaces: [{ etiqueta: "Ver existencias", ruta: "/inventario" }, { etiqueta: "Externo", ruta: "https://ejemplo.com" }],
  sugerencias: ["Valor del inventario"],
  avisos: ["Es una aproximación."],
  alcance: "Toda la empresa",
  periodo: null,
  contexto,
  ...cambios,
});

function abrir() {
  vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ permisos: ["inventario.ver"] }));
  return renderizar(<AsistentePage />, { conSesion: true });
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiAsistente.ayuda).mockResolvedValue({
    saludo: "Buenas tardes, Ana. Soy el asistente de Inventia.",
    iniciales: ["¿Cuánto inventario tenemos?", "¿Qué productos están agotados?"],
    grupos: [{ titulo: "Inventario", ejemplos: ["Valor del inventario"] }],
  });
});

describe("asistente: conversación", () => {
  it("muestra la bienvenida con preguntas para empezar y envía la que se elige", async () => {
    vi.mocked(apiAsistente.preguntar).mockResolvedValue(respuesta());
    const u = userEvent.setup();
    abrir();

    expect(await screen.findByText(/Soy el asistente de Inventia/)).toBeInTheDocument();
    await u.click(await screen.findByRole("button", { name: "¿Cuánto inventario tenemos?" }));

    expect(apiAsistente.preguntar).toHaveBeenCalledWith("¿Cuánto inventario tenemos?", null);
    expect(await screen.findByText(/2\.559 unidades/)).toBeInTheDocument();
  });

  it("dibuja métricas, tabla, barras, lista, avisos y enlaces; el texto nunca se inserta como HTML", async () => {
    vi.mocked(apiAsistente.preguntar).mockResolvedValue(respuesta({ texto: "Hola <img src=x onerror=alert(1)> **negrita**" }));
    const u = userEvent.setup();
    const { container } = abrir();

    await u.type(await screen.findByLabelText("Escribe tu pregunta"), "resumen{Enter}");

    expect(await screen.findByText("negrita")).toHaveProperty("tagName", "STRONG");
    expect(container.querySelector("img")).toBeNull(); // el HTML del texto se muestra como texto, no se interpreta
    expect(screen.getByText("Unidades", { selector: "dt" })).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Por sede" });
    expect(within(tabla).getByRole("link", { name: "Sede Norte" })).toHaveAttribute("href", "/inventario");
    expect(within(tabla).getByText("755")).toBeInTheDocument();
    expect(within(tabla).getByText("Normal")).toBeInTheDocument();
    expect(screen.getByText("659")).toBeInTheDocument();
    expect(screen.getByText("BIC-001")).toBeInTheDocument();
    expect(screen.getByText("Es una aproximación.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Ver existencias/ })).toHaveAttribute("href", "/inventario");
    expect(screen.queryByRole("link", { name: /Externo/ })).not.toBeInTheDocument(); // solo enlaces internos
  });

  it("envía con Enter, deja una línea nueva con Mayús+Enter y manda el contexto de la respuesta anterior", async () => {
    vi.mocked(apiAsistente.preguntar)
      .mockResolvedValueOnce(respuesta({ bloques: [], enlaces: [], avisos: [], sugerencias: [], contexto: { ...contexto, sede_ids: [2] } }))
      .mockResolvedValueOnce(respuesta({ texto: "Segunda respuesta", bloques: [], enlaces: [], avisos: [], sugerencias: [] }));
    const u = userEvent.setup();
    abrir();
    const campo = await screen.findByLabelText("Escribe tu pregunta");

    await u.type(campo, "primera{Shift>}{Enter}{/Shift}línea{Enter}");
    await screen.findByText(/2\.559 unidades/);
    expect(apiAsistente.preguntar).toHaveBeenNthCalledWith(1, "primera\nlínea", null);
    expect(campo).toHaveValue("");

    await u.type(campo, "¿y en la Sede Sur?{Enter}");
    expect(await screen.findByText("Segunda respuesta")).toBeInTheDocument();
    expect(apiAsistente.preguntar).toHaveBeenNthCalledWith(2, "¿y en la Sede Sur?", expect.objectContaining({ sede_ids: [2] }));
  });

  it("no envía mensajes vacíos y el botón Enviar solo se habilita con texto", async () => {
    const u = userEvent.setup();
    abrir();
    const enviar = await screen.findByRole("button", { name: "Enviar" });
    expect(enviar).toBeDisabled();
    await u.type(screen.getByLabelText("Escribe tu pregunta"), "   {Enter}");
    expect(apiAsistente.preguntar).not.toHaveBeenCalled();
  });

  it("muestra un error con opción de reintentar", async () => {
    vi.mocked(apiAsistente.preguntar).mockRejectedValueOnce(new ErrorApi("No se pudo conectar con el servidor.", { codigo: "sin_conexion" })).mockResolvedValueOnce(respuesta({ bloques: [], enlaces: [], avisos: [], sugerencias: [] }));
    const u = userEvent.setup();
    abrir();
    await u.type(await screen.findByLabelText("Escribe tu pregunta"), "inventario{Enter}");

    expect(await screen.findByText("No pude responder")).toBeInTheDocument();
    expect(screen.getByText("No se pudo conectar con el servidor.")).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText(/2\.559 unidades/)).toBeInTheDocument();
    expect(apiAsistente.preguntar).toHaveBeenCalledTimes(2);
  });

  it("«Nueva conversación» limpia los mensajes y olvida el contexto", async () => {
    vi.mocked(apiAsistente.preguntar).mockResolvedValue(respuesta({ bloques: [], enlaces: [], avisos: [], sugerencias: [], contexto: { ...contexto, sede_ids: [3] } }));
    const u = userEvent.setup();
    abrir();
    const campo = await screen.findByLabelText("Escribe tu pregunta");
    await u.type(campo, "inventario{Enter}");
    await screen.findByText(/2\.559 unidades/);

    await u.click(screen.getByRole("button", { name: "Nueva conversación" }));
    await waitFor(() => expect(screen.queryByText(/2\.559 unidades/)).not.toBeInTheDocument());
    expect(screen.getByText(/Soy el asistente de Inventia/)).toBeInTheDocument();

    await u.type(campo, "ventas{Enter}");
    await screen.findByText(/2\.559 unidades/);
    expect(apiAsistente.preguntar).toHaveBeenLastCalledWith("ventas", null);
  });

  it("las sugerencias de la última respuesta se envían como una pregunta nueva", async () => {
    vi.mocked(apiAsistente.preguntar).mockResolvedValue(respuesta({ bloques: [], enlaces: [], avisos: [] }));
    const u = userEvent.setup();
    abrir();
    await u.type(await screen.findByLabelText("Escribe tu pregunta"), "inventario{Enter}");
    await u.click(await screen.findByRole("button", { name: "Valor del inventario" }));
    expect(apiAsistente.preguntar).toHaveBeenLastCalledWith("Valor del inventario", expect.anything());
  });

  it("una respuesta a varias preguntas numera cada parte en el texto y en los títulos de sus bloques", async () => {
    vi.mocked(apiAsistente.preguntar).mockResolvedValue(
      respuesta({
        intencion: "compuesta",
        texto: "**1. Cuántos productos hay**\nEl catálogo tiene **36 productos**.\n\n**2. Cuáles están agotados**\nHay **8 productos agotados**.",
        bloques: [
          { tipo: "metricas", titulo: "1. Cuántos productos hay", metricas: [{ etiqueta: "Productos", valor: "36", detalle: null, tono: "neutral" }] },
          { tipo: "lista", titulo: "2. Cuáles están agotados", elementos: ["Cargador inteligente (**BAT-004**)"] },
        ],
        enlaces: [],
        avisos: ["Respondí las primeras 3 preguntas; envía la otra en un mensaje aparte."],
      }),
    );
    const u = userEvent.setup();
    abrir();
    await u.type(await screen.findByLabelText("Escribe tu pregunta"), "¿cuántos productos hay y cuáles están agotados?{Enter}");

    expect(await screen.findByText("2. Cuáles están agotados", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByText("1. Cuántos productos hay", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByText(/Respondí las primeras 3 preguntas/)).toBeInTheDocument();
  });

  it("la bienvenida muestra los grupos de ayuda que manda el servidor, incluidos los nuevos", async () => {
    vi.mocked(apiAsistente.ayuda).mockResolvedValue({
      saludo: "Hola. Soy el asistente de Inventia.",
      iniciales: ["¿Cuánto inventario tenemos?"],
      grupos: [
        { titulo: "Comparaciones", ejemplos: ["Compara la sede Norte con la sede Sur"] },
        { titulo: "Ayuda del sistema", ejemplos: ["¿Qué es el stock mínimo?", "¿Cómo registro una venta?"] },
      ],
    });
    abrir();
    expect(await screen.findByText("Comparaciones")).toBeInTheDocument();
    expect(screen.getByText("Ayuda del sistema")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "¿Cómo registro una venta?" })).toBeInTheDocument();
  });
});
