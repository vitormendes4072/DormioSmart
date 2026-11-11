package app.dormiosmart.coleta;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ServiceInfo;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Log;

import androidx.core.app.NotificationCompat;
import androidx.core.app.ServiceCompat;

import java.io.File;
import java.io.IOException;

/**
 * Registra a noite inteira pelo acelerometro, com a tela apagada (APP-02, etapa 2).
 *
 * <p>Servico em primeiro plano: a notificacao fixa e o que o Android exige para
 * deixar um app trabalhar em segundo plano por horas. No Android 14+ ele
 * declara o tipo {@code health}, que com {@code HIGH_SAMPLING_RATE_SENSORS} no
 * manifesto nao pede permissao em tempo de execucao e nao tem o limite de 6 h
 * do {@code dataSync}.
 *
 * <p>Cada amostra vai para o nucleo do firmware ({@link NucleoNativo}), que
 * devolve o payload de cada epoca de 30 s no formato da placa. O payload e
 * gravado no aparelho ({@link ArquivoDaNoite}); o envio e da etapa 3.
 *
 * <p>Se o sistema matar o servico, {@code START_STICKY} o traz de volta com
 * intent nulo: o estado gravado diz que havia uma noite, e ele continua no
 * mesmo arquivo, com uma cadeia nova. A noite fica com uma lacuna (as epocas
 * do buraco nao existem), e nao com dados inventados.
 */
public class ServicoDaNoite extends Service implements SensorEventListener {

    public static final String ACAO_INICIAR = "app.dormiosmart.coleta.INICIAR";
    public static final String ACAO_ENCERRAR = "app.dormiosmart.coleta.ENCERRAR";
    /** Extra do INICIAR: onde o celular fica (NotasDaNoite.POSICOES). Etapa 4. */
    public static final String EXTRA_POSICAO = "posicao";

    static final String PASTA = "noites";
    static final String CANAL = "noite";
    static final int ID_NOTIFICACAO = 30;
    /** 50 Hz, a taxa nominal da C2. O aparelho entrega o que quer; a cadeia mede. */
    static final int PERIODO_US = 20_000;
    /** O sensor pode juntar ate 1 s de amostras por entrega; o carimbo de cada uma e preservado. */
    static final int LATENCIA_MAXIMA_US = 1_000_000;
    /** Teto da trava de CPU: uma noite que ninguem encerrou nao segura a CPU para sempre. */
    static final long TETO_DA_TRAVA_MS = 12L * 3600L * 1000L;
    static final long INTERVALO_DA_TEMPERATURA_MS = 30_000L;
    /** Amostras por chamada ao nucleo: 1 s a 50 Hz. */
    static final int LOTE = 50;

    private static final String TAG = "DormioNoite";

    /**
     * Se o servico esta registrando neste processo. O estado gravado pode dizer
     * "ativa" com o servico morto (forcado a parar, sem retomada): a tela usa
     * isto para nao mostrar uma noite em andamento que nao existe.
     */
    private static volatile boolean emExecucao;

    public static boolean emExecucao() {
        return emExecucao;
    }

    private HandlerThread linha;
    private PowerManager.WakeLock trava;
    private NucleoNativo nucleo;
    private RelogioDoSensor relogio;
    private ArquivoDaNoite arquivo;
    private EstadoDaNoite estado;
    private boolean registrando;
    private boolean nucleoIniciado;
    private long proximaTemperaturaMs;

    private final long[] tUs = new long[LOTE];
    private final float[] xyz = new float[3 * LOTE];
    private int pendentes;

