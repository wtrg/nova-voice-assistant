import sys
import os
from pathlib import Path
import soundfile as sf
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def inspect_voice(file_path: str):
    p = Path(file_path)
    print("=" * 60)
    print("NOVA ASSISTANT - VOICE REFERENCE INSPECTOR")
    print("=" * 60)
    print(f"Target Path    : {p.resolve()}")
    
    if not p.exists():
        print(f"[ERROR] File does not exist: {p}")
        return False
        
    file_size = p.stat().st_size
    print(f"File Size      : {file_size:,} bytes ({file_size / 1024:.2f} KB)")
    
    try:
        info = sf.info(str(p))
        print(f"Format         : {info.format}")
        print(f"Subtype        : {info.subtype}")
        print(f"Channels       : {info.channels} ({'Mono' if info.channels == 1 else 'Stereo' if info.channels == 2 else 'Multi-channel'})")
        print(f"Sample Rate    : {info.samplerate} Hz")
        print(f"Duration       : {info.duration:.3f} seconds")
        print(f"Frames         : {info.frames:,}")
        
        # Read audio to check signal quality
        data, sr = sf.read(str(p))
        if data.ndim > 1:
            peak = float(np.max(np.abs(data)))
            rms = float(np.sqrt(np.mean(data**2)))
        else:
            peak = float(np.max(np.abs(data)))
            rms = float(np.sqrt(np.mean(data**2)))
            
        print(f"Peak Amplitude : {peak:.4f} ({'OK' if peak <= 1.0 else 'CLIPPING'})")
        print(f"RMS Energy     : {rms:.4f}")
        
        # Validation checks
        issues = []
        if info.duration < 1.0:
            issues.append("Warning: Audio duration is very short (< 1.0s). Recommend 3 - 12s.")
        elif info.duration > 30.0:
            issues.append("Warning: Audio duration is quite long (> 30s).")
            
        if peak < 0.05:
            issues.append("Warning: Audio signal is very quiet.")
            
        if issues:
            print("\n[VALIDATION WARNINGS]:")
            for iss in issues:
                print(f" - {iss}")
        else:
            print("\n[VALIDATION]: File is healthy and ready for voice cloning.")
            
        return True
    except Exception as e:
        print(f"[ERROR] Failed to read audio with soundfile: {e}")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/Lenovo/AppData/Local/WTStudio/saydi-tts-service/cuppy_sample_8_12s.wav"
    success = inspect_voice(target)
    sys.exit(0 if success else 1)
