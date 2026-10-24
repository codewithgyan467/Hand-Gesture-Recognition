"""Hardware capability detection and automatic performance tier assignment."""

from __future__ import annotations
import os
import sys
import platform
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from app.diagnostics.logger import get_logger

logger = get_logger("hardware")


@dataclass
class HardwareProfile:
    """Consolidated hardware specifications and tiering."""
    os_name: str
    os_version: str
    architecture: str
    cpu_cores_physical: int
    cpu_cores_logical: int
    ram_total_gb: float
    ram_available_gb: float
    gpu_name: str
    gpu_vendor: str
    screen_width: int
    screen_height: int
    multi_monitor_count: int
    assigned_tier: str  # "FULL", "BALANCED", "LIGHT", "COMPATIBILITY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def cpu_name(self) -> str:
        return f"{self.cpu_cores_logical}-Core CPU ({self.architecture})"

    @property
    def cpu_count_logical(self) -> int:
        return self.cpu_cores_logical

    @property
    def total_ram_gb(self) -> float:
        return self.ram_total_gb

    @property
    def available_ram_gb(self) -> float:
        return self.ram_available_gb

    @property
    def primary_display_res(self) -> str:
        return f"{self.screen_width}x{self.screen_height}"

    @property
    def monitors_count(self) -> int:
        return self.multi_monitor_count

    @property
    def recommended_performance_tier(self) -> str:
        return self.assigned_tier


class HardwareProfiler:
    """Helper class for detecting hardware profiles."""

    @staticmethod
    def detect(manual_tier_override: Optional[str] = None) -> HardwareProfile:
        return detect_hardware_profile(manual_tier_override)


def detect_hardware_profile(manual_tier_override: Optional[str] = None) -> HardwareProfile:
    """Inspects CPU, RAM, GPU, display, and assigns optimal performance tier."""
    os_name = platform.system()
    os_ver = platform.version()
    arch = platform.machine()

    # CPU & RAM
    cpu_phys = psutil.cpu_count(logical=False) or 2
    cpu_log = psutil.cpu_count(logical=True) or 2
    vm = psutil.virtual_memory()
    ram_total = round(vm.total / (1024 ** 3), 1)
    ram_avail = round(vm.available / (1024 ** 3), 1)

    # Display & Monitors
    screen_w, screen_h = 1920, 1080
    monitor_count = 1
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0) or 1920
            screen_h = user32.GetSystemMetrics(1) or 1080
            monitor_count = max(1, user32.GetSystemMetrics(80))  # SM_CMONITORS
        except Exception:
            pass

    # GPU Inspection (Safe, non-crashing)
    gpu_name = "Integrated / Standard Display Device"
    gpu_vendor = "Unknown"
    if sys.platform == "win32":
        try:
            import subprocess
            cmd = "wmic path win32_VideoController get name"
            out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            lines = [line.strip() for line in out.strip().split("\n") if line.strip() and "Name" not in line]
            if lines:
                gpu_name = lines[0]
                lower = gpu_name.lower()
                if "nvidia" in lower:
                    gpu_vendor = "NVIDIA"
                elif "amd" in lower or "radeon" in lower:
                    gpu_vendor = "AMD"
                elif "intel" in lower:
                    gpu_vendor = "Intel"
        except Exception:
            pass

    # Determine Performance Tier
    if manual_tier_override and manual_tier_override.upper() in ("FULL", "BALANCED", "LIGHT", "COMPATIBILITY"):
        tier = manual_tier_override.upper()
    else:
        # Automatic Tiering Heuristic
        if cpu_log >= 8 and ram_total >= 12.0:
            tier = "FULL"
        elif cpu_log >= 4 and ram_total >= 6.0:
            tier = "BALANCED"
        elif cpu_log >= 2 and ram_total >= 3.5:
            tier = "LIGHT"
        else:
            tier = "COMPATIBILITY"

    profile = HardwareProfile(
        os_name=os_name,
        os_version=os_ver,
        architecture=arch,
        cpu_cores_physical=cpu_phys,
        cpu_cores_logical=cpu_log,
        ram_total_gb=ram_total,
        ram_available_gb=ram_avail,
        gpu_name=gpu_name,
        gpu_vendor=gpu_vendor,
        screen_width=screen_w,
        screen_height=screen_h,
        multi_monitor_count=monitor_count,
        assigned_tier=tier,
    )

    logger.info(
        f"Hardware Profile: Tier={profile.assigned_tier} CPU={profile.cpu_cores_logical} cores "
        f"RAM={profile.ram_total_gb}GB GPU={profile.gpu_name} ({profile.gpu_vendor}) Display={profile.screen_width}x{profile.screen_height}"
    )
    return profile