    public static File pasta(Context c) {
        return new File(c.getFilesDir(), PASTA);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        final String acao = intent != null ? intent.getAction() : null;
        if (ACAO_ENCERRAR.equals(acao)) {
            encerrar("usuario");
            return START_NOT_STICKY;
        }
        // Cinco segundos para chamar startForeground depois de
        // startForegroundService: primeiro a notificacao, depois o resto.
        entrarEmPrimeiroPlano();
        if (registrando) return START_STICKY;

        arquivo = new ArquivoDaNoite(pasta(this));
        try {
            estado = EstadoDaNoite.ler(arquivo.estado());
            if (ACAO_INICIAR.equals(acao) && !estado.ativa) {
                estado = new EstadoDaNoite();
                estado.ativa = true;
                estado.inicioUtcMs = System.currentTimeMillis();
                estado.arquivo = ArquivoDaNoite.nomeDaNoite(estado.inicioUtcMs);
                final String posicao = intent.getStringExtra(EXTRA_POSICAO);
                if (posicao != null && !posicao.isEmpty()) {
                    try {
                        NotasDaNoite.salvar(pasta(this), estado.arquivo,
                                java.util.Collections.singletonMap("posicao", posicao));
                    } catch (IllegalArgumentException ex) {
                        Log.e(TAG, "posicao recusada: " + posicao, ex);
                    }
                }
            } else if (estado.ativa) {
                // Intent nulo e o START_STICKY trazendo de volta um servico morto.
                if (intent == null) estado.retomadas++;
            } else {
                // Retomada sem noite em andamento: nada a fazer.
                pararServico();
                return START_NOT_STICKY;
            }
            arquivo.abrir(estado.arquivo);
            estado.salvar(arquivo.estado());
        } catch (IOException e) {
            Log.e(TAG, "nao abriu a noite", e);
            pararServico();
            return START_NOT_STICKY;
        }
        comecarARegistrar();
        return START_STICKY;
    }

    private void entrarEmPrimeiroPlano() {
        final NotificationManager nm = getSystemService(NotificationManager.class);
        if (Build.VERSION.SDK_INT >= 26 && nm.getNotificationChannel(CANAL) == null) {
            final NotificationChannel canal = new NotificationChannel(
                    CANAL, "Registro da noite", NotificationManager.IMPORTANCE_LOW);
            canal.setDescription("Aparece enquanto o Dormio registra o movimento da noite.");
            nm.createNotificationChannel(canal);
        }
        final Intent abrir = new Intent(this, MainActivity.class)
                .setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        final PendingIntent aoTocar = PendingIntent.getActivity(
                this, 0, abrir, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        aoTocarNaNotificacao = aoTocar;
        final int tipo = Build.VERSION.SDK_INT >= 34 ? ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH : 0;
        ServiceCompat.startForeground(this, ID_NOTIFICACAO, notificacao("Toque para ver ou encerrar."), tipo);
    }

    private PendingIntent aoTocarNaNotificacao;

    private Notification notificacao(String texto) {
        return new NotificationCompat.Builder(this, CANAL)
                .setContentTitle("Dormio registrando a noite")
                .setContentText(texto)
                .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setContentIntent(aoTocarNaNotificacao)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build();
    }

    private void comecarARegistrar() {
        final PowerManager pm = getSystemService(PowerManager.class);
        trava = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "dormio:noite");
        trava.setReferenceCounted(false);
        trava.acquire(TETO_DA_TRAVA_MS);

        linha = new HandlerThread("dormio-sensor");
        linha.start();
        nucleo = new NucleoNativo();
        relogio = new RelogioDoSensor();
        nucleoIniciado = false;
        pendentes = 0;
        proximaTemperaturaMs = 0;
        atualizarTemperatura();

        final SensorManager sm = getSystemService(SensorManager.class);
        final Sensor acel = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        if (acel == null) {
            Log.e(TAG, "aparelho sem acelerometro");
            encerrar("sem_sensor");
            return;
        }
        registrando = sm.registerListener(
                this, acel, PERIODO_US, LATENCIA_MAXIMA_US, new Handler(linha.getLooper()));
        emExecucao = registrando;
        if (!registrando) {
            Log.e(TAG, "o sistema recusou o acelerometro");
            encerrar("sem_sensor");
        }
    }

