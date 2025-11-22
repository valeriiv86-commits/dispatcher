let allOrders = [];
let currentFilter = 'all';

const statusLabels = {
    new: 'Новый',
    in_progress: 'В работе',
    done: 'Выполнен',
    cancelled: 'Отменён',
};

const statusClasses = {
    new: 'new',
    in_progress: 'in_progress',
    done: 'done',
    cancelled: 'cancelled',
};

function apiUrl(path) {
    if (API_BASE) {
        return `${API_BASE}${path}`;
    }
    return path;
}

async function checkServer() {
    const statusEl = document.getElementById('server-status');
    try {
        const res = await fetch(apiUrl('/'));
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        statusEl.textContent = `Сервер OK (${data.service || 'api'})`;
        statusEl.style.color = '#22c55e';
    } catch (err) {
        statusEl.textContent = 'Сервер недоступен';
        statusEl.style.color = '#ef4444';
    }
}

async function loadOrders() {
    try {
        const res = await fetch(apiUrl('/orders'));
        if (!res.ok) throw new Error('HTTP ' + res.status);
        allOrders = await res.json();
        renderOrders();
    } catch (err) {
        console.error('Ошибка загрузки заказов', err);
    }
}

function g24ExtractPrice(order) {
    if (order.totalPrice != null && order.totalPrice !== '') {
        return `${Number(order.totalPrice).toLocaleString('ru-RU')} ₽`;
    }
    if (order.price != null && order.price !== '') {
        return `${Number(order.price).toLocaleString('ru-RU')} ₽`;
    }
    if (order.comment) {
        const match = order.comment.match(/\[(\d+(?:[\s\d]*)?)\s*₽\]/);
        if (match) {
            const value = Number(match[1].replace(/\D/g, ''));
            if (!Number.isNaN(value)) {
                return `${value.toLocaleString('ru-RU')} ₽`;
            }
        }
    }
    return '-';
}

function g24PriceToNumber(order) {
    if (order.totalPrice != null && order.totalPrice !== '') {
        const n = Number(order.totalPrice);
        if (!Number.isNaN(n)) return n;
    }
    if (order.price != null && order.price !== '') {
        const n = Number(order.price);
        if (!Number.isNaN(n)) return n;
    }
    const extracted = g24ExtractPrice(order);
    if (extracted !== '-') {
        const value = Number(extracted.replace(/\D/g, ''));
        if (!Number.isNaN(value)) return value;
    }
    return 0;
}

function formatDate(value) {
    if (!value) return '';
    const date = new Date(value);
    return date.toLocaleString('ru-RU');
}

function buildOrderCard(order) {
    const card = document.createElement('div');
    card.className = 'order-card';

    const header = document.createElement('div');
    header.className = 'order-header';

    const title = document.createElement('h3');
    title.className = 'order-title';
    title.textContent = order.client_name || 'Без имени';

    const badge = document.createElement('span');
    const statusKey = order.status || 'new';
    badge.className = `badge ${statusClasses[statusKey] || ''}`;
    badge.textContent = statusLabels[statusKey] || statusKey;

    header.appendChild(title);
    header.appendChild(badge);

    const meta = document.createElement('div');
    meta.className = 'order-meta';
    meta.textContent = `${formatDate(order.created_at)} • ${order.client_phone || ''}`;

    const route = document.createElement('div');
    route.className = 'order-meta';
    route.textContent = `${order.from_address || '-'} → ${order.to_address || '-'}`;

    const comment = document.createElement('div');
    comment.className = 'order-comment';
    comment.textContent = order.comment || '';

    const price = document.createElement('div');
    price.className = 'order-price';
    price.textContent = `Цена: ${g24ExtractPrice(order)}`;

    const actions = document.createElement('div');
    actions.className = 'order-actions';

    const takeBtn = document.createElement('button');
    takeBtn.textContent = 'Взять';
    takeBtn.addEventListener('click', () => changeStatus(order.id, 'in_progress'));

    const doneBtn = document.createElement('button');
    doneBtn.textContent = 'Готово';
    doneBtn.addEventListener('click', () => changeStatus(order.id, 'done'));

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Отмена';
    cancelBtn.addEventListener('click', () => changeStatus(order.id, 'cancelled'));

    actions.append(takeBtn, doneBtn, cancelBtn);

    card.append(header, meta, route, comment, price, actions);
    return card;
}

