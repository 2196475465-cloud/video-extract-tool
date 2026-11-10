/**
 * 小程序配置
 *
 * baseUrl 说明：
 *   本地调试 - 填电脑的局域网地址（手机才能连上），例如 http://172.20.10.3:8000
 *              电脑上用 http://127.0.0.1:8000 或 localhost 都行
 *   上线之后 - 填你的 HTTPS 域名，例如 https://api.yourdomain.com
 *
 * 小技巧：真机预览时如果 IP 变了，不用改代码重新预览，
 *        在「我的 → 服务器地址」里改一下就行（会存本地，优先于这里）。
 */
module.exports = {
  // 真机调试：填电脑的局域网地址（换网络会被 DHCP 改掉，随时在「我的」里改）
  baseUrl: 'http://192.168.146.3:8000',

  // 开发者工具模拟器：固定走本机回环，不受 IP 变化影响
  devBaseUrl: 'http://127.0.0.1:8000',

  // 广告位 ID，留空则不展示（也可以在运营后台配置，后台优先级更高）
  adUnits: {
    rewarded: '',
    banner: '',
    interstitial: ''
  },

  // 默认每天免费次数，服务端 /api/config 会覆盖
  freePerDay: 3,

  version: '1.0.0'
}
