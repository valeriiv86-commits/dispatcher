(function () {
'use strict';
var ST = {new:'Новый',assigned:'Назначен',in_progress:'В работе',done:'Выполнен',cancelled:'Отменён'};
var ROLE = {admin:'Администратор',dispatcher:'Диспетчер'};
var S = {token:localStorage.getItem('token'),user:null,tab:'orders',filter:'',orders:[],performers:[],busy:false,editing:null,showForm:false};
var root = document.getElementById('app');
var timer = null;

function h(tag, a) {
  var e = document.createElement(tag);
  if (a) for (var k in a) {
    if (k === 'class') e.className = a[k];
    else if (k.slice(0,2) === 'on') e.addEventListener(k.slice(2), a[k]);
    else if (a[k] !== null && a[k] !== undefined && a[k] !== false) e.setAttribute(k, a[k]);
  }
  for (var i = 2; i < arguments.length; i++) {
    var c = arguments[i];
    if (c === null || c === undefined || c === false) continue;
    e.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
  }
  return e;
}
function fmt(ts) { var d = new Date(ts); return isNaN(d) ? '' : d.toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}); }

function errText(status, body) {
  var d = body && body.detail;
  if (Array.isArray(d)) return d.map(function (x) { return x && x.msg ? x.msg : ''; }).filter(Boolean).join('; ') || 'Проверьте введённые данные';
  if (typeof d === 'string' && d && /[а-яё]/i.test(d)) return d;
  if (status === 0) return 'Нет связи с сервером';
  if (status === 400 || status === 422) return 'Проверьте введённые данные';
  if (status === 403) return 'Недостаточно прав';
  if (status === 404) return 'Не найдено';
  if (status === 409) return 'Такая запись уже существует';
  if (status === 429) return 'Слишком много попыток. Подождите 5 минут';
  return 'Ошибка сервера (' + status + ')';
}
function api(method, url, body, form) {
  var o = {method: method, headers: {}};
  if (S.token) o.headers.Authorization = 'Bearer ' + S.token;
  if (form) { o.headers['Content-Type'] = 'application/x-www-form-urlencoded'; o.body = new URLSearchParams(body).toString(); }
  else if (body) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
  return fetch(url, o).then(function (r) {
    return r.text().then(function (t) {
      var j = null; try { j = t ? JSON.parse(t) : null; } catch (e) {}
      if (r.status === 401 && url !== '/auth/login') { logoutLocal(); throw new Error('Сессия истекла, войдите снова'); }
      if (r.status === 401) throw new Error('Неверный логин или пароль');
      if (!r.ok) throw new Error(errText(r.status, j));
      return j;
    });
  }, function () { throw new Error('Нет связи с сервером'); });
}
function logoutLocal() { S.token = null; S.user = null; localStorage.removeItem('token'); clearInterval(timer); render(); }

// submit helper: disables button, shows error in errEl
function submit(btn, errEl, fn) {
  btn.disabled = true; errEl.textContent = '';
  return Promise.resolve().then(fn).catch(function (e) { errEl.textContent = e.message; }).then(function () { btn.disabled = false; });
}
function field(label, input) { return h('label', null, label, input); }
function inp(type, val, extra) { var a = {type: type}; for (var k in extra||{}) a[k] = extra[k]; var i = h('input', a); i.value = val == null ? '' : val; return i; }

// ---------- login ----------
function loginView() {
  var u = inp('text', '', {autocomplete:'username',required:'required'}), p = inp('password', '', {autocomplete:'current-password',required:'required'});
  var err = h('div', {class:'err',role:'alert'}), btn = h('button', {class:'pri',type:'submit'}, 'Войти');
  var f = h('form', {class:'card login', onsubmit: function (ev) {
    ev.preventDefault();
    submit(btn, err, function () {
      return api('POST','/auth/login',{username:u.value.trim(),password:p.value},true).then(function (r) {
        S.token = r.access_token; S.user = r.user; localStorage.setItem('token', S.token); start();
      });
    });
  }}, h('h2', null, 'Диспетчерская'), field('Логин', u), field('Пароль', p), err, btn);
  return f;
}

