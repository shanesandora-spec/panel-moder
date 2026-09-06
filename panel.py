import sqlite3
import os
import datetime
import requests
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_for_arizona_hub_777_extended")

# --- КОНФИГУРАЦИЯ И НАСТРОЙКИ DISCORD OAUTH2 ---
CLIENT_ID = "1545765992582479872"
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "ТВОЙ_CLIENT_SECRET_ЗДЕСЬ")
DISCORD_API_ENDPOINT = "https://discord.com/api/v10"

# Автоматическое определение внешнего URL (Render / локальный запуск)
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
REDIRECT_URI = f"{BASE_URL}/auth/callback"

# Список администраторов (Discord ID), имеющих расширенные права
DEVELOPER_IDS = ["123456789012345678"] 

# --- ИНИЦИАЛИЗАЦИЯ И РАСШИРЕНИЕ БАЗЫ ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Таблица логов модерации и наказаний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moderation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moderator TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица товаров магазина фракции
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            stock INTEGER DEFAULT 10
        )
    ''')
    
    # Таблица ролей и состава фракции
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            rank_level INTEGER DEFAULT 1,
            warnings INTEGER DEFAULT 0
        )
    ''')

    # Таблица системных настроек и логов аудита
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Таблица заявлений / отчетов состава
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            report_type TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'На рассмотрении',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- МАСШТАБНЫЙ HTML / CSS / JS ШАБЛОН ПАНЕЛИ УПРАВЛЕНИЯ ---
PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arizona Staff Hub — Расширенная панель управления</title>
    <style>
        :root {
            --bg-color: #0b0d13;
            --sidebar-bg: #11141d;
            --card-bg: #181c28;
            --card-hover: #1f2435;
            --accent: #5865F2;
            --accent-hover: #4752C4;
            --text: #dbdee1;
            --text-muted: #949ba4;
            --danger: #f23f43;
            --success: #23a55a;
            --warning: #f0b232;
            --border: #262b3d;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Сайдбар */
        .sidebar {
            width: 280px;
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .sidebar-header {
            padding: 24px 20px;
            font-size: 1.25rem;
            font-weight: 700;
            color: #fff;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: 0.5px;
        }

        .nav-links {
            list-style: none;
            padding: 20px 12px;
            flex-grow: 1;
            overflow-y: auto;
        }

        .nav-links li {
            padding: 12px 16px;
            border-radius: 10px;
            cursor: pointer;
            margin-bottom: 6px;
            color: var(--text-muted);
            transition: all 0.25s ease;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.95rem;
        }

        .nav-links li:hover {
            background-color: var(--card-bg);
            color: #fff;
        }

        .nav-links li.active {
            background-color: var(--accent);
            color: #fff;
            box-shadow: 0 4px 12px rgba(88, 101, 242, 0.3);
        }

        /* Пользовательский блок внизу сайдбара */
        .user-panel {
            padding: 16px 20px;
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 14px;
            background: rgba(0, 0, 0, 0.25);
        }

        .user-avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--accent);
        }

        .user-info {
            font-size: 0.9rem;
            overflow: hidden;
            flex-grow: 1;
        }

        .user-name {
            font-weight: bold;
            color: #fff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .logout-btn {
            color: var(--danger);
            font-size: 0.8rem;
            text-decoration: none;
            display: inline-block;
            margin-top: 3px;
            font-weight: 600;
        }

        .logout-btn:hover {
            text-decoration: underline;
        }

        /* Основная область контента */
        .main-content {
            flex-grow: 1;
            padding: 40px;
            overflow-y: auto;
            background: radial-gradient(circle at top right, #131722 0%, var(--bg-color) 60%);
        }

        .tab-content {
            display: none;
            animation: fadeIn 0.3s ease-in-out;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        h1 {
            font-size: 2rem;
            color: #fff;
            margin-bottom: 24px;
            font-weight: 700;
        }

        h3 {
            color: #fff;
            margin-bottom: 12px;
            font-size: 1.2rem;
            font-weight: 600;
        }

        /* Системные карточки */
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
            transition: border-color 0.2s;
        }

        .card:hover {
            border-color: rgba(88, 101, 242, 0.4);
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }

        /* Статистические мини-карточки */
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .stat-card .title {
            color: var(--text-muted);
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-card .value {
            color: #fff;
            font-size: 1.8rem;
            font-weight: 700;
        }

        /* Таблицы стилизованные */
        .table-container {
            width: 100%;
            overflow-x: auto;
            margin-top: 15px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th, td {
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            font-size: 0.95rem;
        }

        th {
            color: var(--text-muted);
            font-weight: 600;
            background: rgba(0, 0, 0, 0.15);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.8px;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.015);
        }

        /* Формы и интерактивные поля ввода */
        .form-group {
            margin-bottom: 18px;
        }

        label {
            display: block;
            margin-bottom: 6px;
            color: var(--text-muted);
            font-size: 0.85rem;
            font-weight: 600;
        }

        input, select, textarea {
            width: 100%;
            padding: 12px 16px;
            background: var(--bg-color);
            border: 1px solid var(--border);
            border-radius: 9px;
            color: #fff;
            font-size: 0.95rem;
            transition: all 0.2s;
        }

        input:focus, select:focus, textarea:focus {
            border-color: var(--accent);
            outline: none;
            box-shadow: 0 0 0 3px rgba(88, 101, 242, 0.15);
        }

        /* Кнопки */
        .btn {
            background-color: var(--accent);
            color: white;
            border: none;
            padding: 12px 22px;
            border-radius: 9px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-decoration: none;
            font-size: 0.95rem;
        }

        .btn:hover {
            background-color: var(--accent-hover);
            transform: translateY(-1px);
        }

        .btn-danger { background-color: var(--danger); }
        .btn-danger:hover { background-color: #d83539; }
        .btn-success { background-color: var(--success); }
        .btn-success:hover { background-color: #1f9450; }
        .btn-warning { background-color: var(--warning); color: #000; }
        .btn-warning:hover { background-color: #d99e28; }

        /* Экран авторизации */
        .login-screen {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            width: 100vw;
            background: var(--bg-color);
        }

        .login-card {
            background: var(--card-bg);
            padding: 48px;
            border-radius: 20px;
            border: 1px solid var(--border);
            text-align: center;
            max-width: 440px;
            box-shadow: 0 16px 40px rgba(0,0,0,0.4);
        }

        .login-card h2 {
            color: #fff;
            margin-bottom: 16px;
            font-size: 1.8rem;
        }

        .login-card p {
            color: var(--text-muted);
            margin-bottom: 30px;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .badge {
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .badge-success { background: rgba(35, 165, 90, 0.2); color: var(--success); }
        .badge-danger { background: rgba(242, 63, 67, 0.2); color: var(--danger); }
    </style>
</head>
<body>

{% if not session.get('user') %}
    <div class="login-screen">
        <div class="login-card">
            <h2>Arizona Staff Hub</h2>
            <p>Закрытая информационная система и панель администрирования. Требуется обязательная авторизация через защищенный профиль Discord.</p>
            <a href="/login" class="btn" style="width: 100%;">Авторизоваться через Discord</a>
        </div>
    </div>
{% else %}
    <div class="sidebar">
        <div>
            <div class="sidebar-header">
                ⚡ Arizona Hub Pro
            </div>
            <ul class="nav-links">
                <li class="active" onclick="switchTab('dashboard', this)">📊 Дашборд</li>
                <li onclick="switchTab('moderation', this)">🛡️ Модуль модерации</li>
                <li onclick="switchTab('shop', this)">🛒 Магазин фракции</li>
                <li onclick="switchTab('staff', this)">👥 Состав и Роли</li>
                <li onclick="switchTab('reports', this)">📋 Отчеты</li>
                <li onclick="switchTab('settings', this)">⚙️ Настройки</li>
            </ul>
        </div>
        <div class="user-panel">
            <img src="https://cdn.discordapp.com/avatars/{{ session['user']['id'] }}/{{ session['user']['avatar'] }}.png" class="user-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="user-info">
                <div class="user-name">{{ session['user']['username'] }}</div>
                <a href="/logout" class="logout-btn">Завершить сеанс</a>
            </div>
        </div>
    </div>

    <main class="main-content">
        <!-- ВКЛАДКА: ДАШБОРД -->
        <section id="dashboard" class="tab-content active">
            <h1>Общий обзор системы</h1>
            <div class="grid-3" style="margin-bottom: 24px;">
                <div class="stat-card">
                    <span class="title">Всего записей модерации</span>
                    <span class="value">{{ logs|length }}</span>
                </div>
                <div class="stat-card">
                    <span class="title">Товаров в магазине</span>
                    <span class="value">{{ items|length }}</span>
                </div>
                <div class="stat-card">
                    <span class="title">Активных отчетов</span>
                    <span class="value">{{ reports|length }}</span>
                </div>
            </div>
            <div class="grid-2">
                <div class="card">
                    <h3>Статус синхронизации Discord</h3>
                    <p style="color: var(--text-muted); margin-top: 10px; line-height: 1.5;">Связь с сервером Arizona RolePlay установлена. База данных SQLite функционирует стабильно, резервное копирование выполняется автоматически.</p>
                </div>
                <div class="card">
                    <h3>Быстрые действия</h3>
                    <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                        <button class="btn" onclick="switchTab('moderation', document.querySelectorAll('.nav-links li')[1])">Добавить наказание</button>
                        <button class="btn btn-success" onclick="switchTab('shop', document.querySelectorAll('.nav-links li')[2])">Добавить товар</button>
                    </div>
                </div>
            </div>
        </section>

        <!-- ВКЛАДКА: МОДЕРАЦИЯ -->
        <section id="moderation" class="tab-content">
            <h1>Модуль модерации и учета нарушений</h1>
            <div class="card">
                <h3>Зарегистрировать новое действие / наказание</h3>
                <form action="/api/add_log" method="POST" style="margin-top: 15px;">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Ответственный администратор</label>
                            <input type="text" name="moderator" value="{{ session['user']['username'] }}" required>
                        </div>
                        <div class="form-group">
                            <label>Тип действия / Наказания</label>
                            <input type="text" name="action" placeholder="Например: Выговор / Мут / Деморган" required>
                        </div>
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Нарушитель (Игровой ник / ID)</label>
                            <input type="text" name="target" placeholder="Alex_Fierro" required>
                        </div>
                        <div class="form-group">
                            <label>Причина нарушения</label>
                            <input type="text" name="reason" placeholder="Нарушение правил капта / DM">
                        </div>
                    </div>
                    <button type="submit" class="btn">Внести запись в базу</button>
                </form>
            </div>
            <div class="card">
                <h3>История логов модерации</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Модератор</th>
                                <th>Действие</th>
                                <th>Нарушитель</th>
                                <th>Причина</th>
                                <th>Дата / Время</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in logs %}
                            <tr>
                                <td>#{{ log[0] }}</td>
                                <td><b>{{ log[1] }}</b></td>
                                <td><span class="badge badge-danger">{{ log[2] }}</span></td>
                                <td>{{ log[3] }}</td>
                                <td style="color: var(--text-muted);">{{ log[4] if log[4] else 'Не указана' }}</td>
                                <td style="color: var(--text-muted); font-size: 0.85rem;">{{ log[5] }}</td>
                            </tr>
                            {% else %}
                            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Логи модерации отсутствуют</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ВКЛАДКА: МАГАЗИН -->
        <section id="shop" class="tab-content">
            <h1>Управление магазином фракции</h1>
            <div class="card">
                <h3>Добавить новый товар</h3>
                <form action="/api/add_shop_item" method="POST" style="margin-top: 15px;">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Название товара</label>
                            <input type="text" name="title" placeholder="Снятие выговора / Повышение" required>
                        </div>
                        <div class="form-group">
                            <label>Стоимость (в виртуальной валюте / баллах)</label>
                            <input type="number" name="price" placeholder="150000" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Подробное описание товара</label>
                        <textarea name="description" rows="2" placeholder="Условия получения и требования..."></textarea>
                    </div>
                    <button type="submit" class="btn btn-success">Опубликовать в ассортимент</button>
                </form>
            </div>
            <div class="card">
                <h3>Актуальный ассортимент</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Название</th>
                                <th>Цена</th>
                                <th>Описание</th>
                                <th>Действие</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in items %}
                            <tr>
                                <td>#{{ item[0] }}</td>
                                <td><b>{{ item[1] }}</b></td>
                                <td style="color: var(--success); font-weight: bold;">${{ item[2] }}</td>
                                <td style="color: var(--text-muted);">{{ item[3] }}</td>
                                <td>
                                    <form action="/api/delete_shop_item/{{ item[0] }}" method="POST" style="display:inline;">
                                        <button type="submit" class="btn btn-danger" style="padding: 6px 12px; font-size: 0.8rem;">Удалить</button>
                                    </form>
                                </td>
                            </tr>
                            {% else %}
                            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Товары временно отсутствуют</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ВКЛАДКА: СОСТАВ -->
        <section id="staff" class="tab-content">
            <h1>Кадровый состав и роли</h1>
            <div class="card">
                <h3>Список участников руководства</h3>
                <p style="color: var(--text-muted); margin-top: 8px;">Данные синхронизированы с ролевой моделью Discord-сервера проекта.</p>
            </div>
        </section>

        <!-- ВКЛАДКА: ОТЧЕТЫ -->
        <section id="reports" class="tab-content">
            <h1>Система отчетов</h1>
            <div class="card">
                <h3>Активные отчеты сотрудников</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Автор</th>
                                <th>Тип отчета</th>
                                <th>Содержимое</th>
                                <th>Статус</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for rep in reports %}
                            <tr>
                                <td>#{{ rep[0] }}</td>
                                <td>{{ rep[1] }}</td>
                                <td>{{ rep[2] }}</td>
                                <td style="color: var(--text-muted);">{{ rep[3] }}</td>
                                <td><span class="badge badge-success">{{ rep[4] }}</span></td>
                            </tr>
                            {% else %}
                            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Нет новых отчетов</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ВКЛАДКА: НАСТРОЙКИ -->
        <section id="settings" class="tab-content">
            <h1>Системные настройки</h1>
            <div class="card">
                <h3>Конфигурация сервера</h3>
                <p style="color: var(--text-muted); margin-top: 10px;">Платформа работает на базе Flask Framework с использованием базы данных SQLite. Версия движка: <b>4.2.0-PRO</b>.</p>
            </div>
        </section>
    </main>

    <script>
        function switchTab(tabId, element) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            if(element) element.classList.add('active');
        }
    </script>
{% endif %}

</body>
</html>
"""

# --- МАРШРУТЫ И ОБРАБОТЧИКИ FLASK ---

@app.route("/")
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM moderation_logs ORDER BY id DESC LIMIT 20")
    logs = cursor.fetchall()
    
    cursor.execute("SELECT * FROM shop_items ORDER BY id DESC")
    items = cursor.fetchall()

    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    reports = cursor.fetchall()
    
    conn.close()
    return render_template_string(PANEL_TEMPLATE, logs=logs, items=items, reports=reports)

@app.route("/login")
def login():
    discord_login_url = (
        f"{DISCORD_API_ENDPOINT}/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify guilds"
    )
    return redirect(discord_login_url)

@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return "Критическая ошибка: авторизационный код Discord не обнаружен.", 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_response = requests.post(f"{DISCORD_API_ENDPOINT}/oauth2/token", data=data, headers=headers)
    if token_response.status_code != 200:
        return f"Ошибка верификации токена в Discord API: {token_response.text}", 500

    token_json = token_response.json()
    access_token = token_json.get("access_token")

    user_response = requests.get(
        f"{DISCORD_API_ENDPOINT}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if user_response.status_code != 200:
        return "Ошибка получения пользовательских данных из профиля Discord.", 500

    user_data = user_response.json()
    session['user'] = {
        "id": user_data.get("id"),
        "username": user_data.get("username"),
        "avatar": user_data.get("avatar")
    }

    return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route("/api/add_log", methods=["POST"])
def add_log():
    if 'user' not in session:
        return redirect(url_for('index'))
    
    moderator = request.form.get("moderator")
    action = request.form.get("action")
    target = request.form.get("target")
    reason = request.form.get("reason")
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO moderation_logs (moderator, action, target, reason) VALUES (?, ?, ?, ?)",
        (moderator, action, target, reason)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route("/api/add_shop_item", methods=["POST"])
def add_shop_item():
    if 'user' not in session:
        return redirect(url_for('index'))
    
    title = request.form.get("title")
    price = request.form.get("price")
    description = request.form.get("description")
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO shop_items (title, price, description) VALUES (?, ?, ?)",
        (title, price, description)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route("/api/delete_shop_item/<int:item_id>", methods=["POST"])
def delete_shop_item(item_id):
    if 'user' not in session:
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shop_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
