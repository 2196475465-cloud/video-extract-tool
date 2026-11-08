"""运营后台页面（单文件，无外部依赖，直接由 app.py 吐出）。"""

ADMIN_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>去水印工具 · 运营后台</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--line:#e8eaef;--text:#16181d;--sub:#707684;--brand:#2f6bff;--ok:#0aa06e;--warn:#e0523d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 24px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:9}
header h1{font-size:16px;margin:0;font-weight:600}
.dot{width:8px;height:8px;border-radius:50%;background:var(--ok);display:inline-block}
.dot.off{background:var(--warn)}
.tag{font-size:12px;color:var(--sub)}
main{max-width:1080px;margin:0 auto;padding:20px 16px 60px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi b{display:block;font-size:24px;font-weight:650;letter-spacing:-.5px}
.kpi span{color:var(--sub);font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
.card h2{font-size:14px;margin:0 0 12px;font-weight:600;display:flex;justify-content:space-between;align-items:center}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
label.f{display:flex;flex-direction:column;gap:6px;font-size:12px;color:var(--sub);flex:1 1 220px}
input,textarea,select{font:inherit;padding:9px 11px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--text);width:100%}
input:focus,textarea:focus{outline:2px solid rgba(47,107,255,.18);border-color:#b9caff}
button{font:inherit;padding:9px 16px;border-radius:8px;border:1px solid var(--line);background:#fff;cursor:pointer;color:var(--text)}
button:hover{border-color:#c9d3e6}
button.primary{background:var(--brand);border-color:var(--brand);color:#fff}
button.ghost{background:#fafbfc}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--sub);font-weight:500;font-size:12px}
.bar{height:6px;background:#eef1f6;border-radius:4px;overflow:hidden;margin-top:6px}
.bar i{display:block;height:100%;background:var(--brand)}
.muted{color:var(--sub);font-size:12px}
.preview{display:flex;gap:14px;margin-top:12px}
.preview img{width:120px;border-radius:10px;border:1px solid var(--line);object-fit:cover}
.preview video{width:220px;border-radius:10px;border:1px solid var(--line);background:#000}
pre{background:#0f1116;color:#d8e0f0;padding:12px;border-radius:10px;overflow:auto;font-size:12px;max-height:280px}
.toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:#111;color:#fff;padding:10px 18px;border-radius:999px;font-size:13px;opacity:0;transition:.25s;pointer-events:none}
.toast.show{opacity:1}
.hide{display:none}
@media(max-width:600px){.preview{flex-direction:column}}
</style>
</head>
<body>
<header>
  <span class="dot" id="dot"></span><h1>去水印工具 · 运营后台</h1>
  <span class="tag" id="hstat">连接中…</span>
  <span style="flex:1"></span>
  <button class="ghost" id="btnRefresh">刷新</button>
</header>
<main>
  <div class="grid">
    <div class="kpi"><b id="kToday">–</b><span>今日解析</span></div>
    <div class="kpi"><b id="kRate">–</b><span>近 7 天成功率</span></div>
    <div class="kpi"><b id="kMs">–</b><span>平均耗时</span></div>
    <div class="kpi"><b id="kTotal">–</b><span>近 7 天总量</span></div>
    <div class="kpi"><b id="kCache">–</b><span>缓存条数</span></div>
  </div>

  <div class="card">
    <h2>测试解析 <span class="muted">把抖音分享文案粘进来</span></h2>
    <div class="row">
      <label class="f" style="flex:1 1 100%"><textarea id="testInput" rows="3" placeholder="3.14 复制打开抖音，看看【xxx的作品】… https://v.douyin.com/xxxx/"></textarea></label>
    </div>
    <div class="row" style="margin-top:10px">
      <button class="primary" id="btnTest">开始解析</button>
      <span class="muted" id="testMsg"></span>
    </div>
    <div id="testOut"></div>
  </div>

  <div class="card">
    <h2>广告位与次数 <span class="muted">改完保存，小程序下次启动生效</span></h2>
    <div class="row">
      <label class="f">激励视频广告位 ID<input id="cfgReward" placeholder="adunit-xxxxxxxx"></label>
      <label class="f">Banner 广告位 ID<input id="cfgBanner" placeholder="adunit-xxxxxxxx"></label>
      <label class="f">插屏广告位 ID<input id="cfgInter" placeholder="adunit-xxxxxxxx"></label>
    </div>
    <div class="row" style="margin-top:10px">
      <label class="f">每天免费次数<input id="cfgFree" type="number" min="0" max="99"></label>
      <label class="f">每天看广告最多加几次<input id="cfgAdTimes" type="number" min="0" max="99"></label>
      <label class="f">每次广告解锁次数<input id="cfgAdAdd" type="number" min="1" max="10"></label>
    </div>
    <div class="row" style="margin-top:10px">
      <button class="primary" id="btnSaveAds">保存</button>
    </div>
  </div>

  <div class="card">
    <h2>小程序文案与服务</h2>
    <div class="row">
      <label class="f" style="flex:1 1 100%">首页公告（留空不显示）<input id="cfgNotice" placeholder="例如：今天解析服务升级，速度更快了"></label>
    </div>
    <div class="row" style="margin-top:10px">
      <label class="f">客服微信<input id="cfgWechat" placeholder="kefu_xxx"></label>
      <label class="f">对外域名<input id="cfgBase" placeholder="https://api.yourdomain.com"></label>
    </div>
    <div class="row" style="margin-top:10px">
      <label class="f" style="flex:1 1 100%">免责声明<textarea id="cfgDisclaimer" rows="3"></textarea></label>
    </div>
    <div class="row" style="margin-top:10px">
      <button class="primary" id="btnSaveApp">保存</button>
    </div>
  </div>

  <div class="card">
    <h2>解析引擎</h2>
    <div class="row">
      <span class="muted" id="engineInfo">–</span>
      <span style="flex:1"></span>
      <button class="ghost" id="btnRestart">重启浏览器</button>
      <button class="ghost" id="btnClearCache">清空缓存</button>
    </div>
  </div>

  <div class="card">
    <h2>近 7 天趋势</h2>
    <table><thead><tr><th>日期</th><th>解析量</th><th>成功</th><th style="width:40%">占比</th></tr></thead>
    <tbody id="trendBody"></tbody></table>
  </div>

  <div class="card">
    <h2>失败原因 Top</h2>
    <table><thead><tr><th>原因</th><th>次数</th></tr></thead><tbody id="errBody"></tbody></table>
  </div>

  <div class="card">
    <h2>用户反馈</h2>
    <table><thead><tr><th>内容</th><th>联系方式</th><th>设备</th><th>时间</th></tr></thead><tbody id="fbBody"></tbody></table>
  </div>
</main>
<div class="toast" id="toast"></div>

<script>
const TOKEN = new URLSearchParams(location.search).get('token') || '';
const $ = (id) => document.getElementById(id);
function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),1800);}
async function api(path, body){
  const opt = {headers:{'X-Admin-Token':TOKEN}};
  if(body){opt.method='POST';opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(body);}
  const sep = path.includes('?')?'&':'?';
  const r = await fetch(path + sep + 'token=' + encodeURIComponent(TOKEN), opt);
  return r.json();
}
function fmt(n){return (n||0).toLocaleString('zh-CN');}
function ts2str(ts){const d=new Date(ts*1000);return d.toLocaleString('zh-CN',{hour12:false});}

async function load(){
  try{
    const res = await api('/admin/api/overview');
    if(res.code!==0){ $('hstat').textContent='后台密码无效'; $('dot').classList.add('off'); return; }
    const {stats, config, browser, feedback} = res.data;
    $('kToday').textContent = fmt(stats.today.total);
    $('kRate').textContent = stats.rate + '%';
    $('kMs').textContent = stats.avg_ms + 'ms';
    $('kTotal').textContent = fmt(stats.total);
    $('kCache').textContent = fmt(stats.cache);
    $('dot').className = 'dot' + (browser.alive ? '' : ' off');
    $('hstat').textContent = browser.alive ? ('引擎正常 · ' + browser.workers + ' 个标签页') : '引擎未启动';
    $('engineInfo').textContent = 'Chrome：' + browser.chrome + ' · 已运行 ' + Math.floor(browser.uptime/60) + ' 分钟' + (browser.last_error? ' · 最近错误：'+browser.last_error : '');

    $('cfgReward').value = config.ads.rewarded_video||'';
    $('cfgBanner').value = config.ads.banner||'';
    $('cfgInter').value = config.ads.interstitial||'';
    $('cfgFree').value = config.limits.free_per_day;
    $('cfgAdTimes').value = config.limits.ad_unlock_per_day;
    $('cfgAdAdd').value = config.limits.ad_unlock_per_view;
    $('cfgNotice').value = config.app.notice||'';
    $('cfgWechat').value = config.app.service_wechat||'';
    $('cfgBase').value = config.server.public_base||'';
    $('cfgDisclaimer').value = config.app.disclaimer||'';
    const urlTip = config.server.public_base ? '' : '（未填对外域名，正式环境务必填写 HTTPS 域名）';
    $('cfgBase').placeholder = 'https://api.yourdomain.com ' + urlTip;

    $('trendBody').innerHTML = stats.trend.map(d=>{
      const pct = d.total? Math.round(d.ok/d.total*100):0;
      return `<tr><td>${d.date}</td><td>${fmt(d.total)}</td><td>${fmt(d.ok)}</td>
      <td><div class="bar"><i style="width:${pct}%"></i></div><span class="muted">${pct}%</span></td></tr>`;
    }).join('') || '<tr><td colspan="4" class="muted">还没有数据</td></tr>';

    $('errBody').innerHTML = stats.errors.map(e=>`<tr><td>${e.err}</td><td>${e.count}</td></tr>`).join('')
      || '<tr><td colspan="2" class="muted">没有失败记录，很稳</td></tr>';

    $('fbBody').innerHTML = (feedback||[]).map(f=>`<tr><td>${f.content}</td><td>${f.contact||'-'}</td><td>${f.device||'-'}</td><td>${ts2str(f.ts)}</td></tr>`).join('')
      || '<tr><td colspan="4" class="muted">暂无反馈</td></tr>';
  }catch(e){ $('hstat').textContent = '连接失败'; }
}

$('btnRefresh').onclick = () => { load(); toast('已刷新'); };

$('btnSaveAds').onclick = async () => {
  const updates = {ads:{rewarded_video:$('cfgReward').value.trim(),banner:$('cfgBanner').value.trim(),interstitial:$('cfgInter').value.trim()},
    limits:{free_per_day:+$('cfgFree').value, ad_unlock_per_day:+$('cfgAdTimes').value, ad_unlock_per_view:+$('cfgAdAdd').value}};
  const r = await api('/admin/api/config', {updates});
  toast(r.code===0?'已保存':'保存失败');
};

$('btnSaveApp').onclick = async () => {
  const updates = {
    app:{notice:$('cfgNotice').value.trim(), service_wechat:$('cfgWechat').value.trim(), disclaimer:$('cfgDisclaimer').value.trim()},
    server:{public_base:$('cfgBase').value.trim()}
  };
  const r = await api('/admin/api/config', {updates});
  toast(r.code===0?'已保存':'保存失败');
};

$('btnTest').onclick = async () => {
  const url = $('testInput').value.trim();
  if(!url){ toast('先粘一条链接'); return; }
  $('testMsg').textContent = '解析中…';
  $('testOut').innerHTML = '';
  const t0 = Date.now();
  const r = await api('/admin/api/test', {url});
  const cost = Date.now() - t0;
  if(r.code!==0){ $('testMsg').textContent = '失败（' + cost + 'ms）：' + (r.msg||''); return; }
  const d = r.data;
  $('testMsg').textContent = '成功（' + cost + 'ms' + (d.cached?'，来自缓存':'') + '）';
  const media = d.kind==='images'
    ? `<img src="${d.images[0]}" alt="cover">`
    : (d.download.video ? `<video src="${d.download.video}" controls></video>` : '');
  $('testOut').innerHTML = `<div class="preview">${media}<div>
    <div><b>${d.title||'(无标题)'}</b></div>
    <div class="muted">${d.author.name} · ${Math.round(d.duration/1000)}s · ${d.kind==='images'?'图集 '+d.images.length+' 张':'视频'}</div>
    <div class="muted" style="margin-top:6px">点赞 ${fmt(d.stats.digg)} · 评论 ${fmt(d.stats.comment)}</div>
    </div></div>
    <pre>${JSON.stringify(d, null, 1).slice(0, 1200)}</pre>`;
};

$('btnRestart').onclick = async () => { const r = await api('/admin/api/restart', {}); toast(r.msg||'已发送'); setTimeout(load, 16000); };
$('btnClearCache').onclick = async () => { const r = await api('/admin/api/cache', {}); toast(r.msg||'已清理'); load(); };

load();
setInterval(load, 30000);
</script>
</body>
</html>
"""
