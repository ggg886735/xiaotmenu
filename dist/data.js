// ═══════════════════════════════════════════════════
//  小t的菜单 — 数据访问层
//
//  ★ 数据源：后端 API（Flask + SQLite / TiDB Cloud）
//  ★ test_data.js 仅作兜底（API 不可用时使用）
//
//  【环境配置】只需修改下方 API_BASE 即可切换环境：
//    ▸ 本地开发：const API_BASE = '/api';
//    ▸ 生产环境：const API_BASE = 'https://你的用户名.pythonanywhere.com/api';
// ═══════════════════════════════════════════════════

// ─── 环境配置（部署到 Gitee Pages 前，修改为 PythonAnywhere 地址）───
const API_BASE = '/api';  // ← 改成生产环境地址，例如：'https://xiaotmenu.pythonanywhere.com/api'

// 初始化为空，等待 API 返回后再渲染
var CHEFS = [];
var DISHES = [];
var CATEGORIES = [];
var DEFAULT_STATE = { selectedChef: null, cart: [] };

// 标记数据是否已加载完成
var DATA_LOADED = false;

// ────────────────────────────────────────────────────────
//  数据加载（启动时调用）
// ────────────────────────────────────────────────────────

async function loadAppData() {
    var startTime = performance.now();
    console.log('[data.js] 正在从后端 API 加载数据...', 'API_BASE=', API_BASE);

    try {
        var responses = await Promise.all([
            fetch(API_BASE + '/chefs'),
            fetch(API_BASE + '/dishes'),
            fetch(API_BASE + '/categories'),
            fetch(API_BASE + '/user/state')
        ]);

        var jsonResults = await Promise.all(responses.map(function(r) {
            if (!r.ok) throw new Error('API ' + r.url + ' 返回 ' + r.status);
            return r.json();
        }));

        CHEFS         = jsonResults[0].data;
        DISHES        = jsonResults[1].data;
        CATEGORIES    = jsonResults[2].data;
        DEFAULT_STATE = jsonResults[3].data;

        DATA_LOADED = true;
        var elapsed = (performance.now() - startTime).toFixed(0);
        console.log('[data.js] 数据加载完成 (耗时 ' + elapsed + 'ms):',
            CHEFS.length + '位大厨,', DISHES.length + '道菜品,',
            CATEGORIES.length + '个分类');

        if (typeof initApp === 'function') {
            initApp();
        }

    } catch (error) {
        console.warn('[data.js] 后端 API 不可用，尝试本地兜底...', error.message);

        if (typeof TEST_DATA !== 'undefined') {
            console.log('[data.js] 使用 test_data.js 本地数据');
            CHEFS         = TEST_DATA.chefs;
            DISHES        = TEST_DATA.dishes;
            CATEGORIES    = TEST_DATA.categories;
            DEFAULT_STATE = TEST_DATA.defaultState;
            DATA_LOADED   = true;
            if (typeof initApp === 'function') {
                initApp();
            }
        } else {
            console.error('[data.js] 数据加载失败，无可用数据源');
            document.body.insertAdjacentHTML('afterbegin',
                '<div style="position:fixed;top:10px;left:10px;right:10px;z-index:99999;' +
                'background:#ff4444;color:#fff;padding:16px;border-radius:12px;' +
                'font-size:14px;font-family:monospace">' +
                '<strong>⚠ 无法连接到后端服务</strong><br>' +
                '当前 API_BASE: ' + API_BASE + '<br>' +
                '请确认：<br>' +
                '1. 本地开发需启动 Flask：<code>python server/app.py</code><br>' +
                '2. 生产环境需修改 data.js 第 17 行的 API_BASE 地址<br>' +
                '然后刷新页面。</div>');
        }
    }
}

// ────────────────────────────────────────────────────────
//  API 辅助函数 — 菜品 CRUD
// ────────────────────────────────────────────────────────

/**
 * 新增菜品到数据库
 * @param {Object} dishData  { id, name, cat, price, desc, gradient, image }
 * @returns {Promise<Object>} 服务器返回的菜品对象
 */
async function apiAddDish(dishData) {
    var resp = await fetch(API_BASE + '/dishes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dishData)
    });
    if (!resp.ok) {
        var err = await resp.json();
        throw new Error(err.data.error || '新增失败');
    }
    var result = await resp.json();
    return result.data;
}

/**
 * 更新菜品
 * @param {string} dishId
 * @param {Object} updates  { name?, cat?, price?, desc?, gradient?, image? }
 * @returns {Promise<Object>} 更新后的菜品对象
 */
async function apiUpdateDish(dishId, updates) {
    var resp = await fetch(API_BASE + '/dishes/' + dishId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    });
    if (!resp.ok) {
        var err = await resp.json();
        throw new Error(err.data.error || '更新失败');
    }
    var result = await resp.json();
    return result.data;
}

/**
 * 删除菜品
 * @param {string} dishId
 * @returns {Promise<Object>}
 */
async function apiDeleteDish(dishId) {
    var resp = await fetch(API_BASE + '/dishes/' + dishId, {
        method: 'DELETE'
    });
    if (!resp.ok) {
        var err = await resp.json();
        throw new Error(err.data.error || '删除失败');
    }
    var result = await resp.json();
    return result.data;
}

/**
 * 上传图片
 * @param {File} file
 * @returns {Promise<string>} 图片 URL
 */
async function apiUploadImage(file) {
    var formData = new FormData();
    formData.append('file', file);
    var resp = await fetch(API_BASE + '/upload', {
        method: 'POST',
        body: formData
    });
    if (!resp.ok) {
        var err = await resp.json();
        throw new Error(err.data.error || '上传失败');
    }
    var result = await resp.json();
    return result.data.url;
}

// 页面加载时自动开始拉数据
loadAppData();
