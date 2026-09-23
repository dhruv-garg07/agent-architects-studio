import platform
import ctypes
from ctypes import wintypes

# Use direct Win32 API calls for maximum speed
if platform.system() == "Windows":
    user32 = ctypes.windll.user32
    
    # Mouse event constants
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000
    
    # Set cursor position with proper types
    user32.SetCursorPos = user32.SetCursorPos
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = ctypes.c_bool
    
    # Get cursor position
    user32.GetCursorPos = user32.GetCursorPos
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = ctypes.c_bool
    
    # Mouse event with proper types
    user32.mouse_event = user32.mouse_event
    user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.ULONG)]
    user32.mouse_event.restype = None
    
    def move_relative(dx: float, dy: float) -> None:
        """Fast relative mouse movement using direct Win32 API"""
        if dx == 0 and dy == 0:
            return
        
        # Get current position
        point = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(point)):
            # Move to new position
            user32.SetCursorPos(point.x + int(dx), point.y + int(dy))
    
    def click(button: str = "left") -> None:
        """Simulate mouse click"""
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, None)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, None)
        elif button == "middle":
            user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, None)
            user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, None)
    
    def double_click(button: str = "left") -> None:
        """Simulate double click"""
        click(button)
        import time
        time.sleep(0.05)
        click(button)
    
    def mouse_down(button: str = "left") -> None:
        """Press mouse button down"""
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, None)
        elif button == "middle":
            user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, None)
    
    def mouse_up(button: str = "left") -> None:
        """Release mouse button"""
        if button == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
        elif button == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, None)
        elif button == "middle":
            user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, None)
    
    def scroll(clicks: int = 0) -> None:
        """Scroll the mouse wheel"""
        if clicks != 0:
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, clicks * 120, None)
    
    def drag(dx: float, dy: float) -> None:
        """Click and drag the mouse"""
        point = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(point)):
            # Press left button
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
            # Move to new position
            user32.SetCursorPos(point.x + int(dx), point.y + int(dy))
            # Release left button
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)

else:
    # Fallback to pyautogui for non-Windows systems
    import pyautogui
    pyautogui.FAILSAFE = False
    
    def move_relative(dx: float, dy: float) -> None:
        """Move mouse relatively"""
        if dx != 0 or dy != 0:
            pyautogui.moveRel(int(dx), int(dy), duration=0, _pause=False)
    
    def click(button: str = "left") -> None:
        """Click mouse button"""
        pyautogui.click(button=button, _pause=False)
    
    def double_click(button: str = "left") -> None:
        """Double click mouse button"""
        pyautogui.doubleClick(button=button, _pause=False)
    
    def drag(dx: float, dy: float) -> None:
        """Click and drag"""
        x, y = pyautogui.position()
        pyautogui.dragTo(x + dx, y + dy, duration=0.1, button="left", _pause=False)
    
    def mouse_down(button: str = "left") -> None:
        """Press mouse button down"""
        pyautogui.mouseDown(button=button, _pause=False)
    
    def mouse_up(button: str = "left") -> None:
        """Release mouse button"""
        pyautogui.mouseUp(button=button, _pause=False)
    
    def scroll(clicks: int = 0) -> None:
        """Scroll the mouse wheel"""
        if clicks != 0:
            pyautogui.scroll(clicks, _pause=False)