// ---------- shell ----------
function render() {
  root.textContent = '';
  if (!S.token) { root.appendChild(loginView()); return; }
  if (!S.user) { root.appendChild(h('div',{class:'empty'},'Загрузка…')); return; }
  var tabs = [['orders','Заказы'],['performers','Исполнители']];
  if (S.user.role === 'admin') tabs.push(['users','Пользователи'],['audit','Журнал']);
  tabs.push(['profile','Профиль']);
  var nav = h('nav', {class:'nav'});
  tabs.forEach(function (t) { nav.appendChild(h('button', {class: S.tab === t[0] ? 'on' : '', onclick: function () { S.tab = t[0]; S.editing = null; render(); load(); }}, t[1])); });
  var main = h('main', {id:'main'});
  root.appendChild(main); root.appendChild(nav);
  ({orders:ordersView,performers:performersView,users:usersView,audit:auditView,profile:profileView})[S.tab](main);
}
function start() {
  S.tab = 'orders'; render();
  var go = S.user ? Promise.resolve() : api('GET','/auth/me').then(function (u) { S.user = u; });
  go.then(function () { render(); load(); clearInterval(timer); timer = setInterval(function () { if (S.tab === 'orders') load(true); }, 15000); }).catch(function () {});
}
function load(silent) {
  if (S.tab === 'orders') return Promise.all([api('GET','/performers/'), api('GET','/orders/?limit=200')]).then(function (r) {
    S.performers = r[0]; S.orders = r[1];
    if (S.tab === 'orders' && !(silent && S.editing)) refreshOrders();
  }).catch(function (e) { var el = document.getElementById('ordErr'); if (el) el.textContent = e.message; });
  if (S.tab === 'performers') return api('GET','/performers/').then(function (r) { S.performers = r; fill('list', performerList); }).catch(showMainErr);
  if (S.tab === 'users') return api('GET','/users/').then(function (r) { S.users = r; fill('list', userList); }).catch(showMainErr);
  if (S.tab === 'audit') return api('GET','/audit/?limit=100').then(function (r) { S.audit = r; fill('list', auditTable); }).catch(showMainErr);
}
function showMainErr(e) { var el = document.getElementById('listErr'); if (el) el.textContent = e.message; }
function fill(id, fn) { var el = document.getElementById(id); if (el) { el.textContent = ''; el.appendChild(fn()); } }

