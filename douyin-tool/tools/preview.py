"""把小程序页面渲染成 HTML 预览图，用于本地检查视觉效果。

只做静态还原：把 wxss 的 rpx 换算成 px，加上等价结构的 HTML。
改完样式跑一次，看 .shots/*.png 就行。
"""
import re
import subprocess
import pathlib

ROOT = pathlib.Path(r"C:/Users/GLX/OneDrive/Desktop/小项目/douyin-tool/miniprogram")
OUT = pathlib.Path(r"C:/Users/GLX/OneDrive/Desktop/小项目/douyin-tool/.shots")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
AVATAR = "https://p3-pc.douyinpic.com/aweme/100x100/aweme-avatar/tos-cn-i-0813_c21e313b3bc74aa0ae78e5f84b2722a0.jpeg"
COVER = "https://p3-pc-sign.douyinpic.com/image-cut-tos-priv/98e7d84724ac70d9273c7201d6968460~tplv-dy-resize-origshort-autoq-75:330.jpeg"


def css_of(text: str) -> str:
    text = re.sub(r"@import[^;]+;", "", text)
    text = re.sub(r"(-?\d+(?:\.\d+)?)rpx", lambda m: f"{float(m.group(1)) / 2:g}px", text)
    text = re.sub(r"(^|\n)page\s*\{", r"\1.phone{", text)
    return text


BASE = css_of((ROOT / "app.wxss").read_text(encoding="utf-8"))
ICONS = css_of((ROOT / "styles/icons.wxss").read_text(encoding="utf-8"))

SHELL = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#dfe2e9;display:flex;justify-content:center;font-family:-apple-system,"PingFang SC",sans-serif}
.phone{width:375px;min-height:812px;position:relative;overflow:hidden}
img{display:block}
__BASE__
__ICONS__
__PAGE__
</style></head><body><div class="phone">__BODY__</div></body></html>"""

INDEX = f"""
<div class="page">
  <div class="hero" style="padding-top:44px">
    <div class="hero-light l1"></div><div class="hero-light l2"></div><div class="hero-grid"></div>
    <div class="hero-top">
      <div class="brand"><div class="logo"><div class="ic ic-sparkle-w"></div></div><span class="brand-name">短视频提取</span></div>
      <div class="nav-actions">
        <div class="nav-btn"><div class="ic ic-clock-w nav-ic"></div><span>记录</span></div>
        <div class="nav-btn"><div class="ic ic-user-w nav-ic"></div><span>我的</span></div>
      </div>
    </div>
    <div class="hero-title">提取<span class="hl">无水印</span>原片</div>
    <div class="hero-sub">复制抖音分享链接，粘贴后一键存进相册</div>
    <div class="hero-tags"><div class="tag">视频</div><div class="tag">图集</div><div class="tag">原声</div><div class="tag">封面</div></div>
  </div>

  <div class="panel card">
    <div class="panel-head"><span class="panel-title">粘贴分享链接</span><span class="panel-hint">支持整段分享文案</span></div>
    <div class="paste-box">
      <div class="paste-input">7.43 复制打开抖音，看看【户外小北的作品】AI还原一个在当地传了百年的秘境之地 https://v.douyin.com/iF6VyQ83/</div>
      <div class="paste-tools">
        <div class="tool"><div class="ic ic-paste-b tool-ic"></div><span>一键粘贴</span></div>
        <div class="tool ghost">清空</div>
        <span class="counter">86/600</span>
      </div>
    </div>
    <div class="btn btn-primary main-btn"><span>开始提取</span><div class="ic ic-arrow-w main-arrow"></div></div>
    <div class="quota-line">
      <div class="ic ic-fire-b quota-ic"></div>
      <span>今日还可提取 <span class="strong">3</span> 次</span>
      <span class="quota-link">看视频加次数</span>
    </div>
  </div>

  <div class="steps card">
    <div class="step"><div class="step-icon"><div class="ic ic-link-b step-ic"></div></div><div class="step-title">复制链接</div><div class="step-desc">抖音点分享</div></div>
    <div class="step"><div class="step-icon"><div class="ic ic-paste-b step-ic"></div></div><div class="step-title">粘贴提取</div><div class="step-desc">自动识别链接</div></div>
    <div class="step"><div class="step-icon"><div class="ic ic-download-b step-ic"></div></div><div class="step-title">存进相册</div><div class="step-desc">一键保存原片</div></div>
  </div>

  <div class="recent">
    <div class="recent-head"><span class="recent-title">最近提取</span><div class="recent-more"><span>全部</span><div class="ic ic-arrow-m more-ic"></div></div></div>
    <div class="recent-scroll" style="display:flex;padding:0 14px">
      <div class="recent-item" style="margin-right:9px">
        <div class="cover-wrap"><div class="recent-cover" style="background:linear-gradient(150deg,#5b6b8c,#2c3547)"></div><div class="recent-dur">7:05</div><div class="cover-mask"></div></div>
        <div class="recent-name">和两个孩子短暂团聚后…</div>
      </div>
      <div class="recent-item" style="margin-right:9px">
        <div class="cover-wrap"><div class="recent-cover" style="background:linear-gradient(150deg,#5b6b8c,#2c3547)"></div><div class="recent-badge">图集</div><div class="cover-mask"></div></div>
        <div class="recent-name">AI还原秘境之地</div>
      </div>
      <div class="recent-item" style="margin-right:9px">
        <div class="cover-wrap"><div class="recent-cover" style="background:linear-gradient(150deg,#5b6b8c,#2c3547)"></div><div class="recent-dur">0:28</div><div class="cover-mask"></div></div>
        <div class="recent-name">冬天就该吃点热的</div>
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="footer-line">仅用于个人学习与备份，请尊重原作者版权</div>
    <div class="footer-link">使用帮助与免责声明</div>
  </div>
