import os
import subprocess
import shutil
from typing import Tuple


def _find_teamviewer_exe() -> str | None:
    # Common install locations on Windows
    candidates = [
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'TeamViewer', 'TeamViewer.exe'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'TeamViewer', 'TeamViewer.exe'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'TeamViewer', 'TeamViewer_Service.exe'),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    # fallback to PATH
    return shutil.which('TeamViewer.exe') or shutil.which('teamviewer')


def open_teamviewer() -> Tuple[bool, str]:
    """Attempt to start TeamViewer on Windows.

    Returns (ok, message). This function intentionally performs no remote-control actions;
    it only launches the TeamViewer application so the user can accept a session.
    """
    exe = _find_teamviewer_exe()
    if not exe:
        return False, 'TeamViewer executable not found. Please install TeamViewer or add it to PATH.'

    try:
        subprocess.Popen([exe], close_fds=True)
        return True, f'Started TeamViewer from {exe}'
    except Exception as e:
        return False, f'Failed to start TeamViewer: {e}'
