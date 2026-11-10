Component({
  properties: {
    // 上下留白，单位 rpx
    gap: { type: Number, value: 24 }
  },
  data: {
    adUnitId: ''
  },
  lifetimes: {
    attached() {
      const app = getApp()
      const units = (app && app.globalData.adUnits) || {}
      this.setData({ adUnitId: units.banner || '' })
    }
  },
  methods: {
    onError(e) {
      console.warn('[ad] banner error', e.detail)
      this.setData({ adUnitId: '' })
    }
  }
})
