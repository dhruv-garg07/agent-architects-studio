import subprocess
import os
import platform


def launch_chrome() -> None:
    if platform.system() == "Windows":
        chrome_paths = [
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES"), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for path in chrome_paths:
            if path and os.path.exists(path):
                subprocess.Popen([path])
                return
        subprocess.Popen(["start", "chrome"], shell=True)
    else:
        subprocess.Popen(["google-chrome"])
