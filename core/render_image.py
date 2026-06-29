"""
core/render_image.py
"""

import os, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SCALE = 2
W, H = 1200 * SCALE, 630 * SCALE

def S(val): return int(val * SCALE)

C = {
    "bg":     ( 8,  12,  22),
    "card":   (13,  19,  36),
    "border": (30,  44,  68),
    "purple": (124, 58,  237),
    "cyan":   ( 6,  182, 212),
    "green":  ( 16, 185, 129),
    "red":    (239,  68,  68),
    "amber":  (245, 158,  11),
    "pink":   (236,  72, 153),
    "white":  (248, 250, 252),
    "muted":  ( 98, 120, 160),
}

FONT_DIR = Path(__file__).parent.parent / "media" / "fonts"
_font_cache: dict = {}

def strip_emojis(text: str) -> str:
    return re.sub(r'[\U00010000-\U0010ffff]', '', text) if text else ""

def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key in _font_cache: return _font_cache[key]
    path = FONT_DIR / name
    if path.exists():
        try:
            f = ImageFont.truetype(str(path), size)
            _font_cache[key] = f
            return f
        except: pass
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f

def _grad_bg(draw: ImageDraw.ImageDraw):
    top, bot = C["bg"], (11, 17, 33)
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(top[i]+(bot[i]-top[i])*t) for i in range(3)))

def _glow(img: Image.Image, cx, cy, radius, color, alpha_max=45) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(layer)
    steps = 18
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(alpha_max * (i / steps) ** 2)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, a))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

def _drop_shadow(box, radius, blur=20, offset_y=10, alpha=80):
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    bx0, by0, bx1, by1 = box
    sdraw.rounded_rectangle([bx0, by0 + offset_y, bx1, by1 + offset_y], radius=radius, fill=(0, 0, 0, alpha))
    return shadow.filter(ImageFilter.GaussianBlur(blur))