</div>
"""

RESULT = f"""
<div class="page">
  <div class="nav" style="padding-top:44px">
    <div class="nav-back"><div class="ic ic-back"></div></div>
    <div class="nav-title">提取结果</div><div class="nav-space"></div>
  </div>

  <div class="preview">
    <div class="player" style="background:radial-gradient(circle at 50% 40%,#2b3140,#0c0f14);display:flex;align-items:center;justify-content:center">
      <div style="width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center">
        <div class="ic ic-play-w" style="width:30px;height:30px"></div>
      </div>
    </div>
    <div class="badge-nowm"><div class="badge-dot"></div><span>无水印</span></div>
  </div>

  <div class="info card">
    <div class="title ellipsis-2">AI还原一个在当地传了百年的秘境之地！视频为技术合成，请勿当真和模仿！</div>
    <div class="chips">
      <div class="chip"><div class="ic ic-video-m chip-ic"></div><span>视频</span></div>
      <div class="chip"><div class="ic ic-clock-m chip-ic"></div><span>7:05</span></div>
      <div class="chip">1080×1440</div>
      <div class="chip">赞 1.2万</div>
    </div>
    <div class="author-row">
      <div class="avatar" style="background:linear-gradient(135deg,#8fa1c7,#5b6b8c)"></div><span class="author">户外小北</span><span class="verified">作者</span>
    </div>
  </div>

  <div class="actions card">
    <div class="btn btn-primary save-btn"><div class="ic ic-download-w save-ic"></div><span>保存视频到相册</span></div>
    <div class="hint"><div class="hint-bar"></div><span>看一小段短视频即可解锁本次保存，广告收入用来付服务器开销，谢谢支持</span></div>
    <div class="subs">
      <div class="sub"><div class="sub-circle"><div class="ic ic-image"></div></div><span>封面</span></div>
      <div class="sub"><div class="sub-circle"><div class="ic ic-music"></div></div><span>原声</span></div>
      <div class="sub"><div class="sub-circle"><div class="ic ic-text"></div></div><span>文案</span></div>
      <div class="sub"><div class="sub-circle"><div class="ic ic-share"></div></div><span>分享</span></div>
    </div>
  </div>

  <div class="tips">
    <div class="tips-title">保存不了？</div>
    <div class="tips-line">· 第一次保存记得允许「保存到相册」权限</div>
    <div class="tips-line">· 视频较长时下载会慢一些，不要切走</div>
    <div class="tips-line">· 请仅用于个人备份，不要二次传播他人作品</div>
  </div>
