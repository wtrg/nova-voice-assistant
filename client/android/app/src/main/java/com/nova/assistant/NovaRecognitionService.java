package com.nova.assistant;

import android.content.Intent;
import android.speech.RecognitionService;
import android.speech.SpeechRecognizer;

/**
 * Dịch vụ nhận dạng giọng nói tích hợp hệ thống Android (F-10)
 * Phản hồi callback rõ ràng, không để luồng bị treo vĩnh viễn.
 */
public class NovaRecognitionService extends RecognitionService {
    @Override
    protected void onStartListening(Intent recognizerIntent, Callback listener) {
        if (listener != null) {
            try {
                // Phản hồi lỗi client rõ ràng nếu gọi trực tiếp qua service binder thay vì MainActivity
                listener.error(SpeechRecognizer.ERROR_CLIENT);
            } catch (Exception ignored) {}
        }
    }

    @Override
    protected void onCancel(Callback listener) {
        // Hủy an toàn không gây exception
    }

    @Override
    protected void onStopListening(Callback listener) {
        if (listener != null) {
            try {
                listener.endOfSpeech();
            } catch (Exception ignored) {}
        }
    }
}
