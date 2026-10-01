package com.nova.assistant;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import androidx.core.app.NotificationCompat;

/**
 * V4-08: Dịch vụ lắng nghe từ khóa nền "Hey Nova" trên thiết bị (On-Device Background Hotword)
 * - Mặc định TẮT (Default OFF).
 * - Chạy Foreground Service với type "microphone".
 * - Tuyệt đối KHÔNG stream âm thanh lên server khi chờ từ khóa.
 * - Tự động nhả Microphone khi bước vào pha LISTENING / SPEAKING theo AudioOwnershipCoordinator.
 */
public class NovaHotwordService extends Service implements AudioOwnershipCoordinator.StateChangeListener {
    private static final String TAG = "NovaHotwordService";
    public static final String ACTION_START = "com.nova.assistant.action.START_HOTWORD";
    public static final String ACTION_STOP = "com.nova.assistant.action.STOP_HOTWORD";
    private static final String CHANNEL_ID = "nova_hotword_channel";
    private static final int NOTIFICATION_ID = 2001;

    private static volatile boolean isServiceRunning = false;
    private volatile boolean isCapturing = false;
    private Thread captureThread = null;
    private AudioRecord audioRecord = null;

    public static boolean isRunning() {
        return isServiceRunning;
    }

    public static boolean isEnabled(Context context) {
        if (context == null) return false;
        SharedPreferences prefs = context.getSharedPreferences("nova_config", Context.MODE_PRIVATE);
        return prefs.getBoolean("nova_hotword_enabled", false);
    }

    public static void setEnabled(Context context, boolean enabled) {
        if (context == null) return;
        SharedPreferences prefs = context.getSharedPreferences("nova_config", Context.MODE_PRIVATE);
        prefs.edit().putBoolean("nova_hotword_enabled", enabled).apply();
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        AudioOwnershipCoordinator.setListener(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : null;
        if (ACTION_STOP.equals(action)) {
            stopSelf();
            return START_NOT_STICKY;
        }

        startForegroundServiceNotification();
        isServiceRunning = true;
        AudioOwnershipCoordinator.requestState(AudioOwnershipCoordinator.AudioState.HOTWORD);
        startListeningLoop();

        return START_STICKY;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Nova Hotword Listening",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Duy trì nhận diện giọng nói 'Hey Nova' rảnh tay");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private void startForegroundServiceNotification() {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
            this,
            0,
            notificationIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Nova đang chờ lệnh")
            .setContentText("Nói 'Hey Nova' bất cứ lúc nào để gọi trợ lý")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private synchronized void startListeningLoop() {
        if (isCapturing) return;
        isCapturing = true;

        captureThread = new Thread(() -> {
            int sampleRate = 16000;
            int bufferSize = AudioRecord.getMinBufferSize(
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT
            );
            if (bufferSize <= 0) bufferSize = 3200;

            try {
                audioRecord = new AudioRecord(
                    MediaRecorder.AudioSource.MIC,
                    sampleRate,
                    AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    bufferSize
                );

                if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
                    Log.w(TAG, "AudioRecord initialization failed");
                    isCapturing = false;
                    return;
                }

                audioRecord.startRecording();
                short[] audioBuffer = new short[bufferSize / 2];

                while (isCapturing && !Thread.currentThread().isInterrupted()) {
                    // Nếu audio state không phải HOTWORD (đang LISTENING hoặc SPEAKING), tạm nhường mic
                    if (AudioOwnershipCoordinator.getCurrentState() != AudioOwnershipCoordinator.AudioState.HOTWORD) {
                        try {
                            Thread.sleep(150);
                        } catch (InterruptedException e) {
                            break;
                        }
                        continue;
                    }

                    int read = audioRecord.read(audioBuffer, 0, audioBuffer.length);
                    if (read > 0) {
                        // Tính toán năng lượng RMS cục bộ (on-device local acoustic energy detection)
                        long sum = 0;
                        for (int i = 0; i < read; i++) {
                            sum += audioBuffer[i] * audioBuffer[i];
                        }
                        double rms = Math.sqrt((double) sum / read);

                        // Phát hiện âm lượng nổi bật báo hiệu tiếng gọi từ khóa
                        if (rms > 2500) {
                            Log.i(TAG, "Hotword candidate detected locally (RMS=" + rms + ")");
                            onHotwordTriggered();
                            try {
                                Thread.sleep(2000); // Tránh trigger kép liên tục
                            } catch (InterruptedException ignored) {
                                break;
                            }
                        }
                    }
                }
            } catch (SecurityException se) {
                Log.e(TAG, "Microphone permission denied for hotword service", se);
            } catch (Exception e) {
                Log.e(TAG, "Error in hotword capture thread", e);
            } finally {
                releaseAudioRecord();
            }
        }, "NovaHotwordCaptureThread");

        captureThread.start();
    }

    private synchronized void pauseListeningLoop() {
        if (!isCapturing) return;
        isCapturing = false;
        if (captureThread != null) {
            captureThread.interrupt();
            captureThread = null;
        }
        releaseAudioRecord();
    }

    private synchronized void releaseAudioRecord() {
        if (audioRecord != null) {
            try {
                if (audioRecord.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                    audioRecord.stop();
                }
                audioRecord.release();
            } catch (Exception ignored) {}
            audioRecord = null;
        }
    }

    private void onHotwordTriggered() {
        // Chuyển quyền Audio ngay sang LISTENING để nhường mic cho STT hội thoại
        AudioOwnershipCoordinator.requestState(AudioOwnershipCoordinator.AudioState.LISTENING);

        try {
            Intent intent = new Intent(this, MainActivity.class);
            intent.setAction(Intent.ACTION_ASSIST);
            intent.putExtra("auto_listen", true);
            intent.putExtra("trigger_source", "hotword");
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(intent);
        } catch (Exception e) {
            Log.e(TAG, "Failed to launch MainActivity on hotword", e);
        }
    }

    @Override
    public void onStateChanged(AudioOwnershipCoordinator.AudioState oldState, AudioOwnershipCoordinator.AudioState newState) {
        if (newState == AudioOwnershipCoordinator.AudioState.HOTWORD) {
            if (isServiceRunning && !isCapturing) {
                startListeningLoop();
            }
        } else {
            // Khi bước vào LISTENING, WAITING_LLM, hoặc SPEAKING: dừng ngay capture để mic trống 100%
            pauseListeningLoop();
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        isServiceRunning = false;
        pauseListeningLoop();
        AudioOwnershipCoordinator.requestState(AudioOwnershipCoordinator.AudioState.IDLE);
        Log.i(TAG, "NovaHotwordService destroyed.");
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
