package app.dormiosmart.coleta;

import static org.junit.Assert.assertTrue;
import static org.junit.Assume.assumeTrue;

import android.app.UiAutomation;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.os.SystemClock;
import android.util.Log;

import androidx.core.content.ContextCompat;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;

import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Roteiros da etapa 2 do APP-02, rodados so quando pedidos (fora da suite normal).
 *
 * <pre>
 *   adb shell am instrument -w -e roteiro longa -e minutos 10 \
 *     -e class app.dormiosmart.coleta.RoteiroDaNoiteTest#noiteLonga \
 *     app.dormiosmart.coleta.test/androidx.test.runner.AndroidJUnitRunner
 * </pre>
 *
 * <p>{@code longa}: inicia a noite, apaga a tela, desliga a bateria simulada e
 * forca o Doze, espera {@code minutos} e exige cobertura de pelo menos 95 %.
 * {@code iniciar} e {@code encerrar}: deixam o servico rodando entre os dois,
 * para a retomada ser provocada de fora (matando o processo pelo adb).
 */
@RunWith(AndroidJUnit4.class)
public class RoteiroDaNoiteTest {

    private static final String TAG = "DormioRoteiro";

    private static String argumento(String nome, String padrao) {
        final Bundle a = InstrumentationRegistry.getArguments();
        final String v = a.getString(nome);
        return v != null ? v : padrao;
    }

    private static String shell(String comando) throws IOException {
        final UiAutomation ui = InstrumentationRegistry.getInstrumentation().getUiAutomation();
        final ParcelFileDescriptor pfd = ui.executeShellCommand(comando);
        final StringBuilder sb = new StringBuilder();
        try (FileInputStream in = new ParcelFileDescriptor.AutoCloseInputStream(pfd)) {
            final byte[] b = new byte[4096];
            int n;
            while ((n = in.read(b)) > 0) sb.append(new String(b, 0, n));
        }
        return sb.toString().trim();
    }

    private static Context ctx() {
        return InstrumentationRegistry.getInstrumentation().getTargetContext();
    }

    private static EstadoDaNoite estado() throws IOException {
        return EstadoDaNoite.ler(new File(ServicoDaNoite.pasta(ctx()), ArquivoDaNoite.ESTADO));
    }

    private static void limparEIniciar() {
        final File[] arquivos = ServicoDaNoite.pasta(ctx()).listFiles();
        if (arquivos != null) for (File f : arquivos) f.delete();
        ContextCompat.startForegroundService(ctx(),
                new Intent(ctx(), ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_INICIAR));
    }

    private static void encerrar() throws IOException {
        ctx().startService(new Intent(ctx(), ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_ENCERRAR));
        final long limite = SystemClock.elapsedRealtime() + 10_000;
        while (estado().ativa && SystemClock.elapsedRealtime() < limite) SystemClock.sleep(200);
    }

    private static String resumo(EstadoDaNoite e, long agoraMs) {
        final long esperadas = Math.max(0, (agoraMs - e.inicioUtcMs - 3000 - 4200) / 30_000);
        return "gravadas=" + e.epocasGravadas + " esperadas=" + esperadas
                + " recusadas=" + e.recusadas + " por_taxa=" + e.recusadasPorTaxa
                + " amostras=" + e.amostras + " taxa_mhz=" + e.taxaMiliHz
                + " retomadas=" + e.retomadas + " temperatura_decimos=" + e.temperaturaDecimos
                + " deslocamento_ns=" + e.deslocamentoDoRelogioNs;
    }

    @Test
    public void noiteLonga() throws Exception {
        assumeTrue("longa".equals(argumento("roteiro", "")));
        final int minutos = Integer.parseInt(argumento("minutos", "10"));
        try (ActivityScenario<MainActivity> tela = ActivityScenario.launch(MainActivity.class)) {
            limparEIniciar();
        }
        SystemClock.sleep(10_000);
        // Como uma noite: fora da tomada, tela apagada, e o Doze sem esperar a hora dele.
        Log.i(TAG, "bateria: " + shell("dumpsys battery unplug"));
        Log.i(TAG, "tela: " + shell("input keyevent KEYCODE_SLEEP"));
        Log.i(TAG, "doze: " + shell("dumpsys deviceidle force-idle"));
        final long fim = SystemClock.elapsedRealtime() + minutos * 60_000L;
        while (SystemClock.elapsedRealtime() < fim) {
            SystemClock.sleep(60_000);
            Log.i(TAG, "estado do doze: " + shell("dumpsys deviceidle get deep")
                    + " | " + resumo(estado(), System.currentTimeMillis()));
        }
        final EstadoDaNoite e = estado();
        final long agora = System.currentTimeMillis();
        shell("dumpsys deviceidle unforce");
        shell("dumpsys battery reset");
        shell("input keyevent KEYCODE_WAKEUP");
        encerrar();
        final long esperadas = (agora - e.inicioUtcMs - 3000 - 4200) / 30_000;
        final String r = resumo(e, agora);
        Log.i(TAG, "FIM " + r);
        assertTrue("cobertura abaixo de 95 %: " + r, esperadas > 0 && e.epocasGravadas >= 0.95 * esperadas);
    }

    @Test
    public void iniciar() throws Exception {
        assumeTrue("iniciar".equals(argumento("roteiro", "")));
        try (ActivityScenario<MainActivity> tela = ActivityScenario.launch(MainActivity.class)) {
            limparEIniciar();
            SystemClock.sleep(5000);
        }
        assertTrue(estado().ativa);
    }

    @Test
    public void encerrarNoite() throws Exception {
        assumeTrue("encerrar".equals(argumento("roteiro", "")));
        final EstadoDaNoite antes = estado();
        Log.i(TAG, "ANTES DE ENCERRAR " + resumo(antes, System.currentTimeMillis()));
        try (ActivityScenario<MainActivity> tela = ActivityScenario.launch(MainActivity.class)) {
            encerrar();
        }
        assertTrue(!estado().ativa);
    }
}
