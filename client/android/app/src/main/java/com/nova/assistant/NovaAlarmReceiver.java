package com.nova.assistant;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.res.AssetFileDescriptor;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.Ringtone;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import androidx.core.app.NotificationCompat;

public class NovaAlarmReceiver extends BroadcastReceiver {
    private static final String CHANNEL_ID = "nova_alarms_channel_v2";

    @Override
    public void onReceive(Context context, Intent intent) {
        String taskTitle = intent.getStringExtra("task_title");
        if (taskTitle == null || taskTitle.isEmpty()) {
            taskTitle = "Làm việc & Học tập";
        }
        int taskId = intent.getIntExtra("task_id", (int) System.currentTimeMillis());

        // 1. Giữ CPU thức tỉnh và đánh thức màn hình (WakeLock)
        PowerManager pm = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        if (pm != null) {
            try {
                PowerManager.WakeLock wakeLock = pm.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
                    "Nova:AlarmWakeLock"
                );
                wakeLock.acquire(45000);
            } catch (Exception ignored) {}
        }

        // 2. Phát âm thanh chuông báo thức giọng nói Cuppy phòng thu (hoặc nhạc chuông ALARM)
        try {
            final MediaPlayer player = new MediaPlayer();
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                player.setAudioAttributes(
                    new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                );
            } else {
                player.setAudioStreamType(AudioManager.STREAM_ALARM);
            }

            AssetFileDescriptor afd = context.getAssets().openFd("public/assets/cuppy_alarm.wav");
            player.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
            player.prepare();
            try { afd.close(); } catch(Exception ignored) {}

            player.setVolume(1.0f, 1.0f);
            player.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                @Override
                public void onCompletion(MediaPlayer mp) {
                    try { mp.release(); } catch(Exception ignored) {}
                }
            });
            player.start();
        } catch (Exception e) {
            try {
                Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
                if (soundUri == null) soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
                Ringtone r = RingtoneManager.getRingtone(context, soundUri);
                if (r != null) r.play();
            } catch (Exception ignored) {}
        }

        // 3. Khởi chạy MainActivity để đưa giao diện đàm thoại Nova lên màn hình
        Intent openAppIntent = new Intent(context, MainActivity.class);
        openAppIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        openAppIntent.putExtra("auto_alarm", true);
        openAppIntent.putExtra("task_title", taskTitle);
        try {
            context.startActivity(openAppIntent);
        } catch (Exception ex) {
            ex.printStackTrace();
        }

        // 4. Tạo Notification Channel & Heads-Up Notification mức ưu tiên tối cao (ALARM)
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Chuông Báo Lịch Trình Nova",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Thông báo chuông nhắc nhở và đàm thoại rảnh tay cùng Nova");
            channel.enableVibration(true);
            channel.setVibrationPattern(new long[]{0, 400, 200, 400, 200, 600});
            channel.setSound(null, null); // F-19: Tắt sound notification để tránh phát chồng âm với giọng nói Cuppy
            if (manager != null) {
                try { manager.deleteNotificationChannel("nova_alarms_channel"); } catch (Exception ignored) {}
                manager.createNotificationChannel(channel);
            }
        }

        PendingIntent pendingIntent = PendingIntent.getActivity(
            context,
            taskId,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("⏰ Đến giờ rồi cậu ơi: " + taskTitle)
            .setContentText("Nova đang chờ cậu, chạm vào đây để trò chuyện ngay!")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setSilent(true) // F-19: Ngăn chặn phát 2 luồng âm thanh đè nhau
            .setVibrate(new long[]{0, 400, 200, 400, 200, 600})
            .setContentIntent(pendingIntent)
            .setFullScreenIntent(pendingIntent, true)
            .addAction(android.R.drawable.ic_btn_speak_now, "Trò chuyện với Nova", pendingIntent);

        if (manager != null) {
            manager.notify(taskId, builder.build());
        }
    }
}
