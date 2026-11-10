/**
 * 隐私授权
 *
 * 微信 2023-09 起要求：调用相册、剪贴板等隐私接口前，必须先获得用户同意，
 * 否则接口直接 fail（不弹任何提示，表现为「点了没反应」）。
 *
 * wx.requirePrivacyAuthorize 会拉起官方隐私弹窗，用户同意后返回 success。
 * 基础库 2.32.3 以下没有这个 API，直接放行。
 */
function requirePrivacy() {
  return new Promise((resolve) => {
    if (!wx.requirePrivacyAuthorize) {
      resolve(true)
      return
    }
    wx.requirePrivacyAuthorize({
      success: () => resolve(true),
      fail: () => resolve(false)
    })
  })
}

module.exports = { requirePrivacy }
