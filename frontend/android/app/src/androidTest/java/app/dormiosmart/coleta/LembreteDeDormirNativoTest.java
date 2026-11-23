package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assume.assumeTrue;

import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Build;
import android.os.ParcelFileDescriptor;
import android.service.notification.StatusBarNotification;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.util.Calendar;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * O lembrete de dormir no aparelho (APP-20): o alarme agendado no Android, a
 * notificacao no canal proprio, e nada quando a noite esta em andamento ou o
 * lembrete esta desligado. Roda no emulador; as contas estao no teste de JVM.
 */
@RunWith(AndroidJUnit4.class)
public class LembreteDeDormirNativoTest {

    private Context c;
    private NotificationManager nm;
    private File estado;

    private static String shell(String comando) throws Exception {
        final ParcelFileDescriptor pfd = InstrumentationRegistry.getInstrumentation()
                .getUiAutomation().executeShellCommand(comando);
        final StringBuilder s = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(
                new FileInputStream(pfd.getFileDescriptor())))) {
            for (String l; (l = r.readLine()) != null; ) s.append(l).append('\n');
        }
        return s.toString();
    }

    private StatusBarNotification lembrete() {
        for (StatusBarNotification n : nm.getActiveNotifications()) {
            if (n.getId() == LembreteDeDormir.ID_NOTIFICACAO) return n;
        }
        return null;
    }

    @Before
    public void preparar() throws Exception {
        c = InstrumentationRegistry.getInstrumentation().getTargetContext();
        nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 33) {
            shell("pm grant " + c.getPackageName() + " android.permission.POST_NOTIFICATIONS");
        }
        nm.cancel(LembreteDeDormir.ID_NOTIFICACAO);
        estado = new File(ServicoDaNoite.pasta(c), ArquivoDaNoite.ESTADO);
        estado.delete();
    }

    @After
    public void limpar() {
        LembreteDeDormir.gravar(c, new LembreteDeDormir.Config(false, 22, 30));
        nm.cancel(LembreteDeDormir.ID_NOTIFICACAO);
        estado.delete();
    }

    @Test
    public void ligadoAgendaOAlarmeEDesligadoCancela() throws Exception {
        LembreteDeDormir.gravar(c, new LembreteDeDormir.Config(true, 22, 30));
        assertTrue("alarme agendado", shell("dumpsys alarm").contains(LembreteDeDormir.ACAO_LEMBRAR));
        assertTrue(LembreteDeDormir.agendado(c));
        LembreteDeDormir.gravar(c, new LembreteDeDormir.Config(false, 22, 30));
        // O `dumpsys alarm` guarda historico: o que prova o cancelamento e a
        // intencao pendente do alarme deixar de existir.
        assertFalse("alarme cancelado", LembreteDeDormir.agendado(c));
    }

    @Test
    public void aoDispararMostraOLembreteNoCanalProprio() {
        LembreteDeDormir.gravar(c, new LembreteDeDormir.Config(true, 22, 30));
        LembreteDeDormir.aoDisparar(c);
        final StatusBarNotification n = lembrete();
        assertTrue("o lembrete apareceu", n != null);
        assertEquals("Hora de se preparar para dormir",
                n.getNotification().extras.getString(Notification.EXTRA_TITLE));
        if (Build.VERSION.SDK_INT >= 26) assertEquals(LembreteDeDormir.CANAL, n.getNotification().getChannelId());
    }

    @Test
    public void comANoiteEmAndamentoNaoLembra() throws Exception {
        LembreteDeDormir.gravar(c, new LembreteDeDormir.Config(true, 22, 30));
        estado.getParentFile().mkdirs();
        final EstadoDaNoite e = new EstadoDaNoite();
        e.ativa = true;
        e.salvar(estado);
        LembreteDeDormir.aoDisparar(c);
        assertTrue("sem lembrete com a noite gravando", lembrete() == null);
    }

    /**
     * Roteiro, so quando pedido ({@code -e roteiro lembrete}): o alarme de verdade,
     * pelo Android, dispara o receptor do manifesto e a notificacao aparece. Agenda
     * para o proximo minuto e espera ate 3 min (o alarme nao e exato).
     */
    @Test
    public void roteiroOAlarmeDeVerdadeDispara() throws Exception {
        assumeTrue("lembrete".equals(InstrumentationRegistry.getArguments().getString("roteiro", "")));
        final Calendar daqui = Calendar.getInstance();
        daqui.add(Calendar.MINUTE, 1);
        LembreteDeDormir.gravar(c, new LembreteDeDormir.Config(
                true, daqui.get(Calendar.HOUR_OF_DAY), daqui.get(Calendar.MINUTE)));
        final long limite = System.currentTimeMillis() + 3 * 60_000L;
        while (lembrete() == null && System.currentTimeMillis() < limite) Thread.sleep(2_000);
        assertTrue("o alarme disparou e o lembrete apareceu", lembrete() != null);
    }

    @Test
    public void desligadoNaoLembra() {
        LembreteDeDormir.gravar(c, new LembreteDeDormir.Config(false, 22, 30));
        LembreteDeDormir.aoDisparar(c);
        assertTrue(lembrete() == null);
    }
}