    @Override
    public void onSensorChanged(SensorEvent e) {
        final long us = relogio.paraMonotonicoUs(e.timestamp, SystemClock.elapsedRealtimeNanos());
        if (!nucleoIniciado) {
            // A hora real amarrada ao elapsedRealtime, que e a base do relogio acima.
            nucleo.iniciar(us, SystemClock.elapsedRealtime(), System.currentTimeMillis());
            estado.deslocamentoDoRelogioNs = relogio.deslocamentoNs();
            nucleoIniciado = true;
        }
        tUs[pendentes] = us;
        xyz[3 * pendentes] = e.values[0];
        xyz[3 * pendentes + 1] = e.values[1];
        xyz[3 * pendentes + 2] = e.values[2];
        pendentes++;
        if (pendentes == LOTE) entregarAoNucleo();
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        // A precisao do acelerometro nao muda nada na cadeia.
    }

    private void entregarAoNucleo() {
        if (pendentes == 0 || nucleo == null) return;
        nucleo.amostrar(tUs, xyz, pendentes);
        pendentes = 0;
        if (SystemClock.elapsedRealtime() >= proximaTemperaturaMs) atualizarTemperatura();
        boolean gravou = false;
        String payload;
        while ((payload = nucleo.proximoPayload()) != null) {
            try {
                arquivo.anexar(payload);
                gravou = true;
                estado.ultimaEpocaUtcMs = System.currentTimeMillis();
            } catch (IOException ex) {
                Log.e(TAG, "nao gravou a epoca", ex);
            }
        }
        if (gravou) salvarContadores();
    }

