package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.content.Context;
import android.content.Intent;
import android.os.SystemClock;

import androidx.core.content.ContextCompat;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import java.io.File;
import java.util.List;

import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * O servico da noite de ponta a ponta, com o acelerometro do aparelho (APP-02).
 *
 * <p>Sobe o servico, espera duas epocas no arquivo, encerra, e confere o que
 * ficou: o estado inativo, uma linha por epoca gravada, cada linha um payload
 * valido. A noite longa, com tela apagada e Doze, e o roteiro da etapa 2 no
 * diario: este teste prova o caminho, nao a resistencia.
 */
@RunWith(AndroidJUnit4.class)
public class ServicoDaNoiteTest {

    private Context ctx;
    private File pasta;

    @Before
    public void limpar() {
        ctx = InstrumentationRegistry.getInstrumentation().getTargetContext();
        pasta = ServicoDaNoite.pasta(ctx);
        final File[] arquivos = pasta.listFiles();
        if (arquivos != null) for (File f : arquivos) f.delete();
    }

    private EstadoDaNoite estado() throws Exception {
        return EstadoDaNoite.ler(new File(pasta, ArquivoDaNoite.ESTADO));
    }

    @Test
    public void registraEpocasEEncerraLimpo() throws Exception {
        // O app em primeiro plano, como quando o usuario toca "Iniciar a noite".
        try (ActivityScenario<MainActivity> tela = ActivityScenario.launch(MainActivity.class)) {
            ContextCompat.startForegroundService(ctx,
                    new Intent(ctx, ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_INICIAR));

            final long limite = SystemClock.elapsedRealtime() + 180_000;
            EstadoDaNoite e = estado();
            while (e.epocasGravadas < 2 && SystemClock.elapsedRealtime() < limite) {
                SystemClock.sleep(2000);
                e = estado();
            }
            assertTrue("o servico nao gravou 2 epocas em 3 min (gravadas " + e.epocasGravadas
                    + ", recusadas " + e.recusadas + ", por taxa " + e.recusadasPorTaxa
                    + ", amostras " + e.amostras + ")", e.epocasGravadas >= 2);
            assertTrue(e.ativa);
            assertTrue("taxa medida " + e.taxaMiliHz + " mHz", e.taxaMiliHz >= 40_000 && e.taxaMiliHz <= 60_000);

            ctx.startService(new Intent(ctx, ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_ENCERRAR));
            final long limite2 = SystemClock.elapsedRealtime() + 10_000;
            while (estado().ativa && SystemClock.elapsedRealtime() < limite2) SystemClock.sleep(200);
            final EstadoDaNoite fim = estado();
            assertFalse("a noite continuou ativa depois de encerrar", fim.ativa);

            final List<String> linhas = new ArquivoDaNoite(pasta).linhas(fim.arquivo);
            assertEquals(fim.epocasGravadas, linhas.size());
            for (String l : linhas) {
                final JSONObject j = new JSONObject(l);
                assertEquals(30, j.getInt("epoca_s"));
                assertTrue(j.has("ts"));
                // A temperatura e da bateria, em graus, dentro da faixa do contrato.
                final double t = j.getDouble("t");
                assertTrue("t = " + t, t >= -40 && t <= 85);
            }
        }
    }
}
