/** 与服务端通信 */

const { getDeviceId } = require('./store')

function baseUrl() {
  const app = getApp()
  return (app && app.globalData.baseUrl) || ''
}

function post(path, data, timeout = 30000) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: baseUrl() + path,
      method: 'POST',
      data: data || {},
      timeout,
      header: { 'content-type': 'application/json' },
      success: (res) => {
        if (res.statusCode !== 200) {
          reject(new Error('服务繁忙（' + res.statusCode + '）'))
          return
        }
        resolve(res.data || {})
      },
      fail: (err) => {
        const msg = (err && err.errMsg) || ''
        if (msg.indexOf('timeout') >= 0) {
          reject(new Error('解析超时了，稍后再试'))
        } else {
          reject(new Error('网络不太好，检查一下网络'))
        }
      }
    })
  })
}

/** 解析分享文案，返回作品数据 */
async function parse(text) {
  const res = await post('/api/parse', { url: text, device: getDeviceId() }, 45000)
  if (res.code !== 0) {
    const err = new Error(res.msg || '解析失败')
    err.codeType = res.code_type || 'unknown'
    throw err
  }
  return res.data
}

function feedback(content, contact) {
  return post('/api/feedback', { content, contact, device: getDeviceId() })
}

module.exports = { parse, feedback, post }