    private void atualizarTemperatura() {
        proximaTemperaturaMs = SystemClock.elapsedRealtime() + INTERVALO_DA_TEMPERATURA_MS;
        final Intent bateria = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (bateria == null) return;
        // O Android entrega a temperatura da bateria em DECIMOS de grau.
        final int decimos = bateria.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Integer.MIN_VALUE);
        if (decimos == Integer.MIN_VALUE) return;
        estado.temperaturaDecimos = decimos;
        if (nucleo != null) nucleo.definirTemperatura(decimos / 10.0f);
        // Etapa 4: a temperatura na notificacao, e o corte por calor.
        getSystemService(NotificationManager.class).notify(ID_NOTIFICACAO,
                notificacao(String.format(java.util.Locale.ROOT, "Aparelho a %.1f °C. Toque para ver ou encerrar.",
                        decimos / 10.0f)));
        if (CorteDeTemperatura.deveEncerrar(decimos) && !encerrandoPorCalor) {
            encerrandoPorCalor = true;
            Log.w(TAG, "aparelho a " + decimos / 10.0f + " C: a noite sera encerrada");
            // encerrar() espera a linha do sensor terminar; chamado DELA, travaria.
            new Handler(android.os.Looper.getMainLooper()).post(() -> encerrar("temperatura"));
        }
    }

    private void salvarContadores() {
        if (nucleo == null || estado == null) return;
        final long[] c = nucleo.contadores();
        // Os contadores do nucleo sao da cadeia atual; numa retomada, a cadeia
        // recomeca do zero, e o arquivo guarda a soma das anteriores na base.
        estado.amostras = baseAmostras + c[NucleoNativo.RECEBIDAS];
        estado.foraDeOrdem = baseForaDeOrdem + c[NucleoNativo.FORA_DE_ORDEM];
        estado.epocasGravadas = baseGravadas + c[NucleoNativo.COM_PAYLOAD];
        estado.recusadas = baseRecusadas + c[NucleoNativo.RECUSADAS];
        estado.recusadasPorTaxa = baseRecusadasTaxa + c[NucleoNativo.RECUSADAS_POR_TAXA];
        estado.semFeatures = baseSemFeatures + c[NucleoNativo.SEM_FEATURES];
        estado.semPayload = baseSemPayload + c[NucleoNativo.SEM_PAYLOAD];
        if (c[NucleoNativo.TAXA_MILI_HZ] > 0) estado.taxaMiliHz = c[NucleoNativo.TAXA_MILI_HZ];
        try {
            estado.salvar(arquivo.estado());
        } catch (IOException ex) {
            Log.e(TAG, "nao salvou o estado", ex);
        }
    }

    // A base dos contadores numa retomada: o que as cadeias anteriores ja contaram.
    private long baseAmostras, baseForaDeOrdem, baseGravadas, baseRecusadas, baseRecusadasTaxa,
            baseSemFeatures, baseSemPayload;

    @Override
    public void onCreate() {
        super.onCreate();
        try {
            final EstadoDaNoite anterior = EstadoDaNoite.ler(new File(pasta(this), ArquivoDaNoite.ESTADO));
            if (anterior.ativa) {
                baseAmostras = anterior.amostras;
                baseForaDeOrdem = anterior.foraDeOrdem;
                baseGravadas = anterior.epocasGravadas;
                baseRecusadas = anterior.recusadas;
                baseRecusadasTaxa = anterior.recusadasPorTaxa;
                baseSemFeatures = anterior.semFeatures;
                baseSemPayload = anterior.semPayload;
            }
        } catch (IOException ex) {
            Log.e(TAG, "nao leu o estado anterior", ex);
        }
    }

    private volatile boolean encerrandoPorCalor;

    private void encerrar(String motivo) {
        if (registrando) {
            getSystemService(SensorManager.class).unregisterListener(this);
            registrando = false;
        }
        if (linha != null) {
            // O que ficou no lote entra antes de fechar.
            final Handler h = new Handler(linha.getLooper());
            h.post(this::entregarAoNucleo);
            h.post(this::salvarContadores);
            linha.quitSafely();
            try {
                linha.join(2000);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
            }
            linha = null;
        }
        if (estado == null) {
            try {
                estado = EstadoDaNoite.ler(new File(pasta(this), ArquivoDaNoite.ESTADO));
            } catch (IOException ex) {
                estado = new EstadoDaNoite();
            }
        }
        final boolean estavaAtiva = estado.ativa;
        estado.ativa = false;
        if (estavaAtiva && estado.arquivo != null && !estado.arquivo.isEmpty()) {
            try {
                NotasDaNoite.salvar(pasta(this), estado.arquivo,
                        java.util.Collections.singletonMap("fim", motivo));
            } catch (IOException | IllegalArgumentException ex) {
                Log.e(TAG, "nao anotou o fim da noite", ex);
            }
        }
        try {
            if (arquivo == null) arquivo = new ArquivoDaNoite(pasta(this));
            estado.salvar(arquivo.estado());
            arquivo.close();
        } catch (IOException ex) {
            Log.e(TAG, "nao fechou a noite", ex);
        }
        if (nucleo != null) {
            nucleo.close();
            nucleo = null;
        }
        pararServico();
    }

    private void pararServico() {
        emExecucao = false;
        if (trava != null && trava.isHeld()) trava.release();
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    @Override
    public void onDestroy() {
        // Destruido sem ENCERRAR (o sistema parou o servico): solta o sensor e a
        // trava, mas deixa a noite ATIVA no estado, para a retomada continuar.
        emExecucao = false;
        if (registrando) {
            getSystemService(SensorManager.class).unregisterListener(this);
            registrando = false;
        }
        if (linha != null) {
            linha.quitSafely();
            linha = null;
        }
        if (trava != null && trava.isHeld()) trava.release();
        try {
            if (arquivo != null) arquivo.close();
        } catch (IOException ignorada) {
            // nada a fazer: as linhas ja foram sincronizadas uma a uma
        }
        if (nucleo != null) {
            nucleo.close();
            nucleo = null;
        }
        super.onDestroy();
    }
}
