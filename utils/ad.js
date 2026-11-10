/** 广告封装：激励视频 / 插屏 / Banner 广告位读取 */

const adCache = {}
let interstitial = null

function units() {
  const app = getApp()
  return (app && app.globalData.adUnits) || {}
}

function unitId(kind) {
  return units()[kind] || ''
}

function getRewarded() {
  const id = unitId('rewarded')
  if (!id || !wx.createRewardedVideoAd) return null
  if (!adCache[id]) {
    const ad = wx.createRewardedVideoAd({ adUnitId: id })
    ad.onError((err) => console.warn('[ad] rewarded error', err))
    adCache[id] = ad
  }
  return adCache[id]
}

/**
 * 展示激励视频
 * @returns {Promise<{ok:boolean, reason:string}>} ok 表示是否发放奖励
 *   no_ad   未配置广告位（直接放行）
 *   done    完整看完
 *   skip    中途关闭
 *   ad_fail 广告拉取失败（放行，避免用户卡住）
 */
function showRewarded() {
  return new Promise((resolve) => {
    const ad = getRewarded()
    if (!ad) {
      resolve({ ok: true, reason: 'no_ad' })
      return
    }
    let settled = false
    const finish = (result) => {
      if (settled) return
      settled = true
      ad.offClose(onClose)
      resolve(result)
    }
    const onClose = (res) => {
      const ended = !res || res.isEnded === true
      finish({ ok: ended, reason: ended ? 'done' : 'skip' })
    }
    ad.onClose(onClose)
    ad.show()
      .catch(() => ad.load().then(() => ad.show()).catch(() => finish({ ok: true, reason: 'ad_fail' })))
    setTimeout(() => finish({ ok: true, reason: 'ad_fail' }), 15000)
  })
}

function showInterstitial() {
  const id = unitId('interstitial')
  if (!id || !wx.createInterstitialAd) return
  try {
    if (!interstitial) {
      interstitial = wx.createInterstitialAd({ adUnitId: id })
      interstitial.onError((err) => console.warn('[ad] interstitial error', err))
    }
    interstitial.show().catch(() => {})
  } catch (e) {
    // 广告失败不影响主流程
  }
}

module.exports = { showRewarded, showInterstitial, unitId }
