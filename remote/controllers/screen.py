import io
from PIL import Image
import mss


def capture_screen(max_width: int = 720, max_height: int = 405) -> bytes:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        image.thumbnail((max_width, max_height), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=30, optimize=True)
        return buffer.getvalue()
