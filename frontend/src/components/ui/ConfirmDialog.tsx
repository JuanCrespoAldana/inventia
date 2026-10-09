import { useState } from "react";
import { Button } from "./Button";
import { Modal } from "./Modal";
import { Textarea } from "./Field";

interface ConfirmDialogProps {
  abierto: boolean;
  titulo: string;
  mensaje: string;
  confirmarTexto?: string;
  peligroso?: boolean;
  cargando?: boolean;
  error?: string | null;
  /** Si se define, se pide un motivo obligatorio (mínimo `motivoMinimo` caracteres). */
  motivoEtiqueta?: string;
  motivoMinimo?: number;
  onConfirmar: (motivo: string) => void;
  onCancelar: () => void;
}

export function ConfirmDialog({
  abierto,
  titulo,
  mensaje,
  confirmarTexto = "Confirmar",
  peligroso = false,
  cargando = false,
  error,
  motivoEtiqueta,
  motivoMinimo = 3,
  onConfirmar,
  onCancelar,
}: ConfirmDialogProps) {
  const [motivo, setMotivo] = useState("");
  const requiereMotivo = Boolean(motivoEtiqueta);
  const motivoValido = !requiereMotivo || motivo.trim().length >= motivoMinimo;

  function cerrar() {
    setMotivo("");
    onCancelar();
  }

  return (
    <Modal
      abierto={abierto}
      onCerrar={cerrar}
      titulo={titulo}
      ancho="sm"
      bloqueado={cargando}
      pie={
        <>
          <Button variante="ghost" onClick={cerrar} disabled={cargando}>
            Cancelar
          </Button>
          <Button
            variante={peligroso ? "danger" : "primary"}
            cargando={cargando}
            disabled={!motivoValido}
            onClick={() => onConfirmar(motivo.trim())}
          >
            {confirmarTexto}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ink-dim">{mensaje}</p>
      {requiereMotivo && (
        <Textarea
          className="mt-4"
          etiqueta={motivoEtiqueta!}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          maxLength={500}
          required
          data-autofocus
          ayuda={`Mínimo ${motivoMinimo} caracteres.`}
        />
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      )}
    </Modal>
  );
}
