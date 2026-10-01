import sys
import os
import time
from pathlib import Path
import soundfile as sf

SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.vieneu_cuppy import cuppy_engine

TEST_PHRASES = [
    "Chào cậu, tớ là Nova đây.",
    "Mở YouTube rồi đó, cấm lướt linh tinh đấy.",
    "Hôm nay cậu muốn mình giúp gì nào?",
    "Tớ đã đặt lời nhắc cho cậu vào tám giờ tối.",
    "Ngày mai nhớ mang theo ô nhé."
]

def run_evaluation():
    print("=" * 70)
    print("NOVA ASSISTANT - CUPPY VOICE CLONE EVALUATION SUITE")
    print("=" * 70)
    
    health = cuppy_engine.get_health()
    print(f"Health Status      : {health.get('status')}")
    print(f"Model Loaded       : {health.get('model_loaded')}")
    print(f"Voice Loaded       : {health.get('voice_loaded')}")
    print(f"Voice Source       : {health.get('voice_source')}")
    print(f"Reference Duration : {health.get('reference_duration')}s")
    print("-" * 70)
    
    results = []
    
    for idx, phrase in enumerate(TEST_PHRASES, 1):
        print(f"\n[Test {idx}/6] Text: \"{phrase}\"")
        t0 = time.time()
        wav_path = cuppy_engine.synthesize(phrase)
        elapsed = time.time() - t0
        
        if wav_path and wav_path.exists():
            size = wav_path.stat().st_size
            info = sf.info(str(wav_path))
            print(f"  -> Generated: {wav_path.name}")
            print(f"  -> Size: {size:,} bytes | Duration: {info.duration:.2f}s | Infer Time: {elapsed:.2f}s")
            results.append({
                "idx": idx,
                "phrase": phrase,
                "path": str(wav_path),
                "duration": info.duration,
                "infer_time": elapsed,
                "status": "PASS"
            })
        else:
            print("  -> FAILED to synthesize!")
            results.append({
                "idx": idx,
                "phrase": phrase,
                "status": "FAIL"
            })
            
    print("\n" + "=" * 70)
    print("SUMMARY RESULTS:")
    print("=" * 70)
    for r in results:
        if r["status"] == "PASS":
            print(f"[{r['idx']}/5] PASS | {r['infer_time']:.2f}s | {r['duration']:.2f}s audio | {r['phrase']}")
        else:
            print(f"[{r['idx']}/5] FAIL | {r['phrase']}")
            
    all_passed = all(r["status"] == "PASS" for r in results)
    print(f"\nOVERALL RESULT: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
