const store = require('../../utils/store')
const fmt = require('../../utils/format')
const api = require('../../utils/api')

Page({
  data: {
    navTop: 0,
    list: []
  },

  onLoad() {
    this.setData({ navTop: getApp().globalData.statusBarHeight })
  },

  onShow() {
    this.refresh()
  },

  refresh() {
    const list = store.getHistory().map((it) => ({
      ...it,
      kindText: it.kind === 'images' ? '图集' : fmt.duration(it.duration),
      timeText: fmt.timeAgo(it.ts)
    }))
    this.setData({ list })
  },

  async onOpen(e) {
    const id = e.currentTarget.dataset.id
    if (store.remain() <= 0) {
      wx.showToast({ title: '次数不足，去「我的」看广告加次数', icon: 'none' })
      return
    }
    wx.showLoading({ title: '重新解析', mask: true })
    try {
      const item = await api.parse('https://www.douyin.com/video/' + id)
      store.consumeOnce()
      getApp().globalData.currentItem = item
      wx.hideLoading()
      wx.navigateTo({ url: '/pages/result/result?id=' + id })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: err.message || '解析失败', icon: 'none' })
    }
  },

  onRemove(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '删除这条记录？',
      content: '只删除本地记录，不影响已经保存的视频。',
      confirmText: '删除',
      confirmColor: '#E0523D',
      success: (r) => {
        if (!r.confirm) return
        store.removeHistory(id)
        this.refresh()
      }
    })
  },

  onClear() {
    wx.showModal({
      title: '清空全部记录？',
      content: '这个操作不可恢复，已保存到相册的视频不受影响。',
      confirmText: '清空',
      confirmColor: '#E0523D',
      success: (r) => {
        if (!r.confirm) return
        store.clearHistory()
        this.refresh()
      }
    })
  },

  onBack() {
    wx.navigateBack({ fail: () => wx.reLaunch({ url: '/pages/index/index' }) })
  },

  goHome() {
    wx.reLaunch({ url: '/pages/index/index' })
  }
})