// ---------- orders ----------
function ordersView(main) {
  main.appendChild(h('div',{class:'row'},
    h('h2',{class:'grow'},'Заказы'),
    h('button',{onclick:function(){load();}},'↻ Обновить'),
    h('button',{class:'pri',id:'newBtn',onclick:function(){S.showForm=!S.showForm;fill('formBox',orderForm);}},'Новый заказ')));
  main.appendChild(h('div',{id:'formBox'}));
  main.appendChild(h('div',{id:'chips',class:'chips'}));
  main.appendChild(h('div',{id:'ordErr',class:'err',role:'alert'}));
  main.appendChild(h('div',{id:'ordList'}));
  fill('formBox', orderForm); refreshOrders();
}
function refreshOrders() {
  var chips = document.getElementById('chips'), list = document.getElementById('ordList');
  if (!chips || !list) return;
  var y = window.scrollY;
  var counts = {}; S.orders.forEach(function (o) { counts[o.status] = (counts[o.status]||0) + 1; });
  chips.textContent = '';
  [['', 'Все', S.orders.length]].concat(Object.keys(ST).map(function (k) { return [k, ST[k], counts[k]||0]; })).forEach(function (c) {
    chips.appendChild(h('button',{class:S.filter===c[0]?'on':'',onclick:function(){S.filter=c[0];refreshOrders();}}, c[1] + ' ' + c[2]));
  });
  list.textContent = '';
  var shown = S.orders.filter(function (o) { return !S.filter || o.status === S.filter; });
  if (!shown.length) list.appendChild(h('div',{class:'empty'}, S.orders.length ? 'Нет заказов с таким статусом' : 'Заказов пока нет'));
  shown.forEach(function (o) { list.appendChild(orderCard(o)); });
  window.scrollTo(0, y);
}
function orderForm() {
  var box = h('div');
  if (!S.showForm) return box;
  var cn = inp('text','',{required:'required'}), cp = inp('tel','',{required:'required'}), fa = inp('text','',{required:'required'}), ta = inp('text','',{required:'required'}),
      pr = inp('number','',{required:'required',min:'0',step:'any',inputmode:'decimal'}), cm = h('textarea'), ps = perfSelect('');
  var err = h('div',{class:'err',role:'alert'}), btn = h('button',{class:'pri',type:'submit'},'Создать');
  var f = h('form',{class:'card',onsubmit:function(ev){
    ev.preventDefault();
    submit(btn, err, function () {
      var b = {client_name:cn.value.trim(),client_phone:cp.value.trim(),from_address:fa.value.trim(),to_address:ta.value.trim(),price:Number(pr.value)};
      if (cm.value.trim()) b.comment = cm.value.trim();
      if (ps.value) b.performer_id = Number(ps.value);
      return api('POST','/orders/',b).then(function(){ S.showForm=false; fill('formBox',orderForm); return load(); });
    });
  }}, h('h2',null,'Новый заказ'), field('Имя клиента',cn), field('Телефон клиента',cp), field('Откуда',fa), field('Куда',ta), field('Цена, ₽',pr), field('Исполнитель',ps), field('Комментарий',cm), err,
    h('div',{class:'row'}, btn, h('button',{type:'button',onclick:function(){S.showForm=false;fill('formBox',orderForm);}},'Отмена')));
  box.appendChild(f); return box;
}
function perfSelect(val, onlyActive) {
  var s = h('select', null, h('option',{value:''},'— не назначен —'));
  S.performers.forEach(function (p) { if (p.active || String(p.id) === String(val)) s.appendChild(h('option',{value:p.id},p.name + (p.active ? '' : ' (неактивен)'))); });
  s.value = val == null ? '' : String(val); return s;
}
function patchOrder(o, body, err, ctl) {
  if (ctl) ctl.disabled = true;
  return api('PATCH','/orders/'+o.id, body).then(function(){ S.editing = null; return load(); }).catch(function(e){ err.textContent = e.message; if (ctl) ctl.disabled = false; });
}
function orderCard(o) {
  var err = h('div',{class:'err',role:'alert'});
  var st = h('select',{'aria-label':'Статус'}); Object.keys(ST).forEach(function(k){ st.appendChild(h('option',{value:k},ST[k])); }); st.value = o.status;
  st.onchange = function(){ patchOrder(o,{status:st.value},err,st); };
  var ps = perfSelect(o.performer_id); ps.setAttribute('aria-label','Исполнитель');
  ps.onchange = function(){ patchOrder(o,{performer_id: ps.value ? Number(ps.value) : null},err,ps); };
  var cbox = h('div');
  function showComment() {
    cbox.textContent = '';
    cbox.appendChild(h('div',{class:'row'}, h('span',{class:'mut grow'}, o.comment ? 'Комментарий: ' + o.comment : 'Без комментария'),
      h('button',{onclick:function(){ S.editing = o.id; editComment(); }}, 'Изменить комментарий')));
  }
  function editComment() {
    cbox.textContent = '';
    var ta = h('textarea'); ta.value = o.comment || '';
    var b = h('button',{class:'pri'},'Сохранить');
    b.onclick = function(){ submit(b, err, function(){ return api('PATCH','/orders/'+o.id,{comment:ta.value.trim()}).then(function(){ S.editing=null; return load(); }); }); };
    cbox.appendChild(ta); cbox.appendChild(h('div',{class:'row'}, b, h('button',{onclick:function(){S.editing=null;showComment();}},'Отмена')));
    ta.focus();
  }
  if (S.editing === o.id) editComment(); else showComment();
  var tel = h('a',{href:'tel:' + String(o.client_phone).replace(/[^\d+]/g,'')}, o.client_phone);
  return h('div',{class:'card'},
    h('div',{class:'row'}, h('span',{class:'badge s-'+o.status}, ST[o.status]||o.status), h('span',{class:'mut grow'}, '№' + String(o.id).slice(0, 8) + ' · ' + fmt(o.created_at)), h('b',null, o.price + ' ₽')),
    h('div',{class:'route'}, o.from_address + ' → ' + o.to_address),
    h('div',null, o.client_name + ' · ', tel),
    h('div',{class:'mut'}, 'Исполнитель: ' + (o.performer_name || 'не назначен')),
    h('div',{class:'row'}, h('label',{class:'grow'},'Статус',st), h('label',{class:'grow'},'Исполнитель',ps)),
    cbox, err);
}

