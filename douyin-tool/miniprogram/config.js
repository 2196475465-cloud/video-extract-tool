/**
 * 小程序配置
 * 部署后端后，把 baseUrl 改成你自己的 HTTPS 域名（需在小程序后台配置 request / downloadFile 合法域名）
 */
module.exports = {
  // 例如 https://api.yourdomain.com
  baseUrl: 'http://127.0.0.1:8000',

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
