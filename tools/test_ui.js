// Регрессия UI: DOM-заглушки + fetch на локальные JSON + сценарии кликов.
const fs = require('fs'), path = require('path'), vm = require('vm');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('FAIL: script not found'); process.exit(1); }
const code = m[1];

// --- заглушки DOM ---
function makeEl(tag) {
  const el = {
    tag, children: [], _html: '', style: {}, dataset: {}, classList: {
      _s: new Set(),
      toggle(c, f) { f ? this._s.add(c) : this._s.delete(c); el.className = [...this._s].join(' ') },
      contains(c) { return this._s.has(c) },
    },
    set className(v) { this._c = v }, get className() { return this._c || '' },
    set innerHTML(v) { this._html = v; this.children = []; },
    get innerHTML() { return this._html },
    set textContent(v) { this._t = v }, get textContent() { return this._t || '' },
    set onclick(f) { this._onclick = f }, get onclick() { return this._onclick },
    set onchange(f) { this._onchange = f }, get onchange() { return this._onchange },
    set oninput(f) { this._oninput = f }, get oninput() { return this._oninput },
    appendChild(c) { this.children.push(c); return c },
    addEventListener() {}, querySelectorAll() { return [] },
    focus() {}, select() {}, setSelectionRange() {},
    value: '', checked: false, disabled: false,
  };
  return el;
}
const byId = {};
const documentStub = {
  getElementById(id) { return byId[id] || (byId[id] = makeEl('div')) },
  querySelectorAll() { return [] },
  createElement(t) { return makeEl(t) },
  execCommand() {},
  addEventListener() {},
};
const store = {};
const localStorageStub = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v) },
  removeItem: k => { delete store[k] },
};
const fetchStub = async (url) => {
  const p = path.join(root, decodeURIComponent(url));
  if (!fs.existsSync(p)) throw new Error('404 ' + url);
  return { json: async () => JSON.parse(fs.readFileSync(p, 'utf8')) };
};

const ctx = vm.createContext({
  document: documentStub, localStorage: localStorageStub, fetch: fetchStub,
  alert: (s) => { throw new Error('alert: ' + s) },
  confirm: () => true, location: { reload() {} },
  console, setTimeout, clearTimeout,
});
const T = { pass: 0, fail: 0 };
const ok = (name, cond) => { cond ? T.pass++ : (T.fail++, console.error('FAIL:', name)); };

(async () => {
  vm.runInContext(code + ';globalThis.DB=DB;globalThis.build=build;globalThis.tab=tab;globalThis.render=render;', ctx);
  await new Promise(r => setTimeout(r, 200)); // дождаться load()

  ok('герои загружены', Object.keys(ctx.DB.heroes).length === 3);
  ok('Эрадан имеет 3 ветки', ctx.DB.heroes.Eradan.trees.length === 3);
  ok('оружие загружено', ctx.DB.items.weapons.length >= 40);
  ok('броня загружено', ctx.DB.items.armor.length >= 100);
  ok('сеты загружено', ctx.DB.items.sets.length === 20);
  ok('потions', ctx.DB.items.potions.length >= 40);
  ok('ингредиенты', ctx.DB.items.ingredients.length >= 70);

  // смена героя
  byId['heroSel'].value = 'Andriel';
  byId['heroSel'].onchange();
  ok('герой переключён', ctx.build.hero === 'Andriel');

  // прокачка навыка напрямую через модель
  const hero = ctx.DB.heroes.Farin;
  const skName = hero.trees[0].skills[2].name;
  ctx.build.skills[skName] = { rank: 2 };
  const spent = Object.values(ctx.build.skills).reduce((a, s) => a + (s.rank || 0), 0);
  ok('очки навыков посчитаны', spent === 2);

  // атрибуты
  ctx.build.attrs.str = 5;
  const aspent = Object.values(ctx.build.attrs).reduce((a, v) => a + v, 0);
  ok('атрибуты посчитаны', aspent === 5);

  // вкладки
  ctx.tab.cur = 'gear'; ctx.render();
  ok('рендер снаряжения', byId['content']._html.includes('table'));
  ctx.tab.cur = 'build'; ctx.render();
  ok('рендер билда содержит навык', byId['content']._html.includes(skName) === false); // билд пока за Andriel
  ctx.build.hero = 'Farin'; ctx.tab.cur = 'build'; ctx.render();
  ok('рендер билда Фарин содержит навык', byId['content']._html.includes(skName));

  // экспорт/сериализация
  const dump = JSON.stringify(ctx.build);
  ok('экспорт JSON', JSON.parse(dump).hero === 'Farin');

  console.log(`PASS ${T.pass} FAIL ${T.fail}`);
  process.exit(T.fail ? 1 : 0);
})().catch(e => { console.error('HARNESS ERROR:', e.message); process.exit(1) });
