package com.nova.assistant;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;

public class NovaVoiceInteractionSession extends VoiceInteractionSession {
    public NovaVoiceInteractionSession(Context context) {
        super(context);
    }

    @Override
    public void onShow(Bundle args, int showFlags) {
        super.onShow(args, showFlags);
        // Khi người dùng nhấn giữ nút nguồn hoặc vuốt góc màn hình:
        // Khởi động giao diện chính của Nova và kích hoạt mở mic tức thì!
        try {
            Intent intent = new Intent(getContext(), MainActivity.class);
            intent.setAction(Intent.ACTION_ASSIST);
            intent.putExtra("auto_listen", true);
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                startAssistantActivity(intent);
            } else {
                getContext().startActivity(intent);
            }
        } catch (Exception e) {
            try {
                Intent intent = new Intent(getContext(), MainActivity.class);
                intent.setAction(Intent.ACTION_ASSIST);
                intent.putExtra("auto_listen", true);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(intent);
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        }
        hide();
    }
}