</div>
"""

MINE = f"""
<div class="page">
  <div class="nav" style="padding-top:44px">
    <div class="nav-back"><div class="ic ic-back"></div></div>
    <div class="nav-title">我的</div><div class="nav-space"></div>
  </div>

  <div class="quota-card">
    <div class="q-glow"></div>
    <div class="q-top">
      <div class="q-main"><div class="q-num">3</div><div class="q-label">今日剩余次数</div></div>
      <div class="q-btn"><div class="ic ic-play-b q-play"></div><span>看视频 +1</span></div>
    </div>
    <div class="q-bar"><div class="q-bar-in" style="width:0%"></div></div>
    <div class="q-foot"><span>免费 0/3 次已用</span><span class="q-dot">·</span><span>已提取 12 条</span></div>
  </div>

  <div class="menu card">
    <div class="menu-item"><div class="mi-icon"><div class="ic ic-help"></div></div><span class="mi-text">使用帮助</span><div class="ic ic-arrow-m mi-arrow"></div></div>
    <div class="menu-item"><div class="mi-icon"><div class="ic ic-feedback"></div></div><span class="mi-text">意见反馈</span><div class="ic ic-arrow-m mi-arrow"></div></div>
    <div class="menu-item"><div class="mi-icon"><div class="ic ic-headset"></div></div><span class="mi-text">联系客服</span><span class="mi-extra">kefu_001</span><div class="ic ic-arrow-m mi-arrow"></div></div>
    <div class="menu-item"><div class="mi-icon"><div class="ic ic-doc"></div></div><span class="mi-text">免责声明</span><div class="ic ic-arrow-m mi-arrow"></div></div>
    <div class="menu-item"><div class="mi-icon"><div class="ic ic-trash"></div></div><span class="mi-text">清理本地缓存</span><div class="ic ic-arrow-m mi-arrow"></div></div>
  </div>

  <div class="about">
    <div class="brand-line"><div class="ic ic-sparkle-m tiny"></div><span>短视频提取 v1.0.0</span></div>
    <div class="about-line">仅供个人学习备份使用</div>
  </div>
</div>
"""


def render(name: str, body: str) -> None:
    page_css = css_of((ROOT / "pages" / name / f"{name}.wxss").read_text(encoding="utf-8"))
    html = SHELL.replace("__BASE__", BASE).replace("__ICONS__", ICONS).replace("__PAGE__", page_css).replace("__BODY__", body)
    OUT.mkdir(exist_ok=True)
    f = OUT / f"{name}.html"
    f.write_text(html, encoding="utf-8")
    raw = OUT / f"{name}_raw.png"
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--user-data-dir={OUT / 'profile'}",
        "--window-size=443,1300", f"--screenshot={raw}",
        "--virtual-time-budget=4000", f.as_uri(),
    ], capture_output=True)
    # Windows 上无头截图左侧有固定 68px 空白偏移，裁掉
    from PIL import Image
    im = Image.open(raw)
    w, h = im.size
    im.crop((max(0, w - 375), 0, w, h)).save(OUT / f"{name}.png")
    raw.unlink(missing_ok=True)
    print("rendered", name)


if __name__ == "__main__":
    render("index", INDEX)
    render("result", RESULT)
    render("mine", MINE)
