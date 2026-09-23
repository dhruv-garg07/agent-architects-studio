import pyautogui

pyautogui.FAILSAFE = False


def press_key(key: str) -> None:
    pyautogui.press(key)


def type_text(text: str) -> None:
    pyautogui.write(text, interval=0.02)


def hotkey(keys: list[str]) -> None:
    pyautogui.hotkey(*keys)
