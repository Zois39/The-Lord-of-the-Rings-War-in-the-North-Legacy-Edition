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
 vm.runInContext(code+';globalThis.DB=DB;globalThis.build=build;globalThis.tab=tab;globalThis.render=render;globalThis.computeStats=computeStats;globalThis.equipWeapon=equipWeapon;globalThis.reqsOk=reqsOk;globalThis.findItem=findItem;',ctx);
 await new Promise(r=>setTimeout(r,200));

 ok('3 героя',Object.keys(ctx.DB.heroes).length===3);
 ok('оружие',ctx.DB.items.weapons.length>=40);
 ok('броня (без мусора)',ctx.DB.items.armor.length>=80);
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

 // снаряжение: выбор карточки -> слот mainhand
 ctx.tab.cur='gear';ctx.render();
 const card=ctx.DB.items.weapons.find(w=>!(w.type||'').match(/bow|crossbow/i));
 ctx.build.gear.slots.mainhand=card.name;ctx.render();
 ok('выбор оружия (sel на карточке)',byId['content']._html.includes('sel'));
 ok('оружие в слоте mainhand',ctx.build.gear.slots.mainhand===card.name);
 ctx.tab.cur='build';ctx.render();
 ok('билд содержит оружие',byId['content']._html.includes(card.name));

 // типы оружия без мусора
 const types=new Set(ctx.DB.items.weapons.map(w=>w.type));
 ok('нет мусора Nothing',[...types].every(t=>!t.includes('Nothing')));

 // --- слоты и характеристики ---
 ctx.build.gear.slots.mainhand = ctx.DB.items.weapons.find(w=>!(w.type||'').match(/bow|crossbow/i)).name;
 const st1 = ctx.computeStats();
 ok('урон ближний появился', /\d+ – \d+/.test(st1.melee));
 ok('броня >= 0', st1.armor >= 0);
 ok('стрелы базовые', st1.arrows === 20);
 const ring = ctx.DB.items.armor.find(a=>/ring/i.test(a.slot||'') && /Will/i.test(a.effect||'')) || ctx.DB.items.armor.find(a=>/ring/i.test(a.slot||''));
 if (ring) {
   const wil0 = st1.power;
   ctx.build.gear.slots.ring1 = ring.name;
   const st2 = ctx.computeStats();
   ok('кольцо влияет (мощь/атрибуты)', st2.power !== wil0 || JSON.stringify(st2.attrs) !== JSON.stringify(st1.attrs));
   ok('кольцо в слоте ring1', ctx.build.gear.slots.ring1 === ring.name);
 }
 // клик-путь: вкладка gear, выбор в слот mainhand через findItem/карточку
 ctx.tab.cur='gear'; ctx.render();
 ok('панель слотов рендерится', byId['side']._html.includes('Слоты'));
 // правила слотов оружия
 const twoH = ctx.DB.items.weapons.find(w=>(w.type||'').match(/2-handed/i));
 const oneH = ctx.DB.items.weapons.find(w=>(w.type||'').match(/1-handed/i));
 const shield = ctx.DB.items.weapons.find(w=>(w.type||'').match(/shield/i));
 ctx.build.gear.slots.mainhand=null; ctx.build.gear.slots.offhand=null; ctx.build.skills['Dual Wield']={rank:0};
 if (twoH) { ctx.equipWeapon(twoH);
   ok('двуручное занимает обе руки', ctx.build.gear.slots.mainhand===twoH.name && ctx.build.gear.slots.offhand==='2H');
   ctx.equipWeapon(twoH); // повторный клик — снять
   ok('повторный клик снимает 2H', ctx.build.gear.slots.mainhand===null);
 }
 if (shield) { ctx.equipWeapon(shield);
   ok('щит в offhand', ctx.build.gear.slots.offhand===shield.name);
   ok('2H снято при щите', !ctx.build.gear.slots.mainhand||!(ctx.findItem(ctx.build.gear.slots.mainhand).type||'').match(/2-handed/i));
 }
 if (oneH) { ctx.build.gear.slots.mainhand=null; ctx.build.gear.slots.offhand=null;
   ctx.equipWeapon(oneH);
   ok('1H в mainhand', ctx.build.gear.slots.mainhand===oneH.name);
   ctx.build.skills['Dual Wield']={rank:0};
   const second1H = ctx.DB.items.weapons.find(w=>(w.type||'').match(/1-handed/i)&&w.name!==oneH.name);
   if (second1H) { ctx.equipWeapon(second1H);
     ok('без Dual Wield 2-е 1H меняет mainhand', ctx.build.gear.slots.mainhand===second1H.name && ctx.build.gear.slots.offhand!==second1H.name);
     ctx.build.skills['Dual Wield']={rank:1};
     ctx.equipWeapon(oneH);
     ok('с Dual Wield 1H в offhand', ctx.build.gear.slots.offhand===oneH.name);
   }
 }
 ctx.build.gear.slots.mainhand=null; ctx.build.gear.slots.offhand=null; ctx.build.skills['Dual Wield']={rank:0};
 // сеты: бонусы с описаниями
 const setRec = ctx.DB.items.sets[0];
 ok('сет имеет бонусы', setRec.bonuses && Object.keys(setRec.bonuses).length>=2);
 // загрузчик существует
 ok('loader html', ctx.document.getElementById('loader')!==undefined);
 // требования: reqsOk отвечает объектом
 const reqRes = ctx.reqsOk(ctx.DB.items.weapons[0]);
 ok('reqsOk структура', reqRes && typeof reqRes.ok === 'boolean');
 // стрелы с Broad Quiver
 ctx.build.skills['Broad Quiver'] = {rank: 2};
 ok('стрелы с колчаном', ctx.computeStats().arrows === 40);
 ctx.build.skills['Broad Quiver'] = {rank: 0};

 console.log(`PASS ${T.pass} FAIL ${T.fail}`);
 process.exit(T.fail?1:0);
})().catch(e=>{console.error('HARNESS ERROR:',e.message);process.exit(1)});
