"""生成小程序头像（144p 基础上 4 倍图，上传更清晰）"""
from PIL import Image, ImageDraw, ImageFont
import pathlib

OUT = pathlib.Path(r"C:/Users/GLX/OneDrive/Desktop")
S = 576  # 4x，微信会自动缩放


def gradient(size, c1, c2, angle="diag"):
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for i in range(size):
        t = i / (size - 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        if angle == "diag":
            d.line([(0, i), (size, i)], fill=(r, g, b))
        else:
            d.line([(i, 0), (i, size)], fill=(r, g, b))
    return img


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def base(color_a=(78, 110, 242), color_b=(138, 107, 255)):
    """主渐变 + 左上高光 + 右下压暗，做出体积感"""
    img = gradient(S, color_a, color_b).convert("RGBA")
    # 左上柔光
    glow = Image.new("L", (S, S), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-S * 0.35, -S * 0.45, S * 0.55, S * 0.35], fill=90)
    glow = glow.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(70))
    white = Image.new("RGBA", (S, S), (255, 255, 255, 0))
    white.putalpha(glow)
    img = Image.alpha_composite(img, white)
    # 右下压暗
    dark = Image.new("L", (S, S), 0)
    dd = ImageDraw.Draw(dark)
    dd.ellipse([S * 0.55, S * 0.5, S * 1.5, S * 1.45], fill=70)
    dark = dark.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(80))
    black = Image.new("RGBA", (S, S), (18, 12, 60, 0))
    black.putalpha(dark)
    img = Image.alpha_composite(img, black)
    return img


def save(img, name, radius_ratio=0.26):
    mask = rounded_mask(S, int(S * radius_ratio))
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    p = OUT / name
    out.save(p)
    print("生成:", p, out.size)


# ---------- A：下载箭头 ----------
def icon_arrow():
    img = base()
    d = ImageDraw.Draw(img)
    cx = S / 2
    w = S * 0.052          # 线宽
    top = S * 0.22
    bottom = S * 0.62
    head = S * 0.16

    # 竖杆
    d.rounded_rectangle([cx - w / 2, top, cx + w / 2, bottom], radius=w / 2, fill=(255, 255, 255, 255))
    # 箭头
    d.polygon(
        [
            (cx - head, bottom - head * 0.55),
            (cx + head, bottom - head * 0.55),
            (cx, bottom + head * 0.62),
        ],
        fill=(255, 255, 255, 255),
    )
    # 托盘：U 形（左竖 + 右竖 + 底横，端点圆角自然融合）
    x1, x2 = S * 0.255, S * 0.745
    ytop, ybot = S * 0.655, S * 0.775
    d.rounded_rectangle([x1, ytop, x1 + w, ybot], radius=w / 2, fill=(255, 255, 255, 255))
    d.rounded_rectangle([x2 - w, ytop, x2, ybot], radius=w / 2, fill=(255, 255, 255, 255))
    d.rounded_rectangle([x1, ybot - w, x2, ybot], radius=w / 2, fill=(255, 255, 255, 255))
    save(img, "头像A_下载箭头.png")


# ---------- B：单字「冰」 ----------
def icon_char():
    img = gradient(S, (92, 138, 255), (126, 96, 255)).convert("RGBA")
    # 冰面质感：斜向细纹
    lines = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    for i in range(-S, S * 2, 46):
        ld.line([(i, 0), (i + S // 2, S)], fill=(255, 255, 255, 16), width=6)
    img = Image.alpha_composite(img, lines)

    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(r"C:/Windows/Fonts/msyhbd.ttc", int(S * 0.62))
    except Exception:
        font = ImageFont.truetype(r"C:/Windows/Fonts/simhei.ttf", int(S * 0.62))
    text = "冰"
    cx, cy = S / 2, S / 2 + S * 0.012
    d.text((cx, cy), text, font=font, fill=(255, 255, 255, 255), anchor="mm")
    save(img, "头像B_冰字.png")


# ---------- C：播放三角 + 提取箭头（组合） ----------
def icon_play():
    img = base((70, 92, 240), (140, 96, 255))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S * 0.47
    r = S * 0.235
    d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=r * 0.34,
                        fill=(255, 255, 255, 255))
    # 内部播放三角（用主色挖空）
    t = S * 0.085
    d.polygon(
        [(cx - t * 0.55, cy - t), (cx - t * 0.55, cy + t), (cx + t * 0.95, cy)],
        fill=(88, 100, 240, 255),
    )
    # 底部箭头
    w = S * 0.042
    d.rounded_rectangle([cx - w / 2, S * 0.735, cx + w / 2, S * 0.815], radius=w / 2, fill=(255, 255, 255, 240))
    d.polygon(
        [(cx - S * 0.062, S * 0.80), (cx + S * 0.062, S * 0.80), (cx, S * 0.868)],
        fill=(255, 255, 255, 240),
    )
    save(img, "头像C_播放提取.png")


icon_arrow()
icon_char()
icon_play()
