package com.nova.assistant;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.content.res.AssetFileDescriptor;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.Ringtone;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.Vibrator;
import android.os.VibrationEffect;
import android.util.Log;
import androidx.core.app.NotificationCompat;
import com.nova.assistant.reminder.ReminderId;
import java.util.UUID;

public class NovaAlarmService extends Service {
    private static final String TAG = "NovaAlarmService";
    public static final String CHANNEL_ID = "nova_alarms_channel_v2";
    public static final int NOTIFICATION_ID = 99991;

    public static final String ACTION_START_ALARM = "com.nova.assistant.action.START_ALARM";
    public static final String ACTION_STOP_ALARM = "com.nova.assistant.action.STOP_ALARM";
    public static final String ACTION_SNOOZE_ALARM = "com.nova.assistant.action.SNOOZE_ALARM";
    public static final String ACTION_CLAIM_ALARM = "com.nova.assistant.action.CLAIM_ALARM";

    public enum SessionState {
        IDLE,
        RINGING_NATIVE,
        WAITING_WEBVIEW,
        HANDOFF_COMPLETE,
        STOPPED
    }

    public static volatile boolean isAlarmRinging = false;
    public static volatile String currentSessionId = "";
    public static volatile SessionState currentState = SessionState.IDLE;
    public static volatile SessionState lastTerminalState = SessionState.IDLE;

    private MediaPlayer mediaPlayer = null;
    private Ringtone fallbackRingtone = null;
    private PowerManager.WakeLock wakeLock = null;
    private final android.os.Handler safetyHandler = new android.os.Handler(android.os.Looper.getMainLooper());
    private final Runnable safetyTimeoutRunnable = new Runnable() {
        @Override
        public void run() {
            Log.i(TAG, "Alarm safety timeout reached (120s)");
            finishAlarmSession();
        }
    };

    public static void stopAlarm(Context context) {
        try {
            Intent intent = new Intent(context, NovaAlarmService.class);
            intent.setAction(ACTION_STOP_ALARM);
            context.startService(intent);
        } catch (Exception e) {
            Log.e(TAG, "Error requesting stopAlarm", e);
        }
    }

    public static boolean claimAlarm(Context context, String sessionId) {
        if (sessionId != null && !sessionId.isEmpty() && currentSessionId.equals(sessionId) && isAlarmRinging) {
            try {
                Intent intent = new Intent(context, NovaAlarmService.class);
                intent.setAction(ACTION_CLAIM_ALARM);
                intent.putExtra("session_id", sessionId);
                context.startService(intent);
                return true;
            } catch (Exception e) {
                Log.e(TAG, "Error claiming alarm session", e);
            }
        }
        return false;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            finishAlarmSession();
            return START_NOT_STICKY;
        }

        String action = intent.getAction();
        if (ACTION_STOP_ALARM.equals(action)) {
            currentState = SessionState.STOPPED;
            finishAlarmSession();
            return START_NOT_STICKY;
        }

        if (ACTION_CLAIM_ALARM.equals(action)) {
            String incomingSessionId = intent.getStringExtra("session_id");
            if (currentSessionId.equals(incomingSessionId)) {
                Log.i(TAG, "Alarm session successfully claimed by WebView: " + incomingSessionId);
                currentState = SessionState.HANDOFF_COMPLETE;
                finishAlarmSession();
            }
            return START_NOT_STICKY;
        }

        if (ACTION_SNOOZE_ALARM.equals(action)) {
            int taskId = intent.getIntExtra("task_id", 0);
            String reminderId = intent.getStringExtra("reminder_id");
            String taskTitle = intent.getStringExtra("task_title");
            if (taskTitle == null || taskTitle.isEmpty()) taskTitle = "Nhắc nhở";

            long snoozeTime = System.currentTimeMillis() + 5 * 60 * 1000;
            // P1-06: New snooze reminder has unique canonical reminder_id
            String snoozeReminderId = "rem_snz_" + UUID.randomUUID().toString();
            MainActivity.scheduleAlarmDirect(this, snoozeReminderId, taskTitle + " (báo lại)", snoozeTime);

            currentState = SessionState.STOPPED;
            finishAlarmSession();
            return START_NOT_STICKY;
        }