// ---------- performers ----------
function performersView(main) {
  main.appendChild(h('div',{class:'row'}, h('h2',{class:'grow'},'Исполнители'), h('button',{class:'pri',onclick:function(){ S.pform = {}; fill('formBox', performerForm); }},'Добавить')));
  main.appendChild(h('div',{id:'formBox'})); main.appendChild(h('div',{id:'listErr',class:'err'})); main.appendChild(h('div',{id:'list'}));
  fill('list', performerList);
}
function performerForm() {
  var box = h('div'); var p = S.pform; if (!p) return box;
  var n = inp('text',p.name,{required:'required'}), ph = inp('tel',p.phone,{required:'required'}), c = inp('text',p.comment);
  var err = h('div',{class:'err',role:'alert'}), btn = h('button',{class:'pri',type:'submit'},'Сохранить');
  box.appendChild(h('form',{class:'card',onsubmit:function(ev){ ev.preventDefault();
    submit(btn, err, function(){
      var b = {name:n.value.trim(),phone:ph.value.trim(),comment:c.value.trim()};
      return (p.id ? api('PATCH','/performers/'+p.id,b) : api('POST','/performers/',b)).then(function(){ S.pform=null; fill('formBox',performerForm); return load(); });
    }); }}, h('h2',null,p.id?'Изменить исполнителя':'Новый исполнитель'), field('Имя',n), field('Телефон',ph), field('Комментарий',c), err,
    h('div',{class:'row'}, btn, h('button',{type:'button',onclick:function(){S.pform=null;fill('formBox',performerForm);}},'Отмена'))));
  return box;
}
function performerList() {
  var w = h('div'); if (!S.performers.length) { w.appendChild(h('div',{class:'empty'},'Исполнителей пока нет')); return w; }
  S.performers.forEach(function (p) {
    var err = h('div',{class:'err'}), tg = h('button',{class:p.active?'danger':''}, p.active ? 'Деактивировать' : 'Активировать');
    tg.onclick = function(){ submit(tg, err, function(){ return api('PATCH','/performers/'+p.id,{active:!p.active}).then(load); }); };
    w.appendChild(h('div',{class:'card'+(p.active?'':' inactive')}, h('b',null,p.name), p.active ? '' : ' (неактивен)',
      h('div',null,h('a',{href:'tel:'+String(p.phone).replace(/[^\d+]/g,'')},p.phone)), p.comment ? h('div',{class:'mut'},p.comment) : null,
      h('div',{class:'row'}, h('button',{onclick:function(){S.pform=p;fill('formBox',performerForm);window.scrollTo(0,0);}},'Изменить'), tg), err));
  });
  return w;
}

