import os, time, sys
from pathlib import Path
import soundfile as sf

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

print("--- Testing VieNeu v3 Turbo with Cuppy Reference WAV ---")
from vieneu import Vieneu

t0 = time.time()
print("Initializing Vieneu(mode='v3turbo')...")
tts = Vieneu(mode="v3turbo")
print(f"Vieneu initialized in {time.time() - t0:.2f}s!")

ref_wav = os.getenv("CUPPY_REFERENCE_WAV", str(Path(__file__).parent.parent / "data" / "voices" / "cuppy_sample.wav"))
if not Path(ref_wav).exists():
    fallback_win = r"C:\Users\Lenovo\AppData\Local\WTStudio\saydi-tts-service\cuppy_sample_8_12s.wav"
    if Path(fallback_win).exists():
        ref_wav = fallback_win
t1 = time.time()
print(f"Registering voice 'cuppy' from {ref_wav}...")
tts.add_voice("cuppy", ref_wav, denoise=True)
print(f"Voice registered in {time.time() - t1:.2f}s!")

t2 = time.time()
print("Inferring test phrase: 'Chào cậu, tớ là Nova đây.'...")
wav = tts.infer("Chào cậu, tớ là Nova đây.", voice="cuppy")
print(f"Inference finished in {time.time() - t2:.2f}s!")

out_path = Path("test_direct_cuppy.wav")
sf.write(str(out_path), wav, 48000)
print(f"Written output to {out_path}, size: {out_path.stat().st_size} bytes!")
