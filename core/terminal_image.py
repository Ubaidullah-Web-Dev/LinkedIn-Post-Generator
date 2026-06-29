import sys
import shutil
from PIL import Image

def get_terminal_image_ansi(image_path: str, max_width: int = 80) -> str:
    """
    Reads an image, resizes it to fit terminal width, and converts it to
    a 24-bit TrueColor ANSI string using half-block characters (▄).
    """
    try:
        img = Image.open(image_path)
        w, h = img.size
        
        # 1 character = 1 horizontal pixel, 2 vertical pixels (half blocks)
        # However, terminal characters are usually twice as tall as they are wide.
        # So using a half block effectively maps 1 terminal cell to 1x1 image aspect ratio.
        aspect = h / w
        new_w = min(max_width, w)
        # Calculate new height in character rows (where 1 row = 2 pixels)
        # Wait, if aspect is h/w, new image pixel height = new_w * aspect
        new_h = int(new_w * aspect)
        
        if new_h % 2 != 0:
            new_h += 1
            
        img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        img_rgb = img.convert("RGB")
        
        ansi_str = ""
        for y in range(0, new_h, 2):
            for x in range(new_w):
                r1, g1, b1 = img_rgb.getpixel((x, y))
                r2, g2, b2 = img_rgb.getpixel((x, y+1))
                # Foreground = bottom pixel (r2,g2,b2), Background = top pixel (r1,g1,b1)
                ansi_str += f"\033[38;2;{r2};{g2};{b2}m\033[48;2;{r1};{g1};{b1}m▄"
            ansi_str += "\033[0m\n"
        return ansi_str
    except Exception as e:
        return f"[Error rendering terminal image: {e}]"

def render_image_in_terminal(image_path: str):
    """
    Helper to print the ANSI image directly to standard output,
    automatically detecting terminal width.
    """
    term_width, _ = shutil.get_terminal_size((80, 24))
    max_width = term_width - 4
    if max_width < 20:
        max_width = 80
        
    ansi_image = get_terminal_image_ansi(image_path, max_width)
    sys.stdout.write(ansi_image)
    sys.stdout.flush()
