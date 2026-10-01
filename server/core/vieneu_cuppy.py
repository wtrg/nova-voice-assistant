"""
Module tương thích ngược cho CuppyNeuralTTS trỏ về NovaNeuralTTS (Giọng Xuân Tiên).
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.vieneu_engine import NovaNeuralTTS, nova_engine

# Alias để bảo đảm 100% tương thích ngược với các file import cũ
CuppyNeuralTTS = NovaNeuralTTS
cuppy_engine = nova_engine
