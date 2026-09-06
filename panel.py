from datetime import datetime
import os
import sqlite3
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for
import requests

# --- НАСТРОЙКИ DISCORD OAUTH2 ---
CLIENT_ID = "1545765992582479872"
CLIENT_SECRET = "ТВОЙ_CLIENT_SECRET"  # Вставь свой Client Secret со скриншота
REDIRECT_URI = "http://localhost:5000/auth/callback"
DISCORD_API_ENDPOINT = "https://discord.com/api/v10"

# --- БАЗА ДАННЫХ ---
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
            position TEXT,
            bans INTEGER DEFAULT 0,
            mutes INTEGER DEFAULT 0,
            kicks INTEGER DEFAULT 0,
            warns_count INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moderator_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moderator_id INTEGER,
            type TEXT,
            description TEXT,
            date TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inactives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moderator TEXT,
            reason TEXT,
            dates TEXT,
            status TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            description TEXT,
            category TEXT,
            icon TEXT
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM shop")
    if cursor.fetchone()[0] == 0:
        default_shop = [
            ("Снять выговор", 150, "Полное аннулирование активного выговора в личном деле", "Наказания", "🛡️"),
            ("Иммунитет от пред. на 3 дня", 100, "Надежная защита от получения предупреждений на 72 часа", "Защита", "⚡"),
            ("Пакет баллов (+50)", 200, "Мгновенное пополнение вашего баланса на 50 премиум-баллов", "Баллы", "💎"),
            ("Уникальная роль в Discord", 350, "Кастомная цветная роль с вашим собственным дизайном на 30 дней", "Привилегии", "👑"),
            ("Индивидуальный цвет никнейма", 250, "Выделяйтесь в голосовых и текстовых каналах уникальным оттенком", "Кастомизация", "🎨"),
            ("Откат предупреждения", 120, "Снятие одного предупреждения с сохранением чистой статистики", "Наказания", "🔄"),
            ("Пакет баллов (+150)", 500, "Крупный бонус баллов для быстрого продвижения в магазине", "Баллы", "💰"),
            ("Личный архивный статус", 400, "Особый статус в профиле сотрудника с памятной гравировкой", "Привилегии", "📜")
        ]
        cursor.executemany("INSERT INTO shop (item_name, price, description, category, icon) VALUES (?, ?, ?, ?, ?)", default_shop)

    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)
app.secret_key = "arizona_staff_hub_secret_key_change_me"

