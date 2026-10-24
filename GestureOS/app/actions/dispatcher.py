"""Action Dispatcher routing validated ActionIntents to the active Platform Controller with safety enforcement."""

from __future__ import annotations
import time
from typing import Optional
from app.core.types import ActionIntent, IntentType
from app.platform.base_controller import BaseOSController
from app.core.state_machine import GestureStateMachine
from app.actions.cooldown import ActionCooldownManager
from app.core.events import EventBus, EventType, default_event_bus
from app.diagnostics.logger import get_logger

logger = get_logger("action_dispatcher")


class ActionDispatcher:
    """Dispatches high-level intents to operating-system platform controllers."""

    def __init__(
        self,
        controller: BaseOSController,
        state_machine: GestureStateMachine,
        cooldown_manager: Optional[ActionCooldownManager] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.controller = controller
        self.state_machine = state_machine
        self.cooldown_manager = cooldown_manager or ActionCooldownManager()
        self.event_bus = event_bus or default_event_bus

        self._last_volume_time: float = 0.0
        self._min_volume_interval: float = 1.0 / 15.0  # Max 15 volume updates/sec

    def dispatch(self, intent: ActionIntent) -> bool:
        """Validates safety, checks cooldowns, and executes action on platform controller."""
        if intent.intent_type == IntentType.NO_ACTION:
            return False

        # Emergency stop intent can fire even if system is not in ACTIVE state
        if intent.intent_type == IntentType.EMERGENCY_STOP_TRIGGER:
            reason = intent.params.get("reason", "Emergency stop triggered")
            self.state_machine.trigger_emergency_stop(reason)
            return True

        # All other intents require active state
        if not self.state_machine.is_active or self.state_machine.is_emergency_stopped:
            return False

        # Check cooldown
        now = time.time()
        if not self.cooldown_manager.is_action_allowed(intent.intent_type, now):
            return False

        # Route to platform controller
        success = self._execute_intent(intent, now)
        if success:
            self.cooldown_manager.mark_executed(intent.intent_type, now)
            self.event_bus.publish(EventType.INTENT_DISPATCHED, {
                "intent": intent.intent_type.value,
                "params": intent.params,
                "timestamp": now,
            })

        return success

    def _execute_intent(self, intent: ActionIntent, now: float) -> bool:
        t = intent.intent_type
        p = intent.params

        try:
            # --- Pointer & Mouse ---
            if t == IntentType.MOUSE_MOVE:
                self.controller.move_cursor(p["x"], p["y"])
                return True
            elif t == IntentType.LEFT_CLICK:
                if "x" in p and "y" in p:
                    self.controller.move_cursor(p["x"], p["y"])
                self.controller.left_click()
                return True
            elif t == IntentType.RIGHT_CLICK:
                if "x" in p and "y" in p:
                    self.controller.move_cursor(p["x"], p["y"])
                self.controller.right_click()
                return True
            elif t == IntentType.DOUBLE_CLICK:
                if "x" in p and "y" in p:
                    self.controller.move_cursor(p["x"], p["y"])
                self.controller.double_click()
                return True
            elif t == IntentType.DRAG_START:
                self.controller.mouse_down("left")
                return True
            elif t == IntentType.DRAG_MOVE:
                self.controller.move_cursor(p["x"], p["y"])
                return True
            elif t == IntentType.DRAG_END:
                self.controller.mouse_up("left")
                return True
            elif t == IntentType.SCROLL_VERTICAL:
                self.controller.scroll(0, p.get("dy", 1))
                return True
            elif t == IntentType.SCROLL_HORIZONTAL:
                self.controller.scroll(p.get("dx", 1), 0)
                return True

            # --- Audio & Volume (Rate Limited) ---
            elif t == IntentType.VOLUME_SET:
                if now - self._last_volume_time >= self._min_volume_interval:
                    self.controller.set_volume(p["level"])
                    self._last_volume_time = now
                    return True
                return False
            elif t == IntentType.VOLUME_UP:
                if now - self._last_volume_time >= self._min_volume_interval:
                    self.controller.volume_up(p.get("step", 4.0))
                    self._last_volume_time = now
                    return True
                return False
            elif t == IntentType.VOLUME_DOWN:
                if now - self._last_volume_time >= self._min_volume_interval:
                    self.controller.volume_down(p.get("step", 4.0))
                    self._last_volume_time = now
                    return True
                return False
            elif t == IntentType.VOLUME_MUTE:
                self.controller.volume_mute_toggle()
                return True

            # --- Media Playback ---
            elif t == IntentType.MEDIA_PLAY_PAUSE:
                self.controller.media_play_pause()
                return True
            elif t == IntentType.MEDIA_NEXT:
                self.controller.media_next()
                return True
            elif t == IntentType.MEDIA_PREV:
                self.controller.media_previous()
                return True

            # --- Browser Navigation ---
            elif t == IntentType.BROWSER_BACK:
                self.controller.browser_back()
                return True
            elif t == IntentType.BROWSER_FORWARD:
                self.controller.browser_forward()
                return True
            elif t == IntentType.BROWSER_PAGE_UP:
                self.controller.browser_page_up()
                return True
            elif t == IntentType.BROWSER_PAGE_DOWN:
                self.controller.browser_page_down()
                return True
            elif t == IntentType.BROWSER_ZOOM_IN:
                self.controller.browser_zoom_in()
                return True
            elif t == IntentType.BROWSER_ZOOM_OUT:
                self.controller.browser_zoom_out()
                return True
            elif t == IntentType.BROWSER_NEW_TAB:
                self.controller.browser_new_tab()
                return True

            # --- Window Controls ---
            elif t == IntentType.WINDOW_NEXT:
                self.controller.window_switch_next()
                return True
            elif t == IntentType.WINDOW_PREV:
                self.controller.window_switch_prev()
                return True
            elif t == IntentType.WINDOW_MINIMIZE:
                self.controller.window_minimize()
                return True
            elif t == IntentType.WINDOW_MAXIMIZE:
                self.controller.window_maximize()
                return True
            elif t == IntentType.WINDOW_RESTORE:
                self.controller.window_restore()
                return True

            # --- Presentation Mode ---
            elif t == IntentType.PRESENTATION_NEXT:
                self.controller.presentation_next()
                return True
            elif t == IntentType.PRESENTATION_PREV:
                self.controller.presentation_prev()
                return True
            elif t == IntentType.PRESENTATION_START:
                self.controller.presentation_start()
                return True
            elif t == IntentType.PRESENTATION_STOP:
                self.controller.presentation_stop()
                return True

            # --- Drawing Canvas Intents ---
            elif t in (IntentType.DRAW_STROKE, IntentType.DRAW_CLEAR, IntentType.DRAW_UNDO, IntentType.DRAW_REDO):
                return True

        except Exception as e:
            logger.error(f"Error executing intent {intent.intent_type}: {e}", exc_info=True)
            return False

        return False
