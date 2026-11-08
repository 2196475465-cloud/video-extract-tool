Page({
  data: {
    navTop: 0,
    tab: 'help',
    disclaimer: '',
    steps: [
      { n: '1', title: '在抖音复制链接', desc: '打开要保存的视频，点右侧「分享」，选择「复制链接」' },
      { n: '2', title: '回到小程序粘贴', desc: '点首页的「一键粘贴」，或者手动粘贴到输入框' },
      { n: '3', title: '开始提取', desc: '点「开始提取」，通常 1 秒内出结果' },
      { n: '4', title: '保存到相册', desc: '在结果页点保存，第一次会申请相册权限，允许即可' }
    ],
    faqs: [
      { q: '为什么提示「没识别到链接」？', a: '确认复制的是抖音的完整分享文案，里面必须带 v.douyin.com 或 douyin.com 的链接。只有标题文字是不行的。', open: false },
      { q: '提示「作品不存在或已被删除」？', a: '这条视频可能被作者删除、设为私密，或者分享链接已过期。换一条视频再试。', open: false },
      { q: '为什么保存按钮要我先看广告？', a: '服务器和带宽都是自费的，看一次短广告可以覆盖一部分成本。每天也有若干次免费额度，先用完免费额度。', open: false },
      { q: '保存的视频在哪里？', a: '安卓一般在相册的「视频」或「最近」里，iPhone 在「照片」App 的最近项目或「视频」相簿里。', open: false },
      { q: '支持图集和原声吗？', a: '支持。图集可以一次保存全部图片，原声可以单独保存。', open: false },
      { q: '解析很慢是什么原因？', a: '视频时长较长、当前网络较慢时会慢一些。如果一直卡住，返回重试一次，或者看下网络。', open: false }
    ]
  },

  onLoad(options) {
    const app = getApp()
    this.setData({
      navTop: app.globalData.statusBarHeight,
      tab: options.tab === 'disclaimer' ? 'disclaimer' : 'help',
      disclaimer: (app.globalData.app || {}).disclaimer ||
        '本工具仅用于个人学习与备份，请勿用于商业传播。视频版权归原作者所有。'
    })
  },

  toggleFaq(e) {
    const index = e.currentTarget.dataset.index
    const faqs = this.data.faqs.map((item, i) => ({ ...item, open: i === index ? !item.open : false }))
    this.setData({ faqs })
  },

  onBack() {
    wx.navigateBack({ fail: () => wx.reLaunch({ url: '/pages/index/index' }) })
  }
})
