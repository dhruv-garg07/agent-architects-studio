import pyautogui

pyautogui.FAILSAFE = False


def play_pause() -> None:
    pyautogui.press("playpause")


def volume_up() -> None:
    pyautogui.press("volumeup")


def volume_down() -> None:
    pyautogui.press("volumedown")


def mute() -> None:
    pyautogui.press("volumemute")


def next_track() -> None:
    pyautogui.press("nexttrack")


def previous_track() -> None:
    pyautogui.press("prevtrack")