function renderOrders() {
    const container = document.getElementById('orders-list');
    container.innerHTML = '';

    const filtered = allOrders.filter((o) => currentFilter === 'all' || (o.status || 'new') === currentFilter);

    if (filtered.length === 0) {
        container.innerHTML = '<div class="order-meta">Заявок нет</div>';
    } else {
        filtered
            .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
            .forEach((order) => container.appendChild(buildOrderCard(order)));
    }

    updateOrdersSummary(filtered);
}

function updateOrdersSummary(orders) {
    const summary = document.getElementById('orders-summary');
    const total = orders.reduce((sum, order) => sum + g24PriceToNumber(order), 0);
    summary.textContent = `Итого по выбранным: ${total.toLocaleString('ru-RU')} ₽ (${orders.length} заявок)`;
}

async function changeStatus(orderId, status) {
    try {
        const res = await fetch(apiUrl(`/orders/${orderId}`), {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        await loadOrders();
    } catch (err) {
        console.error('Ошибка смены статуса', err);
    }
}

function addPriceTag(comment, priceValue) {
    if (!priceValue || Number.isNaN(priceValue)) return comment;
    const priceTag = `[${Number(priceValue).toLocaleString('ru-RU')} ₽]`;
    if (!comment) return priceTag;
    if (/\[.*₽\]/.test(comment)) {
        return comment.replace(/\[.*?₽\]/, priceTag);
    }
    return `${priceTag} ${comment}`.trim();
}

async function createOrder(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    const priceValue = Number(payload.price || payload.totalPrice || 0);
    payload.price = priceValue || 0;
    payload.totalPrice = priceValue || 0;
    payload.comment = addPriceTag(payload.comment, priceValue);

    try {
        const res = await fetch(apiUrl('/orders'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        form.reset();
        await loadOrders();
    } catch (err) {
        console.error('Ошибка создания заказа', err);
    }
}

function setupFilters() {
    const buttons = document.querySelectorAll('.filter');
    buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
            buttons.forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderOrders();
        });
    });
}

function setupExport() {
    const btn = document.getElementById('export-csv');
    btn.addEventListener('click', () => {
        const filtered = allOrders.filter((o) => currentFilter === 'all' || (o.status || 'new') === currentFilter);
        const lines = ['id;дата;клиент;телефон;адрес откуда;адрес куда;комментарий;статус;цена'];
        filtered.forEach((o) => {
            const row = [
                o.id,
                formatDate(o.created_at),
                o.client_name || '',
                o.client_phone || '',
                o.from_address || '',
                o.to_address || '',
                (o.comment || '').replace(/\n/g, ' '),
                statusLabels[o.status || 'new'] || o.status || '',
                g24PriceToNumber(o),
            ];
            lines.push(row.map((cell) => `${String(cell).replace(/;/g, ',')}`).join(';'));
        });
        const csv = lines.join('\n');
        const stamp = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const fileName = `orders_${stamp.getFullYear()}${pad(stamp.getMonth() + 1)}${pad(stamp.getDate())}_${pad(stamp.getHours())}${pad(stamp.getMinutes())}.csv`;
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });
}

function setupPriceCalculator() {
    const priceInput = document.getElementById('price-input');
    const rate = document.getElementById('calc-rate');
    const workers = document.getElementById('calc-workers');
    const hours = document.getElementById('calc-hours');
    const time = document.getElementById('calc-time');
    const apply = document.getElementById('calc-apply');

    if (!priceInput || !apply) return;

    apply.addEventListener('click', () => {
        const result = Math.round(Number(rate.value || 0) * Number(workers.value || 0) * Number(hours.value || 0) * Number(time.value || 1));
        priceInput.value = result;
        priceInput.dispatchEvent(new Event('input'));
        priceInput.dispatchEvent(new Event('change'));
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('order-form');
    form.addEventListener('submit', createOrder);

    setupFilters();
    setupExport();
    setupPriceCalculator();
    checkServer();
    loadOrders();
});
