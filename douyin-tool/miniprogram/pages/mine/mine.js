const store = require('../../utils/store')
const ad = require('../../utils/ad')
const api = require('../../utils/api')
const config = require('../../config')

Page({
  data: {
    navTop: 0,
    quota: { remain: 0, freeUsed: 0, freeTotal: 3, bonus: 0, canWatchAd: true },
    freePercent: 0,
    adOnce: 1,
    totalCount: 0,
    serviceWechat: '',
    version: config.version
  },

  onLoad() {
    this.setData({ navTop: getApp().globalData.statusBarHeight })
  },

  onShow() {
    this.refresh()
    const app = getApp().globalData.app || {}
    this.setData({ serviceWechat: app.service_wechat || '' })
  },

  refresh() {
    const quota = store.quotaInfo()
    const limits = getApp().globalData.limits || {}
    const percent = quota.freeTotal > 0
      ? Math.min(100, Math.round((quota.freeUsed / quota.freeTotal) * 100))
      : 0
    this.setData({
      quota,
      freePercent: percent,
      adOnce: limits.ad_unlock_per_view || 1,
      totalCount: store.getHistory().length
    })
  },

  async onWatchAd() {
    if (!store.canWatchAd()) {
      wx.showToast({ title: '今天广告次数用完了，明天再来', icon: 'none' })
      return
    }
    const res = await ad.showRewarded()
    if (res.ok) {
      const once = (getApp().globalData.limits || {}).ad_unlock_per_view || 1
      store.addBonus(once)
      this.refresh()
      wx.showToast({ title: '已增加 ' + once + ' 次', icon: 'success' })
    } else if (res.reason === 'skip') {
      wx.showToast({ title: '完整看完才送次数', icon: 'none' })
    }
  },

  goHelp() {
    wx.navigateTo({ url: '/pages/help/help' })
  },

  goDisclaimer() {
    wx.navigateTo({ url: '/pages/help/help?tab=disclaimer' })
  },

  onFeedback() {
    wx.showModal({
      title: '意见反馈',
      editable: true,
      placeholderText: '遇到什么问题？或者想要什么功能？',
      success: async (r) => {
        if (!r.confirm) return
        const content = (r.content || '').trim()
        if (content.length < 2) {
          wx.showToast({ title: '多写两个字吧', icon: 'none' })
          return
        }
        try {
          await api.feedback(content, '')
          wx.showToast({ title: '已收到，谢谢', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: '提交失败，稍后再试', icon: 'none' })
        }
      }
    })
  },

  onCopyWechat() {
    const wx2 = this.data.serviceWechat
    if (!wx2) return
    wx.setClipboardData({ data: wx2, success: () => wx.showToast({ title: '微信号已复制', icon: 'success' }) })
  },

  onClearCache() {
    wx.showModal({
      title: '清理本地缓存？',
      content: '会清掉提取记录和今日额度统计，不影响已保存的视频。',
      success: (r) => {
        if (!r.confirm) return
        store.clearHistory()
        wx.removeStorageSync('quota')
        wx.removeStorageSync('remote_config')
        this.refresh()
        wx.showToast({ title: '已清理', icon: 'success' })
      }
    })
  },

  onBack() {
    wx.navigateBack({ fail: () => wx.reLaunch({ url: '/pages/index/index' }) })
  }
})
