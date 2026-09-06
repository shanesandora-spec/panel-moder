import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Таблица модераторов (без фейковых людей, пустая для старта)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moderators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT,
            username TEXT,
            real_name TEXT,
            lvl INTEGER,
            days_lvl INTEGER,
            days_all INTEGER,
            warnings INTEGER,
            prevs INTEGER,
            inactives TEXT,
            points REAL,
            position TEXT
        )
    """)
    
    # Таблица неактивов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inactives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moderator TEXT,
            reason TEXT,
            dates TEXT,
            status TEXT
        )
    """)
    
    # Таблица магазина
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            description TEXT
        )
    """)
    
    # Добавим дефолтные товары в магазин Prime, если он пустой
    cursor.execute("SELECT COUNT(*) FROM shop")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO shop (item_name, price, description) VALUES (?, ?, ?)", ("Снять выговор", 150, "Полное аннулирование активного выговора"))
        cursor.execute("INSERT INTO shop (item_name, price, description) VALUES (?, ?, ?)", ("Иммунитет от пред. на 3 дня", 100, "Защита от получения предупреждений"))
        cursor.execute("INSERT INTO shop (item_name, price, description) VALUES (?, ?, ?)", ("Пакет балов (+50)", 200, "Мгновенное начисление баллов на баланс"))

    conn.commit()
    conn.close()

init_db()

app = Flask("")

MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Arizona Hub & Prime — Панель управления</title>
    <style>
        :root {
            --bg-base: #060709;
            --bg-surface: #0d0f17;
            --bg-card: #12151f;
            --border-color: #1f2433;
            --accent-primary: #f59e0b;
            --accent-glow: rgba(245, 158, 11, 0.25);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --success: #10b981;
            --danger: #ef4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Segoe UI', sans-serif; }
        body { background-color: var(--bg-base); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; position: relative; }

        /* Летающий интерактивный фон (частицы/анимация) */
        .particles { position: absolute; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; z-index: 0; pointer-events: none; }
        .particle { position: absolute; display: block; list-style: none; width: 4px; height: 4px; background: rgba(245, 158, 11, 0.4); box-shadow: 0 0 10px var(--accent-primary); border-radius: 50%; animation: animate 25s linear infinite; bottom: -150px; }
        .particle:nth-child(1) { left: 25%; width: 6px; height: 6px; animation-delay: 0s; }
        .particle:nth-child(2) { left: 10%; width: 3px; height: 3px; animation-delay: 2s; animation-duration: 12s; }
        .particle:nth-child(3) { left: 70%; width: 5px; height: 5px; animation-delay: 4s; }
        .particle:nth-child(4) { left: 40%; width: 4px; height: 4px; animation-delay: 0s; animation-duration: 18s; }
        .particle:nth-child(5) { left: 65%; width: 6px; height: 6px; animation-delay: 3s; }
        .particle:nth-child(6) { left: 85%; width: 3px; height: 3px; animation-delay: 5s; }

        @keyframes animate {
            0% { transform: translateY(0) rotate(0deg); opacity: 1; }
            100% { transform: translateY(-1000px) rotate(720deg); opacity: 0; }
        }

        /* Сайдбар */
        .sidebar { width: 260px; background-color: var(--bg-surface); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 24px; z-index: 10; backdrop-filter: blur(10px); }
        .brand { font-size: 15px; font-weight: 800; color: #fff; margin-bottom: 35px; display: flex; align-items: center; gap: 10px; letter-spacing: 0.5px; text-transform: uppercase; }
        .brand span { color: var(--accent-primary); text-shadow: 0 0 20px var(--accent-glow); }
        
        .menu-label { font-size: 10px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; letter-spacing: 1.5px; font-weight: 600; }
        .nav-link { padding: 12px 16px; border-radius: 12px; color: var(--text-muted); text-decoration: none; margin-bottom: 6px; display: flex; align-items: center; gap: 14px; font-size: 14px; font-weight: 500; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; border: 1px solid transparent; }
        .nav-link:hover, .nav-link.active { background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.02)); color: #fff; border-color: rgba(245, 158, 11, 0.3); transform: translateX(4px); box-shadow: 0 4px 20px rgba(245, 158, 11, 0.1); }

        /* Контент */
        .main-container { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 35px; z-index: 10; position: relative; }
        
        .top-bar { display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 18px; padding: 20px 30px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); backdrop-filter: blur(5px); }
        .top-title { font-size: 20px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 12px; }
        
        /* Кнопки с анимацией */
        .btn-action { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; font-weight: 700; padding: 12px 24px; border-radius: 12px; border: none; cursor: pointer; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; }
        .btn-action:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 8px 25px rgba(245, 158, 11, 0.5); background: linear-gradient(135deg, #fbbf24, #f59e0b); }
        .btn-action:active { transform: translateY(1px) scale(0.98); }

        /* Вкладки */
        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.4s ease forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* Карточки и сетка */
        .content-card { background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 18px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .grid-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 25px; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border-color); padding: 22px; border-radius: 16px; position: relative; overflow: hidden; }
        .stat-card::after { content: ''; position: absolute; top: 0; right: 0; width: 100px; height: 100px; background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 70%); pointer-events: none; }
        .stat-title { font-size: 12px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; margin-bottom: 8px; letter-spacing: 1px; }
        .stat-value { font-size: 28px; font-weight: 800; color: #fff; }

        /* Таблицы */
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13.5px; }
        th { color: var(--text-muted); font-weight: 600; padding: 14px 12px; border-bottom: 1px solid var(--border-color); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        td { padding: 16px 12px; border-bottom: 1px solid rgba(31, 36, 51, 0.4); color: #d1d5db; }
        tr:hover td { background-color: rgba(255, 255, 255, 0.015); }
        
        .user-block { display: flex; align-items: center; gap: 12px; font-weight: 600; color: #fff; }
        .avatar-stub { width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, #1f2433, #12151f); display: flex; align-items: center; justify-content: center; font-size: 15px; border: 1px solid var(--border-color); }
        .lvl-pill { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: var(--accent-primary); padding: 5px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }

        /* Магазин сетка */
        .shop-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
        .shop-item { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; transition: 0.3s; }
        .shop-item:hover { border-color: rgba(245, 158, 11, 0.4); transform: translateY(-4px); box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
        .shop-name { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 8px; }
        .shop-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; line-height: 1.4; }
        .shop-price { font-size: 18px; font-weight: 800; color: var(--accent-primary); margin-bottom: 15px; }

        /* Модальные окна */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); justify-content: center; align-items: center; z-index: 1000; }
        .modal.active { display: flex; animation: fadeInModal 0.3s ease; }
        @keyframes fadeInModal { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        .modal-content { background: var(--bg-surface); border: 1px solid var(--border-color); width: 450px; padding: 30px; border-radius: 20px; box-shadow: 0 25px 50px rgba(0,0,0,0.7); }
        .modal-header { font-size: 18px; font-weight: 700; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; color: #fff; }
        .close-btn { background: none; border: none; color: var(--text-muted); font-size: 22px; cursor: pointer; transition: 0.2s; }
        .close-btn:hover { color: #fff; }
        
        .form-group { margin-bottom: 15px; }
        .form-label { display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; letter-spacing: 0.5px; }
        .form-input, .form-select { width: 100%; background: var(--bg-base); border: 1px solid var(--border-color); padding: 12px 15px; border-radius: 12px; color: #fff; font-size: 14px; outline: none; transition: 0.3s; }
        .form-input:focus, .form-select:focus { border-color: var(--accent-primary); box-shadow: 0 0 15px var(--accent-glow); }
        .form-submit { width: 100%; margin-top: 10px; padding: 14px; background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; font-weight: 700; border: none; border-radius: 12px; cursor: pointer; text-transform: uppercase; font-size: 13px; transition: 0.3s; box-shadow: 0 4px 15px rgba(245,158,11,0.3); }
        .form-submit:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(245,158,11,0.5); }
    </style>
</head>
<body>

    <!-- Летающие неоновые частицы на фоне -->
    <ul class="particles">
        <li class="particle"></li>
        <li class="particle"></li>
        <li class="particle"></li>
        <li class="particle"></li>
        <li class="particle"></li>
        <li class="particle"></li>
    </ul>

    <div class="sidebar">
        <div class="brand">⚡ <span>Arizona Hub & Prime</span></div>
        <div class="menu-label">Навигация</div>
        <a class="nav-link active" onclick="switchTab('moderation', this)">🛡️ Модерация</a>
        <a class="nav-link" onclick="switchTab('stats', this)">📊 Статистика</a>
        <a class="nav-link" onclick="switchTab('inactives', this)">⏳ Неактивы</a>
        <a class="nav-link" onclick="switchTab('shop', this)">🛒 Магазин Prime</a>
    </div>

    <div class="main-container">
        
        <!-- ВКЛАДКА 1: МОДЕРАЦИЯ -->
        <div id="moderation" class="tab-content active">
            <div class="top-bar">
                <div class="top-title">⚔️ Состав модерации сервера</div>
                <button class="btn-action" onclick="toggleModal('addModal', true)">+ Добавить модератора</button>
            </div>
            <div class="content-card">
                <table>
                    <thead>
                        <tr>
                            <th>Уровень</th>
                            <th>Пользователь</th>
                            <th>Имя</th>
                            <th>Дни (Lvl)</th>
                            <th>Дни (All)</th>
                            <th>Выговоры</th>
                            <th>Преды</th>
                            <th>Неактивы</th>
                            <th>Баллы</th>
                            <th>Должность</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if mods %}
                            {% for m in mods %}
                            <tr>
                                <td><span class="lvl-pill">{{ m[4] }} LVL</span></td>
                                <td>
                                    <div class="user-block">
                                        <div class="avatar-stub">👤</div>
                                        <div>
                                            <div>{{ m[2] }}</div>
                                            <div style="font-size: 11px; color: var(--text-muted);">ID: {{ m[1] }}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>{{ m[3] }}</td>
                                <td>{{ m[5] }}</td>
                                <td>{{ m[6] }}</td>
                                <td style="color: {% if m[7] > 0 %}var(--danger){% else %}inherit{% endif %};">{{ m[7] }}</td>
                                <td>{{ m[8] }}</td>
                                <td>{{ m[9] }}</td>
                                <td style="color: var(--success); font-weight: bold;">{{ m[10] }}</td>
                                <td>{{ m[11] }}</td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 40px;">Список модераторов пуст. Нажмите кнопку «Добавить модератора» вверху.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ВКЛАДКА 2: СТАТИСТИКА -->
        <div id="stats" class="tab-content">
            <div class="top-bar">
                <div class="top-title">📈 Общая статистика сервера</div>
            </div>
            <div class="grid-stats">
                <div class="stat-card">
                    <div class="stat-title">Всего модераторов</div>
                    <div class="stat-value">{{ mods|length }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Активных выговоров</div>
                    <div class="stat-value" style="color: var(--danger);">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Общий баланс баллов</div>
                    <div class="stat-value" style="color: var(--success);">0.0</div>
                </div>
            </div>
            <div class="content-card">
                <p style="color: var(--text-muted); text-align: center; padding: 20px;">Интерактивные графики и подробные метрики активности будут наполняться по мере работы бота.</p>
            </div>
        </div>

        <!-- ВКЛАДКА 3: НЕАКТИВЫ -->
        <div id="inactives" class="tab-content">
            <div class="top-bar">
                <div class="top-title">⏳ Запросы на неактив</div>
                <button class="btn-action" onclick="toggleModal('inactiveModal', true)">Подать заявку</button>
            </div>
            <div class="content-card">
                <table>
                    <thead>
                        <tr>
                            <th>Модератор</th>
                            <th>Причина</th>
                            <th>Сроки</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if inactives %}
                            {% for i in inactives %}
                            <tr>
                                <td>{{ i[1] }}</td>
                                <td>{{ i[2] }}</td>
                                <td>{{ i[3] }}</td>
                                <td style="color: var(--accent-primary); font-weight: bold;">{{ i[4] }}</td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 40px;">Активных запросов на неактив нет.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ВКЛАДКА 4: МАГАЗИН PRIME -->
        <div id="shop" class="tab-content">
            <div class="top-bar">
                <div class="top-title">🛒 Магазин привилегий Prime</div>
            </div>
            <div class="shop-grid">
                {% for item in shop_items %}
                <div class="shop-item">
                    <div>
                        <div class="shop-name">{{ item[1] }}</div>
                        <div class="shop-desc">{{ item[3] }}</div>
                    </div>
                    <div>
                        <div class="shop-price">⭐ {{ item[2] }} баллов</div>
                        <button class="btn-action" style="width: 100%;" onclick="alert('Покупка товара доступна после привязки Discord аккаунта!')">Приобрести</button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

    </div>

    <!-- МОДАЛКА: Добавить модератора -->
    <div class="modal" id="addModal">
        <div class="modal-content">
            <div class="modal-header">
                <span>Добавить модератора</span>
                <button class="close-btn" onclick="toggleModal('addModal', false)">&times;</button>
            </div>
            <form action="/add" method="POST">
                <div class="form-group">
                    <label class="form-label">Никнейм в Discord</label>
                    <input type="text" name="username" class="form-input" required placeholder="Например: Ryo Weather">
                </div>
                <div class="form-group">
                    <label class="form-label">Discord ID</label>
                    <input type="text" name="discord_id" class="form-input" required placeholder="146258648225457743">
                </div>
                <div class="form-group">
                    <label class="form-label">Имя</label>
                    <input type="text" name="real_name" class="form-input" required placeholder="Никита">
                </div>
                <div class="form-group">
                    <label class="form-label">Уровень модерации</label>
                    <select name="lvl" class="form-select">
                        <option value="1">1 Уровень</option>
                        <option value="2">2 Уровень</option>
                        <option value="3">3 Уровень</option>
                        <option value="4">4 Уровень</option>
                        <option value="5">5 Уровень (Главный Модератор)</option>
                        <option value="6">6 Уровень (Технический Специалист)</option>
                        <option value="7">7 Уровень (Руководство Discord)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Должность / Роль</label>
                    <input type="text" name="position" class="form-input" required placeholder="Куратор Модерации">
                </div>
                <button type="submit" class="form-submit">Сохранить модератора</button>
            </form>
        </div>
    </div>

    <!-- МОДАЛКА: Подать неактив -->
    <div class="modal" id="inactiveModal">
        <div class="modal-content">
            <div class="modal-header">
                <span>Запрос на неактив</span>
                <button class="close-btn" onclick="toggleModal('inactiveModal', false)">&times;</button>
            </div>
            <form action="/add_inactive" method="POST">
                <div class="form-group">
                    <label class="form-label">Ваш Никнейм</label>
                    <input type="text" name="moderator" class="form-input" required placeholder="Ryo Weather">
                </div>
                <div class="form-group">
                    <label class="form-label">Причина</label>
                    <input type="text" name="reason" class="form-input" required placeholder="Семейные обстоятельства / Экзамены">
                </div>
                <div class="form-group">
                    <label class="form-label">Сроки (например, с 06.09 по 10.09)</label>
                    <input type="text" name="dates" class="form-input" required placeholder="06.09 - 10.09 (4 дня)">
                </div>
                <button type="submit" class="form-submit">Отправить заявку</button>
            </form>
        </div>
    </div>

    <script>
        function switchTab(tabId, element) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            element.classList.add('active');
        }

        function toggleModal(modalId, open) {
            const modal = document.getElementById(modalId);
            if(open) modal.classList.add('active');
            else modal.classList.remove('active');
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM moderators")
    mods = cursor.fetchall()
    
    cursor.execute("SELECT * FROM inactives")
    inactives = cursor.fetchall()
    
    cursor.execute("SELECT * FROM shop")
    shop_items = cursor.fetchall()
    
    conn.close()
    return render_template_string(MAIN_TEMPLATE, mods=mods, inactives=inactives, shop_items=shop_items)

@app.route("/add", methods=["POST"])
def add_moderator():
    username = request.form.get("username")
    discord_id = request.form.get("discord_id")
    real_name = request.form.get("real_name")
    lvl = int(request.form.get("lvl", 1))
    position = request.form.get("position")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO moderators (discord_id, username, real_name, lvl, days_lvl, days_all, warnings, prevs, inactives, points, position)
        VALUES (?, ?, ?, ?, 0, 0, 0, 0, '0', 0, ?)
    """, (discord_id, username, real_name, lvl, position))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route("/add_inactive", methods=["POST"])
def add_inactive():
    moderator = request.form.get("moderator")
    reason = request.form.get("reason")
    dates = request.form.get("dates")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inactives (moderator, reason, dates, status)
        VALUES (?, ?, ?, ?)
    """, (moderator, reason, dates, "На рассмотрении"))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