def _glass_panel(img, box, radius, fill=(255,255,255,10), outline=(255,255,255,30), width=1):
    shadow = _drop_shadow(box, radius)
    img.paste(Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB"), (0,0))
    
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(panel)
    pdraw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    img.paste(Image.alpha_composite(img.convert("RGBA"), panel).convert("RGB"), (0,0))
    return img

def _centered_text(draw, text, y, font, color, x0=0, x1=W):
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text((x0 + (x1 - x0 - tw) // 2, y), text, font=font, fill=color)

def _wrap(draw, text, font, max_w) -> list[str]:
    words = text.split(); lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w: line = test
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    return lines

def _save(img, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return path

def _draw_tick(draw, cx, cy, col):
    draw.line([(cx-S(6), cy-S(2)), (cx-S(2), cy+S(4)), (cx+S(8), cy-S(6))], fill=col, width=S(4))

def _draw_cross(draw, cx, cy, col):
    draw.line([(cx-S(6), cy-S(6)), (cx+S(6), cy+S(6))], fill=col, width=S(4))
    draw.line([(cx-S(6), cy+S(6)), (cx+S(6), cy-S(6))], fill=col, width=S(4))


# ── Renderers ─────────────────────────────────────────────────────────────────

def render_scene_card(data: dict, save_path: str) -> str:
    img = Image.new("RGB", (W, H), C["bg"])
    draw = ImageDraw.Draw(img)
    _grad_bg(draw)
    img = _glow(img, W // 4, H // 2, S(350), C["purple"], 60)
    img = _glow(img, 3 * W // 4, H // 3, S(280), C["cyan"], 50)
    
    f_hook = _font("Inter-Bold.ttf", S(48))
    f_body = _font("Inter-Regular.ttf", S(24))
    f_tag  = _font("Inter-SemiBold.ttf", S(18))
    f_code = _font("Inter-Regular.ttf", S(16))

    title = strip_emojis(data.get("title", ""))
    body  = strip_emojis(data.get("body",  ""))
    tag   = strip_emojis(data.get("tag",   "#WebDev"))

    PAD = S(55)
    RX = W - S(360)

    # Glassmorphism terminal panel
    img = _glass_panel(img, [RX - S(10), S(20), W - S(20), H - S(20)], S(16), fill=(13, 19, 36, 180), outline=(255,255,255,40), width=S(1))
    draw = ImageDraw.Draw(img)

    for j, col in enumerate([(239, 68, 68), (245, 158, 11), (16, 185, 129)]):
        draw.ellipse([RX + S(6 + j * 20), S(38), RX + S(20 + j * 20), S(52)], fill=col)
        
    code_snippet = [
        ("const ", C["purple"]),  ("dev", C["cyan"]),  (" = {", C["white"]),
        ("  role:", C["muted"]),  (f" \"{tag.strip('#')}\"", C["amber"]), (None, None),
        ("  learning:", C["muted"]), (" true", C["green"]), (None, None),
        ("  stack:", C["muted"]),  (" [", C["white"]), (None, None),
        ("    'React',", C["cyan"]), (None, None),
        ("    'TypeScript'", C["cyan"]), (None, None),
        ("  ],", C["white"]), (None, None),
        ("};", C["white"]), (None, None),
        ("", None), (None, None),
        ("// Happy coding", C["muted"]), (None, None),
    ]
    cx, cy = RX + S(10), S(80)
    line_buf = []
    for tok, col in code_snippet:
        if tok is None:
            tx = cx
            for t, c in line_buf:
                bb = draw.textbbox((0, 0), t, font=f_code)
                draw.text((tx, cy), t, font=f_code, fill=c or C["muted"])
                tx += bb[2] - bb[0]
            cy += S(26)
            line_buf = []
        else:
            line_buf.append((tok, col))

    y = S(40)
    tb = draw.textbbox((0, 0), tag, font=f_tag)
    img = _glass_panel(img, [PAD, y, PAD + tb[2] - tb[0] + S(28), y + S(32)], S(16), fill=(124, 58, 237, 200), outline=(255,255,255,0))
    draw = ImageDraw.Draw(img)
    draw.text((PAD + S(14), y + S(6)), tag, font=f_tag, fill=C["white"])
    y += S(52)

    max_w = RX - PAD - S(24)
    for line in _wrap(draw, title, f_hook, max_w)[:3]:
        draw.text((PAD, y), line, font=f_hook, fill=C["white"])
        y += S(64)
    y += S(8)

    if body:
        for line in _wrap(draw, body, f_body, max_w)[:3]:
            draw.text((PAD, y), line, font=f_body, fill=C["muted"])
            y += S(34)

    return _save(img, save_path)


def render_comparison(data: dict, save_path: str) -> str:
    img = Image.new("RGB", (W, H), C["bg"])
    draw = ImageDraw.Draw(img)
    _grad_bg(draw)
    img = _glow(img, 0,   0,   S(320), C["purple"], 60)
    img = _glow(img, W,   0,   S(320), C["cyan"],   60)
    img = _glow(img, W//2, H,  S(250), C["purple"], 40)
    draw = ImageDraw.Draw(img)

    f_title  = _font("Inter-Bold.ttf",     S(40))
    f_sub    = _font("Inter-Regular.ttf",  S(20))
    f_hdr    = _font("Inter-Bold.ttf",     S(24))
    f_feat   = _font("Inter-Regular.ttf",  S(20))
    f_sym    = _font("Inter-Bold.ttf",     S(28))
    f_score  = _font("Inter-SemiBold.ttf", S(18))

    title    = strip_emojis(data.get("title",    "Comparison"))
    subtitle = strip_emojis(data.get("subtitle", ""))
    ln       = strip_emojis(data.get("left",  {}).get("name", "A"))
    rn       = strip_emojis(data.get("right", {}).get("name", "B"))
    rows     = data.get("rows", [])[:6]

    _centered_text(draw, title, S(24), f_title, C["white"])
    _centered_text(draw, subtitle, S(70), f_sub, C["muted"])

    TOP   = S(110)
    ROW_H = S(50)
    PAD_L = S(50)
    PAD_R = W - S(50)

    feat_x   = PAD_L + S(16)
    feat_end = PAD_L + S(400)
    mid_end  = feat_end + S(350)
    
    la_x0    = feat_end + S(20)
    la_x1    = mid_end - S(20)
    rb_x0    = mid_end + S(20)
    rb_x1    = PAD_R - S(20)

    table_h  = ROW_H * (len(rows) + 2) + S(12)

    # Glassmorphism container for the table
    img = _glass_panel(img, [PAD_L - S(8), TOP - S(8), PAD_R + S(8), TOP + table_h + S(8)], S(16), fill=(13,19,36, 150), outline=(255,255,255,30), width=S(1))
    draw = ImageDraw.Draw(img)
    
    # Header backgrounds
    draw.rounded_rectangle([la_x0 - S(6), TOP + S(4), la_x1 + S(6), TOP + ROW_H - S(4)], radius=S(10), fill=(124, 58, 237, 100))
    draw.rounded_rectangle([rb_x0 - S(6), TOP + S(4), rb_x1 + S(6), TOP + ROW_H - S(4)], radius=S(10), fill=(6, 182, 212, 100))

    draw.text((feat_x, TOP + S(12)), "Feature", font=f_hdr, fill=C["muted"])
    _centered_text(draw, ln, TOP + S(12), f_hdr, C["white"], la_x0 - S(6), la_x1 + S(6))
    _centered_text(draw, rn, TOP + S(12), f_hdr, C["white"], rb_x0 - S(6), rb_x1 + S(6))

    lw = rw = 0
    for i, row in enumerate(rows):
        y = TOP + (i + 1) * ROW_H + S(6)
        feat = strip_emojis(row.get("feature", ""))
        lv   = row.get("left",  False)
        rv   = row.get("right", False)

        if i % 2 == 0:
            draw.rounded_rectangle([PAD_L - S(8), y, PAD_R + S(8), y + ROW_H - S(2)], radius=S(8), fill=(18, 25, 45))
            
        draw.line([(PAD_L, y), (PAD_R, y)], fill=(35, 50, 75), width=S(1))

        draw.text((feat_x, y + S(14)), feat, font=f_feat, fill=C["white"])

        lcx = la_x0 + (la_x1 - la_x0) // 2
        lcy = y + ROW_H // 2
        if isinstance(lv, bool):
            if lv:
                _draw_tick(draw, lcx, lcy, C["green"])
                lw += 1
            else:
                _draw_cross(draw, lcx, lcy, C["red"])
        else:
            _centered_text(draw, strip_emojis(str(lv)), y + S(10), f_sym, C["muted"], la_x0, la_x1)

        rcx = rb_x0 + (rb_x1 - rb_x0) // 2
        rcy = y + ROW_H // 2
        if isinstance(rv, bool):
            if rv:
                _draw_tick(draw, rcx, rcy, C["green"])
                rw += 1
            else:
                _draw_cross(draw, rcx, rcy, C["red"])
        else:
            _centered_text(draw, strip_emojis(str(rv)), y + S(10), f_sym, C["muted"], rb_x0, rb_x1)

    # Vertical dividers
    draw.line([(feat_end, TOP), (feat_end, TOP + table_h)], fill=(35, 50, 75), width=S(1))
    draw.line([(mid_end, TOP), (mid_end, TOP + table_h)],    fill=(35, 50, 75), width=S(1))

    n = len(rows) or 1
    sy = TOP + (n + 1) * ROW_H + S(12)
    draw.line([(PAD_L, sy - S(2)), (PAD_R, sy - S(2))], fill=(35, 50, 75), width=S(1))
    _centered_text(draw, f"{lw}/{n} points", sy + S(6), f_score, C["green"] if lw >= rw else C["muted"], la_x0, la_x1)
    _centered_text(draw, f"{rw}/{n} points", sy + S(6), f_score, C["green"] if rw >= lw else C["muted"], rb_x0, rb_x1)

    return _save(img, save_path)


def render_tips(data: dict, save_path: str) -> str:
    img = Image.new("RGB", (W, H), C["bg"])
    draw = ImageDraw.Draw(img)
    _grad_bg(draw)
    img = _glow(img, W // 2, H, S(380), C["purple"], 50)
    img = _glow(img, 0,      0, S(200), C["cyan"],   40)
    draw = ImageDraw.Draw(img)

    f_title = _font("Inter-Bold.ttf",     S(42))
    f_sub   = _font("Inter-Regular.ttf",  S(20))
    f_num   = _font("Inter-Bold.ttf",     S(22))
    f_head  = _font("Inter-Bold.ttf",     S(22))
    f_body  = _font("Inter-Regular.ttf",  S(20))

    title    = strip_emojis(data.get("title",    "Tips"))
    subtitle = strip_emojis(data.get("subtitle", ""))
    tips     = data.get("tips", [])[:5]

    PAD = S(54)
    y   = S(32)

    # Header section
    draw.rectangle([PAD, y, PAD + S(6), y + S(56)], fill=C["purple"])
    draw.text((PAD + S(20), y + S(6)), title, font=f_title, fill=C["white"])
    y += S(64)
    if subtitle:
        draw.text((PAD + S(20), y), subtitle, font=f_sub, fill=C["muted"])
        y += S(32)
    y += S(12)

    accents = [C["purple"], C["cyan"], C["amber"], C["green"], C["pink"]]

    # FIX: Draw the vertical connecting lines FIRST so they sit behind the circles
    # We need to calculate the positions before drawing
    tip_positions = []
    curr_y = y
    for i, tip in enumerate(tips):
        tip_positions.append(curr_y)
        
        if ":" in tip and tip.index(":") < 45: _, body = tip.split(":", 1)
        else: body = ""
            
        by = curr_y + S(32)
        if strip_emojis(body).strip():
            # Estimate height based on wrap
            for line in _wrap(draw, strip_emojis(body).strip(), f_body, W - (PAD + S(54)) - PAD)[:2]:
                by += S(26)
        
        row_h = max(S(56), by - curr_y + S(12))
        curr_y += row_h + S(4)

    # Draw vertical connecting lines (now they won't overlap the circles!)
    for i, start_y in enumerate(tip_positions):
        col = accents[i % len(accents)]
        # We only draw a short vertical connector between the circles, not through them
        # Wait, the previous code was drawing a rectangle to the left:
        # draw.rectangle([PAD + S(4), y - S(2), PAD + S(6), y + S(56)], fill=col)
        # Instead, let's draw a vertical line from this circle down to the next circle
        if i < len(tip_positions) - 1:
            next_y = tip_positions[i+1]
            cx  = PAD + S(20)
            # Line goes from bottom of current circle to top of next circle
            draw.line([(cx, start_y + S(40)), (cx, next_y + S(10))], fill=col, width=S(2))

    # Now draw the circles and text on top
    for i, tip in enumerate(tips):
        col = accents[i % len(accents)]
        cy_base = tip_positions[i]
        
        cx  = PAD + S(20)
        cy  = cy_base + S(24)

        # Draw circle
        draw.ellipse([cx - S(20), cy - S(20), cx + S(20), cy + S(20)], fill=col)
        
        # Draw number
        ns = str(i + 1)
        nbb = draw.textbbox((0, 0), ns, font=f_num)
        draw.text((cx - (nbb[2]-nbb[0])//2, cy - (nbb[3]-nbb[1])//2 - S(2)), ns, font=f_num, fill=C["white"])

        tip_x = PAD + S(54)
        max_w = W - tip_x - PAD

        if ":" in tip and tip.index(":") < 45:
            hdr, body = tip.split(":", 1)
        else:
            hdr, body = tip, ""

        hdr = strip_emojis(hdr)
        body = strip_emojis(body)

        draw.text((tip_x, cy_base + S(6)), hdr.strip(), font=f_head, fill=C["white"])
        by = cy_base + S(32)
        if body.strip():
            for line in _wrap(draw, body.strip(), f_body, max_w)[:2]:
                draw.text((tip_x, by), line, font=f_body, fill=C["muted"])
                by += S(26)

    return _save(img, save_path)

