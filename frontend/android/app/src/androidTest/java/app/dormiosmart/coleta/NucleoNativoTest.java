package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import androidx.test.ext.junit.runners.AndroidJUnit4;

import java.util.ArrayList;
import java.util.List;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * O Java chama o nucleo C++ de verdade, no aparelho ou no emulador (APP-02).
 *
 * <p>A paridade das contas com o {@code ml/} e provada no host ({@code make
 * celular}). Aqui o que se prova e a PONTE: os tipos atravessam o JNI, a
 * biblioteca carrega na arquitetura do aparelho, e o payload que sai e o do
 * contrato.
 */
@RunWith(AndroidJUnit4.class)
public class NucleoNativoTest {

    private static final double G = 9.80665;
    private static final long PAREDE_MS = 1_794_096_000_000L; // 2026-11-08T00:00:00Z
    private static final long T0_US = 1_000_000_000L;

    /** Um sinal quase parado, com um balanco lento, a {@code fs} Hz por {@code segundos}. */
    private static List<String> alimentar(NucleoNativo n, double fs, double segundos) {
        n.iniciar(T0_US, T0_US / 1000L, PAREDE_MS);
        n.definirTemperatura(31.5f);
        final List<String> saida = new ArrayList<>();
        final int total = (int) (segundos * fs);
        final long[] t = new long[50];
        final float[] xyz = new float[150];
        int k = 0;
        for (int i = 0; i < total; i++) {
            final double s = i / fs;
            final double ang = 0.05 * Math.sin(2 * Math.PI * 0.3 * s);
            t[k] = T0_US + Math.round(s * 1e6);
            xyz[3 * k] = (float) (G * Math.sin(ang));
            xyz[3 * k + 1] = 0f;
            xyz[3 * k + 2] = (float) (G * Math.cos(ang));
            k++;
            if (k == 50) {
                n.amostrar(t, xyz, k);
                k = 0;
                String p;
                while ((p = n.proximoPayload()) != null) saida.add(p);
            }
        }
        return saida;
    }

    @Test
    public void cinquentaHertzProduzemOPayloadDaPlaca() throws Exception {
        try (NucleoNativo n = new NucleoNativo()) {
            final List<String> payloads = alimentar(n, 50.0, 100.0);
            assertTrue("esperava ao menos 2 epocas, saiu " + payloads.size(), payloads.size() >= 2);

            long anteriorMs = -1;
            for (int i = 0; i < payloads.size(); i++) {
                final JSONObject j = new JSONObject(payloads.get(i));
                assertEquals(30, j.getInt("epoca_s"));
                assertEquals("pico-da-magnitude", j.getString("metodo"));
                assertEquals(960, j.getInt("amostras"));
                assertEquals(31.5, j.getDouble("t"), 1e-9);
                assertEquals(32.0, j.getDouble("fs"), 1e-9);
                final JSONArray f = j.getJSONArray("f");
                assertEquals(6, f.length());
                final JSONArray g = j.getJSONArray("g");
                assertEquals(3, g.length());
                // A gravidade do sinal e quase toda no eixo z.
                assertTrue("g = " + g, g.getDouble(2) > 0.99);
                final double norma = Math.sqrt(g.getDouble(0) * g.getDouble(0)
                        + g.getDouble(1) * g.getDouble(1) + g.getDouble(2) * g.getDouble(2));
                assertEquals(1.0, norma, 1e-3);

                // ts no inicio de cada epoca: a primeira 3 s depois da primeira amostra,
                // e as seguintes de 30 em 30 s.
                final long ms = java.time.Instant.parse(j.getString("ts")).toEpochMilli();
                if (i == 0) assertEquals(PAREDE_MS + 3000, ms);
                else assertEquals(30_000, ms - anteriorMs);
                anteriorMs = ms;
            }
            final long[] c = n.contadores();
            assertEquals(payloads.size(), c[NucleoNativo.COM_PAYLOAD]);
            assertEquals(0, c[NucleoNativo.RECUSADAS]);
            assertEquals(50_000, c[NucleoNativo.TAXA_MILI_HZ], 50);
        }
    }

    @Test
    public void cemHertzSaoRecusadosPorTaxaEContados() {
        try (NucleoNativo n = new NucleoNativo()) {
            final List<String> payloads = alimentar(n, 100.0, 100.0);
            assertEquals(0, payloads.size());
            final long[] c = n.contadores();
            assertTrue(c[NucleoNativo.RECUSADAS_POR_TAXA] >= 2);
            assertEquals(c[NucleoNativo.RECUSADAS], c[NucleoNativo.RECUSADAS_POR_TAXA]);
        }
    }

    @Test
    public void aAntecedenciaDaOrigemEADoNucleo() {
        assertEquals(3_000_000L, NucleoNativo.antecedenciaDaOrigemUs());
    }
}
