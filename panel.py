import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for

# --- БАЗА ДАННЫХ И СБРОС БАЛЛОВ ---
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
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
    # Обнуляем баллы у всех при перезапуске/обновлении по требованию
    cursor.execute("UPDATE moderators SET points = 0")
    
    cursor.execute("SELECT COUNT(*) FROM moderators")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO moderators (discord_id, username, real_name, lvl, days_lvl, days_all, warnings, prevs, inactives, points, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("146258648225457743", "Ryo Weather", "Никита", 7, 240, 240, 0, 0, "0", 0, "Руководство Discord"))
        cursor.execute("""
            INSERT INTO moderators (discord_id, username, real_name, lvl, days_lvl, days_all, warnings, prevs, inactives, points, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("215070867408080186", "Shepy Explosion", "Андрей", 7, 45, 109, 0, 0, "7 дн.", 0, "Руководство Discord"))
    conn.commit()
    conn.close()

init_db()

app = Flask("")

PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Arizona Hub & Prime — Панель управления</title>
    <style>
        :root {
            --bg-base: #08090c;
            --bg-surface: #101218;
            --bg-card: #151821;
            --border-color: #222634;
            --accent-primary: #f59e0b;
            --accent-glow: rgba(245, 158, 11, 0.15);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --success: #10b981;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Segoe UI', sans-serif; }
        body { background-color: var(--bg-base); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }

        /* Уникальный сайдбар */
        .sidebar { width: 260px; background-color: var(--bg-surface); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 24px; }
        .brand { font-size: 16px; font-weight: 800; color: #fff; margin-bottom: 40px; display: flex; align-items: center; gap: 10px; letter-spacing: 0.5px; text-transform: uppercase; }
        .brand span { color: var(--accent-primary); text-shadow: 0 0 15px var(--accent-glow); }
        
        .menu-label { font-size: 10px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; letter-spacing: 1.5px; font-weight: 600; }
        .nav-link { padding: 12px 16px; border-radius: 10px; color: var(--text-muted); text-decoration: none; margin-bottom: 6px; display: flex; align-items: center; gap: 14px; font-size: 14px; font-weight: 500; transition: all 0.25s ease; }
        .nav-link:hover, .nav-link.active { background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.02)); color: #fff; border-left: 3px solid var(--accent-primary); }

        /* Контентная часть */
        .main-container { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 35px; background: radial-gradient(circle at top right, #121520 0%, var(--bg-base) 60%); }
        
        .top-bar { display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 16px; padding: 20px 30px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .top-title { font-size: 20px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 12px; }
        
        .btn-action { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; font-weight: 700; padding: 12px 22px; border-radius: 10px; border: none; cursor: pointer; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3); transition: 0.2s; }
        .btn-action:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4); }

        /* Таблица */
        .content-card { background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 16px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13.5px; }
        th { color: var(--text-muted); font-weight: 600; padding: 14px 12px; border-bottom: 1px solid var(--border-color); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        td { padding: 16px 12px; border-bottom: 1px solid rgba(34, 38, 52, 0.5); color: #d1d5db; }
        tr:hover td { background-color: rgba(255, 255, 255, 0.01); }
        
        .user-block { display: flex; align-items: center; gap: 12px; font-weight: 600; color: #fff; }
        .avatar-stub { width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, #222634, #151821); display: flex; align-items: center; justify-content: center; font-size: 15px; border: 1px solid var(--border-color); }
        .lvl-pill { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: var(--accent-primary); padding: 5px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }

        /* Модальное окно */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); justify-content: center; align-items: center; z-index: 1000; }
        .modal.active { display: flex; }
        .modal-content { background: var(--bg-surface); border: 1px solid var(--border-color); width: 450px; padding: 30px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
        .modal-header { font-size: 18px; font-weight: 700; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .close-btn { background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; }
        
        .form-group { margin-bottom: 15px; }
        .form-label { display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; letter-spacing: 0.5px; }
        .form-input, .form-select { width: 100%; background: var(--bg-base); border: 1px solid var(--border-color); padding: 12px 15px; border-radius: 10px; color: #fff; font-size: 14px; outline: none; transition: 0.2s; }
        .form-input:focus, .form-select:focus { border-color: var(--accent-primary); box-shadow: 0 0 10px var(--accent-glow); }
        .form-submit { width: 100%; margin-top: 10px; padding: 14px; background: var(--accent-primary); color: #000; font-weight: 700; border: none; border-radius: 10px; cursor: pointer; text-transform: uppercase; font-size: 13px; transition: 0.2s; }
        .form-submit:hover { opacity: 0.9; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="brand">⚡ <span>Arizona Hub & Prime</span></div>
        <div class="menu-label">Управление</div>
        <a href="/" class="nav-link active">🛡️ Модерация</a>
        <a href="#" class="nav-link">📊 Статистика</a>
        <a href="#" class="nav-link">⏳ Неактивы</a>
        <a href="#" class="nav-link">🛒 Магазин Prime</a>
    </div>

    <div class="main-container">
        <div class="top-bar">
            <div class="top-title">⚔️ Состав модерации сервера</div>
            <button class="btn-action" onclick="toggleModal(true)">+ Добавить модератора</button>
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
                        <td style="color: {% if m[7] > 0 %}#ef4444{% else %}inherit{% endif %};">{{ m[7] }}</td>
                        <td>{{ m[8] }}</td>
                        <td>{{ m[9] }}</td>
                        <td style="color: var(--success); font-weight: bold;">{{ m[10] }}</td>
                        <td>{{ m[11] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Модальное окно добавления модератора -->
    <div class="modal" id="addModal">
        <div class="modal-content">
            <div class="modal-header">
                <span>Добавить модератора</span>
                <button class="close-btn" onclick="toggleModal(false)">&times;</button>
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

    <script>
        function toggleModel(show) {} // заглушка
        function toggleModal(open) {
            const modal = document.getElementById('addModal');
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
    conn.close()
    return render_template_string(PANEL_TEMPLATE, mods=mods)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
