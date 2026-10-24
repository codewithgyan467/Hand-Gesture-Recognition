"""StudyGuard — Unified AI Meme Distraction & Hydration Monitor + GestureOS Touchless Mouse.

Single unified application window featuring:
1. Touchless AI mouse and gesture controls
2. Real-time StudyGuard Meme Monitor with Header ON/OFF Switch:
   - Book Closing: plays "E:\\Hand Gesture Recognition\\meme audios\\kyu-nahi-ho-rahi-padhai.mp3"
   - Phone Distraction after Book: plays "E:\\Hand Gesture Recognition\\meme audios\\abeyy-padhai-likhai-karo.mp3"
   - Drinking Water: plays "E:\\Hand Gesture Recognition\\meme audios\\pani pani.mp3"
"""

from __future__ import annotations
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GESTUREOS_DIR = os.path.join(BASE_DIR, "GestureOS")
if GESTUREOS_DIR not in sys.path:
    sys.path.insert(0, GESTUREOS_DIR)

from run_gestureos import main as run_unified_app

if __name__ == "__main__":
    # Ensure --study-guard is passed so the unified window starts with Study Guard enabled
    if "--study-guard" not in sys.argv and "--study" not in sys.argv:
        sys.argv.append("--study-guard")
    sys.exit(run_unified_app())
