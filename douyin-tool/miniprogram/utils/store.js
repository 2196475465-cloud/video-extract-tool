/** 本地存储：设备号、每日额度、历史记录 */

const KEY_DEVICE = 'device_id'
const KEY_QUOTA = 'quota'
const KEY_HISTORY = 'history'
const HISTORY_MAX = 30

function todayStr() {
  const d = new Date()
  const p = (n) => (n < 10 ? '0' + n : '' + n)
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate())
}

function getDeviceId() {
  let id = wx.getStorageSync(KEY_DEVICE)
  if (!id) {
    id = 'd_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
    wx.setStorageSync(KEY_DEVICE, id)
  }
  return id
}

function getLimits() {
  const app = getApp()
  return (app && app.globalData.limits) || { free_per_day: 3, ad_unlock_per_day: 10, ad_unlock_per_view: 1 }
}

function getQuota() {
  const raw = wx.getStorageSync(KEY_QUOTA)
  const today = todayStr()
  if (!raw || raw.date !== today) {
    return { date: today, freeUsed: 0, adUsed: 0, bonus: 0 }
  }
  return raw
}

function saveQuota(q) {
  wx.setStorageSync(KEY_QUOTA, q)
  return q
}

/** 剩余可用次数 = 免费剩余 + 看广告攒的次数 */
function remain() {
  const q = getQuota()
  const limits = getLimits()
  const freeLeft = Math.max(0, limits.free_per_day - q.freeUsed)
  return freeLeft + Math.max(0, q.bonus)
}

function canWatchAd() {
  const q = getQuota()
  const limits = getLimits()
  return q.adUsed < limits.ad_unlock_per_day
}

function consumeOnce() {
  const q = getQuota()
  const limits = getLimits()
  if (q.freeUsed < limits.free_per_day) {
    q.freeUsed += 1
  } else if (q.bonus > 0) {
    q.bonus -= 1
  } else {
    return false
  }
  saveQuota(q)
  return true
}

function addBonus(count) {
  const q = getQuota()
  const limits = getLimits()
  q.bonus += count
  q.adUsed += 1
  saveQuota(q)
  return Math.max(0, limits.ad_unlock_per_day - q.adUsed)
}

function quotaInfo() {
  const q = getQuota()
  const limits = getLimits()
  return {
    remain: remain(),
    freeTotal: limits.free_per_day,
    freeUsed: q.freeUsed,
    bonus: q.bonus,
    adUsed: q.adUsed,
    adTotal: limits.ad_unlock_per_day,
    canWatchAd: canWatchAd()
  }
}

function pushHistory(item) {
  const list = getHistory()
  const next = [{
    id: item.id,
    title: item.title,
    cover: item.cover,
    author: item.author && item.author.name,
    kind: item.kind,
    duration: item.duration,
    ts: Date.now()
  }].concat(list.filter((x) => x.id !== item.id)).slice(0, HISTORY_MAX)
  wx.setStorageSync(KEY_HISTORY, next)
  return next
}

function getHistory() {
  const list = wx.getStorageSync(KEY_HISTORY)
  return Array.isArray(list) ? list : []
}

function removeHistory(id) {
  const next = getHistory().filter((x) => x.id !== id)
  wx.setStorageSync(KEY_HISTORY, next)
  return next
}

function clearHistory() {
  wx.removeStorageSync(KEY_HISTORY)
}

module.exports = {
  todayStr,
  getDeviceId,
  getQuota,
  remain,
  canWatchAd,
  consumeOnce,
  addBonus,
  quotaInfo,
  pushHistory,
  getHistory,
  removeHistory,
  clearHistory
}
