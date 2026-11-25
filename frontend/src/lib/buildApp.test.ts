import { loadConfigFromFile } from "vite";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const carregarConfig = (mode: string) => loadConfigFromFile({ command: "build", mode });

describe("configuração de login do build Android", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "");
    vi.stubEnv("DORMIO_APP_SEM_SUPABASE", "");
  });

  afterEach(() => vi.unstubAllEnvs());

  it("lista as duas variáveis ausentes e indica o frontend/.env", async () => {
    await expect(carregarConfig("app")).rejects.toThrow(
      /VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY.*frontend\/\.env/,
    );
  });

  it.each([
    ["VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"],
    ["VITE_SUPABASE_ANON_KEY", "VITE_SUPABASE_URL"],
  ])("reprova %s em branco mesmo com %s preenchida", async (ausente, presente) => {
    vi.stubEnv(ausente, "  ");
    vi.stubEnv(presente, "valor de teste");
    await expect(carregarConfig("app")).rejects.toThrow(new RegExp(`em ${ausente}\\.`));
  });

  it("aceita as duas variáveis do ambiente", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "valor de teste");
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "valor de teste");
    await expect(carregarConfig("app")).resolves.not.toBeNull();
  });

  it("aceita a liberação explícita do CI", async () => {
    vi.stubEnv("DORMIO_APP_SEM_SUPABASE", "1");
    await expect(carregarConfig("app")).resolves.not.toBeNull();
  });

  it("deixa o site compilar sem a configuração do app", async () => {
    await expect(carregarConfig("production")).resolves.not.toBeNull();
  });
});
