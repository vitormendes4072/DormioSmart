package app.dormiosmart.coleta;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import androidx.test.ext.junit.runners.AndroidJUnit4;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * A autocalibracao pelo JNI de verdade (CAL-03, etapa 2), no aparelho.
 *
 * <p>O ciclo inteiro: um sensor com o erro do eixo z do Moto E7 (escala +1,17 %,
 * desvio -7,6 mg), pontos parados de tela para cima e para baixo, a estimativa
 * pelo nucleo, e uma noite com a calibracao aplicada -- {@code cal: 1}, o ENMO
 * parado perto de zero, e o ponto parado de volta no BRUTO.
 */
@RunWith(AndroidJUnit4.class)
public class CalibracaoNativaTest {

    private static final double G = 9.80665;
    private static final long PAREDE_MS = 1_794_096_000_000L;
    private static final long T0_US = 1_000_000_000L;
    private static final double ESCALA_Z = 1.0117;
    private static final double DESVIO_Z = -0.0076;

    /** O celular parado de tela para baixo, lido pelo sensor com erro, por {@code segundos}. */
    private static List<String> noiteParada(NucleoNativo n, double segundos, List<double[]> pontos) {
        n.iniciar(T0_US, T0_US / 1000L, PAREDE_MS);
        n.definirTemperatura(19.0f);
        final List<String> saida = new ArrayList<>();
        final float z = (float) (G * (-ESCALA_Z + DESVIO_Z));
        final long[] t = new long[50];
        final float[] xyz = new float[150];
        for (int i = 0, k = 0; i < (int) (segundos * 50); i++) {
            t[k] = T0_US + Math.round(i / 50.0 * 1e6);
            xyz[3 * k] = 0f;
            xyz[3 * k + 1] = 0f;
            xyz[3 * k + 2] = z;
            if (++k == 50) {
                n.amostrar(t, xyz, k);
                k = 0;
                String p;
                while ((p = n.proximoPayload()) != null) {
                    saida.add(p);
                    final double[] ponto = n.pontoParado();
                    if (ponto != null && pontos != null) pontos.add(ponto);
                }
            }
        }
        return saida;
    }

    @Test
    public void oCicloInteiroPeloJni() throws Exception {
        // 1. Os pontos de duas posicoes, como o app os guardaria.
        final Random r = new Random(7);
        final List<double[]> pontos = new ArrayList<>();
        for (int i = 0; i < 60; i++) {
            final double s = i < 30 ? 1 : -1;
            pontos.add(new double[] {
                0.01 * r.nextGaussian(), 0.01 * r.nextGaussian(),
                ESCALA_Z * s + DESVIO_Z + 0.0005 * r.nextGaussian(), 19.0,
            });
        }
        final Calibracao c = NucleoNativo.estimar(pontos);
        assertTrue("a estimativa devia aceitar: " + c.resumo(40), c.aceita);
        assertEquals(2, c.modos[2]);
        assertTrue(c.erroDepoisG < 0.002);

        // 2. A noite calibrada: cal 1, e o ENMO parado ~0.
        try (NucleoNativo n = new NucleoNativo()) {
            n.definirCalibracao(c);
            final List<double[]> novos = new ArrayList<>();
            final List<String> payloads = noiteParada(n, 95, novos);
            assertTrue(payloads.size() >= 2);
            final JSONObject ultimo = new JSONObject(payloads.get(payloads.size() - 1));
            assertEquals(1, ultimo.getInt("cal"));
            final JSONArray f = ultimo.getJSONArray("f");
            assertTrue("ENMO parado calibrado: " + f.getDouble(0), f.getDouble(0) < 0.001);
            assertEquals(1.0, ultimo.getDouble("gn"), 0.002);
            // 3. O ponto parado volta no BRUTO, para a proxima estimativa.
            assertFalse(novos.isEmpty());
            final double[] p = novos.get(novos.size() - 1);
            assertEquals(-ESCALA_Z + DESVIO_Z, p[2], 0.002);
            assertEquals(19.0, p[3], 0.01);
        }
    }

    @Test
    public void semCalibracaoSaiCalZeroEOErroAparece() throws Exception {
        try (NucleoNativo n = new NucleoNativo()) {
            final List<String> payloads = noiteParada(n, 95, null);
            final JSONObject ultimo = new JSONObject(payloads.get(payloads.size() - 1));
            assertEquals(0, ultimo.getInt("cal"));
            assertTrue(ultimo.getJSONArray("f").getDouble(0) > 0.015);
        }
    }

    @Test
    public void poucosPontosSaoRecusados() {
        final List<double[]> pontos = new ArrayList<>();
        for (int i = 0; i < NucleoNativo.pontosMinimos() - 1; i++) pontos.add(new double[] {0, 0, 1.01, 20});
        final Calibracao c = NucleoNativo.estimar(pontos);
        assertFalse(c.aceita);
        assertEquals(NucleoNativo.pontosMinimos() - 1, c.pontos);
        assertArrayEquals(new Calibracao().parametros(), c.parametros(), 0);
        assertNotNull(c.resumo(NucleoNativo.pontosMinimos()));
    }
}