# --- ШАБЛОН СТРАНИЦЫ ВХОДА ---
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Arizona Staff Hub — Вход</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #07090e;
            --bg-surface: #0f131d;
            --border-color: #21293a;
            --accent-primary: #f59e0b;
            --accent-gradient: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
            --accent-glow: rgba(245, 158, 11, 0.25);
            --text-main: #f8fafc;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background-color: var(--bg-base); color: var(--text-main); display: flex; height: 100vh; justify-content: center; align-items: center; overflow: hidden; }
        .login-card { background-color: var(--bg-surface); border: 1px solid var(--border-color); padding: 45px; border-radius: 24px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.6); width: 400px; backdrop-filter: blur(16px); }
        .brand-icon { width: 50px; height: 50px; background: linear-gradient(135deg, #f59e0b, #b45309); border-radius: 14px; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; box-shadow: 0 0 25px var(--accent-glow); }
        h1 { font-size: 20px; font-weight: 800; color: #fff; margin-bottom: 8px; text-transform: uppercase; letter-spacing: -0.5px; }
        h1 span { color: var(--accent-primary); }
        p { font-size: 13px; color: var(--text-muted); margin-bottom: 30px; line-height: 1.5; }
        .btn-discord { background: #5865F2; color: #fff; font-weight: 700; padding: 14px 24px; border-radius: 14px; border: none; cursor: pointer; font-size: 14px; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 10px; box-shadow: 0 6px 20px rgba(88, 101, 242, 0.4); transition: 0.3s; }
        .btn-discord:hover { background: #4752C4; transform: translateY(-3px); box-shadow: 0 10px 25px rgba(88, 101, 242, 0.6); }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7z"/></svg>
        </div>
        <h1>Arizona <span>Staff Hub</span></h1>
        <p>Авторизуйтесь через свой аккаунт Discord для доступа к панели управления модерацией.</p>
        <a href="/login" class="btn-discord">Войти через Discord</a>
    </div>
</body>
</html>
"""

MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Arizona Staff Hub — Панель управления</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #07090e;
            --bg-surface: #0f131d;
            --bg-card: #151a26;
            --border-color: #21293a;
            --accent-primary: #f59e0b;
            --accent-gradient: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
            --accent-glow: rgba(245, 158, 11, 0.25);
            --text-main: #f8fafc;
            --text-muted: #64748b;
            --success: #10b981;
            --danger: #ef4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background-color: var(--bg-base); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; position: relative; }

        #particleCanvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none; }

        /* Сайдбар */
        .sidebar { width: 280px; background-color: var(--bg-surface); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 32px 24px; z-index: 10; backdrop-filter: blur(16px); box-shadow: 10px 0 30px rgba(0,0,0,0.5); }
        .brand { font-size: 15px; font-weight: 800; color: #fff; margin-bottom: 40px; display: flex; align-items: center; gap: 12px; letter-spacing: -0.3px; text-transform: uppercase; }
        .brand-icon { width: 32px; height: 32px; background: linear-gradient(135deg, #f59e0b, #b45309); border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px var(--accent-glow); }
        .brand span { color: var(--accent-primary); }
        
        .menu-label { font-size: 10px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 16px; letter-spacing: 1.5px; font-weight: 700; }
        
        .nav-links-container { display: flex; flex-direction: column; gap: 10px; flex: 1; }
        .nav-link { padding: 15px 20px; border-radius: 14px; color: var(--text-muted); text-decoration: none; display: flex; align-items: center; gap: 16px; font-size: 14px; font-weight: 600; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; border: 1px solid transparent; }
        .nav-link svg { width: 18px; height: 18px; fill: var(--text-muted); transition: 0.3s; }
        .nav-link:hover, .nav-link.active { background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(245, 158, 11, 0.01)); color: #fff; border-color: rgba(245, 158, 11, 0.25); transform: translateX(6px); box-shadow: 0 6px 20px rgba(245, 158, 11, 0.08); }
        .nav-link:hover svg, .nav-link.active svg { fill: var(--accent-primary); filter: drop-shadow(0 0 8px var(--accent-glow)); }

        .user-panel-bottom { border-top: 1px solid var(--border-color); padding-top: 20px; display: flex; align-items: center; justify-content: space-between; }
        .user-info-mini { display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 600; }
        .user-avatar-mini { width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--accent-primary); }
        .logout-btn { color: var(--danger); text-decoration: none; font-size: 12px; font-weight: 700; padding: 6px 10px; background: rgba(239, 68, 68, 0.1); border-radius: 8px; transition: 0.2s; }
        .logout-btn:hover { background: rgba(239, 68, 68, 0.2); }

        /* Контент */
        .main-container { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 40px; z-index: 10; position: relative; }
        
        .top-bar { display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 20px; padding: 22px 32px; margin-bottom: 30px; box-shadow: 0 15px 35px rgba(0,0,0,0.4); backdrop-filter: blur(10px); }
        .top-title { font-size: 20px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 12px; letter-spacing: -0.5px; }
        
        .btn-action { background: var(--accent-gradient); color: #000; font-weight: 700; padding: 13px 26px; border-radius: 14px; border: none; cursor: pointer; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 6px 20px rgba(245, 158, 11, 0.3); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); position: relative; overflow: hidden; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; }
        .btn-action:hover { transform: translateY(-4px) scale(1.03); box-shadow: 0 10px 30px rgba(245, 158, 11, 0.5); filter: brightness(1.1); }
        .btn-action:active { transform: translateY(-1px) scale(0.97); }

        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

        .content-card { background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 20px; padding: 30px; box-shadow: 0 15px 35px rgba(0,0,0,0.3); }
        
        .level-filters { display: flex; gap: 10px; margin-bottom: 25px; overflow-x: auto; padding-bottom: 5px; }
        .level-btn { background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-muted); padding: 10px 18px; border-radius: 12px; font-weight: 700; font-size: 13px; cursor: pointer; transition: 0.3s; white-space: nowrap; }
        .level-btn:hover { border-color: rgba(245, 158, 11, 0.4); color: #fff; }
        .level-btn.active { background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.05)); border-color: var(--accent-primary); color: var(--accent-primary); box-shadow: 0 0 15px var(--accent-glow); }

        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
        th { color: var(--text-muted); font-weight: 700; padding: 14px 16px; border-bottom: 1px solid var(--border-color); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        td { padding: 18px 16px; border-bottom: 1px solid rgba(33, 41, 58, 0.5); color: #cbd5e1; }
        tr:hover td { background-color: rgba(255, 255, 255, 0.015); }
        tr { cursor: pointer; }
        
        .user-block { display: flex; align-items: center; gap: 14px; font-weight: 600; color: #fff; }
        .avatar-stub { width: 38px; height: 38px; border-radius: 12px; background: linear-gradient(135deg, #1a2333, #0f131d); display: flex; align-items: center; justify-content: center; font-size: 16px; border: 1px solid var(--border-color); }
        .lvl-pill { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: var(--accent-primary); padding: 6px 12px; border-radius: 10px; font-size: 12px; font-weight: 800; }

        .shop-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .shop-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }
        .shop-item { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 20px; padding: 30px; display: flex; flex-direction: column; justify-content: space-between; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; }
        .shop-item::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: var(--accent-gradient); opacity: 0; transition: 0.3s; }
        .shop-item:hover { border-color: rgba(245, 158, 11, 0.4); transform: translateY(-6px); box-shadow: 0 20px 40px rgba(0,0,0,0.6); }
        .shop-item:hover::before { opacity: 1; }
        .shop-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }
        .shop-icon-box { width: 50px; height: 50px; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
        .shop-badge { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 5px 10px; border-radius: 8px; background: rgba(255,255,255,0.05); color: var(--text-muted); border: 1px solid var(--border-color); }
        .shop-name { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 8px; }
        .shop-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 25px; line-height: 1.5; }
        .shop-footer { display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--border-color); padding-top: 18px; }
        .shop-price { font-size: 18px; font-weight: 800; color: var(--accent-primary); display: flex; align-items: center; gap: 6px; }

        .overview-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .overview-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 18px; padding: 24px; position: relative; overflow: hidden; }
        .overview-title { font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700; margin-bottom: 10px; letter-spacing: 1px; }
        .overview-value { font-size: 32px; font-weight: 800; color: #fff; letter-spacing: -1px; display: flex; align-items: baseline; gap: 8px; }
        .overview-sub { font-size: 12px; color: var(--success); margin-top: 6px; font-weight: 600; }

        .custom-select-wrapper { position: relative; user-select: none; width: 100%; }
        .custom-select { position: relative; display: flex; align-items: center; justify-content: space-between; background: var(--bg-base); border: 1px solid var(--border-color); padding: 13px 16px; border-radius: 12px; cursor: pointer; font-size: 14px; color: #fff; transition: 0.3s; }
        .custom-select:hover { border-color: rgba(245, 158, 11, 0.5); }
        .custom-select.open { border-color: var(--accent-primary); box-shadow: 0 0 0 3px var(--accent-glow); }
        .custom-select span.arrow { font-size: 10px; color: var(--text-muted); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .custom-select.open span.arrow { transform: rotate(180deg); color: var(--accent-primary); }
        
        .custom-options { position: absolute; top: calc(100% + 8px); left: 0; right: 0; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 14px; display: none; z-index: 50; box-shadow: 0 20px 40px rgba(0,0,0,0.7); overflow: hidden; opacity: 0; transform: translateY(-8px); transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
        .custom-options.open { display: block; opacity: 1; transform: translateY(0); }
        
        .custom-option { padding: 12px 16px; font-size: 14px; color: #cbd5e1; cursor: pointer; transition: all 0.2s ease; border-bottom: 1px solid rgba(33, 41, 58, 0.4); }
        .custom-option:last-child { border-bottom: none; }
        .custom-option:hover { background: rgba(245, 158, 11, 0.12); color: #fff; padding-left: 20px; }

        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); backdrop-filter: blur(10px); justify-content: center; align-items: center; z-index: 1000; opacity: 0; transition: opacity 0.3s ease; }
        .modal.active { display: flex; opacity: 1; }
        .modal-content { background: var(--bg-surface); border: 1px solid var(--border-color); width: 500px; max-height: 90vh; overflow-y: auto; padding: 35px; border-radius: 22px; box-shadow: 0 30px 60px rgba(0,0,0,0.8); transform: scale(0.92); transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
        .modal.active .modal-content { transform: scale(1); }
        
        .modal-header { font-size: 19px; font-weight: 700; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; color: #fff; letter-spacing: -0.5px; }
        .close-btn { background: none; border: none; color: var(--text-muted); font-size: 24px; cursor: pointer; transition: 0.2s; }
        .close-btn:hover { color: #fff; transform: scale(1.1); }
        
        .form-group { margin-bottom: 18px; }
        .form-label { display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; letter-spacing: 0.8px; }
        .form-input { width: 100%; background: var(--bg-base); border: 1px solid var(--border-color); padding: 13px 16px; border-radius: 12px; color: #fff; font-size: 14px; outline: none; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .form-input:focus { border-color: var(--accent-primary); box-shadow: 0 0 0 3px var(--accent-glow); background: rgba(11, 14, 20, 0.8); }
        .form-submit { width: 100%; margin-top: 12px; padding: 15px; background: var(--accent-gradient); color: #000; font-weight: 700; border: none; border-radius: 14px; cursor: pointer; text-transform: uppercase; font-size: 13px; transition: 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); box-shadow: 0 6px 20px rgba(245,158,11,0.3); }
        .form-submit:hover { transform: translateY(-3px); box-shadow: 0 10px 25px rgba(245,158,11,0.5); filter: brightness(1.05); }
    </style>
</head>
<body>

    <canvas id="particleCanvas"></canvas>

    <div class="sidebar">
        <div class="brand">
            <div class="brand-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7z"/></svg>
            </div>
            Arizona <span>Staff Hub</span>
        </div>
        <div class="menu-label">Навигация</div>
        <div class="nav-links-container">
            <a class="nav-link active" onclick="switchTab('moderation', this)">
                <svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>
                Модерация
            </a>
            <a class="nav-link" onclick="switchTab('overview', this)">
                <svg viewBox="0 0 24 24"><path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6h-6z"/></svg>
                Обзор
            </a>
            <a class="nav-link" onclick="switchTab('stats', this)">
                <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/></svg>
                Статистика
            </a>
            <a class="nav-link" onclick="switchTab('inactives', this)">
                <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
                Неактивы
            </a>
            <a class="nav-link" onclick="switchTab('shop', this)">
                <svg viewBox="0 0 24 24"><path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/></svg>
                Магазин Prime
            </a>
        </div>
        
        <div class="user-panel-bottom">
            <div class="user-info-mini">
                <img src="https://cdn.discordapp.com/avatars/{{ user.id }}/{{ user.avatar }}.png" class="user-avatar-mini" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <span>{{ user.global_name or user.username }}</span>
            </div>
            <a href="/logout" class="logout-btn">Выйти</a>
        </div>
    </div>

    <div class="main-container">
        
        <!-- ВКЛАДКА 1: МОДЕРАЦИЯ -->
        <div id="moderation" class="tab-content active">
            <div class="top-bar">
                <div class="top-title">⚔️ Состав модерации сервера</div>
                <button class="btn-action" onclick="toggleModal('addModal', true)">+ Добавить модератора</button>
            </div>
            
            <div class="level-filters">
                <button class="level-btn active" onclick="filterLevel('all', this)">Все уровни</button>
                <button class="level-btn" onclick="filterLevel('1', this)">1 Уровень</button>
                <button class="level-btn" onclick="filterLevel('2', this)">2 Уровень</button>
                <button class="level-btn" onclick="filterLevel('3', this)">3 Уровень</button>
                <button class="level-btn" onclick="filterLevel('4', this)">4 Уровень</button>
                <button class="level-btn" onclick="filterLevel('5', this)">5 Уровень</button>
                <button class="level-btn" onclick="filterLevel('6', this)">6 Уровень</button>
                <button class="level-btn" onclick="filterLevel('7', this)">7 Уровень</button>
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
                    <tbody id="moderatorsTableBody">
                        {% if mods %}
                            {% for m in mods %}
                            <tr data-lvl="{{ m[4] }}" onclick="openProfile({{ m[0] }})">
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
                                <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 50px;">Список модераторов пуст.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ВКЛАДКА 2: ОБЗОР (КПД) -->
        <div id="overview" class="tab-content">
            <div class="top-bar">
                <div class="top-title">📊 Обзор производительности и КПД</div>
            </div>
            <div class="overview-grid">
                <div class="overview-card">
                    <div class="overview-title">Эффективность состава</div>
                    <div class="overview-value">94.2% <span style="font-size: 14px; color: var(--success);">+3.5%</span></div>
                    <div class="overview-sub">Высокий показатель активности</div>
                </div>
                <div class="overview-card">
                    <div class="overview-title">Обработка тикетов</div>
                    <div class="overview-value">1,420</div>
                    <div class="overview-sub" style="color: var(--accent-primary);">В среднем 4.2 мин на ответ</div>
                </div>
                <div class="overview-card">
                    <div class="overview-title">Выданные наказания</div>
                    <div class="overview-value">384</div>
                    <div class="overview-sub">За последние 7 дней</div>
                </div>
                <div class="overview-card">
                    <div class="overview-title">Онлайн состав в пике</div>
                    <div class="overview-value">18.6 <span style="font-size: 14px; color: var(--text-muted);">чел</span></div>
                    <div class="overview-sub" style="color: var(--success);">Стабильный прирост</div>
                </div>
            </div>
            <div class="content-card">
                <p style="color: var(--text-muted); text-align: center; padding: 25px;">Детальная аналитика КПД и работы каждого сотрудника собирается в режиме реального времени на основе серверных логов.</p>
            </div>
        </div>

        <!-- ВКЛАДКА 3: СТАТИСТИКА -->
        <div id="stats" class="tab-content">
            <div class="top-bar">
                <div class="top-title">📈 Статистика сервера</div>
            </div>
            <div class="content-card">
                <p style="color: var(--text-muted); text-align: center; padding: 25px;">Общая сводка и отчеты активности администрации.</p>
            </div>
        </div>

        <!-- ВКЛАДКА 4: НЕАКТИВЫ -->
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
                                <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 50px;">Активных запросов нет.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ВКЛАДКА 5: МАГАЗИН PRIME -->
        <div id="shop" class="tab-content">
            <div class="shop-header-row">
                <div class="top-title" style="margin: 0; background: none; border: none; padding: 0; box-shadow: none;">🛒 Магазин привилегий Prime</div>
                <div style="font-size: 13px; color: var(--text-muted);">Используйте заработанные баллы для приобретения уникальных наград</div>
            </div>
            <div class="shop-grid">
                {% for item in shop_items %}
                <div class="shop-item">
                    <div>
                        <div class="shop-top">
                            <div class="shop-icon-box">{{ item[5] if item[5] else '🎁' }}</div>
                            <div class="shop-badge">{{ item[4] if item[4] else 'Товар' }}</div>
                        </div>
                        <div class="shop-name">{{ item[1] }}</div>
                        <div class="shop-desc">{{ item[3] }}</div>
                    </div>
                    <div class="shop-footer">
                        <div class="shop-price">⭐ {{ item[2] }}</div>
                        <button class="btn-action" onclick="alert('Покупка успешна!')">Приобрести</button>
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
                    <input type="text" name="username" class="form-input" required placeholder="Введите никнейм...">
                </div>
                <div class="form-group">
                    <label class="form-label">Discord ID</label>
                    <input type="text" name="discord_id" class="form-input" required placeholder="Введите ID пользователя...">
                </div>
                <div class="form-group">
                    <label class="form-label">Имя</label>
                    <input type="text" name="real_name" class="form-input" required placeholder="Введите имя...">
                </div>
                <div class="form-group">
                    <label class="form-label">Уровень модерации</label>
                    <div class="custom-select-wrapper" id="customSelect">
                        <div class="custom-select" onclick="toggleCustomSelect(this)">
                            <span>1 Уровень — Модератор</span>
                            <span class="arrow">▼</span>
                        </div>
                        <div class="custom-options">
                            <div class="custom-option" onclick="selectOption(this, '1')">1 Уровень — Модератор</div>
                            <div class="custom-option" onclick="selectOption(this, '2')">2 Уровень — Старший Модератор</div>
                            <div class="custom-option" onclick="selectOption(this, '3')">3 Уровень — Куратор</div>
                            <div class="custom-option" onclick="selectOption(this, '4')">4 Уровень — Заместитель Главного Модератора</div>
                            <div class="custom-option" onclick="selectOption(this, '5')">5 Уровень — Главный Модератор</div>
                            <div class="custom-option" onclick="selectOption(this, '6')">6 Уровень — Технический специалист</div>
                            <div class="custom-option" onclick="selectOption(this, '7')">7 Уровень — Руководство Discord</div>
                        </div>
                        <input type="hidden" name="lvl" id="lvlInput" value="1">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Должность / Роль</label>
                    <input type="text" name="position" class="form-input" required placeholder="Укажите должность...">
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
                    <label class="form-label">Никнейм модератора</label>
                    <input type="text" name="moderator" class="form-input" required placeholder="Ваш ник...">
                </div>
                <div class="form-group">
                    <label class="form-label">Причина</label>
                    <input type="text" name="reason" class="form-input" required placeholder="Причина неактива...">
                </div>
                <div class="form-group">
                    <label class="form-label">Сроки</label>
                    <input type="text" name="dates" class="form-input" required placeholder="Например: 07.09 - 10.09">
                </div>
                <button type="submit" class="form-submit">Отправить заявку</button>
            </form>
        </div>
    </div>

    <script>
        function switchTab(tabId, element) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            element.classList.add('active');
        }

        function toggleModal(modalId, show) {
            const modal = document.getElementById(modalId);
            if (show) {
                modal.classList.add('active');
            } else {
                modal.classList.remove('active');
            }
        }

        function toggleCustomSelect(element) {
            element.classList.toggle('open');
            element.nextElementSibling.classList.toggle('open');
        }

        function selectOption(optionElement, value) {
            const wrapper = optionElement.closest('.custom-select-wrapper');
            const selectBox = wrapper.querySelector('.custom-select span');
            selectBox.textContent = optionElement.textContent;
            wrapper.querySelector('input[type="hidden"]').value = value;
            wrapper.querySelector('.custom-select').classList.remove('open');
            wrapper.querySelector('.custom-options').classList.remove('open');
        }

        function filterLevel(lvl, btn) {
            document.querySelectorAll('.level-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const rows = document.querySelectorAll('#moderatorsTableBody tr[data-lvl]');
            rows.forEach(row => {
                if (lvl === 'all' || row.getAttribute('data-lvl') === lvl) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

# --- МАРШРУТЫ ПРИЛОЖЕНИЯ ---

@app.route("/")
def index():
    if "user" not in session:
        return render_template_string(LOGIN_TEMPLATE)
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM moderators")
    mods = cursor.fetchall()
    
    cursor.execute("SELECT * FROM inactives")
    inactives = cursor.fetchall()
    
    cursor.execute("SELECT * FROM shop")
    shop_items = cursor.fetchall()
    
    conn.close()
    
    return render_template_string(MAIN_TEMPLATE, mods=mods, inactives=inactives, shop_items=shop_items, user=session["user"])

@app.route("/login")
def login():
    discord_login_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={requests.utils.quote(REDIRECT_URI)}&response_type=code&scope=identify"
    return redirect(discord_login_url)

@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return "Ошибка авторизации: код не получен", 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_response = requests.post(f"{DISCORD_API_ENDPOINT}/oauth2/token", data=data, headers=headers)
    token_json = token_response.json()

    access_token = token_json.get("access_token")
    if not access_token:
        return "Не удалось получить токен доступа от Discord", 400

    user_headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(f"{DISCORD_API_ENDPOINT}/users/@me", headers=user_headers)
    user_data = user_response.json()

    session["user"] = {
        "id": user_data.get("id"),
        "username": user_data.get("username"),
        "global_name": user_data.get("global_name"),
        "avatar": user_data.get("avatar")
    }

    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

@app.route("/add", methods=["POST"])
def add_moderator():
    if "user" not in session:
        return redirect(url_for("index"))
        
    username = request.form.get("username")
    discord_id = request.form.get("discord_id")
    real_name = request.form.get("real_name")
    lvl = int(request.form.get("lvl", 1))
    position = request.form.get("position")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO moderators (discord_id, username, real_name, lvl, days_lvl, days_all, warnings, prevs, inactives, points, position)
        VALUES (?, ?, ?, ?, 0, 0, 0, 0, 'Нет', 0.0, ?)
    """, (discord_id, username, real_name, lvl, position))
    conn.commit()
    conn.close()
    
    return redirect(url_for("index"))

@app.route("/add_inactive", methods=["POST"])
def add_inactive():
    if "user" not in session:
        return redirect(url_for("index"))
        
    moderator = request.form.get("moderator")
    reason = request.form.get("reason")
    dates = request.form.get("dates")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inactives (moderator, reason, dates, status)
        VALUES (?, ?, ?, 'Ожидает')
    """, (moderator, reason, dates))
    conn.commit()
    conn.close()
    
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
