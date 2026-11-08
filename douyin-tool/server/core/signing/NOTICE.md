# NOTICE · 第三方代码说明

本目录下的 `core/signing/abogus.py` 与 `core/signing/sm3.py` 来自开源项目：

- 项目：Evil0ctal / Douyin_TikTok_Download_API
- 地址：https://github.com/Evil0ctal/Douyin_TikTok_Download_API
- 许可证：Apache License 2.0
- 用途：计算抖音 Web 接口的 `a_bogus` 签名参数

原始文件路径：
- `src/dtk/signing/native/abogus.py`
- `src/dtk/signing/native/sm3.py`

按 Apache-2.0 要求保留原始版权声明与许可文本，本项目的修改仅为调整模块内相对导入路径。

完整许可证文本见项目根目录 `upstream/LICENSE`，或访问：
http://www.apache.org/licenses/LICENSE-2.0

注意：签名算法会随平台更新而变化。若某天解析大量失败并提示签名相关错误，
请同步上游项目的最新实现。
