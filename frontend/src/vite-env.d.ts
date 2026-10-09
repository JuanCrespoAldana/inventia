/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL base de la API cuando el frontend no está detrás del mismo origen (por defecto, mismo origen). */
  readonly VITE_API_URL?: string;
  readonly VITE_LOCALE?: string;
  readonly VITE_MONEDA?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
