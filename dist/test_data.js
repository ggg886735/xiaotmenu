// ═══════════════════════════════════════════════════════
//  小t的菜单 — 模拟数据（测试用）
//
//  这个文件仅供前端独立开发阶段使用。
//  等后端 API 开发完成、data.js 接入真实接口后，
//  删除本文件并在 index.html 中移除对应的 <script> 引用即可。
// ═══════════════════════════════════════════════════════

var TEST_DATA = {

  // ===== 大厨数据 =====
  chefs: [
    { id: 'lulu',    name: '水豚噜噜',   img: 'assets/images/2_68.png', emoji: '🐹', role: '汤品专家 🥣', tag: '汤品超好喝~' },
    { id: 'nailong', name: '奶龙',       img: 'assets/images/2_74.png', emoji: '🐲', role: '荤菜大师 🍖', tag: '肉肉超满足~' },
    { id: 'beini',   name: '小恐龙贝尼', img: 'assets/images/2_80.png', emoji: '🦕', role: '素菜达人 🥬', tag: '素菜超美味~' }
  ],

  // ===== 菜品数据 =====
  dishes: [
    { id: 'fanqiedantang',   name: '番茄蛋汤',   cat: 'soup', price: 12, desc: '酸甜可口，暖心暖胃~', gradient: 'var(--gradient-orange)' },
    { id: 'dongguapaigutang', name: '冬瓜排骨汤', cat: 'soup', price: 22, desc: '清淡鲜美，营养满分',   gradient: 'var(--gradient-green)' },
    { id: 'chaoniurou',       name: '炒牛肉',     cat: 'meat', price: 28, desc: '鲜嫩多汁，肉香四溢~', gradient: 'var(--gradient-orange)' },
    { id: 'chaokongxincai',   name: '炒空心菜',   cat: 'veg',  price: 16, desc: '清脆爽口，鲜嫩美味~', gradient: 'var(--gradient-green)' }
  ],

  // ===== 分类列表 =====
  categories: [
    { key: 'all',  label: '所有菜品' },
    { key: 'soup', label: '汤品🥣' },
    { key: 'meat', label: '荤菜🍖' },
    { key: 'veg',  label: '素菜🥬' }
  ],

  // ===== 默认应用状态 =====
  defaultState: {
    selectedChef: 'lulu',
    cart: []
  }

};
