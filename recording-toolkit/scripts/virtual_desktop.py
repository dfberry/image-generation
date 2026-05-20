"""Windows Virtual Desktop helper — creates/destroys isolated desktops for automation."""

import sys


class VirtualDesktopSession:
    """Context manager for running automation on a separate virtual desktop."""

    def __init__(self):
        self._created_desktop = None
        self._original_desktop = None

    def __enter__(self):
        if sys.platform != "win32":
            raise RuntimeError("Virtual desktop mode requires Windows 10+")

        from pyvda import VirtualDesktop

        self._original_desktop = VirtualDesktop.current()
        self._created_desktop = VirtualDesktop.create()
        self._created_desktop.go()
        return self

    def __exit__(self, *exc):
        if self._original_desktop:
            self._original_desktop.go()

        if self._created_desktop:
            try:
                self._created_desktop.remove()
            except Exception:
                pass

        return False
