"""StudyGuard — Real-Time AI Meme Detector for Study Habits and Hydration.

Detects:
1. Book Reading -> Book Closing: plays "E:\\Hand Gesture Recognition\\meme audios\\kyu-nahi-ho-rahi-padhai.mp3"
2. Phone Usage after keeping book: plays "E:\\Hand Gesture Recognition\\meme audios\\abeyy-padhai-likhai-karo.mp3"
3. Drinking Water (Bottle/Cup to mouth): plays "E:\\Hand Gesture Recognition\\meme audios\\pani pani.mp3"
"""

from __future__ import annotations
import os
import sys
import time
import argparse
import numpy as np
import cv2

# Add GestureOS to path for shared vision components
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GESTUREOS_DIR = os.path.join(BASE_DIR, "GestureOS")
if GESTUREOS_DIR not in sys.path:
    sys.path.insert(0, GESTUREOS_DIR)

from app.vision.meme_audio_player import MemeAudioPlayer
from app.vision.study_detector import StudyVisionDetector, StudyDetectionResult
from app.vision.study_state_machine import StudyStateMachine, StudyState


class StudyGuardApp:
    """Production StudyGuard desktop application with camera capture and real-time HUD."""

    def __init__(self, camera_index: int = 0, simulation: bool = False, muted: bool = False) -> None:
        self.camera_index = camera_index
        self.simulation = simulation
        self.muted = muted

        print("======================================================================")
        print("                STUDYGUARD AI MEME MONITORING SYSTEM                  ")
        print("======================================================================")
        print(f"[*] Base Directory: {BASE_DIR}")
        print(f"[*] Simulation Mode: {self.simulation}")

        # Initialize audio player
        self.audio_player = MemeAudioPlayer(muted=self.muted)
        print(f"[*] Audio Player Initialized:")
        print(f"    - Book Close:  {os.path.basename(self.audio_player.kyu_nahi_path)}")
        print(f"    - Phone Alert: {os.path.basename(self.audio_player.abeyy_path)}")
        print(f"    - Water Alert: {os.path.basename(self.audio_player.pani_pani_path)}")

        # Initialize vision detector
        print("[*] Loading MediaPipe Vision Detectors...")
        self.detector = StudyVisionDetector()

        # Initialize state machine
        self.state_machine = StudyStateMachine(
            audio_player=self.audio_player,
            book_absence_sec=0.8,
            phone_cooldown_sec=7.0,
            drinking_cooldown_sec=7.0,
            book_closed_cooldown_sec=7.0,
        )

        self.cap: Optional[cv2.VideoCapture] = None
        self._sim_cycle_step: int = 0
        self._sim_auto_demo: bool = self.simulation
        self._last_fps_calc = time.time()
        self._fps: float = 30.0

    def start_camera(self) -> bool:
        """Attempts to open real camera; falls back to simulation mode if unavailable."""
        if not self.simulation:
            print(f"[*] Opening webcam index {self.camera_index}...")
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
            if not self.cap.isOpened():
                print(f"[!] Could not access webcam {self.camera_index}. Switching to Simulation Mode.")
                self.simulation = True
                self._sim_auto_demo = True
            else:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                print("[+] Webcam stream opened successfully!")
        return True

    def run(self) -> None:
        """Main execution loop displaying camera feed and overlaying HUD."""
        self.start_camera()
        window_title = "StudyGuard — AI Meme Monitor (Press 'Q' to quit)"
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 1280, 720)

        frame_count = 0
        t_start = time.time()

        try:
            while True:
                t_frame_start = time.time()

                # 1. Fetch frame
                if not self.simulation and self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        # Temporary frame drop or camera disconnect
                        frame = self._generate_simulated_frame()
                else:
                    frame = self._generate_simulated_frame()

                h, w = frame.shape[:2]

                # 2. Vision Inference
                result = self.detector.detect(frame)

                # 3. State Machine Update
                current_state = self.state_machine.update(result)

                # 4. Render HUD
                annotated = self._render_hud(frame, result, current_state)

                # 5. Calculate FPS
                frame_count += 1
                if frame_count % 15 == 0:
                    elapsed = time.time() - self._last_fps_calc
                    self._fps = 15.0 / max(0.001, elapsed)
                    self._last_fps_calc = time.time()

                cv2.imshow(window_title, annotated)

                # 6. Key Handlers
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), ord('Q'), 27):  # Q or ESC
                    print("[*] Exit requested by user.")
                    break
                elif key in (ord('b'), ord('B')):
                    print("[Hotkey] Triggering Book Reading...")
                    self.state_machine.trigger_manual_book_read()
                elif key in (ord('c'), ord('C')):
                    print("[Hotkey] Triggering Book Closing -> Playing 'Kyu nahi ho rahi padhai'...")
                    self.state_machine.trigger_manual_book_close()
                elif key in (ord('p'), ord('P')):
                    print("[Hotkey] Triggering Phone Distraction -> Playing 'Abeyy padhai likhai karo'...")
                    self.state_machine.trigger_manual_phone_distraction()
                elif key in (ord('w'), ord('W')):
                    print("[Hotkey] Triggering Drinking Water -> Playing 'Pani pani'...")
                    self.state_machine.trigger_manual_drinking()
                elif key in (ord('r'), ord('R')):
                    print("[Hotkey] Resetting session...")
                    self.state_machine.reset_session()
                elif key in (ord('m'), ord('M')):
                    is_muted = self.audio_player.toggle_mute()
                    print(f"[Hotkey] Audio Mute Toggled: {'MUTED' if is_muted else 'UNMUTED'}")
                elif key in (ord('s'), ord('S')):
                    self._sim_auto_demo = not self._sim_auto_demo
                    print(f"[Hotkey] Auto-Demo Simulation: {self._sim_auto_demo}")

        finally:
            self._cleanup()
            cv2.destroyAllWindows()

    def _cleanup(self) -> None:
        """Releases camera and audio resources."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.audio_player.stop()
        print("[+] StudyGuard exited cleanly.")

    def _render_hud(self, frame: np.ndarray, res: StudyDetectionResult, state: StudyState) -> np.ndarray:
        """Renders rich HUD annotations, bounding boxes, state cards, and meme alert banners."""
        img = frame.copy()
        h, w = img.shape[:2]

        # Draw Face and Mouth Landmark
        if res.face_detected and res.face_box:
            fx1, fy1, fx2, fy2 = res.face_box
            cv2.rectangle(img, (fx1, fy1), (fx2, fy2), (180, 105, 255), 2)  # Soft Purple
            cv2.putText(img, "FACE", (fx1, max(15, fy1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 105, 255), 1)

            if res.mouth_point:
                mx, my = res.mouth_point
                cv2.circle(img, (mx, my), 5, (255, 105, 180), -1)

        # Draw Book Box
        if res.book_detected and res.book_box:
            bx1, by1, bx2, by2 = res.book_box
            cv2.rectangle(img, (bx1, by1), (bx2, by2), (0, 220, 100), 3)  # Bright Emerald
            cv2.putText(
                img,
                f"BOOK: {int(res.book_score * 100)}%",
                (bx1, max(20, by1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 220, 100),
                2,
            )

        # Draw Phone Box
        if res.phone_detected and res.phone_box:
            px1, py1, px2, py2 = res.phone_box
            cv2.rectangle(img, (px1, py1), (px2, py2), (50, 50, 255), 3)  # Crimson Red
            cv2.putText(
                img,
                f"PHONE: {int(res.phone_score * 100)}%",
                (px1, max(20, py1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (50, 50, 255),
                2,
            )

        # Draw Container (Bottle/Cup) Box
        if res.container_detected and res.container_box:
            cx1, cy1, cx2, cy2 = res.container_box
            color = (255, 220, 0) if res.is_drinking else (230, 180, 50)  # Cyan
            cv2.rectangle(img, (cx1, cy1), (cx2, cy2), color, 3 if res.is_drinking else 2)
            label = f"{res.container_label.upper()}: {int(res.container_score * 100)}%"
            if res.is_drinking:
                label += " [DRINKING!]"
            cv2.putText(img, label, (cx1, max(20, cy1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Draw trajectory link to mouth if drinking
            if res.is_drinking and res.mouth_point:
                mx, my = res.mouth_point
                cont_top = (int((cx1 + cx2) / 2), cy1)
                cv2.line(img, cont_top, (mx, my), (255, 255, 0), 2, cv2.LINE_AA)

        # Top Header Bar (Semi-transparent dark strip)
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 75), (20, 22, 28), -1)
        cv2.rectangle(overlay, (0, h - 50), (w, h), (20, 22, 28), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        # App Title & Badges
        cv2.putText(img, "STUDYGUARD", (20, 32), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(img, "AI Meme Distraction & Hydration Monitor", (20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 170, 185), 1)

        # State Badge Color and Label
        state_colors = {
            StudyState.IDLE: (140, 150, 160),
            StudyState.READING_BOOK: (0, 220, 100),
            StudyState.BOOK_CLOSED: (0, 180, 255),
            StudyState.PHONE_DISTRACTED: (50, 50, 255),
            StudyState.DRINKING_WATER: (255, 220, 0),
        }
        color = state_colors.get(state, (200, 200, 200))

        # Draw State Pill
        badge_text = f"STATE: {state.value}"
        cv2.rectangle(img, (w - 380, 14), (w - 20, 60), color, 2)
        cv2.putText(img, badge_text, (w - 365, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(img, self.state_machine.status_message[:40], (w - 365, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Flashing Center Alert Banner if a meme is triggered
        if self.state_machine.recent_alert:
            banner_text = self.state_machine.recent_alert
            # Draw glowing centered banner
            banner_w = min(w - 60, len(banner_text) * 16 + 60)
            bx1 = (w - banner_w) // 2
            bx2 = bx1 + banner_w
            by1 = 90
            by2 = 145

            # Outer glow
            cv2.rectangle(img, (bx1, by1), (bx2, by2), (25, 25, 30), -1)
            cv2.rectangle(img, (bx1, by1), (bx2, by2), (0, 215, 255), 3)
            cv2.putText(
                img,
                banner_text,
                (bx1 + 25, by1 + 35),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (0, 240, 255),
                2,
                cv2.LINE_AA,
            )

        # Bottom Bar: Stats and Controls
        stats_text = (
            f"Read Time: {int(self.state_machine.total_reading_time)}s | "
            f"Distractions: {self.state_machine.distraction_count} | "
            f"Waters Drank: {self.state_machine.drinking_count} | "
            f"FPS: {self._fps:.1f}"
        )
        if self.audio_player.muted:
            stats_text += " | [AUDIO MUTED]"
        else:
            stats_text += f" | Last Audio: {self.audio_player.last_played}"

        cv2.putText(img, stats_text, (20, h - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 230, 240), 1)

        ctrl_text = "[B] Read Book | [C] Close Book | [P] Phone | [W] Water | [M] Mute | [R] Reset | [Q] Quit"
        cv2.putText(img, ctrl_text, (20, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (130, 140, 160), 1)

        return img

    def _generate_simulated_frame(self) -> np.ndarray:
        """Generates dynamic simulation frame demonstrating reading, book closing, phone, and drinking."""
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Gradient background
        for y in range(720):
            frame[y, :] = (int(30 + 15 * (y / 720)), int(32 + 10 * (y / 720)), int(38 + 5 * (y / 720)))

        # Draw desk
        cv2.rectangle(frame, (0, 480), (1280, 720), (50, 45, 40), -1)
        cv2.line(frame, (0, 480), (1280, 480), (80, 70, 60), 2)

        # Draw Person silhouette
        cv2.circle(frame, (640, 250), 85, (120, 110, 130), -1)  # Head
        cv2.ellipse(frame, (640, 480), (180, 140), 0, 0, 360, (90, 85, 110), -1)  # Torso

        # Simulation Demo cycle
        if self._sim_auto_demo:
            t = time.time() % 24  # 24-second cycle
            if t < 7.0:
                # Phase 1: Reading Book
                cv2.rectangle(frame, (510, 430), (770, 570), (220, 220, 230), -1)
                cv2.rectangle(frame, (510, 430), (770, 570), (40, 40, 40), 2)
                cv2.line(frame, (640, 430), (640, 570), (100, 100, 100), 2)
                cv2.putText(frame, "SIMULATED OPEN BOOK", (530, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1)
            elif t < 10.0:
                # Phase 2: Book Closed / Kept away (Empty desk)
                cv2.putText(frame, "[Book Closed & Kept Away]", (520, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
            elif t < 16.0:
                # Phase 3: Phone Picked Up & In Use
                cv2.rectangle(frame, (600, 340), (680, 470), (30, 30, 35), -1)
                cv2.rectangle(frame, (605, 345), (675, 465), (70, 130, 240), -1)
                cv2.rectangle(frame, (600, 340), (680, 470), (200, 200, 200), 2)
                cv2.putText(frame, "PHONE", (612, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            else:
                # Phase 4: Drinking Water
                cv2.rectangle(frame, (615, 240), (665, 350), (200, 230, 255), -1)
                cv2.rectangle(frame, (615, 240), (665, 350), (0, 180, 240), 2)
                cv2.circle(frame, (640, 235), 15, (0, 180, 240), -1)
                cv2.putText(frame, "WATER", (618, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (10, 10, 10), 1)

        return frame


def main():
    parser = argparse.ArgumentParser(description="StudyGuard — AI Meme Distraction & Hydration Monitor")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default 0)")
    parser.add_argument("--simulation", action="store_true", help="Launch in simulation test mode without hardware webcam")
    parser.add_argument("--muted", action="store_true", help="Start with audio muted")
    args = parser.parse_args()

    app = StudyGuardApp(camera_index=args.camera, simulation=args.simulation, muted=args.muted)
    app.run()


if __name__ == "__main__":
    main()
