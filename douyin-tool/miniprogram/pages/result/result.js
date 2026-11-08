const api = require('../../utils/api')
const ad = require('../../utils/ad')
const fmt = require('../../utils/format')

/** 电脑端（Windows / Mac 微信）没有「相册」，要用保存到磁盘 */
function isDesktop() {
  try {
    const info = wx.getDeviceInfo ? wx.getDeviceInfo() : wx.getSystemInfoSync()
    const p = (info.platform || '').toLowerCase()
    return p === 'windows' || p === 'mac'
  } catch (e) {
    return false
  }
}

const IS_PC = isDesktop()

Page({
  data: {
    navTop: 0,
    item: null,
    durText: '',
    diggText: '',
    saving: false,
    needAd: false,
    unlocked: false,
    isPC: IS_PC
  },

  onLoad(options) {
    const app = getApp()
    this.setData({ navTop: app.globalData.statusBarHeight })
    this.applyItem(app.globalData.currentItem)
    this.setNeedAd()
    if (!this.data.item && options.id) {
      this.loadById(options.id)
    }
  },

  applyItem(item) {
    if (!item) return
    this.setData({
      item,
      durText: fmt.duration(item.duration),
      diggText: fmt.num(item.stats && item.stats.digg)
    })
  },

  setNeedAd() {
    const app = getApp()
    const units = app.globalData.adUnits || {}
    const adsOn = (app.globalData.limits && app.globalData.limits.ad_enabled) !== false
    const need = !this.data.unlocked && adsOn && !!units.rewarded
    this.setData({ needAd: need })
  },

  async loadById(id) {
    wx.showLoading({ title: '重新解析中', mask: true })
    try {
      const item = await api.parse('https://www.douyin.com/video/' + id)
      this.applyItem(item)
      this.setNeedAd()
      getApp().globalData.currentItem = item
    } catch (e) {
      wx.showToast({ title: e.message || '解析失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  // ---------------- 解锁 ----------------
  async ensureUnlocked() {
    if (!this.data.needAd) return true
    const res = await ad.showRewarded()
    if (res.ok) {
      this.setData({ unlocked: true, needAd: false })
      return true
    }
    if (res.reason === 'skip') {
      wx.showToast({ title: '看完广告才能保存哦', icon: 'none' })
    }
    return false
  },

  // ---------------- 保存 ----------------
  async onSaveMain() {
    if (this.data.saving) return
    const item = this.data.item
    if (!item) return
    const ok = await this.ensureUnlocked()
    if (!ok) return

    if (item.kind === 'images') {
      await this.saveImages(item.download.images)
    } else {
      await this.saveVideo(item.download.video)
    }
    ad.showInterstitial()
  },

  async saveVideo(url) {
    if (!url) {
      wx.showToast({ title: '没有可保存的视频', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    try {
      const filePath = await this.download(url, 'video')
      await this.saveToAlbum(filePath, 'video')
      wx.showToast({ title: '已保存到相册', icon: 'success' })
    } catch (e) {
      this.handleSaveError(e)
    } finally {
      this.setData({ saving: false })
    }
  },

  async saveImages(urls) {
    if (!urls || !urls.length) {
      wx.showToast({ title: '没有可保存的图片', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    let done = 0
    for (let i = 0; i < urls.length; i++) {
      try {
        wx.showLoading({ title: '保存 ' + (i + 1) + '/' + urls.length, mask: true })
        const filePath = await this.download(urls[i], 'image')
        await this.saveToAlbum(filePath, 'image')
        done += 1
      } catch (e) {
        // 单张失败继续
      }
    }
    wx.hideLoading()
    this.setData({ saving: false })
    if (done > 0) {
      wx.showToast({ title: '已保存 ' + done + ' 张', icon: 'success' })
    } else {
      this.handleSaveError(new Error('save_failed'))
    }
  },

  async onSaveCover() {
    const item = this.data.item
    if (!item || !item.download.cover) return
    const ok = await this.ensureUnlocked()
    if (!ok) return
    try {
      wx.showLoading({ title: '保存中', mask: true })
      const filePath = await this.download(item.download.cover, 'image')
      await this.saveToAlbum(filePath, 'image')
      wx.hideLoading()
      wx.showToast({ title: '封面已保存', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      this.handleSaveError(e)
    }
  },

  async onSaveMusic() {
    const item = this.data.item
    if (!item || !item.download.music) return
    const ok = await this.ensureUnlocked()
    if (!ok) return
    try {
      wx.showLoading({ title: '保存中', mask: true })
      const filePath = await this.download(item.download.music, 'file')
      await this.saveToAlbum(filePath, 'file')
      wx.hideLoading()
      wx.showToast({ title: '原声已保存', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      this.handleSaveError(e)
    }
  },

  download(url, type) {
    return new Promise((resolve, reject) => {
      const task = wx.downloadFile({
        url,
        timeout: 120000,
        success: (res) => {
          if (res.statusCode === 200 && res.tempFilePath) {
            resolve(res.tempFilePath)
          } else if (res.statusCode === 403) {
            reject(new Error('链接过期，返回重新解析'))
          } else {
            reject(new Error('下载失败（' + res.statusCode + '）'))
          }
        },
        fail: (err) => reject(new Error((err && err.errMsg) || '下载失败'))
      })
      if (task && task.onProgressUpdate) {
        task.onProgressUpdate((p) => {
          if (p.progress > 3 && p.progress < 100) {
            wx.showLoading({ title: '下载中 ' + p.progress + '%', mask: true })
          }
        })
      }
    })
  },

  saveToAlbum(filePath, type) {
    // 电脑端：直接存到电脑磁盘（wx.saveFileToDisk，基础库 2.16.0+）
    if (IS_PC) {
      return new Promise((resolve, reject) => {
        if (!wx.saveFileToDisk) {
          reject(new Error('当前微信版本太旧，请升级微信，或用浏览器打开网页版'))
          return
        }
        wx.saveFileToDisk({
          filePath,
          success: () => resolve(),
          fail: (err) => reject(new Error((err && err.errMsg) || '保存到电脑失败'))
        })
      })
    }

    return new Promise((resolve, reject) => {
      const done = (err) => {
        if (!err) {
          resolve()
          return
        }
        const msg = (err && err.errMsg) || ''
        if (msg.indexOf('auth deny') >= 0 || msg.indexOf('authorize') >= 0) {
          wx.hideLoading()
          wx.showModal({
            title: '需要相册权限',
            content: '保存原片需要访问相册，去设置里打开一下就好',
            confirmText: '去设置',
            success: (r) => {
              if (r.confirm) wx.openSetting()
            }
          })
          reject(new Error('auth'))
          return
        }
        reject(new Error(msg || '保存失败'))
      }
      if (type === 'video') {
        wx.saveVideoToPhotosAlbum({ filePath, success: () => done(null), fail: done })
      } else if (type === 'image') {
        wx.saveImageToPhotosAlbum({ filePath, success: () => done(null), fail: done })
      } else {
        wx.saveFile({
          tempFilePath: filePath,
          success: () => done(null),
          fail: done
        })
      }
    })
  },

  handleSaveError(e) {
    const msg = (e && e.message) || ''
    if (msg === 'auth') return
    if (msg.indexOf('过期') >= 0) {
      wx.showModal({
        title: '链接过期了',
        content: '视频地址有时效，返回首页重新提取一次就行。',
        confirmText: '重新提取',
        success: (r) => {
          if (r.confirm) wx.navigateBack()
        }
      })
      return
    }
    wx.showToast({ title: msg || '保存失败，再试一次', icon: 'none' })
  },

  // ---------------- 其它 ----------------
  onCopyText() {
    const item = this.data.item
    if (!item || !item.title) return
    wx.setClipboardData({
      data: item.title,
      success: () => wx.showToast({ title: '文案已复制', icon: 'success' })
    })
  },

  previewImage(e) {
    const src = e.currentTarget.dataset.src
    wx.previewImage({ current: src, urls: this.data.item.images })
  },

  onPlay() {
    // 播放时不做打断，保留给后续埋点
  },

  onBack() {
    wx.navigateBack({
      fail: () => wx.reLaunch({ url: '/pages/index/index' })
    })
  },

  onShareAppMessage() {
    const item = this.data.item
    return {
      title: (item && item.title) || '短视频提取 · 一键保存原片',
      path: '/pages/index/index',
      imageUrl: (item && item.cover) || ''
    }
  }
})
