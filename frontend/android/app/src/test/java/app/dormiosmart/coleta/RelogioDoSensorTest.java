package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

/** O carimbo do sensor na base do elapsedRealtime (APP-02). Roda na JVM. */
public class RelogioDoSensorTest {

    @Test
    public void sensorNaBaseCertaPassaIntactoEmMicrossegundos() {
        final RelogioDoSensor r = new RelogioDoSensor();
        // Entregue 0,8 s depois (lote de 1 s): mesma base, nada a corrigir.
        assertEquals(5_000_000L, r.paraMonotonicoUs(5_000_000_000L, 5_800_000_000L));
        assertEquals(0L, r.deslocamentoNs());
        assertEquals(5_020_000L, r.paraMonotonicoUs(5_020_000_000L, 5_820_000_000L));
    }

    @Test
    public void sensorEmOutraBaseGanhaDeslocamentoFixo() {
        final RelogioDoSensor r = new RelogioDoSensor();
        // Aparelho que carimba pelo uptime: 1 h atras do elapsedRealtime.
        final long hora = 3_600_000_000_000L;
        assertEquals((7_200_000_000_000L) / 1000L, r.paraMonotonicoUs(3_600_000_000_000L, 3_600_000_000_000L + hora));
        assertEquals(hora, r.deslocamentoNs());
        // Os intervalos ficam exatos: 20 ms depois sao 20 ms depois.
        assertEquals(7_200_020_000L, r.paraMonotonicoUs(3_600_020_000_000L, 0L));
    }

    @Test
    public void aCalibracaoEUmaSoVez() {
        final RelogioDoSensor r = new RelogioDoSensor();
        r.paraMonotonicoUs(1_000_000_000L, 1_000_000_000L);
        // Um lote atrasado 30 s depois nao muda a base escolhida na primeira amostra.
        assertEquals(2_000_000L, r.paraMonotonicoUs(2_000_000_000L, 32_000_000_000L));
        assertEquals(0L, r.deslocamentoNs());
    }
}
