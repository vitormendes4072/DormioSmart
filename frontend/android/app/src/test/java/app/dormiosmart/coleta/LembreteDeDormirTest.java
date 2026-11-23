package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Calendar;
import java.util.TimeZone;

import org.junit.Test;

/** As contas do lembrete de dormir (APP-20). Roda na JVM. */
public class LembreteDeDormirTest {

    private static final TimeZone SAO_PAULO = TimeZone.getTimeZone("America/Sao_Paulo");
    private static final TimeZone NOVA_YORK = TimeZone.getTimeZone("America/New_York");

    private static long em(TimeZone fuso, int ano, int mes, int dia, int hora, int minuto) {
        final Calendar c = Calendar.getInstance(fuso);
        c.clear();
        c.set(ano, mes - 1, dia, hora, minuto, 0);
        return c.getTimeInMillis();
    }

    @Test
    public void antesDoHorarioLembraHoje() {
        final long agora = em(SAO_PAULO, 2026, 11, 23, 20, 0);
        assertEquals(em(SAO_PAULO, 2026, 11, 23, 22, 30),
                LembreteDeDormir.proximoDisparo(agora, 22, 30, SAO_PAULO));
    }

    @Test
    public void depoisDoHorarioLembraAmanha() {
        final long agora = em(SAO_PAULO, 2026, 11, 23, 23, 0);
        assertEquals(em(SAO_PAULO, 2026, 11, 24, 22, 30),
                LembreteDeDormir.proximoDisparo(agora, 22, 30, SAO_PAULO));
    }

    @Test
    public void noProprioMinutoLembraAmanhaENaoDuasVezes() {
        // O alarme dispara as 22:30 e agenda o proximo: tem de ser o de amanha.
        final long agora = em(SAO_PAULO, 2026, 11, 23, 22, 30);
        assertEquals(em(SAO_PAULO, 2026, 11, 24, 22, 30),
                LembreteDeDormir.proximoDisparo(agora, 22, 30, SAO_PAULO));
    }

    @Test
    public void lembreteDeMadrugadaDepoisDaMeiaNoite() {
        final long agora = em(SAO_PAULO, 2026, 11, 23, 23, 50);
        assertEquals(em(SAO_PAULO, 2026, 11, 24, 0, 15),
                LembreteDeDormir.proximoDisparo(agora, 0, 15, SAO_PAULO));
    }

    @Test
    public void viradaDeMesEDeAno() {
        final long agora = em(SAO_PAULO, 2026, 12, 31, 23, 0);
        assertEquals(em(SAO_PAULO, 2027, 1, 1, 22, 30),
                LembreteDeDormir.proximoDisparo(agora, 22, 30, SAO_PAULO));
    }

    @Test
    public void naMudancaDeHorarioSegueORelogioDeParede() {
        // Em Nova York o relogio adianta uma hora em 08/03/2026, as 2h. O lembrete
        // das 22:30 continua as 22:30 locais, e o intervalo do dia e de 23 h.
        final long agora = em(NOVA_YORK, 2026, 3, 7, 23, 0);
        final long proximo = LembreteDeDormir.proximoDisparo(agora, 22, 30, NOVA_YORK);
        assertEquals(em(NOVA_YORK, 2026, 3, 8, 22, 30), proximo);
        final long anterior = em(NOVA_YORK, 2026, 3, 7, 22, 30);
        assertEquals(23L * 3600 * 1000, proximo - anterior);
    }

    @Test
    public void naoLembraComANoiteEmAndamentoNemDesligado() {
        assertTrue(LembreteDeDormir.deveLembrar(true, false));
        assertFalse(LembreteDeDormir.deveLembrar(true, true));
        assertFalse(LembreteDeDormir.deveLembrar(false, false));
        assertFalse(LembreteDeDormir.deveLembrar(false, true));
    }

    @Test
    public void horarioValido() {
        assertTrue(LembreteDeDormir.valido(0, 0));
        assertTrue(LembreteDeDormir.valido(23, 59));
        assertFalse(LembreteDeDormir.valido(24, 0));
        assertFalse(LembreteDeDormir.valido(-1, 30));
        assertFalse(LembreteDeDormir.valido(22, 60));
        assertFalse(LembreteDeDormir.valido(22, -1));
    }
}
