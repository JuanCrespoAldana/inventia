export interface SegmentoDona {
  clave: string;
  etiqueta: string;
  valor: number;
  color: string;
}

export function Dona({ segmentos, centro, descripcion, tamano = 148 }: { segmentos: SegmentoDona[]; centro?: { valor: string; etiqueta: string }; descripcion: string; tamano?: number }) {
  const total = segmentos.reduce((s, x) => s + x.valor, 0);
  const radio = tamano / 2 - 10;
  const circunferencia = 2 * Math.PI * radio;
  let acumulado = 0;
  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg width={tamano} height={tamano} viewBox={`0 0 ${tamano} ${tamano}`} role="img" aria-label={descripcion} className="shrink-0">
        <circle cx={tamano / 2} cy={tamano / 2} r={radio} fill="none" stroke="rgb(255 255 255 / 0.06)" strokeWidth="14" />
        {total > 0 &&
          segmentos
            .filter((s) => s.valor > 0)
            .map((s) => {
              const largo = (s.valor / total) * circunferencia;
              const desplazamiento = -acumulado;
              acumulado += largo;
              return (
                <circle
                  key={s.clave}
                  cx={tamano / 2}
                  cy={tamano / 2}
                  r={radio}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="14"
                  strokeDasharray={`${Math.max(largo - 2, 0)} ${circunferencia - Math.max(largo - 2, 0)}`}
                  strokeDashoffset={desplazamiento}
                  transform={`rotate(-90 ${tamano / 2} ${tamano / 2})`}
                />
              );
            })}
        {centro && (
          <g>
            <text x="50%" y="48%" textAnchor="middle" className="fill-ink font-display text-2xl font-semibold">
              {centro.valor}
            </text>
            <text x="50%" y="62%" textAnchor="middle" className="fill-ink-faint text-[11px]">
              {centro.etiqueta}
            </text>
          </g>
        )}
      </svg>
      <ul className="flex min-w-36 flex-1 flex-col gap-2 text-[13px]">
        {segmentos.map((s) => (
          <li key={s.clave} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-ink-dim">
              <span className="inline-block size-2.5 rounded-full" style={{ background: s.color }} aria-hidden />
              {s.etiqueta}
            </span>
            <span className="tabular font-semibold text-ink">{s.valor}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