// ---------- users ----------
function usersView(main) {
  main.appendChild(h('div',{class:'row'}, h('h2',{class:'grow'},'Пользователи'), h('button',{class:'pri',onclick:function(){ S.uform = true; fill('formBox', userForm); }},'Добавить')));
  main.appendChild(h('div',{id:'formBox'})); main.appendChild(h('div',{id:'listErr',class:'err'})); main.appendChild(h('div',{id:'list'}));
}
function userForm() {
  var box = h('div'); if (!S.uform) return box;
  var n = inp('text','',{required:'required',autocomplete:'off'}), p = inp('password','',{required:'required',minlength:'8',autocomplete:'new-password'});
  var r = h('select',null,h('option',{value:'dispatcher'},ROLE.dispatcher),h('option',{value:'admin'},ROLE.admin));
  var err = h('div',{class:'err',role:'alert'}), btn = h('button',{class:'pri',type:'submit'},'Создать');
  box.appendChild(h('form',{class:'card',onsubmit:function(ev){ ev.preventDefault();
    submit(btn, err, function(){ return api('POST','/users/',{username:n.value.trim(),password:p.value,role:r.value}).then(function(){ S.uform=false; fill('formBox',userForm); return load(); }); });
  }}, h('h2',null,'Новый пользователь'), field('Логин',n), field('Пароль (не короче 8 символов)',p), field('Роль',r), err,
    h('div',{class:'row'}, btn, h('button',{type:'button',onclick:function(){S.uform=false;fill('formBox',userForm);}},'Отмена'))));
  return box;
}
function userList() {
  var w = h('div'); if (!(S.users||[]).length) { w.appendChild(h('div',{class:'empty'},'Пользователей нет')); return w; }
  S.users.forEach(function (u) {
    var err = h('div',{class:'err'}), tg = h('button',{class:u.active?'danger':''}, u.active ? 'Деактивировать' : 'Активировать');
    tg.onclick = function(){ submit(tg, err, function(){ return api('PATCH','/users/'+u.id,{active:!u.active}).then(load); }); };
    var np = inp('password','',{placeholder:'Новый пароль (от 8 символов)',autocomplete:'new-password','aria-label':'Новый пароль'}), rb = h('button',null,'Сбросить пароль');
    rb.onclick = function(){ submit(rb, err, function(){ return api('PATCH','/users/'+u.id,{password:np.value}).then(function(){ np.value=''; err.textContent='Пароль изменён'; }); }); };
    w.appendChild(h('div',{class:'card'+(u.active?'':' inactive')}, h('b',null,u.username), ' · ' + (ROLE[u.role]||u.role) + (u.active?'':' (неактивен)'),
      h('div',{class:'mut'},'Создан: '+fmt(u.created_at)), h('div',{class:'row'}, np, rb, tg), err));
  });
  return w;
}

// ---------- audit ----------
function auditView(main) {
  main.appendChild(h('div',{class:'row'}, h('h2',{class:'grow'},'Журнал'), h('button',{onclick:function(){load();}},'↻ Обновить')));
  main.appendChild(h('div',{id:'listErr',class:'err'})); main.appendChild(h('div',{id:'list'}));
}
function auditTable() {
  if (!(S.audit||[]).length) return h('div',{class:'empty'},'Записей пока нет');
  var t = h('table', null, h('tr', null, h('th',null,'Время'), h('th',null,'Кто'), h('th',null,'Действие'), h('th',null,'Объект'), h('th',null,'Детали')));
  S.audit.forEach(function (a) {
    var d = a.details; if (d && typeof d === 'object') d = JSON.stringify(d);
    t.appendChild(h('tr', null, h('td',null,fmt(a.ts)), h('td',null,a.username), h('td',null,a.action), h('td',null,a.entity + (a.entity_id != null ? ' #' + a.entity_id : '')), h('td',null,d)));
  });
  return h('div',{class:'tbl'}, t);
}

// ---------- profile ----------
function profileView(main) {
  var o = inp('password','',{required:'required',autocomplete:'current-password'}), n = inp('password','',{required:'required',minlength:'8',autocomplete:'new-password'});
  var err = h('div',{class:'err',role:'alert'}), btn = h('button',{class:'pri',type:'submit'},'Сменить пароль');
  var lo = h('button',{class:'danger'},'Выйти'); var lerr = h('div',{class:'err'});
  lo.onclick = function(){ submit(lo, lerr, function(){ return api('POST','/auth/logout').catch(function(){}).then(logoutLocal); }); };
  main.appendChild(h('h2',null,'Профиль'));
  main.appendChild(h('div',{class:'card'}, h('b',null,S.user.username), ' · ' + (ROLE[S.user.role]||S.user.role)));
  main.appendChild(h('form',{class:'card',onsubmit:function(ev){ ev.preventDefault();
    submit(btn, err, function(){ return api('POST','/auth/password',{old_password:o.value,new_password:n.value}).then(function(){ o.value=''; n.value=''; err.textContent='Пароль изменён'; }); });
  }}, h('b',null,'Смена пароля'), field('Текущий пароль',o), field('Новый пароль (не короче 8 символов)',n), err, btn));
  main.appendChild(h('div',{class:'card'}, lo, lerr));
}

if (S.token) { S.user = null; start(); } else render();
})();
