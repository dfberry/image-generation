"""Windows Virtual Desktop helper — creates/destroys isolated desktops for automation."""

import logging
import sys

logger = logging.getLogger("virtual_desktop")


class VirtualDesktopSession:
    """Context manager for running automation on a separate virtual desktop."""

    def __init__(self):
        self._created_desktop = None
        self._original_desktop = None

    def __enter__(self):
        if sys.platform != "win32":
            raise RuntimeError("Virtual desktop mode requires Windows 10+")

        try:
            from pyvda import VirtualDesktop
        except ImportError:
            raise RuntimeError(
                "pyvda required for virtual desktop mode. Install: pip install pyvda>=0.4.0"
            )

        logger.info("[vdesktop] Creating new virtual desktop")
        self._original_desktop = VirtualDesktop.current()
        if not self._original_desktop:
            raise RuntimeError("[vdesktop] Failed to get current desktop")
        self._created_desktop = VirtualDesktop.create()
        if not self._created_desktop:
            raise RuntimeError("[vdesktop] Failed to create new virtual desktop")
        self._created_desktop.go()
        logger.info("[vdesktop] Switched to new virtual desktop")
        return self

    def __exit__(self, *exc):
        if self._original_desktop:
            self._original_desktop.go()
            logger.info("[vdesktop] Returned to original desktop")
        if self._created_desktop:
            try:
                self._created_desktop.remove()
                logger.info("[vdesktop] Removed virtual desktop")
            except Exception as e:
                logger.warning(f"[vdesktop] Failed to remove virtual desktop: {e}")
        return False
