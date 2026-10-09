export function Sparkline({ valores, color = "#8AA3FF", ancho = 96, alto = 28 }: { valores: number[]; color?: string; ancho?: number; alto?: number }) {
  if (valores.length < 2) return null;
  const max = Math.max(...valores);
  const min = Math.min(...valores);
  const rango = max - min || 1;
  const puntos = valores.map((v, i) => `${((i / (valores.length - 1)) * ancho).toFixed(1)},${(alto - 3 - ((v - min) / rango) * (alto - 6)).toFixed(1)}`);
  return (
    <svg width={ancho} height={alto} viewBox={`0 0 ${ancho} ${alto}`} aria-hidden>
      <polyline points={puntos.join(" ")} fill="none" stroke={color} strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
