package com.nova.assistant;

import android.Manifest;
import android.app.AlarmManager;
import android.app.KeyguardManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.PlaybackParams;
import android.media.RingtoneManager;
import android.content.res.AssetFileDescriptor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.AlarmClock;
import android.provider.MediaStore;
import android.provider.Settings;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import androidx.core.app.ActivityCompat;
import androidx.core.app.NotificationManagerCompat;
import androidx.core.content.ContextCompat;
import org.json.JSONObject;
import com.nova.assistant.reminder.ReminderId;
import android.content.ComponentName;
import android.content.pm.ResolveInfo;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.Voice;
import android.webkit.PermissionRequest;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebChromeClient;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import android.content.SharedPreferences;
import android.util.Log;

public class MainActivity extends BridgeActivity {
    private static final int RECORD_AUDIO_REQUEST_CODE = 1001;
    private TextToSpeech tts;
    private boolean ttsReady = false;
    private MediaPlayer mediaPlayer = null;
    private AssetFileDescriptor currentAssetFd = null;
    private SpeechRecognizer nativeRecognizer = null;
    private boolean isNativeListening = false;
    private final java.util.concurrent.atomic.AtomicLong currentAudioRequestId = new java.util.concurrent.atomic.AtomicLong(0);

    private String getServerBaseUrl() {
        SharedPreferences prefs = getSharedPreferences("nova_config", Context.MODE_PRIVATE);
        return prefs.getString("server_base_url", "http://192.168.100.48:8000");
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Bật sáng màn hình, hiển thị đè màn hình khóa và mở khóa khi được gọi làm trợ lý
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
                setShowWhenLocked(true);
                setTurnScreenOn(true);
                KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
                if (km != null) {
                    km.requestDismissKeyguard(this, null);
                }
            } else {
                getWindow().addFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON |
                    WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
                );
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        // 1. Xin quyền Microphone ngay khi khởi động app
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.MODIFY_AUDIO_SETTINGS
            }, RECORD_AUDIO_REQUEST_CODE);
        }

        // Xin quyền gửi thông báo trên Android 13+ (TIRAMISU)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1002);
            }
        }
        // 2. Khởi tạo Native Android Text-to-Speech Engine
        try {
            boolean hasGoogleTts = false;
            try {
                getPackageManager().getPackageInfo("com.google.android.tts", 0);
                hasGoogleTts = true;
            } catch (Exception ignored) {}

            TextToSpeech.OnInitListener ttsInitListener = new TextToSpeech.OnInitListener() {
                @Override
                public void onInit(int status) {
                    if (status == TextToSpeech.SUCCESS) {
                        int result = tts.setLanguage(new Locale("vi", "VN"));
                        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                            tts.setLanguage(Locale.getDefault());
                        }

                        // Ưu tiên chọn giọng nữ truyền cảm & dễ thương trong hệ thống
                        try {
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                                Set<Voice> voices = tts.getVoices();
                                if (voices != null) {
                                    for (Voice v : voices) {
                                        if (v.getLocale() != null && "vi".equals(v.getLocale().getLanguage())) {
                                            String name = v.getName().toLowerCase();
                                            if (name.contains("female") || name.contains("vif") || name.contains("vn-2")) {
                                                tts.setVoice(v);
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        } catch (Exception ex) {
                            ex.printStackTrace();
                        }

                        // Điều chỉnh tông pitch 1.25f, tốc độ 1.08f giúp giọng trẻ trung, nhí nhảnh đúng chất bạn thân
                        tts.setPitch(1.25f);
                        tts.setSpeechRate(1.08f);
                        ttsReady = true;
                    }
                }
            };

            if (hasGoogleTts) {
                tts = new TextToSpeech(this, ttsInitListener, "com.google.android.tts");
            } else {
                tts = new TextToSpeech(this, ttsInitListener);
            }

            tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                @Override
                public void onStart(String utteranceId) {
                    runOnJs("if (window.onNovaSpeechStarted) window.onNovaSpeechStarted();");
                }

                @Override
                public void onDone(String utteranceId) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            if (bridge != null && bridge.getWebView() != null) {
                                bridge.getWebView().evaluateJavascript("if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();", null);
                            }
                        }
                    });
                }

                @Override
                public void onError(String utteranceId) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            if (bridge != null && bridge.getWebView() != null) {
                                bridge.getWebView().evaluateJavascript("if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();", null);
                            }
                        }
                    });
                }
            });
        } catch (Exception e) {
            e.printStackTrace();
        }

        // F-16: Dọn dẹp cache audio tạm thời khi khởi động app
        cleanOldAudioCache();

        // 3. Cấu hình WebView & Gắn cầu nối AndroidNative cho Nova
        try {
            if (this.bridge != null && this.bridge.getWebView() != null) {
                WebSettings settings = this.bridge.getWebView().getSettings();
                settings.setMediaPlaybackRequiresUserGesture(false);
                settings.setDomStorageEnabled(true);
                settings.setDatabaseEnabled(true);
                settings.setJavaScriptCanOpenWindowsAutomatically(true);
                settings.setAllowFileAccess(true);
                settings.setAllowContentAccess(true);

                this.bridge.getWebView().setWebChromeClient(new BridgeWebChromeClient(this.bridge) {
                    @Override
                    public void onPermissionRequest(final PermissionRequest request) {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                Uri origin = request.getOrigin();
                                String host = origin != null ? origin.getHost() : null;
                                String originStr = origin != null ? origin.toString() : "";
                                // F-02: Kiểm tra nguồn gốc tin cậy (Local app, localhost, hoặc Cloudflare tunnel)
                                boolean isTrusted = host == null ||
                                    host.equals("localhost") ||
                                    host.equals("127.0.0.1") ||
                                    originStr.startsWith("capacitor://") ||
                                    originStr.startsWith("http://localhost") ||
                                    originStr.startsWith("https://localhost") ||
                                    (host != null && host.endsWith(".trycloudflare.com"));

                                if (isTrusted) {
                                    request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
                                } else {
                                    request.deny();
                                }
                            }
                        });
                    }
                });

                this.bridge.getWebView().addJavascriptInterface(new Object() {
                    // Cầu nối nhận diện giọng nói Native phần cứng qua Android SpeechRecognizer
                    @JavascriptInterface
                    public void startNativeSpeech() {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                startNativeSpeechInternal();
                            }
                        });
                    }

                    @JavascriptInterface
                    public void stopNativeSpeech() {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                stopNativeSpeechInternal();
                            }
                        });
                    }

                    @JavascriptInterface
                    public boolean isNativeSpeechAvailable() {
                        return SpeechRecognizer.isRecognitionAvailable(MainActivity.this);
                    }

                    // Mở giao diện Voice Recognition Prompt chuẩn của Android (Google Mic Dialog)
                    @JavascriptInterface
                    public void startSpeechPrompt() {
                        startSpeechPromptInternal();
                    }

                    // Phát stream âm thanh qua URL có request-id gắn liền với phiên TurnController
                    @JavascriptInterface
                    public void playAudioUrl(final String requestId, final String url) {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                playAudioUrlInternal(requestId, url);
                            }
                        });
                    }

                    @JavascriptInterface
                    public void playAudioUrl(final String url) {
                        playAudioUrl("", url);
                    }

                    // Dừng phát toàn bộ âm thanh (MediaPlayer và TextToSpeech)
                    @JavascriptInterface
                    public void stopAudio() {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                stopAudioInternal();
                            }
                        });
                    }

                    @JavascriptInterface
                    public void setServerBaseUrl(final String url) {
                        if (url != null && !url.trim().isEmpty()) {
                            getSharedPreferences("nova_config", Context.MODE_PRIVATE)
                                .edit().putString("server_base_url", url.trim()).apply();
                        }
                    }

                    // Phát giọng nói nhân vật gốc Cuppy 100%, loại bỏ hoàn toàn giọng nam robot mặc định của máy
                    @JavascriptInterface
                    public void speak(final String text) {
                        if (text == null || text.trim().isEmpty()) {
                            runOnJs("if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
                            return;
                        }

                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                try {
                                    String encoded = java.net.URLEncoder.encode(text.trim(), "UTF-8");
                                    playAudioUrlInternal(getServerBaseUrl() + "/api/cuppy-tts?text=" + encoded);
                                } catch (Exception e) {
                                    runOnJs("if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
                                }
                            }
                        });
                    }

                    @JavascriptInterface
                    public void stop() {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                stopAudioInternal();
                            }
                        });
                    }

                    @JavascriptInterface
                    public boolean isReady() {
                        return true;
                    }

                    @JavascriptInterface
                    public boolean isTtsLanguageAvailable() {
                        try {
                            if (tts != null && ttsReady) {
                                int avail = tts.isLanguageAvailable(new Locale("vi", "VN"));
                                return avail >= TextToSpeech.LANG_AVAILABLE;
                            }
                        } catch (Exception ignored) {}
                        return false;
                    }

                    // Mở ứng dụng và tìm kiếm sâu (YouTube, Maps, Camera, Zalo, v.v.)
                    @JavascriptInterface
                    public boolean openApp(String appName, String query) {
                        return launchTargetApp(appName, query);
                    }

                    // Đặt chuông báo thức phần cứng qua AlarmManager khi tắt app (Phase 1, 2, 3 Canonical Reminder ID & ACK)
                    @JavascriptInterface
                    public String scheduleNativeAlarm(int id, String title, long timestampMillis) {
                        long nowMs = System.currentTimeMillis();
                        if (timestampMillis <= 0 || timestampMillis < (nowMs - 60000L) || timestampMillis > (nowMs + 100L * 365 * 24 * 3600 * 1000L)) {
                            return "{\"ok\":false,\"reminder_id\":\"" + id + "\",\"error_code\":\"INVALID_TIMESTAMP\",\"message\":\"Thời gian đặt lịch không hợp lệ hoặc đã qua\"}";
                        }
                        boolean exact = canScheduleExactAlarms();
                        boolean success = scheduleAlarmDirect(MainActivity.this, id, title, timestampMillis);
                        return "{\"ok\":" + success + ",\"reminder_id\":\"" + id + "\",\"pending_intent_id\":" + id + ",\"exact\":" + exact + ",\"scheduled_at_epoch_ms\":" + timestampMillis + "}";
                    }

                    @JavascriptInterface
                    public String scheduleNativeAlarm(String taskJson) {
                        try {
                            JSONObject obj = new JSONObject(taskJson);
                            String reminderId = obj.optString("reminder_id", "");
                            int id = obj.optInt("task_id", 0);
                            if (reminderId.isEmpty() && id != 0) {
                                reminderId = String.valueOf(id);
                            } else if (reminderId.isEmpty()) {
                                reminderId = java.util.UUID.randomUUID().toString();
                            }
                            int pendingIntentId = ReminderId.toRequestCode(reminderId);

                            String title = obj.optString("title", "Lịch hẹn");
                            long timestampMillis = obj.optLong("scheduled_at_epoch_ms", 0);
                            if (timestampMillis <= 0) {
                                String timeStr = obj.optString("scheduled_time", "");
                                if (!timeStr.isEmpty()) {
                                    try {
                                        java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault());
                                        java.util.Date d = sdf.parse(timeStr);
                                        if (d != null) timestampMillis = d.getTime();
                                    } catch (Exception ignored) {}
                                }
                            }

                            long nowMs = System.currentTimeMillis();
                            if (timestampMillis <= 0 || timestampMillis < (nowMs - 60000L) || timestampMillis > (nowMs + 100L * 365 * 24 * 3600 * 1000L)) {
                                return "{\"ok\":false,\"reminder_id\":\"" + reminderId + "\",\"error_code\":\"INVALID_TIMESTAMP\",\"message\":\"Thời gian đặt lịch không hợp lệ hoặc đã qua\"}";
                            }

                            boolean exact = canScheduleExactAlarms();
                            boolean success = scheduleAlarmDirect(MainActivity.this, reminderId, title, timestampMillis);
                            if (success) {
                                return "{\"ok\":true,\"reminder_id\":\"" + reminderId + "\",\"pending_intent_id\":" + pendingIntentId + ",\"exact\":" + exact + ",\"scheduled_at_epoch_ms\":" + timestampMillis + "}";
                            } else {
                                return "{\"ok\":false,\"reminder_id\":\"" + reminderId + "\",\"error_code\":\"SCHEDULE_FAILED\",\"message\":\"Không thể đặt lịch trên hệ thống Android\"}";
                            }
                        } catch (Exception e) {
                            return "{\"ok\":false,\"error_code\":\"INVALID_PAYLOAD\",\"message\":\"" + escapeForJs(e.getMessage()) + "\"}";
                        }
                    }

                    // Hủy chuông báo thức bằng int id hoặc canonical reminder_id string
                    @JavascriptInterface
                    public void cancelNativeAlarm(int id) {
                        cancelAlarmDirect(MainActivity.this, id);
                    }

                    @JavascriptInterface
                    public void cancelNativeAlarm(String reminderIdOrInt) {
                        if (reminderIdOrInt == null || reminderIdOrInt.isEmpty()) return;
                        SharedPreferences prefs = getSharedPreferences("nova_alarms_store", Context.MODE_PRIVATE);
                        int id = prefs.getInt("rem_code_" + reminderIdOrInt, -1);
                        if (id != -1) {
                            cancelAlarmDirect(MainActivity.this, id);
                        } else {
                            try {
                                int code = Integer.parseInt(reminderIdOrInt);
                                cancelAlarmDirect(MainActivity.this, code);
                            } catch (NumberFormatException e) {
                                int code = ReminderId.toRequestCode(reminderIdOrInt);
                                cancelAlarmDirect(MainActivity.this, code);
                            }
                        }
                        removeAlarmFromPrefs(MainActivity.this, reminderIdOrInt);
                    }

                    // Nhận quyền điều khiển chuông từ WebView (Safe Alarm Handoff Phase 5)
                    @JavascriptInterface
                    public boolean claimAlarmSession(String sessionId) {
                        return NovaAlarmService.claimAlarm(MainActivity.this, sessionId);
                    }

                    // Kiểm tra và yêu cầu quyền Alarm / Notification cho Diagnostics & Reliability Plan
                    @JavascriptInterface
                    public boolean canScheduleExactAlarms() {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                            AlarmManager am = (AlarmManager) getSystemService(Context.ALARM_SERVICE);
                            return am != null && am.canScheduleExactAlarms();
                        }
                        return true;
                    }

                    @JavascriptInterface
                    public void openExactAlarmSettings() {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                            try {
                                Intent intent = new Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM);
                                intent.setData(Uri.parse("package:" + getPackageName()));
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                startActivity(intent);
                            } catch (Exception e) {
                                try {
                                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                                    intent.setData(Uri.parse("package:" + getPackageName()));
                                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                    startActivity(intent);
                                } catch (Exception ignored) {}
                            }
                        }
                    }

                    @JavascriptInterface
                    public boolean areNotificationsEnabled() {
                        return NotificationManagerCompat.from(MainActivity.this).areNotificationsEnabled();
                    }

                    @JavascriptInterface
                    public void openNotificationSettings() {
                        try {
                            Intent intent = new Intent();
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                                intent.setAction(Settings.ACTION_APP_NOTIFICATION_SETTINGS);
                                intent.putExtra(Settings.EXTRA_APP_PACKAGE, getPackageName());
                            } else {
                                intent.setAction(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                                intent.setData(Uri.parse("package:" + getPackageName()));
                            }
                            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                            startActivity(intent);
                        } catch (Exception ignored) {}
                    }

                    @JavascriptInterface
                    public void stopAlarm() {
                        NovaAlarmService.stopAlarm(MainActivity.this);
                    }

                    @JavascriptInterface
                    public boolean isAlarmRinging() {
                        return NovaAlarmService.isAlarmRinging;
                    }

                    // Tùy chỉnh cao độ & tốc độ giọng nói ngay trong app
                    @JavascriptInterface
                    public void setVoiceTune(float pitch, float rate) {
                        if (tts != null) {
                            tts.setPitch(pitch);
                            tts.setSpeechRate(rate);
                        }
                    }

                    // Mở thẳng màn hình Cài đặt Trợ lý Kỹ thuật số của Android
                    @JavascriptInterface
                    public void openAssistantSettings() {
                        try {
                            Intent intent = new Intent(Settings.ACTION_VOICE_INPUT_SETTINGS);
                            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                            startActivity(intent);
                        } catch (Exception e) {
                            try {
                                Intent intent2 = new Intent("android.settings.VOICE_INPUT_SETTINGS");
                                intent2.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                startActivity(intent2);
                            } catch (Exception e2) {
                                try {
                                    Intent intent3 = new Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS);
                                    intent3.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                    startActivity(intent3);
                                } catch (Exception e3) {
                                    Intent intent4 = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName()));
                                    intent4.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                    startActivity(intent4);
                                }
                            }
                        }
                    }

                    // Mở quyền Xuất hiện trên cùng (Draw Over Other Apps)
                    @JavascriptInterface
                    public void openOverlaySettings() {
                        try {
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                                Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + getPackageName()));
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                startActivity(intent);
                            }
                        } catch (Exception e) {
                            Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName()));
                            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                            startActivity(intent);
                        }
                    }
                }, "AndroidNova");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        checkAlarmIntent(getIntent());
        checkAssistantIntent(getIntent());
    }

    @Override
    public void onResume() {
        super.onResume();
        checkAlarmIntent(getIntent());
        checkAssistantIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        checkAlarmIntent(intent);
        checkAssistantIntent(intent);
    }

    private void checkAlarmIntent(Intent intent) {
        if (intent != null && intent.getBooleanExtra("auto_alarm", false)) {
            String title = intent.getStringExtra("task_title");
            if (title == null) title = "Làm việc & Học tập";
            String sessionId = intent.getStringExtra("alarm_session_id");
            if (sessionId == null) sessionId = "";
            String reminderId = intent.getStringExtra("reminder_id");
            if (reminderId == null) reminderId = "";
            intent.removeExtra("auto_alarm");
            final String safeTitle = title.replace("'", "\\'");
            final String safeSessionId = sessionId.replace("'", "\\'");
            final String safeReminderId = reminderId.replace("'", "\\'");
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (bridge != null && bridge.getWebView() != null) {
                        bridge.getWebView().evaluateJavascript(
                            "(function(){\n" +
                            "  var attempts = 0;\n" +
                            "  function tryTrigger() {\n" +
                            "    if (window.handleNativeAlarmTrigger) {\n" +
                            "      window.handleNativeAlarmTrigger('" + safeTitle + "', '" + safeSessionId + "', '" + safeReminderId + "');\n" +
                            "    } else if (attempts < 20) {\n" +
                            "      attempts++;\n" +
                            "      setTimeout(tryTrigger, 200);\n" +
                            "    }\n" +
                            "  }\n" +
                            "  setTimeout(tryTrigger, 300);\n" +
                            "})();",
                            null
                        );
                    }
                }
            });
        }
    }

    private void checkAssistantIntent(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        Uri data = intent.getData();
        boolean isAssist = Intent.ACTION_ASSIST.equals(action)
            || Intent.ACTION_VOICE_COMMAND.equals(action)
            || (data != null && "nova".equalsIgnoreCase(data.getScheme()))
            || intent.getBooleanExtra("auto_listen", false);

        if (isAssist) {
            intent.setAction(Intent.ACTION_MAIN);
            intent.setData(null);
            intent.removeExtra("auto_listen");

            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (bridge != null && bridge.getWebView() != null) {
                        bridge.getWebView().evaluateJavascript(
                            "(function(){\n" +
                            "  var attempts = 0;\n" +
                            "  function tryTrigger() {\n" +
                            "    if (window.triggerAutoAssistant) {\n" +
                            "      window.triggerAutoAssistant();\n" +
                            "    } else if (attempts < 12) {\n" +
                            "      attempts++;\n" +
                            "      setTimeout(tryTrigger, 250);\n" +
                            "    }\n" +
                            "  }\n" +
                            "  setTimeout(tryTrigger, 300);\n" +
                            "})();",
                            null
                        );
                    }
                }
            });
        }
    }

    // =========================================================================
    // BỘ PHÓNG ỨNG DỤNG & TÌM KIẾM SÂU TRÊN ĐIỆN THOẠI (DEEP APP LAUNCHER)
    // =========================================================================
    private boolean launchPackage(PackageManager pm, String packageName) {
        try {
            Intent intent = pm.getLaunchIntentForPackage(packageName);
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
                startActivity(intent);
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private boolean launchTargetApp(String appName, String query) {
        if (appName == null) appName = "";
        String appClean = appName.toLowerCase().trim();
        if (query == null) query = "";
        String qClean = query.trim();

        // Xóa các từ phụ ngữ tiếng Việt
        appClean = appClean.replaceAll("^(mở|bật|vào|hãy mở|hãy bật|khởi động)\\s+", "")
                           .replaceAll("\\s+(giúp tớ|giúp tôi|hộ tớ|hộ tôi|nhé|nha|với|đi)$", "")
                           .replace("ứng dụng", "")
                           .replace("app", "")
                           .trim();

        PackageManager pm = getPackageManager();

        try {
            // 1. YouTube & Tìm kiếm bài hát / video
            if (appClean.contains("youtube") || appClean.contains("nhạc") || appClean.contains("bài hát") || appClean.contains("video")) {
                if (!qClean.isEmpty()) {
                    Intent ytSearchIntent = new Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com/results?search_query=" + Uri.encode(qClean)));
                    ytSearchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    try {
                        ytSearchIntent.setPackage("com.google.android.youtube");
                        startActivity(ytSearchIntent);
                        return true;
                    } catch (Exception ex) {
                        try {
                            ytSearchIntent.setPackage(null);
                            startActivity(ytSearchIntent);
                            return true;
                        } catch (Exception ex2) {
                            ex2.printStackTrace();
                        }
                    }
                } else {
                    String[] ytPkgs = new String[]{"com.google.android.youtube", "app.revanced.android.youtube", "com.google.android.youtube.tv", "org.schabi.newpipe"};
                    for (String pkg : ytPkgs) {
                        if (launchPackage(pm, pkg)) return true;
                    }
                    try {
                        Intent webYt = new Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com"));
                        webYt.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(webYt);
                        return true;
                    } catch (Exception ignored) {}
                }
            }

            // 2. Zalo (Hỗ trợ cả bản chính thức, bản nhân bản/clone và các biến thể)
            if (appClean.contains("zalo")) {
                String[] zaloPkgs = new String[]{"com.zing.zalo", "com.zing.zalo.play", "com.zing.zalo.app"};
                for (String pkg : zaloPkgs) {
                    if (launchPackage(pm, pkg)) return true;
                }
            }

            // 3. Facebook & Messenger
            if (appClean.contains("facebook") || appClean.contains("fb")) {
                String[] fbPkgs = new String[]{"com.facebook.katana", "com.facebook.lite"};
                for (String pkg : fbPkgs) {
                    if (launchPackage(pm, pkg)) return true;
                }
            }

            if (appClean.contains("messenger") || appClean.contains("nhắn tin")) {
                String[] msgPkgs = new String[]{"com.facebook.orca", "com.facebook.mlite"};
                for (String pkg : msgPkgs) {
                    if (launchPackage(pm, pkg)) return true;
                }
            }

            // 4. TikTok
            if (appClean.contains("tiktok") || appClean.contains("tóp tóp") || appClean.contains("top top")) {
                String[] ttPkgs = new String[]{"com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"};
                for (String pkg : ttPkgs) {
                    if (launchPackage(pm, pkg)) return true;
                }
            }

            // 5. Google Maps / Bản đồ & Chỉ đường
            if (appClean.contains("bản đồ") || appClean.contains("map") || appClean.contains("chỉ đường")) {
                Uri mapUri = qClean.isEmpty() ? Uri.parse("geo:0,0") : Uri.parse("google.navigation:q=" + Uri.encode(qClean));
                Intent mapIntent = new Intent(Intent.ACTION_VIEW, mapUri);
                mapIntent.setPackage("com.google.android.apps.maps");
                mapIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                try {
                    startActivity(mapIntent);
                    return true;
                } catch (Exception ex) {
                    Intent geoIntent = new Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0?q=" + Uri.encode(qClean)));
                    geoIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(geoIntent);
                    return true;
                }
            }

            // 6. Camera / Chụp ảnh (Mở thẳng kính ngắm chụp hình)
            if (appClean.contains("camera") || appClean.contains("chụp ảnh") || appClean.contains("máy ảnh")) {
                try {
                    Intent camIntent = new Intent("android.media.action.STILL_IMAGE_CAMERA");
                    camIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(camIntent);
                    return true;
                } catch (Exception ex) {
                    Intent camIntent2 = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                    camIntent2.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(camIntent2);
                    return true;
                }
            }

            // 7. Spotify & Trình phát nhạc
            if (appClean.contains("spotify")) {
                if (launchPackage(pm, "com.spotify.music")) return true;
            }

            // 8. Cài đặt hệ thống (Settings)
            if (appClean.contains("cài đặt") || appClean.contains("settings")) {
                Intent setIntent = new Intent(Settings.ACTION_SETTINGS);
                setIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(setIntent);
                return true;
            }

            // 9. Đồng hồ báo thức
            if (appClean.contains("đồng hồ") || appClean.contains("báo thức") || appClean.contains("clock") || appClean.contains("alarm")) {
                Intent alarmIntent = new Intent(AlarmClock.ACTION_SHOW_ALARMS);
                alarmIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(alarmIntent);
                return true;
            }

            // 10. Tìm kiếm web trên Chrome / Trình duyệt
            if (!qClean.isEmpty() && (appClean.contains("chrome") || appClean.contains("tìm kiếm") || appClean.contains("web") || appClean.contains("google"))) {
                Intent webSearch = new Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/search?q=" + Uri.encode(qClean)));
                webSearch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(webSearch);
                return true;
            } else if (appClean.contains("chrome")) {
                if (launchPackage(pm, "com.android.chrome")) return true;
            }

            // 11. Các app phổ biến khác ở Việt Nam (Shopee, Lazada, MoMo, Telegram, Instagram)
            if (appClean.contains("shopee")) { if (launchPackage(pm, "com.shopee.vn")) return true; }
            if (appClean.contains("lazada")) { if (launchPackage(pm, "com.lazada.android")) return true; }
            if (appClean.contains("momo")) { if (launchPackage(pm, "com.mservice.momopay")) return true; }
            if (appClean.contains("telegram")) { if (launchPackage(pm, "org.telegram.messenger")) return true; }
            if (appClean.contains("instagram") || appClean.contains("insta")) { if (launchPackage(pm, "com.instagram.android")) return true; }

            // 12. QUÉT TOÀN BỘ ỨNG DỤNG ĐÃ CÀI ĐẶT TRÊN MÁY QUA LAUNCHER INTENT
            Intent queryIntent = new Intent(Intent.ACTION_MAIN, null);
            queryIntent.addCategory(Intent.CATEGORY_LAUNCHER);
            List<ResolveInfo> resolveInfos = pm.queryIntentActivities(queryIntent, 0);

            for (ResolveInfo ri : resolveInfos) {
                if (ri.activityInfo == null) continue;
                String label = ri.loadLabel(pm).toString().toLowerCase();
                String pkg = ri.activityInfo.packageName.toLowerCase();

                if (label.contains(appClean) || pkg.contains(appClean)) {
                    Intent intent = pm.getLaunchIntentForPackage(ri.activityInfo.packageName);
                    if (intent == null) {
                        intent = new Intent(Intent.ACTION_MAIN);
                        intent.addCategory(Intent.CATEGORY_LAUNCHER);
                        intent.setComponent(new ComponentName(ri.activityInfo.packageName, ri.activityInfo.name));
                    }
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
                    startActivity(intent);
                    return true;
                }
            }

            // Vòng quét 2: Theo ApplicationInfo
            List<ApplicationInfo> packages = pm.getInstalledApplications(PackageManager.GET_META_DATA);
            for (ApplicationInfo packageInfo : packages) {
                String appLabel = pm.getApplicationLabel(packageInfo).toString().toLowerCase();
                String pkg = packageInfo.packageName.toLowerCase();
                if (appLabel.contains(appClean) || pkg.contains(appClean)) {
                    if (launchPackage(pm, packageInfo.packageName)) return true;
                }
            }

            // KHÔNG tự ý mở CH Play nếu app chưa cài! Trả về false để Nova báo người dùng.
            return false;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    // =========================================================================
    // BỘ THU ÂM VÀ NHẬN DIỆN GIỌNG NÓI PHẦN CỨNG NATIVE ANDROID SPEECHRECOGNIZER
    // =========================================================================
    // BỘ THU ÂM VÀ NHẬN DIỆN GIỌNG NÓI PHẦN CỨNG NATIVE ANDROID SPEECHRECOGNIZER
    // =========================================================================
    private void runOnJs(final String script) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (bridge != null && bridge.getWebView() != null) {
                    bridge.getWebView().evaluateJavascript(script, null);
                }
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == RECORD_AUDIO_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                runOnJs("if (window.onPermissionGranted) window.onPermissionGranted();");
            } else {
                runOnJs("if (window.onNativeSpeechError) window.onNativeSpeechError(9);");
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 2002) {
            if (resultCode == RESULT_OK && data != null) {
                ArrayList<String> matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
                if (matches != null && !matches.isEmpty()) {
                    String text = matches.get(0);
                    String safe = escapeForJs(text);
                    runOnJs("if (window.onNativeSpeechResult) window.onNativeSpeechResult('" + safe + "', true);");
                } else {
                    runOnJs("if (window.onNativeSpeechError) window.onNativeSpeechError(7);");
                }
            } else {
                runOnJs("if (window.onNativeSpeechError) window.onNativeSpeechError(6);");
            }
        }
    }

    private void destroyNativeRecognizer() {
        if (nativeRecognizer != null) {
            try {
                nativeRecognizer.cancel();
            } catch (Exception ignored) {}
            try {
                nativeRecognizer.destroy();
            } catch (Exception ignored) {}
            nativeRecognizer = null;
        }
        isNativeListening = false;
    }

    private void ensureNativeRecognizer() {
        if (nativeRecognizer != null) return;

        try {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                nativeRecognizer = null;
                return;
            }

            // Sử dụng SpeechRecognizer mặc định của hệ điều hành Android
            nativeRecognizer = SpeechRecognizer.createSpeechRecognizer(this);

            nativeRecognizer.setRecognitionListener(new RecognitionListener() {
                @Override
                public void onReadyForSpeech(Bundle params) {
                    isNativeListening = true;
                    runOnJs("if (window.onNativeSpeechReady) window.onNativeSpeechReady();");
                }

                @Override
                public void onBeginningOfSpeech() {
                    runOnJs("if (window.onNativeSpeechBeginning) window.onNativeSpeechBeginning();");
                }

                @Override
                public void onRmsChanged(float rmsdB) {
                    if (rmsdB > 0.0f) {
                        runOnJs("if (window.onNativeSpeechRms) window.onNativeSpeechRms(" + rmsdB + ");");
                    }
                }

                @Override
                public void onBufferReceived(byte[] buffer) {}

                @Override
                public void onEndOfSpeech() {
                    isNativeListening = false;
                    runOnJs("if (window.onNativeSpeechEnd) window.onNativeSpeechEnd();");
                }

                @Override
                public void onError(final int error) {
                    isNativeListening = false;
                    // Hủy sạch recognizer khi gặp lỗi kết nối/hệ thống để lần sau khởi tạo mới không bị kẹt
                    if (error == SpeechRecognizer.ERROR_CLIENT || 
                        error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY || 
                        error == SpeechRecognizer.ERROR_SERVER || 
                        error == SpeechRecognizer.ERROR_AUDIO) {
                        destroyNativeRecognizer();
                    }
                    runOnJs("if (window.onNativeSpeechError) window.onNativeSpeechError(" + error + ");");
                }

                @Override
                public void onResults(Bundle results) {
                    isNativeListening = false;
                    String recognizedText = "";
                    if (results != null) {
                        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                        if (matches != null && !matches.isEmpty()) {
                            recognizedText = matches.get(0);
                        }
                    }
                    String safe = escapeForJs(recognizedText);
                    runOnJs("if (window.onNativeSpeechResult) window.onNativeSpeechResult('" + safe + "', true);");
                }

                @Override
                public void onPartialResults(Bundle partialResults) {
                    if (partialResults != null) {
                        ArrayList<String> matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                        if (matches != null && !matches.isEmpty()) {
                            String partialText = matches.get(0);
                            if (partialText != null && !partialText.trim().isEmpty()) {
                                String safe = escapeForJs(partialText);
                                runOnJs("if (window.onNativeSpeechResult) window.onNativeSpeechResult('" + safe + "', false);");
                            }
                        }
                    }
                }

                @Override
                public void onEvent(int eventType, Bundle params) {}
            });
        } catch (Exception e) {
            e.printStackTrace();
            destroyNativeRecognizer();
        }
    }

    private void stopAssistantAudioInternal() {
        currentAudioRequestId.incrementAndGet();
        try {
            if (mediaPlayer != null) {
                if (mediaPlayer.isPlaying()) {
                    mediaPlayer.stop();
                }
                mediaPlayer.reset();
                mediaPlayer.release();
                mediaPlayer = null;
            }
        } catch (Exception e) {
            mediaPlayer = null;
        }
        if (currentAssetFd != null) {
            try {
                currentAssetFd.close();
            } catch (Exception ignored) {}
            currentAssetFd = null;
        }
        try {
            if (tts != null) {
                tts.stop();
            }
        } catch (Exception ignored) {}
    }

    private void stopAlarmSessionInternal() {
        try {
            NovaAlarmService.stopAlarm(MainActivity.this);
        } catch (Exception ignored) {}
    }

    private void stopAudioInternal() {
        stopAssistantAudioInternal();
    }

    private void playLocalFileInternal(final String filePath) {
        try {
            stopAudioInternal();

            mediaPlayer = new MediaPlayer();
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                mediaPlayer.setAudioAttributes(
                    new AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .build()
                );
            } else {
                mediaPlayer.setAudioStreamType(AudioManager.STREAM_MUSIC);
            }
            mediaPlayer.setVolume(1.0f, 1.0f);
            mediaPlayer.setDataSource(filePath);

            mediaPlayer.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
                @Override
                public void onPrepared(MediaPlayer mp) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        try {
                            PlaybackParams params = mp.getPlaybackParams();
                            if (params == null) {
                                params = new PlaybackParams();
                            }
                            params.setSpeed(1.10f);
                            mp.setPlaybackParams(params);
                        } catch (Exception ignored) {}
                    }
                    runOnJs("if (window.onNovaSpeechStarted) window.onNovaSpeechStarted();");
                    try {
                        mp.start();
                    } catch (Exception ex) {
                        ex.printStackTrace();
                        stopAudioInternal();
                        runOnJs("if (window.onNativeAudioFailed) window.onNativeAudioFailed(); else if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
                    }
                }
            });

            mediaPlayer.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                @Override
                public void onCompletion(MediaPlayer mp) {
                    stopAudioInternal();
                    // F-16: Xóa file audio tạm trong cache sau khi phát xong
                    if (filePath != null && filePath.contains("nova_tts_")) {
                        try {
                            new File(filePath).delete();
                        } catch (Exception ignored) {}
                    }
                    runOnJs("if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
                }
            });

            mediaPlayer.setOnErrorListener(new MediaPlayer.OnErrorListener() {
                @Override
                public boolean onError(MediaPlayer mp, int what, int extra) {
                    stopAudioInternal();
                    // F-16: Xóa file audio tạm trong cache khi gặp lỗi
                    if (filePath != null && filePath.contains("nova_tts_")) {
                        try {
                            new File(filePath).delete();
                        } catch (Exception ignored) {}
                    }
                    runOnJs("if (window.onNativeAudioFailed) window.onNativeAudioFailed(); else if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
                    return true;
                }
            });

            mediaPlayer.prepareAsync();
        } catch (Exception e) {
            e.printStackTrace();
            stopAudioInternal();
            runOnJs("if (window.onNativeAudioFailed) window.onNativeAudioFailed(); else if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
        }
    }

    // =========================================================================
    // QUẢN LÝ BÁO THỨC PHẦN CỨNG & KHÔI PHỤC SAU REBOOT (F-08, F-09, STAGE 8, P1-05)
    // =========================================================================
    public static void saveAlarmToPrefs(Context context, String reminderId, String title, long timestampMillis, int id) {
        if (reminderId == null || reminderId.isEmpty()) return;
        try {
            SharedPreferences prefs = context.getSharedPreferences("nova_alarms_store", Context.MODE_PRIVATE);
            prefs.edit()
                .putString("alarm_" + id, reminderId + "|||" + title + "|||" + timestampMillis)
                .putInt("rem_code_" + reminderId, id)
                .apply();
        } catch (Exception ignored) {}
    }

    public static void saveAlarmToPrefs(Context context, String reminderId, String title, long timestampMillis) {
        int id = ReminderId.toRequestCode(reminderId);
        saveAlarmToPrefs(context, reminderId, title, timestampMillis, id);
    }

    public static void saveAlarmToPrefs(Context context, int id, String title, long timestampMillis) {
        try {
            SharedPreferences prefs = context.getSharedPreferences("nova_alarms_store", Context.MODE_PRIVATE);
            prefs.edit().putString("alarm_" + id, String.valueOf(id) + "|||" + title + "|||" + timestampMillis).apply();
        } catch (Exception ignored) {}
    }

    public static void removeAlarmFromPrefs(Context context, int id) {
        try {
            SharedPreferences prefs = context.getSharedPreferences("nova_alarms_store", Context.MODE_PRIVATE);
            prefs.edit().remove("alarm_" + id).apply();
        } catch (Exception ignored) {}
    }

    public static void removeAlarmFromPrefs(Context context, String reminderId) {
        if (reminderId == null || reminderId.isEmpty()) return;
        try {
            SharedPreferences prefs = context.getSharedPreferences("nova_alarms_store", Context.MODE_PRIVATE);
            int id = prefs.getInt("rem_code_" + reminderId, -1);
            if (id == -1) {
                try {
                    id = Integer.parseInt(reminderId);
                } catch (NumberFormatException e) {
                    id = ReminderId.toRequestCode(reminderId);
                }
            }
            prefs.edit()
                .remove("alarm_" + id)
                .remove("rem_code_" + reminderId)
                .apply();
        } catch (Exception ignored) {}
    }

    public static boolean scheduleAlarmDirect(Context context, String reminderId, String title, long timestampMillis) {
        long nowMs = System.currentTimeMillis();
        if (timestampMillis <= 0 || timestampMillis < (nowMs - 60000L) || timestampMillis > (nowMs + 100L * 365 * 24 * 3600 * 1000L)) {
            return false;
        }

        SharedPreferences prefs = context.getSharedPreferences("nova_alarms_store", Context.MODE_PRIVATE);
        int id = ReminderId.toRequestCode(reminderId);
        int existingAssigned = prefs.getInt("rem_code_" + reminderId, -1);
        if (existingAssigned != -1) {
            id = existingAssigned;
        } else {
            String existing = prefs.getString("alarm_" + id, null);
            if (existing != null) {
                String[] parts = existing.split("\\|\\|\\|");
                if (parts.length > 0 && !reminderId.equals(parts[0])) {
                    int candidate = id;
                    for (int p = 0; p < 100; p++) {
                        candidate = (candidate + 1) & 0x7FFFFFFF;
                        String candExisting = prefs.getString("alarm_" + candidate, null);
                        if (candExisting == null) {
                            id = candidate;
                            break;
                        }
                        String[] candParts = candExisting.split("\\|\\|\\|");
                        if (candParts.length > 0 && reminderId.equals(candParts[0])) {
                            id = candidate;
                            break;
                        }
                    }
                }
            }
        }

        try {
            AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            if (alarmManager == null) return false;

            Intent intent = new Intent(context, NovaAlarmReceiver.class);
            intent.putExtra("reminder_id", reminderId);
            intent.putExtra("task_id", id);
            intent.putExtra("task_title", title);
            PendingIntent pendingIntent = PendingIntent.getBroadcast(
                context,
                id,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
            );

            boolean canExact = true;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                canExact = alarmManager.canScheduleExactAlarms();
            }

            if (canExact) {
                try {
                    Intent showIntent = new Intent(context, MainActivity.class);
                    showIntent.putExtra("auto_alarm", true);
                    showIntent.putExtra("reminder_id", reminderId);
                    showIntent.putExtra("task_title", title);
                    PendingIntent showPendingIntent = PendingIntent.getActivity(
                        context,
                        id,
                        showIntent,
                        PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
                    );
                    AlarmManager.AlarmClockInfo clockInfo = new AlarmManager.AlarmClockInfo(timestampMillis, showPendingIntent);
                    alarmManager.setAlarmClock(clockInfo, pendingIntent);
                    saveAlarmToPrefs(context, reminderId, title, timestampMillis, id);
                    return true;
                } catch (SecurityException se) {
                    Log.w("NovaAlarm", "SecurityException trên setAlarmClock, tự động fallback", se);
                }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, timestampMillis, pendingIntent);
            } else {
                alarmManager.set(AlarmManager.RTC_WAKEUP, timestampMillis, pendingIntent);
            }
            saveAlarmToPrefs(context, reminderId, title, timestampMillis, id);
            return true;
        } catch (Exception e) {
            Log.e("NovaAlarm", "Lỗi đặt báo thức canonical:", e);
            return false;
        }
    }

    public static boolean scheduleAlarmDirect(Context context, int id, String title, long timestampMillis) {
        long nowMs = System.currentTimeMillis();
        if (timestampMillis <= 0 || timestampMillis < (nowMs - 60000L) || timestampMillis > (nowMs + 100L * 365 * 24 * 3600 * 1000L)) {
            return false;
        }
        try {
            AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            if (alarmManager == null) return false;

            Intent intent = new Intent(context, NovaAlarmReceiver.class);
            intent.putExtra("task_id", id);
            intent.putExtra("task_title", title);
            PendingIntent pendingIntent = PendingIntent.getBroadcast(
                context,
                id,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
            );

            // F-08: Kiểm tra quyền canScheduleExactAlarms trên Android 12+ (API 31+) và Android 14+ (API 34+)
            boolean canExact = true;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                canExact = alarmManager.canScheduleExactAlarms();
            }

            if (canExact) {
                try {
                    Intent showIntent = new Intent(context, MainActivity.class);
                    showIntent.putExtra("auto_alarm", true);
                    showIntent.putExtra("task_title", title);
                    PendingIntent showPendingIntent = PendingIntent.getActivity(
                        context,
                        id,
                        showIntent,
                        PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
                    );
                    AlarmManager.AlarmClockInfo clockInfo = new AlarmManager.AlarmClockInfo(timestampMillis, showPendingIntent);
                    alarmManager.setAlarmClock(clockInfo, pendingIntent);
                    saveAlarmToPrefs(context, id, title, timestampMillis);
                    return true;
                } catch (SecurityException se) {
                    Log.w("NovaAlarm", "SecurityException trên setAlarmClock, tự động fallback sang setAndAllowWhileIdle", se);
                }
            }

            // Fallback an toàn nếu không có quyền exact alarm
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, timestampMillis, pendingIntent);
            } else {
                alarmManager.set(AlarmManager.RTC_WAKEUP, timestampMillis, pendingIntent);
            }
            saveAlarmToPrefs(context, id, title, timestampMillis);
            return true;
        } catch (Exception e) {
            Log.e("NovaAlarm", "Lỗi đặt báo thức:", e);
            return false;
        }
    }

    public static void cancelAlarmDirect(Context context, int id) {
        try {
            AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            if (alarmManager != null) {
                Intent intent = new Intent(context, NovaAlarmReceiver.class);
                PendingIntent pendingIntent = PendingIntent.getBroadcast(
                    context,
                    id,
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
                );
                alarmManager.cancel(pendingIntent);
            }
            removeAlarmFromPrefs(context, id);
        } catch (Exception e) {
            Log.e("NovaAlarm", "Lỗi hủy báo thức:", e);
        }
    }

    private void cleanOldAudioCache() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    File cacheDir = getCacheDir();
                    if (cacheDir != null && cacheDir.exists()) {
                        File[] files = cacheDir.listFiles();
                        if (files != null) {
                            long now = System.currentTimeMillis();
                            for (File f : files) {
                                if (f.getName().startsWith("nova_tts_") && (now - f.lastModified() > 1800000L)) {
                                    f.delete();
                                }
                            }
                        }
                    }
                } catch (Exception ignored) {}
            }
        }).start();
    }

    private void dispatchAudioEvent(final String requestId, final String event) {
        final String req = requestId != null ? escapeForJs(requestId) : "";
        final String ev = escapeForJs(event);
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                runOnJs("if (window.onNovaAudioEvent) window.onNovaAudioEvent('" + req + "', '" + ev + "');");
                // Invariant: Legacy global callbacks are allowed ONLY for no-request-ID compatibility.
                // For non-empty requestId, emit ONLY onNovaAudioEvent(requestId, event).
                if (req.isEmpty()) {
                    if ("started".equals(ev)) {
                        runOnJs("if (window.onNovaSpeechStarted) window.onNovaSpeechStarted();");
                    } else if ("completed".equals(ev)) {
                        runOnJs("if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
                    } else if ("failed".equals(ev)) {
                        runOnJs("if (window.onNativeAudioFailed) window.onNativeAudioFailed(); else if (window.onNovaSpeechEnded) window.onNovaSpeechEnded();");
                    }
                }
            }
        });
    }

    private void playAudioUrlInternal(final String url) {
        playAudioUrlInternal("", url);
    }

    private void playAudioUrlInternal(final String requestId, final String url) {
        if (url == null || url.trim().isEmpty()) {
            dispatchAudioEvent(requestId, "completed");
            return;
        }

        try {
            stopAudioInternal();
            final long reqId = currentAudioRequestId.get();

            if (url.startsWith("file:///android_asset/")) {
                // 1. Phục vụ các file âm thanh giọng phòng thu Bundled sẵn trong APK
                String assetPath = url.substring("file:///android_asset/".length());
                currentAssetFd = getAssets().openFd(assetPath);

                mediaPlayer = new MediaPlayer();
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    mediaPlayer.setAudioAttributes(
                        new AudioAttributes.Builder()
                            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .build()
                    );
                } else {
                    mediaPlayer.setAudioStreamType(AudioManager.STREAM_MUSIC);
                }
                mediaPlayer.setVolume(1.0f, 1.0f);
                mediaPlayer.setDataSource(currentAssetFd.getFileDescriptor(), currentAssetFd.getStartOffset(), currentAssetFd.getLength());

                mediaPlayer.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
                    @Override
                    public void onPrepared(MediaPlayer mp) {
                        if (reqId != currentAudioRequestId.get()) {
                            stopAudioInternal();
                            dispatchAudioEvent(requestId, "cancelled");
                            return;
                        }
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                            try {
                                PlaybackParams params = mp.getPlaybackParams();
                                if (params == null) {
                                    params = new PlaybackParams();
                                }
                                params.setSpeed(1.10f);
                                mp.setPlaybackParams(params);
                            } catch (Exception ignored) {}
                        }
                        dispatchAudioEvent(requestId, "started");
                        try {
                            mp.start();
                        } catch (Exception ex) {
                            ex.printStackTrace();
                            stopAudioInternal();
                            dispatchAudioEvent(requestId, "failed");
                        }
                    }
                });

                mediaPlayer.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                    @Override
                    public void onCompletion(MediaPlayer mp) {
                        if (reqId != currentAudioRequestId.get()) return;
                        stopAudioInternal();
                        dispatchAudioEvent(requestId, "completed");
                    }
                });

                mediaPlayer.setOnErrorListener(new MediaPlayer.OnErrorListener() {
                    @Override
                    public boolean onError(MediaPlayer mp, int what, int extra) {
                        if (reqId != currentAudioRequestId.get()) return true;
                        stopAudioInternal();
                        dispatchAudioEvent(requestId, "failed");
                        return true;
                    }
                });

                mediaPlayer.prepareAsync();
            } else if (url.startsWith("http://") || url.startsWith("https://")) {
                // 2. Progressive Streaming trực tiếp qua MediaPlayer không chặn đợi tải toàn bộ file
                mediaPlayer = new MediaPlayer();
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    mediaPlayer.setAudioAttributes(
                        new AudioAttributes.Builder()
                            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .build()
                    );
                } else {
                    mediaPlayer.setAudioStreamType(AudioManager.STREAM_MUSIC);
                }
                mediaPlayer.setVolume(1.0f, 1.0f);

                Map<String, String> headers = new HashMap<>();
                headers.put("User-Agent", "Mozilla/5.0 (Linux; Android 12; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36");
                mediaPlayer.setDataSource(MainActivity.this, Uri.parse(url), headers);

                mediaPlayer.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
                    @Override
                    public void onPrepared(MediaPlayer mp) {
                        if (reqId != currentAudioRequestId.get()) {
                            stopAudioInternal();
                            dispatchAudioEvent(requestId, "cancelled");
                            return;
                        }
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                            try {
                                PlaybackParams params = mp.getPlaybackParams();
                                if (params == null) {
                                    params = new PlaybackParams();
                                }
                                params.setSpeed(1.10f);
                                mp.setPlaybackParams(params);
                            } catch (Exception ignored) {}
                        }
                        dispatchAudioEvent(requestId, "started");
                        try {
                            mp.start();
                        } catch (Exception ex) {
                            ex.printStackTrace();
                            stopAudioInternal();
                            dispatchAudioEvent(requestId, "failed");
                        }
                    }
                });

                mediaPlayer.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                    @Override
                    public void onCompletion(MediaPlayer mp) {
                        if (reqId != currentAudioRequestId.get()) return;
                        stopAudioInternal();
                        dispatchAudioEvent(requestId, "completed");
                    }
                });

                mediaPlayer.setOnErrorListener(new MediaPlayer.OnErrorListener() {
                    @Override
                    public boolean onError(MediaPlayer mp, int what, int extra) {
                        if (reqId != currentAudioRequestId.get()) return true;
                        stopAudioInternal();
                        dispatchAudioEvent(requestId, "failed");
                        return true;
                    }
                });

                mediaPlayer.prepareAsync();
            } else {
                // 3. File cục bộ trên máy
                playLocalFileInternal(url);
            }
        } catch (Exception e) {
            e.printStackTrace();
            stopAudioInternal();
            dispatchAudioEvent(requestId, "failed");
        }
    }

    private void startNativeSpeechInternal() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.MODIFY_AUDIO_SETTINGS
            }, RECORD_AUDIO_REQUEST_CODE);
            runOnJs("if (window.onNativeSpeechError) window.onNativeSpeechError(9);");
            return;
        }

        try {
            ensureNativeRecognizer();

            if (nativeRecognizer == null) {
                runOnJs("if (window.onNativeSpeechError) window.onNativeSpeechError(-1);");
                return;
            }

            // Hủy phiên cũ an toàn trước khi start session mới
            try {
                nativeRecognizer.cancel();
            } catch (Exception ignored) {}

            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "vi-VN");
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "vi-VN");
            intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, getPackageName());
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
            intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 3000L);
            intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 2400L);
            intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 2200L);

            isNativeListening = true;
            nativeRecognizer.startListening(intent);
        } catch (Exception e) {
            e.printStackTrace();
            destroyNativeRecognizer();
            runOnJs("if (window.onNativeSpeechError) window.onNativeSpeechError(-1);");
        }
    }

    private void startSpeechPromptInternal() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                // Đã loại bỏ hoàn toàn cơ chế Fallback Google Voice Dialog popup.
                // Chuyển thẳng sang Native Speech in-app của Nova.
                startNativeSpeechInternal();
            }
        });
    }

    private void stopNativeSpeechInternal() {
        try {
            if (nativeRecognizer != null) {
                nativeRecognizer.cancel();
            }
            isNativeListening = false;
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private String escapeForJs(String str) {
        if (str == null) return "";
        return str.replace("\\", "\\\\")
                  .replace("'", "\\'")
                  .replace("\"", "\\\"")
                  .replace("\r", " ")
                  .replace("\n", " ");
    }

    @Override
    public void onPause() {
        stopNativeSpeechInternal();
        super.onPause();
    }

    @Override
    public void onDestroy() {
        stopAudioInternal();
        if (tts != null) {
            try {
                tts.stop();
                tts.shutdown();
            } catch (Exception ignored) {}
        }
        if (nativeRecognizer != null) {
            try {
                nativeRecognizer.cancel();
                nativeRecognizer.destroy();
            } catch (Exception ignored) {}
            nativeRecognizer = null;
        }
        super.onDestroy();
    }
}