        // Mặc định hoặc ACTION_START_ALARM:
        String reminderId = intent.getStringExtra("reminder_id");
        String taskTitle = intent.getStringExtra("task_title");
        if (taskTitle == null || taskTitle.isEmpty()) {
            taskTitle = "Làm việc & Học tập";
        }
        int taskId = intent.getIntExtra("task_id", (reminderId != null ? ReminderId.toRequestCode(reminderId) : (int) (System.currentTimeMillis() % 1000000)));

        currentSessionId = UUID.randomUUID().toString();
        currentState = SessionState.RINGING_NATIVE;

        // V2 Correct Lifecycle Order:
        // 1. Dọn dẹp phiên trước
        releaseMediaPlayer();
        stopFallbackRingtone();
        // 2. Chiếm giữ WakeLock
        acquireWakeLock();
        // 3. Khởi chạy Foreground Service Notification
        startForegroundWithNotification(taskId, reminderId, taskTitle, currentSessionId);
        // 4. Bật cờ chuông đang reo
        isAlarmRinging = true;
        safetyHandler.removeCallbacks(safetyTimeoutRunnable);
        safetyHandler.postDelayed(safetyTimeoutRunnable, 120000L);
        // 5. Bắt đầu phát âm thanh chuông
        startAlarmAudio();

