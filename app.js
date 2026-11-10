const config = require('./config')
const { getDeviceId, getApiBase } = require('./utils/store')

App({
  globalData: {
    baseUrl: config.baseUrl,
    devBaseUrl: config.devBaseUrl || 'http://127.0.0.1:8000',
    adUnits: { ...config.adUnits },
    limits: { free_per_day: config.freePerDay, ad_unlock_per_day: 10, ad_unlock_per_view: 1 },
    app: { notice: '', service_wechat: '', disclaimer: '' },
    statusBarHeight: 20,
    navHeight: 44,
    deviceId: ''
  },

  onLaunch() {
    // getSystemInfoSync 已废弃，优先用 getWindowInfo，旧基础库回退
    let win = {}
    try {
      win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
    } catch (e) {
      win = {}
    }
    const statusBarHeight = win.statusBarHeight || 20
    const menu = wx.getMenuButtonBoundingClientRect
      ? wx.getMenuButtonBoundingClientRect()
      : null

    this.globalData.statusBarHeight = statusBarHeight
    this.globalData.navHeight = menu && menu.top
      ? menu.bottom + (menu.top - statusBarHeight)
      : 44 + statusBarHeight
    this.globalData.deviceId = getDeviceId()

    // 先用本地缓存跑起来，再静默拉最新配置
    const cached = wx.getStorageSync('remote_config')
    if (cached && cached.ads) {
      this.globalData.adUnits = {
        rewarded: cached.ads.rewarded_video || config.adUnits.rewarded,
        banner: cached.ads.banner || config.adUnits.banner,
        interstitial: cached.ads.interstitial || config.adUnits.interstitial
      }
      this.globalData.limits = cached.limits || this.globalData.limits
      this.globalData.app = cached.app || this.globalData.app
    }
    this.syncConfig()
  },

  /** 模拟器走本机回环，真机走局域网地址 */
  apiBase() {
    const local = getApiBase()
    if (local) return local
    let isDev = false
    try {
      const info = wx.getDeviceInfo ? wx.getDeviceInfo() : wx.getSystemInfoSync()
      isDev = (info.platform || '').toLowerCase() === 'devtools'
    } catch (e) {
      isDev = false
    }
    return isDev ? this.globalData.devBaseUrl : this.globalData.baseUrl
  },

  syncConfig() {
    const base = this.apiBase()
    wx.request({
      url: base + '/api/config',
      timeout: 8000,
      success: (res) => {
        const data = res.data && res.data.data
        if (!data) return
        this.globalData.adUnits = {
          rewarded: data.ads.rewarded_video || config.adUnits.rewarded,
          banner: data.ads.banner || config.adUnits.banner,
          interstitial: data.ads.interstitial || config.adUnits.interstitial
        }
        this.globalData.limits = data.limits || this.globalData.limits
        this.globalData.app = data.app || this.globalData.app
        wx.setStorageSync('remote_config', data)
      }
    })
  }
})
