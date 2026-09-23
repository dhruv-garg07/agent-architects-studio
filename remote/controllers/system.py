import os
import subprocess
import platform


def lock() -> None:
    if platform.system() == "Windows":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
    else:
        raise NotImplementedError("Lock is only implemented for Windows.")


def sleep() -> None:
    if platform.system() == "Windows":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"], check=False)
    else:
        raise NotImplementedError("Sleep is only implemented for Windows.")


def shutdown() -> None:
    if platform.system() == "Windows":
        subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
    else:
        raise NotImplementedError("Shutdown is only implemented for Windows.")


def restart() -> None:
    if platform.system() == "Windows":
        subprocess.run(["shutdown", "/r", "/t", "0"], check=False)
    else:
        raise NotImplementedError("Restart is only implemented for Windows.")


def open_target(target: str) -> None:
    if platform.system() == "Windows":
        os.startfile(target)
    else:
        subprocess.run(["xdg-open", target], check=False)
