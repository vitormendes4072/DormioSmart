/**
 * UI-54: o dia e o aparelho do Início no endereço, ida e volta.
 */
import { describe, expect, it } from "vitest";

import { destinoDoDia, lerDiaDoEndereco, semDiaNoEndereco } from "./diaNoEndereco";

describe("diaNoEndereco", () => {
  it("o dia é o do começo da sessão, mesmo que ela termine no dia seguinte", () => {
    const inicio = new Date(2026, 10, 25, 23, 10).getTime();
    expect(destinoDoDia(inicio, "p", "")).toBe("/dashboard?dia=2026-11-25&aparelho=p");
  });

  it("ida e volta: o Início lê o mesmo dia, ao meio-dia como o calendário, e o aparelho", () => {
    const { dia, aparelho } = lerDiaDoEndereco("?dia=2026-11-25&aparelho=p");
    expect(dia?.getTime()).toBe(new Date(2026, 10, 25, 12).getTime());
    expect(aparelho).toBe("p");
  });

  it("guarda o modo demonstração e não leva aparelho sem id", () => {
    const inicio = new Date(2026, 0, 5, 22).getTime();
    expect(destinoDoDia(inicio, null, "?demo=1")).toBe("/dashboard?dia=2026-01-05&demo=1");
  });

  it("ignora dia malformado ou inexistente, e o aparelho sem dia", () => {
    for (const busca of ["?dia=2026-02-31", "?dia=26/11/2026", "?dia=", "", "?aparelho=p"]) {
      expect(lerDiaDoEndereco(busca)).toEqual({ dia: null, aparelho: null });
    }
    expect(lerDiaDoEndereco("?dia=2026-11-25&aparelho=../x").aparelho).toBeNull();
  });

  it("tira só o dia e o aparelho do endereço", () => {
    expect(semDiaNoEndereco("?dia=2026-11-25&aparelho=p&demo=1")).toBe("?demo=1");
    expect(semDiaNoEndereco("?dia=2026-11-25")).toBe("");
    expect(semDiaNoEndereco("?demo=1")).toBeNull();
  });
});
