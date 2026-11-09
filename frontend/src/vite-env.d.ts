/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Endereço do backend no build do app Android (APP-02); ausente no site. */
  readonly VITE_API_BASE?: string;
}
