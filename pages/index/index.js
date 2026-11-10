const api = require('../../utils/api')
const store = require('../../utils/store')
const ad = require('../../utils/ad')
const fmt = require('../../utils/format')
const privacy = require('../../utils/privacy')

const LOADING_TEXTS = ['正在读取作品…', '正在获取原片地址…', '马上就好…']

Page({
  data: {
    navTop: 0,
    maxLen: 600,
    text: '',
    len: 0,
    loading: false,
    loadingText: LOADING_TEXTS[0],
    quota: { remain: 0, adOnce: 1 },
    history: [],
    notice: '',
    steps: [
      { icon: 'link', title: '复制链接', desc: '抖音点分享' },
      { icon: 'paste', title: '粘贴提取', desc: '自动识别链接' },
      { icon: 'download', title: '存进相册', desc: '一键保存原片' }
    ]
  },

  onLoad() {
    const app = getApp()
    this.setData({ navTop: app.globalData.statusBarHeight })
    this._timer = null
  },

  onShow() {
    this.refreshQuota()
    this.refreshHistory()
    this.setData({ notice: (getApp().globalData.app || {}).notice || '' })
  },

  onUnload() {
    if (this._timer) clearInterval(this._timer)
  },

  // ---------------- 数据 ----------------
  refreshQuota() {
    const info = store.quotaInfo()
    const limits = getApp().globalData.limits || {}
    this.setData({ quota: { ...info, adOnce: limits.ad_unlock_per_view || 1 } })
  },

  refreshHistory() {
    const list = store.getHistory().slice(0, 8).map((it) => ({
      ...it,
      durText: fmt.duration(it.duration)
    }))
    this.setData({ history: list })
  },

  // ---------------- 输入 ----------------
  onInput(e) {
    const text = e.detail.value
    this.setData({ text, len: text.length })
  },

  onClear() {
    this.setData({ text: '', len: 0 })
  },

  async onPaste() {
    const agreed = await privacy.requirePrivacy()
    if (!agreed) {
      wx.showToast({ title: '需要同意隐私协议才能读取剪贴板', icon: 'none' })
      return
    }
    wx.getClipboardData({
      success: (res) => {
        const data = (res.data || '').trim()
        if (!data) {
          wx.showToast({ title: '剪贴板是空的', icon: 'none' })
          return
        }
        if (!/douyin\.com|iesdouyin|kuaishou|xhslink/i.test(data)) {
          wx.showToast({ title: '没识别到链接，确认复制的是分享文案', icon: 'none' })
          return
        }
        this.setData({ text: data, len: data.length })
        wx.showToast({ title: '已粘贴', icon: 'success' })
      },
      fail: () => wx.showToast({ title: '读取剪贴板失败', icon: 'none' })
    })
  },

  // ---------------- 提取 ----------------
  async onParse() {
    if (this.data.loading) return
    const text = (this.data.text || '').trim()
    if (!text) {
      wx.showToast({ title: '先粘贴分享链接', icon: 'none' })
      return
    }

    if (store.remain() <= 0) {
      this.onWatchAd()
      return
    }

    this.startLoading()
    try {
      const item = await api.parse(text)
      this.stopLoading()
      store.consumeOnce()
      store.pushHistory(item)
      this.refreshQuota()
      this.refreshHistory()
      getApp().globalData.currentItem = item
      wx.navigateTo({ url: '/pages/result/result?id=' + item.id })
      this.setData({ text: '', len: 0 })
    } catch (err) {
      this.stopLoading()
      this.showError(err)
    }
  },

  showError(err) {
    const msg = (err && err.message) || '解析失败'
    const code = err && err.codeType
    if (code === 'user_link') {
      wx.showModal({
        title: '这是主页链接',
        content: '请打开要下载的那条视频，点「分享 → 复制链接」再粘贴过来。',
        showCancel: false,
        confirmText: '知道了'
      })
      return
    }
    if (code === 'not_found') {
      wx.showModal({
        title: '作品不可用',
        content: '这条视频可能被作者删除、设为私密，或链接已过期。换一条试试。',
        showCancel: false,
        confirmText: '好'
      })
      return
    }
    wx.showToast({ title: msg, icon: 'none', duration: 2200 })
  },

  startLoading() {
    let i = 0
    this.setData({ loading: true, loadingText: LOADING_TEXTS[0] })
    wx.vibrateShort && wx.vibrateShort({ type: 'light' })
    this._timer = setInterval(() => {
      i = (i + 1) % LOADING_TEXTS.length
      this.setData({ loadingText: LOADING_TEXTS[i] })
    }, 1200)
  },

  stopLoading() {
    if (this._timer) clearInterval(this._timer)
    this._timer = null
    this.setData({ loading: false })
  },

  // ---------------- 广告 ----------------
  async onWatchAd() {
    if (this.data.watching) return
    if (!store.canWatchAd()) {
      wx.showToast({ title: '今天的次数用完了，明天再来', icon: 'none' })
      return
    }
    this.setData({ watching: true })
    const res = await ad.showRewarded()
    this.setData({ watching: false })

    if (res.ok) {
      const limits = getApp().globalData.limits || {}
      const once = limits.ad_unlock_per_view || 1
      store.addBonus(once)
      this.refreshQuota()
      wx.showToast({ title: '已增加 ' + once + ' 次', icon: 'success' })
    } else if (res.reason === 'skip') {
      wx.showToast({ title: '完整看完才送次数哦', icon: 'none' })
    }
  },

  // ---------------- 导航 ----------------
  onQuotaTap() {
    if (this.data.quota.remain > 0) {
      this.goMine()
    } else {
      this.onWatchAd()
    }
  },

  goHistory() {
    wx.navigateTo({ url: '/pages/history/history' })
  },

  goMine() {
    wx.navigateTo({ url: '/pages/mine/mine' })
  },

  goHelp() {
    wx.navigateTo({ url: '/pages/help/help' })
  },

  openHistory(e) {
    const id = e.currentTarget.dataset.id
    const it = store.getHistory().find((x) => x.id === id)
    if (!it) return
    if (store.remain() <= 0) {
      wx.showToast({ title: '次数不足，先看个广告', icon: 'none' })
      return
    }
    this.setData({ text: 'https://www.douyin.com/video/' + id, len: 40 })
    this.onParse()
  },

  onShareAppMessage() {
    return {
      title: '短视频提取 · 一键保存无水印原片',
      path: '/pages/index/index'
    }
  }
})