        return START_STICKY;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Chuông Báo Lịch Trình Nova",
                    NotificationManager.IMPORTANCE_HIGH
                );
                channel.setDescription("Thông báo chuông nhắc nhở và đàm thoại rảnh tay cùng Nova");
                channel.enableVibration(true);
                channel.setVibrationPattern(new long[]{0, 400, 200, 400, 200, 600});
                channel.setSound(null, null);
                manager.createNotificationChannel(channel);
            }
        }
    }

    private void startForegroundWithNotification(int taskId, String reminderId, String taskTitle, String sessionId) {
        Intent openAppIntent = new Intent(this, MainActivity.class);
        openAppIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        openAppIntent.putExtra("auto_alarm", true);
        openAppIntent.putExtra("task_title", taskTitle);
        openAppIntent.putExtra("alarm_session_id", sessionId);
        if (reminderId != null) {
            openAppIntent.putExtra("reminder_id", reminderId);
        }
        PendingIntent openPendingIntent = PendingIntent.getActivity(
            this,
            taskId,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Intent stopIntent = new Intent(this, NovaAlarmService.class);
        stopIntent.setAction(ACTION_STOP_ALARM);
        PendingIntent stopPendingIntent = PendingIntent.getService(
            this,
            taskId + 1,
            stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Intent snoozeIntent = new Intent(this, NovaAlarmService.class);
        snoozeIntent.setAction(ACTION_SNOOZE_ALARM);
        snoozeIntent.putExtra("task_id", taskId);
        if (reminderId != null) {
            snoozeIntent.putExtra("reminder_id", reminderId);
        }
        snoozeIntent.putExtra("task_title", taskTitle);
        PendingIntent snoozePendingIntent = PendingIntent.getService(
            this,
            taskId + 2,
            snoozeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("⏰ Đến giờ rồi cậu ơi: " + taskTitle)
            .setContentText("Nova đang chờ cậu, chạm vào đây để trò chuyện ngay!")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setOngoing(true)
            .setSilent(true)
            .setVibrate(new long[]{0, 400, 200, 400, 200, 600})
            .setContentIntent(openPendingIntent)
            .setFullScreenIntent(openPendingIntent, true)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Tắt chuông", stopPendingIntent)
            .addAction(android.R.drawable.ic_lock_idle_alarm, "Báo lại 5p", snoozePendingIntent)
            .addAction(android.R.drawable.ic_btn_speak_now, "Trò chuyện", openPendingIntent);

        Notification notification = builder.build();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private void startAlarmAudio() {
        try {
            mediaPlayer = new MediaPlayer();
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                mediaPlayer.setAudioAttributes(
                    new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                );
            } else {
                mediaPlayer.setAudioStreamType(AudioManager.STREAM_ALARM);
            }

            AssetFileDescriptor afd = getAssets().openFd("public/assets/cuppy_alarm.wav");
            mediaPlayer.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
            mediaPlayer.prepare();
            try { afd.close(); } catch (Exception ignored) {}

            mediaPlayer.setVolume(1.0f, 1.0f);
            mediaPlayer.setLooping(true);
            mediaPlayer.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                @Override
                public void onCompletion(MediaPlayer mp) {
                    // Invariant: Do not finish the alarm session simply because cuppy_alarm.wav completes.
                    // Keep native alerting alive until STOP, SNOOZE, successful CLAIM, or safety timeout.
                    Log.d(TAG, "cuppy_alarm.wav playback cycle completed; continuing looping until user action or claim");
                }
            });
            mediaPlayer.setOnErrorListener(new MediaPlayer.OnErrorListener() {
                @Override
                public boolean onError(MediaPlayer mp, int what, int extra) {
                    Log.w(TAG, "mediaPlayer error what=" + what + ", extra=" + extra + "; falling back to system ringtone");
                    releaseMediaPlayer();
                    playFallbackRingtone();
                    return true;
                }
            });
            mediaPlayer.start();
        } catch (Exception e) {
            Log.w(TAG, "Cannot play asset cuppy_alarm.wav, falling back to system ringtone", e);
            releaseMediaPlayer();
            playFallbackRingtone();
        }
    }

    private void playFallbackRingtone() {
        try {
            Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            if (soundUri == null) soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
            fallbackRingtone = RingtoneManager.getRingtone(this, soundUri);
            if (fallbackRingtone != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    fallbackRingtone.setLooping(true);
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    fallbackRingtone.setAudioAttributes(
                        new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_ALARM)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()
                    );
                }
                fallbackRingtone.play();
                Log.i(TAG, "Fallback system ringtone playing successfully");
            } else {
                Log.w(TAG, "Both primary audio and fallback ringtone unavailable; maintaining foreground notification and vibration alert");
                triggerVibrationAlert();
            }
        } catch (Exception ex) {
            Log.e(TAG, "Error playing fallback ringtone; maintaining foreground notification and vibration alert", ex);
            triggerVibrationAlert();
        }
    }

    private void triggerVibrationAlert() {
        try {
            Vibrator vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (vibrator != null && vibrator.hasVibrator()) {
                long[] pattern = new long[]{0, 500, 250, 500, 250, 500};
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createWaveform(pattern, 0));
                } else {
                    vibrator.vibrate(pattern, 0);
                }
            }
        } catch (Exception ignored) {}
    }

    private void stopVibrationAlert() {
        try {
            Vibrator vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (vibrator != null) {
                vibrator.cancel();
            }
        } catch (Exception ignored) {}
    }

    private void acquireWakeLock() {
        try {
            if (wakeLock == null) {
                PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
                if (pm != null) {
                    wakeLock = pm.newWakeLock(
                        PowerManager.PARTIAL_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
                        "Nova:AlarmServiceWakeLock"
                    );
                }
            }
            if (wakeLock != null && !wakeLock.isHeld()) {
                wakeLock.acquire(130000L);
            }
        } catch (Exception ignored) {}
    }

    private void releaseWakeLock() {
        try {
            if (wakeLock != null && wakeLock.isHeld()) {
                wakeLock.release();
            }
        } catch (Exception ignored) {}
    }

    private void releaseMediaPlayer() {
        try {
            if (mediaPlayer != null) {
                if (mediaPlayer.isPlaying()) {
                    mediaPlayer.stop();
                }
                mediaPlayer.release();
                mediaPlayer = null;
            }
        } catch (Exception e) {
            Log.e(TAG, "Error stopping mediaPlayer", e);
            mediaPlayer = null;
        }
    }

    private void stopFallbackRingtone() {
        try {
            if (fallbackRingtone != null) {
                if (fallbackRingtone.isPlaying()) {
                    fallbackRingtone.stop();
                }
                fallbackRingtone = null;
            }
        } catch (Exception e) {
            Log.e(TAG, "Error stopping fallbackRingtone", e);
            fallbackRingtone = null;
        }
    }

    private void finishAlarmSession() {
        safetyHandler.removeCallbacks(safetyTimeoutRunnable);
        lastTerminalState = currentState;
        isAlarmRinging = false;
        currentSessionId = "";
        currentState = SessionState.IDLE;
        releaseMediaPlayer();
        stopFallbackRingtone();
        stopVibrationAlert();
        releaseWakeLock();
        try {
            stopForeground(true);
        } catch (Exception ignored) {}
        stopSelf();
    }

    @Override
    public void onDestroy() {
        finishAlarmSession();
        super.onDestroy();
    }
}
