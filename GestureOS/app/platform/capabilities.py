"""Platform capabilities detection and capability matrix for GestureOS."""

from __future__ import annotations
import sys
import platform
import os
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class PlatformCapabilities:
    """Matrix detailing available platform-specific hardware and OS capabilities."""
    os_name: str
    os_version: str
    architecture: str
    supports_native_cursor: bool = True
    supports_virtual_desktop: bool = False
    supports_hardware_volume: bool = False
    supports_low_latency_mci: bool = False
    supports_foreground_window_detection: bool = False
    supports_global_shortcuts: bool = True
    capability_notes: Dict[str, str] = field(default_factory=dict)

    def is_feature_available(self, feature_key: str) -> bool:
        """Queries whether a specific hardware/OS feature is available."""
        return getattr(self, feature_key, False)

    def get_unavailability_reason(self, feature_key: str) -> str:
        """Returns friendly human-readable explanation if a feature is unavailable."""
        return self.capability_notes.get(
            feature_key, f"Feature '{feature_key}' is not supported on {self.os_name}."
        )

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def detect(cls) -> PlatformCapabilities:
        return detect_platform_capabilities()

    @property
    def system(self) -> str:
        if self.os_name == "win32":
            return "windows"
        elif self.os_name == "darwin":
            return "macos"
        return "linux"

    @property
    def release(self) -> str:
        return self.os_version

    @property
    def has_native_mouse(self) -> bool:
        return self.supports_native_cursor

    @property
    def has_mci_audio(self) -> bool:
        return self.supports_low_latency_mci

    @property
    def has_global_hotkeys(self) -> bool:
        return self.supports_global_shortcuts

    @property
    def has_foreground_app_detection(self) -> bool:
        return self.supports_foreground_window_detection


def detect_platform_capabilities() -> PlatformCapabilities:
    """Probes the current host operating system and constructs the capability matrix."""
    os_name = sys.platform
    os_ver = platform.platform()
    arch = platform.machine()

    caps = PlatformCapabilities(
        os_name=os_name,
        os_version=os_ver,
        architecture=arch,
    )

    if os_name == "win32":
        caps.supports_native_cursor = True
        caps.supports_virtual_desktop = True
        caps.supports_low_latency_mci = True
        caps.supports_global_shortcuts = True

        # Check pycaw / Windows CoreAudio support
        try:
            import pycaw.pycaw as pc
            caps.supports_hardware_volume = True
        except Exception:
            caps.supports_hardware_volume = False
            caps.capability_notes["supports_hardware_volume"] = (
                "Windows Core Audio (pycaw) is unavailable. Fallback volume steps will be used."
            )

        # Check user32 window inspection
        try:
            import ctypes
            caps.supports_foreground_window_detection = hasattr(ctypes.windll.user32, "GetForegroundWindow")
        except Exception:
            caps.supports_foreground_window_detection = False

    elif os_name.startswith("linux"):
        caps.supports_native_cursor = True
        caps.supports_virtual_desktop = False
        caps.supports_low_latency_mci = False
        caps.capability_notes["supports_low_latency_mci"] = (
            "Windows MCI audio is not native to Linux. Standard cross-platform audio fallback is active."
        )

        # Check display server (X11 vs Wayland)
        xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if xdg_session == "wayland":
            caps.capability_notes["supports_native_cursor"] = (
                "Wayland detected: global cursor injection may require XWayland or accessibility permissions."
            )

        # Check ALSA/Pulse/Pipewire volume
        caps.supports_hardware_volume = False
        caps.capability_notes["supports_hardware_volume"] = (
            "Linux system volume control requires ALSA/PulseAudio/amixer."
        )

    elif os_name == "darwin":  # macOS
        caps.supports_native_cursor = True
        caps.supports_virtual_desktop = True
        caps.supports_low_latency_mci = False
        caps.capability_notes["supports_low_latency_mci"] = (
            "Windows MCI audio is not native to macOS. Standard audio fallback is active."
        )
        caps.supports_hardware_volume = False
        caps.capability_notes["supports_hardware_volume"] = (
            "macOS volume automation uses osascript fallback."
        )

    else:
        caps.supports_native_cursor = False
        caps.capability_notes["supports_native_cursor"] = f"Unknown OS platform: {os_name}."

    return caps
