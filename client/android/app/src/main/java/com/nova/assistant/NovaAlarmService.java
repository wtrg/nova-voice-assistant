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
import android.util.Log;
import androidx.core.app.NotificationCompat;

public class NovaAlarmService extends Service {
    private static final String TAG = "NovaAlarmService";
    public static final String CHANNEL_ID = "nova_alarms_channel_v2";
    public static final int NOTIFICATION_ID = 99991;

    public static final String ACTION_START_ALARM = "com.nova.assistant.action.START_ALARM";
    public static final String ACTION_STOP_ALARM = "com.nova.assistant.action.STOP_ALARM";
    public static final String ACTION_SNOOZE_ALARM = "com.nova.assistant.action.SNOOZE_ALARM";

    public static volatile boolean isAlarmRinging = false;

    private MediaPlayer mediaPlayer = null;
    private PowerManager.WakeLock wakeLock = null;

    public static void stopAlarm(Context context) {
        try {
            Intent intent = new Intent(context, NovaAlarmService.class);
            intent.setAction(ACTION_STOP_ALARM);
            context.startService(intent);
        } catch (Exception e) {
            Log.e(TAG, "Error requesting stopAlarm", e);
        }
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
            stopSelf();
            return START_NOT_STICKY;
        }

        String action = intent.getAction();
        if (ACTION_STOP_ALARM.equals(action)) {
            stopAlarmPlayback();
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }

        if (ACTION_SNOOZE_ALARM.equals(action)) {
            int taskId = intent.getIntExtra("task_id", 0);
            String taskTitle = intent.getStringExtra("task_title");
            if (taskTitle == null || taskTitle.isEmpty()) taskTitle = "Nhắc nhở";

            long snoozeTime = System.currentTimeMillis() + 5 * 60 * 1000;
            MainActivity.scheduleAlarmDirect(this, taskId > 0 ? taskId : (int) (System.currentTimeMillis() % 1000000), taskTitle + " (báo lại)", snoozeTime);

            stopAlarmPlayback();
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }

        String taskTitle = intent.getStringExtra("task_title");
        if (taskTitle == null || taskTitle.isEmpty()) {
            taskTitle = "Làm việc & Học tập";
        }
        int taskId = intent.getIntExtra("task_id", (int) (System.currentTimeMillis() % 1000000));

        acquireWakeLock();
        startForegroundWithNotification(taskId, taskTitle);
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

    private void startForegroundWithNotification(int taskId, String taskTitle) {
        Intent openAppIntent = new Intent(this, MainActivity.class);
        openAppIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        openAppIntent.putExtra("auto_alarm", true);
        openAppIntent.putExtra("task_title", taskTitle);
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
        isAlarmRinging = true;
        try {
            stopAlarmPlayback();
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
            mediaPlayer.setLooping(false);
            mediaPlayer.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                @Override
                public void onCompletion(MediaPlayer mp) {
                    stopAlarmPlayback();
                }
            });
            mediaPlayer.start();
        } catch (Exception e) {
            Log.w(TAG, "Cannot play asset cuppy_alarm.wav, falling back to system ringtone", e);
            try {
                Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
                if (soundUri == null) soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
                Ringtone r = RingtoneManager.getRingtone(this, soundUri);
                if (r != null) r.play();
            } catch (Exception ignored) {}
        }
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
                wakeLock.acquire(60000);
            }
        } catch (Exception ignored) {}
    }

    private void stopAlarmPlayback() {
        isAlarmRinging = false;
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
        }
        try {
            if (wakeLock != null && wakeLock.isHeld()) {
                wakeLock.release();
            }
        } catch (Exception ignored) {}
    }

    @Override
    public void onDestroy() {
        stopAlarmPlayback();
        super.onDestroy();
    }
}
