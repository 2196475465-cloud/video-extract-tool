"""生成小程序内联 SVG 图标（base64 data URI），输出 wxss。

用法：python tools/gen_icons.py
输出：miniprogram/styles/icons.wxss
"""

import base64
import pathlib

ROOT = pathlib.Path(r"C:/Users/GLX/OneDrive/Desktop/小项目/douyin-tool/miniprogram")

# 24x24 线性图标，描边风格
ICONS = {
    "paste": '<rect x="8" y="2" width="8" height="4" rx="1.5"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "video": '<rect x="2" y="5" width="20" height="14" rx="3"/><path d="m10 9.5 4.5 2.5L10 14.5z"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.4"/><path d="m21 15-4.5-4.5L5.5 21"/>',
    "music": '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="2.6"/><circle cx="17" cy="16" r="2.6"/>',
    "text": '<path d="M4 7V4h16v3"/><path d="M12 4v16"/><path d="M9 20h6"/>',
    "share": '<circle cx="18" cy="5" r="2.6"/><circle cx="6" cy="12" r="2.6"/><circle cx="18" cy="19" r="2.6"/><path d="m8.4 13.4 7.2 4.2M15.6 6.4l-7.2 4.2"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.2 9.2a3 3 0 1 1 4.3 2.8c-.9.5-1.5 1.2-1.5 2.2"/><path d="M12 17.4h.01"/>',
    "feedback": '<path d="M21 14.5a2.5 2.5 0 0 1-2.5 2.5H8l-4.5 3.5V5.5A2.5 2.5 0 0 1 6 3h12.5A2.5 2.5 0 0 1 21 5.5z"/>',
    "headset": '<path d="M4.5 14v-2a7.5 7.5 0 0 1 15 0v2"/><rect x="2.5" y="13.5" width="4" height="6" rx="2"/><rect x="17.5" y="13.5" width="4" height="6" rx="2"/>',
    "doc": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/>',
    "trash": '<path d="M4 7h16"/><path d="M9.5 7V4.5h5V7"/><path d="M6.5 7l.9 12.2a1.5 1.5 0 0 0 1.5 1.4h6.2a1.5 1.5 0 0 0 1.5-1.4L17.5 7"/>',
    "arrow": '<path d="m9.5 5 7 7-7 7"/>',
    "back": '<path d="m14.5 5-7 7 7 7"/>',
    "check": '<path d="m4.5 12.5 5 5L20 6.5"/>',
    "download": '<path d="M12 3v12"/><path d="m7.5 10.5 4.5 4.5 4.5-4.5"/><path d="M4.5 20h15"/>',
    "sparkle": '<path d="M12 3.5 13.6 9l5.4 1.6-5.4 1.6L12 17.7 10.4 12.2 5 10.6 10.4 9z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.3l3.4 2"/>',
    "link": '<path d="M10 13a4 4 0 0 0 5.7 0l2.8-2.8a4 4 0 0 0-5.7-5.7L11.5 6"/><path d="M14 11a4 4 0 0 0-5.7 0l-2.8 2.8a4 4 0 0 0 5.7 5.7L12.5 18"/>',
    "fire": '<path d="M12 3s5 4.2 5 8.5a5 5 0 0 1-10 0C7 9.6 9 7.4 9 7.4s.4 2 1.6 2.6C11.2 7.5 12 3 12 3z"/>',
    "user": '<circle cx="12" cy="8" r="3.6"/><path d="M4.8 20.4c1.3-3.5 3.9-5.4 7.2-5.4s5.9 1.9 7.2 5.4"/>',
    "play": '<circle cx="12" cy="12" r="9"/><path d="m10 8.8 5.2 3.2-5.2 3.2z"/>',
}

COLORS = {
    "": "#5B6273",      # 常规
    "-m": "#9AA0AE",    # 更淡
    "-b": "#4E6EF2",    # 主色
    "-w": "#FFFFFF",    # 白色
}


def svg(inner: str, color: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{inner}</svg>"
    )


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def main() -> None:
    out = ROOT / "styles"
    out.mkdir(exist_ok=True)
    lines = [
        "/* 自动生成，请勿手改。重新生成：python tools/gen_icons.py */",
        ".ic{display:inline-block;width:40rpx;height:40rpx;background-repeat:no-repeat;"
        "background-position:center;background-size:100% 100%;vertical-align:middle}",
    ]
    for name, inner in ICONS.items():
        for suffix, color in COLORS.items():
            data = b64(svg(inner, color))
            lines.append(f'.ic-{name}{suffix}{{background-image:url("data:image/svg+xml;base64,{data}")}}')
    (out / "icons.wxss").write_text("\n".join(lines) + "\n", encoding="utf-8")
    size = (out / "icons.wxss").stat().st_size
    print(f"generated {out / 'icons.wxss'}  icons={len(ICONS)} colors={len(COLORS)} size={size/1024:.1f}KB")


if __name__ == "__main__":
    main()
