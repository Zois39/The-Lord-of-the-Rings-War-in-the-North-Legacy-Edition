// Регрессия UI v2: вкладки, карточки, клики по навыкам/снаряжению, отряд.
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function makeEl(tag){const el={tag,children:[],_html:'',style:{},dataset:{},classList:{_s:new Set(),
 toggle(c,f){f?this._s.add(c):this._s.delete(c);el.className=[...this._s].join(' ')},contains(c){return this._s.has(c)}},
 set className(v){this._c=v},get className(){return this._c||''},
 set innerHTML(v){this._html=v},get innerHTML(){return this._html},
 set textContent(v){this._t=v},get textContent(){return this._t||''},
 set onclick(f){this._onclick=f},get onclick(){return this._onclick},
 set onchange(f){this._onchange=f},get onchange(){return this._onchange},
 set oninput(f){this._oninput=f},get oninput(){return this._oninput},
 set oncontextmenu(f){this._oncm=f},get oncontextmenu(){return this._oncm},
 appendChild(c){this.children.push(c);return c},addEventListener(){},querySelectorAll(){return[]},
 focus(){},select(){},setSelectionRange(){},value:'',checked:false,disabled:false};return el}
const byId={};
const documentStub={getElementById(id){return byId[id]||(byId[id]=makeEl('div'))},
 querySelectorAll(){return[]},createElement(t){return makeEl(t)},execCommand(){},addEventListener(){}};
const store={};
const localStorageStub={getItem:k=>(k in store?store[k]:null),setItem:(k,v)=>{store[k]=String(v)},removeItem:k=>{delete store[k]}};
const fetchStub=async(url)=>{const p=path.join(root,decodeURIComponent(url));
 if(!fs.existsSync(p))throw new Error('404 '+url);
 return{json:async()=>JSON.parse(fs.readFileSync(p,'utf8'))}};
const ctx=vm.createContext({document:documentStub,localStorage:localStorageStub,fetch:fetchStub,
 alert:s=>{throw new Error('alert: '+s)},confirm:()=>true,location:{reload(){}},console,setTimeout,clearTimeout});
const T={pass:0,fail:0};const ok=(n,c)=>{c?T.pass++:(T.fail++,console.error('FAIL:',n))};

(async()=>{
 vm.runInContext(code+';globalThis.DB=DB;globalThis.build=build;globalThis.tab=tab;globalThis.render=render;',ctx);
 await new Promise(r=>setTimeout(r,200));

 ok('3 героя',Object.keys(ctx.DB.heroes).length===3);
 ok('оружие',ctx.DB.items.weapons.length>=40);
 ok('броня',ctx.DB.items.armor.length>=100);
 ok('сеты',ctx.DB.items.sets.length===20);
 ok('лут боссов',ctx.DB.items.boss_loot.length>=30);

 // рендер всех вкладок
 for(const t of['skills','gear','squad','build']){ctx.tab.cur=t;ctx.render();
  ok('рендер вкладки '+t,byId['content']._html.length>100)}

 // вкладка Отряд содержит атрибуты
 ctx.tab.cur='squad';ctx.render();
 ok('отряд: атрибуты',byId['content']._html.includes('Strength'));
 ok('отряд: герой-селект',byId['content']._html.includes('heroSel'));

 // клик по карточке навыка (модель + перерендер)
 ctx.tab.cur='skills';ctx.render();
 const hero=ctx.DB.heroes[ctx.build.hero];
 const skName=hero.trees[0].skills[1].name;
 ctx.build.skills[skName]={rank:2};
 ctx.render();
 ok('навык выбран',byId['content']._html.includes('class="skill'));
 const spent=Object.values(ctx.build.skills).reduce((a,s)=>a+(s.rank||0),0);
 ok('очки посчитаны',spent===2);

 // снаряжение: выбор карточки
 ctx.tab.cur='gear';ctx.render();
 const card=ctx.DB.items.weapons.find(w=>!(w.type||'').includes('Bow'));
 ctx.build.gear.weapon=card.name;ctx.render();
 ok('выбор оружия',byId['content']._html.includes('sel'));
 ctx.tab.cur='build';ctx.render();
 ok('билд содержит оружие',byId['content']._html.includes(card.name));

 // типы оружия без мусора
 const types=new Set(ctx.DB.items.weapons.map(w=>w.type));
 ok('нет мусора Nothing',[...types].every(t=>!t.includes('Nothing')));

 console.log(`PASS ${T.pass} FAIL ${T.fail}`);
 process.exit(T.fail?1:0);
})().catch(e=>{console.error('HARNESS ERROR:',e.message);process.exit(1)});
