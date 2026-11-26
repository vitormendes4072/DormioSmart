package app.dormiosmart.coleta;

import org.junit.Test;
import static org.junit.Assert.*;

public class NomeDoAparelhoTest {
    @Test public void combina() { assertEquals("Marca Modelo", NomeDoAparelho.formatar("marca", "Modelo")); }
    @Test public void naoRepete() { assertEquals("MARCA Modelo", NomeDoAparelho.formatar("marca", "MARCA Modelo")); }
    @Test public void inicialMaiuscula() { assertEquals("Marca Modelo", NomeDoAparelho.formatar("marca", "marca Modelo")); }
    @Test public void vazio() { assertNull(NomeDoAparelho.formatar("", "Modelo")); assertNull(NomeDoAparelho.formatar("marca", "")); }
    @Test public void desconhecido() { assertNull(NomeDoAparelho.formatar("unknown", "Modelo")); assertNull(NomeDoAparelho.formatar("marca", "UNKNOWN")); }
    @Test public void limitaSemEspacoFinal() { String n = NomeDoAparelho.formatar("marca", "x".repeat(53) + " " + "y".repeat(20)); assertEquals(59, n.length()); assertFalse(n.endsWith(" ")); }
}
