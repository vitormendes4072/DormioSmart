package app.dormiosmart.coleta;

import android.app.AlarmManager;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

import java.io.File;
import java.util.Calendar;
import java.util.TimeZone;

/**
 * O lembrete de dormir (APP-20): todo dia, no horario que a pessoa escolheu,
 * uma notificacao lembra de comecar a registrar a noite.
 *
 * <p>Tudo fica no aparelho: o horario em {@link SharedPreferences}, o agendamento
 * no {@link AlarmManager}. Nada vai ao servidor. O alarme nao e exato
 * ({@code setAndAllowWhileIdle}): o exato pede outra permissao, e alguns minutos
 * de atraso nao importam num lembrete de dormir. Cada disparo agenda o do dia
 * seguinte; reiniciar o celular, atualizar o app ou mudar o fuso reagenda
 * ({@link ReceptorDeInicializacao}).
 *
 * <p>As contas ({@link #proximoDisparo}, {@link #deveLembrar}, {@link #valido})
 * sao funcoes puras, testadas na JVM.
 */
public final class LembreteDeDormir {

    static final String CANAL = "lembretes";
    static final int ID_NOTIFICACAO = 2;
    static final String ACAO_LEMBRAR = "app.dormiosmart.coleta.LEMBRAR";
    private static final String PREFERENCIAS = "lembrete-de-dormir";
    private static final String ATIVO = "ativo";
    private static final String HORA = "hora";
    private static final String MINUTO = "minuto";
    static final int HORA_PADRAO = 22;
    static final int MINUTO_PADRAO = 30;

    private LembreteDeDormir() {}

    /** O horario escolhido. */
    public static final class Config {
        public final boolean ativo;
        public final int hora;
        public final int minuto;

        public Config(boolean ativo, int hora, int minuto) {
            this.ativo = ativo;
            this.hora = hora;
            this.minuto = minuto;
        }
    }

    /** Hora de 0 a 23 e minuto de 0 a 59. */
    static boolean valido(int hora, int minuto) {
        return hora >= 0 && hora <= 23 && minuto >= 0 && minuto <= 59;
    }

    /**
     * O proximo instante, estritamente depois de {@code agoraMs}, em que o
     * relogio de parede do fuso marca {@code hora:minuto}. Se hoje ja passou (ou
     * e agora), e amanha. Num dia de mudanca de horario, segue o relogio de
     * parede, como um despertador.
     */
    static long proximoDisparo(long agoraMs, int hora, int minuto, TimeZone fuso) {
        final Calendar c = Calendar.getInstance(fuso);
        c.setTimeInMillis(agoraMs);
        c.set(Calendar.HOUR_OF_DAY, hora);
        c.set(Calendar.MINUTE, minuto);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        if (c.getTimeInMillis() <= agoraMs) c.add(Calendar.DAY_OF_MONTH, 1);
        return c.getTimeInMillis();
    }

    /** Lembra so com o lembrete ligado e sem noite em andamento. */
    static boolean deveLembrar(boolean ativo, boolean noiteEmAndamento) {
        return ativo && !noiteEmAndamento;
    }

    // ── O lado Android ─────────────────────────────────────────────────────

    private static SharedPreferences preferencias(Context c) {
        return c.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE);
    }

    public static Config ler(Context c) {
        final SharedPreferences p = preferencias(c);
        return new Config(p.getBoolean(ATIVO, false), p.getInt(HORA, HORA_PADRAO), p.getInt(MINUTO, MINUTO_PADRAO));
    }

    public static void gravar(Context c, Config cfg) {
        preferencias(c).edit()
                .putBoolean(ATIVO, cfg.ativo)
                .putInt(HORA, cfg.hora)
                .putInt(MINUTO, cfg.minuto)
                .apply();
        agendar(c);
    }

    private static Intent intencao(Context c) {
        return new Intent(c, ReceptorDoLembrete.class).setAction(ACAO_LEMBRAR);
    }

    private static PendingIntent disparo(Context c) {
        return PendingIntent.getBroadcast(c, 0, intencao(c), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    /** Ha um disparo agendado (a intencao pendente existe). Para os testes no aparelho. */
    static boolean agendado(Context c) {
        return PendingIntent.getBroadcast(c, 0, intencao(c),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_NO_CREATE) != null;
    }

    /** Agenda o proximo disparo, ou cancela se o lembrete esta desligado. */
    public static void agendar(Context c) {
        final AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return;
        final Config cfg = ler(c);
        final PendingIntent pi = disparo(c);
        if (!cfg.ativo) {
            am.cancel(pi);
            pi.cancel();
            return;
        }
        final long quando = proximoDisparo(System.currentTimeMillis(), cfg.hora, cfg.minuto, TimeZone.getDefault());
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, quando, pi);
    }

    /** A noite esta sendo registrada: o servico roda, ou o estado gravado diz ativa. */
    static boolean noiteEmAndamento(Context c) {
        if (ServicoDaNoite.emExecucao()) return true;
        try {
            return EstadoDaNoite.ler(new File(ServicoDaNoite.pasta(c), ArquivoDaNoite.ESTADO)).ativa;
        } catch (Exception e) {
            return false;
        }
    }

    /** Chamado pelo alarme: mostra o lembrete se for o caso e agenda o de amanha. */
    static void aoDisparar(Context c) {
        if (deveLembrar(ler(c).ativo, noiteEmAndamento(c))) mostrar(c);
        agendar(c);
    }

    private static void mostrar(Context c) {
        final NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        if (Build.VERSION.SDK_INT >= 26) {
            final NotificationChannel canal = new NotificationChannel(
                    CANAL, "Lembretes", NotificationManager.IMPORTANCE_DEFAULT);
            canal.setDescription("O lembrete de dormir, no horário escolhido em Configurações.");
            nm.createNotificationChannel(canal);
        }
        // Sem a permissao (Android 13+), o Android descarta a notificacao.
        if (!NotificationManagerCompat.from(c).areNotificationsEnabled()) return;
        final Intent abrir = new Intent(c, MainActivity.class)
                .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        final PendingIntent aoTocar = PendingIntent.getActivity(
                c, 1, abrir, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        nm.notify(ID_NOTIFICACAO, new NotificationCompat.Builder(c, CANAL)
                .setContentTitle("Hora de se preparar para dormir")
                .setContentText("Toque para começar a registrar a noite.")
                .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentIntent(aoTocar)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .build());
    }
}
