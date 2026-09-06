import os
import sqlite3
from flask import Flask, render_template_string

# --- БАЗА ДАННЫХ ДЛЯ ПАНЕЛИ ---
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
    # Добавим тестовых модераторов, если таблица пустая
    cursor.execute("SELECT COUNT(*) FROM moderators")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO moderators (discord_id, username, real_name, lvl, days_lvl, days_all, warnings, prevs, inactives, points, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("146258648225457743", "Ryo Weather", "Никита", 7, 240, 240, 0, 0, "0", 772, "Руководство Discord"))
        cursor.execute("""
            INSERT INTO moderators (discord_id, username, real_name, lvl, days_lvl, days_all, warnings, prevs, inactives, points, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("215070867408080186", "Shepy Explosion", "Андрей", 7, 45, 109, 0, 0, "7 дн.", 422, "Руководство Discord"))
    conn.commit()
    conn.close()

init_db()

# --- ВЕБ-СЕРВЕР И ПАНЕЛЬ ---
app = Flask("")

MODERATION_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Панель модератора - Arizona RP</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #0d0e12; color: #fff; display: flex; height: 100vh; overflow: hidden; }
        
        .sidebar { width: 240px; background-color: #13151b; border-right: 1px solid #1f232d; display: flex; flex-direction: column; padding: 20px; }
        .logo { font-size: 20px; font-weight: bold; color: #fff; margin-bottom: 30px; display: flex; align-items: center; gap: 10px; }
        .logo span { color: #8a5cf5; }
        .menu-title { font-size: 11px; text-transform: uppercase; color: #6b7280; margin-bottom: 10px; letter-spacing: 1px; }
        .nav-item { padding: 12px 15px; border-radius: 8px; color: #9ca3af; text-decoration: none; margin-bottom: 5px; display: flex; align-items: center; gap: 12px; font-size: 14px; transition: 0.2s; }
        .nav-item:hover, .nav-item.active { background-color: #1f232d; color: #fff; }
        
        .main-content { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 30px; }
        .header-panel { background-color: #161922; border: 1px solid #1f232d; border-radius: 12px; padding: 20px 25px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
        .header-title { font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
        
        .table-container { background-color: #161922; border: 1px solid #1f232d; border-radius: 12px; padding: 20px; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
        th { color: #6b7280; font-weight: 500; padding: 12px 10px; border-bottom: 1px solid #1f232d; font-size: 12px; text-transform: uppercase; }
        td { padding: 14px 10px; border-bottom: 1px solid #1a1d26; color: #d1d5db; }
        tr:hover td { background-color: #1a1d26; }
        .user-cell { display: flex; align-items: center; gap: 10px; font-weight: 500; color: #fff; }
        .user-avatar { width: 32px; height: 32px; border-radius: 50%; background-color: #374151; }
        .lvl-badge { background: #1f232d; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; color: #8a5cf5; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ <span>Envision</span></div>
        <div class="menu-title">Панель модератора</div>
        <a href="/" class="nav-item">📊 Обзор</a>
        <a href="/moderation" class="nav-item active">🛡️ Модерация</a>
        <a href="#" class="nav-item">📈 Статистика</a>
        <a href="#" class="nav-item">⏳ Неактивы</a>
        <a href="#" class="nav-item">🛒 Магазин</a>
    </div>

    <div class="main-content">
        <div class="header-panel">
            <div class="header-title">Модерация сервера Arizona Role Play 🍁 Event Community</div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>LVL</th>
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
                        <td><span class="lvl-badge">{{ m[4] }}</span></td>
                        <td>
                            <div class="user-cell">
                                <div class="user-avatar"></div>
                                <div>
                                    <div>{{ m[2] }}</div>
                                    <div style="font-size: 11px; color: #6b7280;">Discord: {{ m[1] }}</div>
                                </div>
                            </div>
                        </td>
                        <td>{{ m[3] }}</td>
                        <td>{{ m[5] }}</td>
                        <td>{{ m[6] }}</td>
                        <td>{{ m[7] }}</td>
                        <td>{{ m[8] }}</td>
                        <td>{{ m[9] }}</td>
                        <td style="color: #10b981; font-weight: bold;">{{ m[10] }}</td>
                        <td>{{ m[11] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

</body>
</html>
"""

@app.route("/")
def home():
    return "⚡ Панель модератора запущена! Перейдите на <a href='/moderation'>/moderation</a>"

@app.route("/moderation")
def moderation_panel():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM moderators")
    mods = cursor.fetchall()
    conn.close()
    return render_template_string(MODERATION_TEMPLATE, mods=mods)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
