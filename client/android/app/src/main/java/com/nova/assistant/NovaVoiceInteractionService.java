package com.nova.assistant;

import android.content.ComponentName;
import android.content.Context;
import android.os.Bundle;
import android.service.voice.VoiceInteractionService;
import android.service.voice.VoiceInteractionSession;
import android.util.Log;

/**
 * V4-06: Trợ lý kỹ thuật số mặc định của hệ thống Android (Default Assistant)
 * Triển khai đầy đủ lifecycle: onReady, onShutdown, onLaunchVoiceAssistFromKeyguard,
 * onPrepareToShowSession, onShowSessionFailed, isActiveService.
 */
public class NovaVoiceInteractionService extends VoiceInteractionService {
    private static final String TAG = "NovaVoiceInteraction";

    @Override
    public void onReady() {
        super.onReady();
        Log.i(TAG, "NovaVoiceInteractionService is ready and active as default assistant.");
    }

    @Override
    public void onShutdown() {
        super.onShutdown();
        Log.i(TAG, "NovaVoiceInteractionService has shut down.");
    }

    @Override
    public void onLaunchVoiceAssistFromKeyguard() {
        super.onLaunchVoiceAssistFromKeyguard();
        Log.i(TAG, "onLaunchVoiceAssistFromKeyguard triggered.");
        try {
            showSession(new Bundle(), VoiceInteractionSession.SHOW_SOURCE_ASSIST_GESTURE);
        } catch (Exception e) {
            Log.e(TAG, "Failed to showSession from keyguard", e);
        }
    }

    @Override
    public void onPrepareToShowSession(Bundle args, int showFlags) {
        super.onPrepareToShowSession(args, showFlags);
        Log.d(TAG, "onPrepareToShowSession flags: " + showFlags);
    }

    @Override
    public void onShowSessionFailed(Bundle args) {
        super.onShowSessionFailed(args);
        Log.w(TAG, "onShowSessionFailed triggered.");
    }

    /**
     * Kiểm tra chính xác Nova có đang được chọn làm Default Digital Assistant không
     */
    public static boolean isActiveService(Context context) {
        if (context == null) return false;
        try {
            ComponentName serviceComponent = new ComponentName(context, NovaVoiceInteractionService.class);
            return VoiceInteractionService.isActiveService(context, serviceComponent);
        } catch (Exception e) {
            Log.w(TAG, "Failed to check isActiveService: " + e.getMessage());
            return false;
        }
    }
}
