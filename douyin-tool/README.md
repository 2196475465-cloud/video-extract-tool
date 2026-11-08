# 短视频提取（抖音无水印原片）· 小程序 + 后端

一个完整可跑的「复制抖音链接 → 提取无水印原片 → 保存到相册」小程序项目，
带激励视频广告位、每日额度、运营后台和解析统计。

## 这东西是怎么跑通的

抖音 2026 年起给 Web 接口加了风控（`Blocked by ArgusSecurityPlugin Uifid Not Found`），
纯服务端请求即使签名正确也会被拦。本项目的做法是：

```
小程序 ──粘贴链接──▶ 后端
                     ├─ 1. 解析短链，拿到作品 ID（纯 HTTP，毫秒级）
                     ├─ 2. 复用本机 Chrome 打开一个抖音页面（预热一次）
                     ├─ 3. 在页面上下文里 fetch 官方详情接口，SDK 自动签名
                     ├─ 4. 取 play_addr 里的无水印直链，归一化后返回
                     └─ 5. 签名生成下载地址，反代 CDN 流量吐给小程序
```

实测：预热后单条解析 **0.2 ~ 0.5 秒**，无需登录、无需维护 Cookie。
代价是服务器上要有一个 Chrome（无头模式，约 300MB 内存）。

## 三个入口，手机电脑都能用

| 入口 | 打开方式 | 保存到哪 | 适合 |
| --- | --- | --- | --- |
| 微信小程序（手机） | 微信搜索 / 扫码 | 手机相册 | 手机日常使用 |
| 微信小程序（电脑版微信） | PC 微信打开同一个小程序 | 弹「另存为」，可自己选文件夹 | 电脑上顺手用 |
| 网页版 | 浏览器打开 `https://你的域名/` | 浏览器下载目录（Chrome 可设「每次询问保存位置」） | 电脑主力、长视频 |

网页版由后端直接托管（`server/web/index.html`），和小程序共用同一套解析接口，
手机浏览器、电脑浏览器都能打开，不需要装任何东西。

同一局域网内手机预览：

```bash
# 电脑上先跑起来
python app.py
# 手机浏览器访问（把 IP 换成电脑的局域网地址）
http://192.168.x.x:8000/
```

电脑端保存的差异说明：

- 小程序在 Windows/Mac 微信里没有「相册」，代码已自动切换成 `wx.saveFileToDisk`，
  点保存会弹系统另存为窗口，文件夹、文件名都能改
- 微信小程序下载单个文件上限 200MB，超长视频用网页版没有这个限制
- iPhone 上用网页版下载视频会先在浏览器里播放，长按画面选「存储到照片」

## 目录结构

```
douyin-tool/
├── server/                  后端（Python 标准库，零第三方依赖）
│   ├── app.py               入口：路由、下载代理、后台接口、网页版托管
│   ├── web/index.html       网页版（手机/电脑浏览器打开即用）
│   ├── config.json          配置（首次运行自动生成，含后台密码）
│   ├── core/
│   │   ├── browser.py       CDP 浏览器池（自己实现的 WebSocket 客户端）
│   │   ├── douyin.py        短链解析、详情归一化
│   │   ├── db.py            SQLite：记录、缓存、反馈
│   │   ├── settings.py      配置热加载
│   │   ├── admin.py         运营后台页面
│   │   └── signing/         a_bogus 签名（Apache-2.0，见 NOTICE.md）
│   └── data/data.db         运行后生成
├── miniprogram/             微信小程序
│   ├── pages/index          首页：粘贴、提取、额度
│   ├── pages/result         结果页：预览、保存、广告解锁
│   ├── pages/history        提取记录
│   ├── pages/mine           我的：额度、反馈、客服
│   ├── pages/help           使用帮助 / 免责声明
│   ├── components/ad-banner Banner 广告位组件
│   ├── utils/               请求、广告、本地存储、格式化
│   └── config.js            ← 改这里的 baseUrl
├── docs/
│   ├── 部署指南.md
│   ├── 小程序上线与广告接入.md
│   └── 维护手册.md
├── upstream/                参考的开源项目（21.2k stars，仅作对照）
└── tools/preview.py         把页面渲染成图片，本地看效果
```

## 5 分钟跑起来

**后端**

```bash
cd server
python app.py
```

首次启动会打印后台地址和密码：

```
[ok] 后台地址：http://0.0.0.0:8000/admin?token=xxxxxxxx
```

浏览器打开它，粘一条抖音分享文案点「开始解析」，能看到封面、标题和视频预览，
说明链路通了。

> Windows 上 Chrome 一般在默认路径，会自动找到。找不到就在 `config.json` 里
> 把 `parse.chrome_path` 填成 `C:\Program Files\Google\Chrome\Application\chrome.exe`。

**小程序**

1. 用微信开发者工具打开 `miniprogram/` 目录
2. 填自己的 AppID（没有就先用测试号）
3. 详情 → 本地设置 → 勾选「不校验合法域名」
4. 点首页「一键粘贴」→「开始提取」

正式发布前，把 `miniprogram/config.js` 的 `baseUrl` 改成你的 HTTPS 域名。

## 参考的开源项目

| 项目 | Stars | 用到了什么 |
| --- | --- | --- |
| [Evil0ctal/Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) | 21.2k | a_bogus 签名实现、抖音接口参数集（Apache-2.0） |
| [JoeanAmier/TikTokDownloader](https://github.com/JoeanAmier/TikTokDownloader) | 17.4k | 参数与字段结构的对照参考 |

`upstream/` 里保留了一份完整克隆，方便平台更新后对照。它功能更全（TikTok、B站、
直播、评论采集），但需要 PostgreSQL + 浏览器 RPC，体量比这个项目大得多。
如果你后面要做批量下载、评论导出，可以直接把它当引擎用。

## 几个必须知道的点

1. **抖音会改**。风控参数、`version_code`、接口路径都可能变。`config.json` 里的
   `parse.version_code` 之类的值更新时，参考 `upstream/src/dtk/platforms/douyin/`。
2. **小程序审核**。「去水印」这个词在审核里比较敏感，类目建议选「工具 - 图片/视频处理」，
   名称用「××提取」「视频助手」这类，功能描述写「视频链接解析与本地保存」。
3. **广告门槛**。开通流量主要小程序累计独立访客 ≥ 1000，之后才能在后台创建广告位。
4. **合规**。工具本身只做「解析 + 下载」，但下载他人作品再传播涉及著作权。
   小程序内已内置免责声明，实际运营时别做搬运号引流那套。

细化的部署与运维见 `docs/` 下三份文档。
