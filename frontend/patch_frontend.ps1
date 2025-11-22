$ErrorActionPreference = 'Stop'

function Write-Info($message) { Write-Host $message }

function Set-FileContent($path, $content) {
    $existing = if (Test-Path $path) { Get-Content -Raw -Path $path } else { '' }
    if ($existing -eq $content) {
        Write-Info "[SKIP] $path без изменений"
    } else {
        $dir = Split-Path -Parent $path
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
        $content | Set-Content -Path $path -Encoding UTF8
        Write-Info "[UPDATE] $path записан"
    }
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-FileContent "$root/index.html" @'
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Диспетчерская 24/7</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="page">
        <header class="page-header">
            <h1>Диспетчерская 24/7</h1>
            <div id="server-status" class="status-indicator">Проверка сервера...</div>
        </header>
        <main class="grid">
            <section class="card">
                <h2>Новая заявка</h2>
                <form id="order-form">
                    <div class="form-row">
                        <label>Имя клиента</label>
                        <input type="text" name="client_name" required>
                    </div>
                    <div class="form-row">
                        <label>Телефон</label>
                        <input type="tel" name="client_phone" required>
                    </div>
                    <div class="form-row">
                        <label>Адрес (откуда)</label>
                        <input type="text" name="from_address" required>
                    </div>
                    <div class="form-row">
                        <label>Адрес (куда)</label>
                        <input type="text" name="to_address" required>
                    </div>
                    <div class="form-row">
                        <label>Комментарий</label>
                        <textarea name="comment" rows="3"></textarea>
                    </div>
                    <div class="form-row">
                        <label for="price-input">Цена</label>
                        <input type="number" id="price-input" name="price" min="0" step="100" placeholder="0">
                    </div>
                    <div class="price-calculator">
                        <div class="price-calculator-row">
                            <label for="calc-rate">Ставка за час (₽)</label>
                            <input type="number" id="calc-rate" value="1000" min="0" step="100">
                        </div>
                        <div class="price-calculator-row">
                            <label for="calc-workers">Кол-во грузчиков</label>
                            <input type="number" id="calc-workers" value="2" min="1" step="1">
                        </div>
                        <div class="price-calculator-row">
                            <label for="calc-hours">Часы работы</label>
                            <input type="number" id="calc-hours" value="3" min="1" step="1">
                        </div>
                        <div class="price-calculator-row">
                            <label for="calc-time">Время суток</label>
                            <select id="calc-time">
                                <option value="1">День (x1)</option>
                                <option value="1.2">Вечер (x1.2)</option>
                                <option value="1.5">Ночь (x1.5)</option>
                            </select>
                        </div>
                        <div class="price-calculator-actions">
                            <button type="button" id="calc-apply">Рассчитать цену</button>
                        </div>
                    </div>
                    <div class="form-actions">
                        <button type="submit">Создать заявку</button>
                    </div>
                </form>
            </section>
            <section class="card">
                <div class="card-header">
                    <h2>Список заявок</h2>
                    <div class="actions">
                        <button id="export-csv">Экспорт в CSV</button>
                    </div>
                </div>
                <div class="filters">
                    <button data-filter="all" class="filter active">Все</button>
                    <button data-filter="new" class="filter">Новый</button>
                    <button data-filter="in_progress" class="filter">В работе</button>
                    <button data-filter="done" class="filter">Выполнен</button>
                    <button data-filter="cancelled" class="filter">Отменён</button>
                </div>
                <div id="orders-list" class="orders-list"></div>
                <div id="orders-summary" class="orders-summary">Итого по выбранным: 0 ₽ (0 заявок)</div>
            </section>
        </main>
    </div>
    <script src="config.js"></script>
    <script src="app.js"></script>
</body>
</html>
'@

Set-FileContent "$root/styles.css" @'
:root {
    --bg: #0f172a;
    --card: #1e293b;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --accent-2: #22c55e;
    --danger: #ef4444;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    font-family: "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
}

.page {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.page-header h1 { margin: 0; }

.status-indicator {
    padding: 6px 12px;
    border-radius: 8px;
    background: #1f2937;
    color: var(--muted);
    font-size: 14px;
}

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.card {
    background: var(--card);
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}

.card h2 {
    margin: 0 0 12px;
}

.form-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
}

.form-row label { color: var(--muted); }

.form-row input,
.form-row textarea,
.form-row select {
    background: #0b1220;
    color: var(--text);
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 10px 12px;
}

.form-row textarea { resize: vertical; }

.form-actions { margin-top: 12px; }

button {
    background: var(--accent);
    color: #0b1220;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s ease;
}

button:hover { opacity: 0.9; }

.filters {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}

.filter {
    background: #111827;
    color: var(--text);
    border: 1px solid #1f2937;
}

.filter.active { border-color: var(--accent); color: var(--accent); }

.orders-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.order-card {
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 12px;
    background: #0b1220;
}

.order-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.order-title { margin: 0; font-size: 16px; }

.badge {
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 12px;
    color: #0b1220;
    font-weight: 700;
}

.badge.new { background: var(--accent); }
.badge.in_progress { background: #f59e0b; }
.badge.done { background: var(--accent-2); }
.badge.cancelled { background: var(--danger); }

.order-meta { color: var(--muted); font-size: 14px; margin-bottom: 6px; }
.order-comment { margin: 6px 0; }

.order-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.order-price { font-weight: 700; }

.price-calculator {
    margin: 8px 0 12px;
    padding: 12px;
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 10px;
}

.price-calculator-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 10px;
}

.price-calculator-actions { text-align: right; }

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.orders-summary {
    margin-top: 12px;
    padding: 10px 12px;
    background: #111827;
    border-radius: 10px;
    color: var(--muted);
}

@media (max-width: 960px) {
    .grid { grid-template-columns: 1fr; }
}
'@

Set-FileContent "$root/config.js" "const API_BASE = '';"

Set-FileContent "$root/app.js" @'
$(Get-Content -Raw "$root/app.js")
'@
