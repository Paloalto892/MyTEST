from flask import Flask, request, redirect, url_for, Response, session, g, render_template_string
import boto3
import pymysql
import os
import requests
import datetime
import time

app = Flask(__name__)
admin_sessions = {}  
user_approvals = {
    'user1': False,
    'user2': False,
    'user3': True,
}

# ---------- 共通 ----------
S3_BUCKET = 's3buck-any'
REGION = 'ap-northeast-1'
LOCAL_DOWNLOAD_DIR = '/home/ec2-user/tmpdownload'  # EC2内 Download経路

s3 = boto3.client('s3', region_name=REGION)

def html_header(title):
    header = f"""
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background-color: #f9f9fb;
                background-image: url('https://images.unsplash.com/photo-1488109811119-98431feb6929?q=80&w=880&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                margin: 30px;
                color: #333;
            }}
            h1 {{ color: #2c3e50; }}
            a {{ text-decoration: none; color: #3498db; }}
            a:hover {{ text-decoration: underline; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ padding: 8px 0; font-size: 18px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }}
            th, td {{ padding: 10px; border-bottom: 1px solid #ddd; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .button {{ display: inline-block; margin-top: 20px; padding: 10px 15px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; }}
            .button:hover {{ background-color: #2980b9; }}
        </style>
    """

    # ✅ 관리자 로그인 시 상태 표시
    if session.get('admin_logged_in') and session.get('login_time'):
        remaining_sec = max(0, 1800 - int(time.time() - session['login_time']))
        minutes = remaining_sec // 60
        seconds = remaining_sec % 60
        header += f"""
        <script>
        let remaining = {remaining_sec};
        setInterval(() => {{
            if (--remaining <= 0) {{
                window.location.href = '/logout';
            }} else {{
                const m = String(Math.floor(remaining / 60)).padStart(2, '0');
                const s = String(remaining % 60).padStart(2, '0');
                const el = document.getElementById('countdown');
                if (el) el.textContent = `自動ログアウトまで残り ${{parseInt(m)}}分${{s}}秒`;
            }}
        }}, 1000);
        </script>
        """

        header += f"""
        </head>
        <body style="padding-top: 60px;">
        <div style="
            position: fixed; top: 0; left: 0; width: 100%;
            box-sizing: border-box;
            height: 50px;
            background-color: #2c3e50; color: white;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 30px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            z-index: 9999;
            ">
                <span>✅ 管理者接続中</span>
                <div style="display: flex; align-items: center; gap: 20px;">
                    <span id="countdown" style="white-space: nowrap;">自動ログアウトまで残り {minutes}分{seconds:02d}秒</span>
                    <a href="/logout" style="
                    color: white; background-color: #e74c3c;
                    padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold;
                    margin-right: 10px;
                    white-space: nowrap;
                    ">ログアウト</a>
                </div>
            </div>
            """
    else:
        header += "</head><body>"
    
    return header

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        # 관리자 로그인 처리
        if user_id == 'admin' and password == 'PASSW0RD':
            session.clear()
            session['admin_logged_in'] = True
            session['login_time'] = int(time.time())
            return redirect('/admin')

        # 일반 사용자 로그인 처리
        if user_id in user_approvals:
            if not user_approvals[user_id]:
                error = '⚠️ このアカウントはまだ承認されていません。管理者の承認をお待ちください。'
            else:
                session.clear()
                session['user_logged_in'] = True
                session['user_id'] = user_id
                session['login_time'] = int(time.time())
                return redirect('/')
        else:
            error = '⚠️ ユーザーIDまたはパスワードが正しくありません。'

    html = html_header("ログイン")
    html += f"""
    <style>
        .login-box {{
            max-width: 400px;
            margin: 100px auto;
            padding: 30px;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }}
        .login-box h2 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 20px;
        }}
        input {{
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border-radius: 6px;
            border: 1px solid #ccc;
        }}
        button {{
            width: 100%;
            padding: 12px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            margin-top: 10px;
        }}
        button:hover {{
            background: #2980b9;
        }}
        .error-msg {{
            color: red;
            text-align: center;
            margin-top: 10px;
        }}
        .extra-links {{
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            font-size: 14px;
        }}
        .extra-links a {{
            color: #3498db;
            text-decoration: none;
        }}
        .extra-links a:hover {{
            text-decoration: underline;
        }}
    </style>

    <div class="login-box">
        <h2>🔐 ユーザーログイン</h2>
        <form method="POST">
            <input type="text" name="user_id" placeholder="ユーザーID" required>
            <input type="password" name="password" placeholder="パスワード" required>
            <button type="submit">ログイン</button>
        </form>

        <div class="extra-links">
            <a href="/signup">アカウント作成</a>
        </div>

        {'<div class="error-msg">' + error + '</div>' if error else ''}
    </div>
    </body></html>
    """
    return html

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ''
    if request.method == 'POST':
        user_id = request.form.get('user_id')

        if not user_id:
            message = '⚠️ ユーザーIDを入力してください。'
        elif user_id in user_approvals:
            message = '⚠️ そのユーザーIDはすでに存在します。'
        elif len(user_approvals) >= 1000:
            message = '⚠️ 作成可能なユーザー数の上限（1000件）に達しました。'
        else:
            user_approvals[user_id] = False  # 승인 대기 상태로 추가
            message = f'✅ アカウント「{user_id}」が作成されました。管理者の承認をお待ちください。'

    html = html_header("アカウント作成")
    html += f"""
    <style>
        .signup-box {{
            max-width: 400px;
            margin: 100px auto;
            padding: 30px;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }}
        h2 {{
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        input {{
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ccc;
            border-radius: 6px;
        }}
        button {{
            width: 100%;
            padding: 12px;
            background: #27ae60;
            color: white;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            font-size: 16px;
        }}
        button:hover {{
            background: #219150;
        }}
        .message {{
            text-align: center;
            color: {'red' if '⚠️' in message else 'green'};
            font-weight: bold;
            margin-top: 15px;
        }}
    </style>

    <div class="signup-box">
        <h2>📝 アカウント作成</h2>
        <form method="POST">
            <input type="text" name="user_id" placeholder="希望するユーザーID" required>
            <button type="submit">作成する</button>
        </form>
        {'<div class="message">' + message + '</div>' if message else ''}
    </div>
    </body></html>
    """
    return html

@app.route('/')
def home():
    if session.get('admin_logged_in'):
        pass
    else:
        user_id = session.get('user_id')
        if not session.get('user_logged_in') or not user_id or not user_approvals.get(user_id):
            return redirect('/login')
    
    #ログインが出来た人のみ
    html = html_header("ホーム")
    html += """
    <style>
        .hero {
            background: linear-gradient(135deg, #74ebd5 0%, #acb6e5 100%);
            padding: 50px 30px;
            border-radius: 12px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            text-align: center;
            color: #fff;
            margin-bottom: 30px;
            animation: fadeIn 1s ease-in-out;
        }
        .hero h1 {
            font-size: 48px;
            margin-bottom: 10px;
            font-weight: bold;
        }
        .hero p {
            font-size: 18px;
            color: #f5f5f5;
        }
        .menu {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 40px;
            flex-wrap: wrap;
        }
        .menu-item {
            background: #fff;
            color: #333;
            padding: 25px;
            border-radius: 12px;
            width: 250px;
            text-align: center;
            text-decoration: none;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .menu-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }
        .menu-item h2 {
            font-size: 20px;
            margin-top: 10px;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>

    <div class="hero">
        <h1>📦 Demo Web Server 管理ポータル</h1>
        <p>ようこそ！ここから S3 と RDS の操作が簡単にできます。</p>
    </div>

    <div class="menu">
        <a class="menu-item" href="/s3">
            <div style="font-size: 40px;">🗂️</div>
            <h2>S3 ファイルリスト</h2>
            <p>ファイルのアップロード、ダウンロードが可能</p>
        </a>
        <a class="menu-item" href="/db">
            <div style="font-size: 40px;">🗃️</div>
            <h2>RDS データベース</h2>
            <p>データベースとテーブルの操作が可能</p>
        </a>
        <a class="menu-item" href="/admin_login">
            <div style="font-size: 40px;">🔧</div>
            <h2>管理者メニュー</h2>
            <p>⚠️ 現在工事中です</p>
        </a>
    </div>

    </body></html>
    """
    return html

# ---------- S3 セクション ----------
@app.route('/s3')
def s3_list():
    objects = s3.list_objects_v2(Bucket=S3_BUCKET)
    html = html_header("S3 ファイルリスト")
    html += f"<h1>🗂️ S3 ファイルリスト(接続中S3は {S3_BUCKET}です)</h1><ul>"
    html += """
<style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f4f6f9;
        color: #333;
        padding: 40px;
    }
    h1 {
        font-size: 32px;
        margin-bottom: 30px;
        color: #2c3e50;
    }
    ul.file-list {
        list-style: none;
        padding: 0;
    }
    ul.file-list li {
        background: white;
        border-radius: 10px;
        margin-bottom: 15px;
        padding: 15px 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .file-name {
        font-weight: bold;
    }
    .file-actions {
        display: flex;
        gap: 5px;
    }
    .file-actions a {
        text-decoration: none;
        padding: 6px 12px;
        background-color: #3498db;
        color: white;
        border-radius: 5px;
        font-size: 14px;
        transition: background-color 0.2s ease;
    }
    .file-actions a:hover {
        background-color: #2980b9;
    }
    form {
        margin-top: 30px;
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    input[type='file'] {
        margin-right: 10px;
    }
    input[type='submit'] {
        background-color: #2ecc71;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 5px;
        cursor: pointer;
    }
    input[type='submit']:hover {
        background-color: #27ae60;
    }
    .button {
        display: inline-block;
        margin-top: 20px;
        padding: 10px 20px;
        background-color: #95a5a6;
        color: white;
        border-radius: 5px;
        text-decoration: none;
    }
    .button:hover {
        background-color: #7f8c8d;
    }
    #progressContainer {
        display: none;
        margin-top: 15px;
    }
    #uploadProgress {
        width: 100%;
        height: 20px;
    }
    #progressText {
        text-align: center;
        margin-top: 5px;
    }
</style>
<ul class="file-list">
"""
    for obj in objects.get('Contents', []):
        key = obj['Key']
        html += f"""
        <li>
            <span class="file-name">{key}</span>
            <div class="file-actions">
                <a href='/s3/download/{key}'>署名付きURL</a>
                <a href='/s3/download_local/{key}'>サーバーDL</a>
            </div>
        </li>
        """
    html += "</ul>"

    html += """
<h3>📤 ファイルアップロード</h3>
<form id="uploadForm" method="post" action="/s3/upload" enctype="multipart/form-data">
    <input type="file" name="file" required>
    <input type="submit" value="アップロード">
</form>

<div id="progressContainer">
    <progress id="uploadProgress" value="0" max="100"></progress>
    <div id="progressText">0%</div>
</div>

<a class='button' href='/'>← ホームへ戻る</a>

<script>
document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault();
    var form = this;
    var fileInput = form.file;

    if (!fileInput.files.length) {
        alert('ファイルを選択してください。');
        return;
    }

    var formData = new FormData(form);
    var xhr = new XMLHttpRequest();

    xhr.open('POST', form.action, true);

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            var percent = Math.round((e.loaded / e.total) * 100);
            document.getElementById('uploadProgress').value = percent;
            document.getElementById('progressText').innerText = percent + '%';
            document.getElementById('progressContainer').style.display = 'block';
        }
    };

    xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            document.getElementById('progressText').innerText = 'アップロード完了、リダイレクト中...';
            window.location.href = '/s3';
        } else {
            alert('アップロード失敗しました。');
            document.getElementById('progressContainer').style.display = 'none';
        }
    };

    xhr.send(formData);
});
</script>

</body></html>
"""
    return html

@app.route('/s3/upload', methods=['POST'])
def s3_upload():
    file = request.files['file']
    if file:
        s3.upload_fileobj(file, S3_BUCKET, file.filename)
    return redirect('/s3')

@app.route('/s3/download/<path:key>')
def download_s3_signed_url(key):
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': key},
        ExpiresIn=3600
    )
    return redirect(url)

@app.route('/s3/download_local/<path:key>')
def download_s3_direct(key):
    os.makedirs(LOCAL_DOWNLOAD_DIR, exist_ok=True)
    local_path = os.path.join(LOCAL_DOWNLOAD_DIR, key)
    s3.download_file(S3_BUCKET, key, local_path)
    return f"""
    <html>
    <head>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f9;
            color: #2c3e50;
            padding: 50px;
            text-align: center;
        }}
        .message-box {{
            display: inline-block;
            background: white;
            padding: 40px 60px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-top: 100px;
        }}
        h3 {{
            font-size: 24px;
            margin-bottom: 30px;
        }}
        a.button {{
            display: inline-block;
            text-decoration: none;
            padding: 12px 24px;
            background-color: #3498db;
            color: white;
            border-radius: 8px;
            font-size: 16px;
            transition: background-color 0.2s ease;
        }}
        a.button:hover {{
            background-color: #2980b9;
        }}
    </style>
    </head>
    <body>
        <div class="message-box">
            <h3>✅ <code>{key}</code> をWEB Serverに正常に保存しました。</h3>
            <a href="/s3" class="button">←戻る</a>
        </div>
    </body>
    </html>
    """

# ---------- RDS セクション ----------
def get_rds_connection(database=None):
    return pymysql.connect(
        host='admin.chm2cqegc7se.ap-northeast-1.rds.amazonaws.com',
        user='admin',
        password='passw0rd',
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_database_names():
    conn = get_rds_connection()
    with conn.cursor() as cursor:
        cursor.execute("SHOW DATABASES")
        dbs = [row['Database'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
    conn.close()
    return [db for db in dbs if db not in ('information_schema', 'mysql', 'performance_schema', 'sys')]

@app.route('/db')
def db_index():
    dbs = get_database_names()
    html = html_header("RDS データベース")

    html += """
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f9;
            color: #2c3e50;
            padding: 40px;
        }
        h1 {
            font-size: 32px;
            margin-bottom: 30px;
            color: #34495e;
        }
        ul.db-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        ul.db-list li {
            background: white;
            border-radius: 10px;
            padding: 18px 24px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }
        .db-name {
            font-size: 18px;
            font-weight: 500;
        }
        .actions {
            display: flex;
            gap: 10px;
        }
        .actions a {
            text-decoration: none;
            padding: 6px 14px;
            border-radius: 5px;
            font-size: 14px;
            color: white;
            transition: background-color 0.2s ease;
        }
        .open-btn {
            background-color: #3498db;
        }
        .open-btn:hover {
            background-color: #2980b9;
        }
        .delete-btn {
            background-color: #e74c3c;
        }
        .delete-btn:hover {
            background-color: #c0392b;
        }
        .create-btn {
            display: inline-block;
            margin-top: 30px;
            text-decoration: none;
            background-color: #2ecc71;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
        }
        .create-btn:hover {
            background-color: #27ae60;
        }
        .button {
            display: inline-block;
            margin-top: 30px;
            padding: 10px 20px;
            background-color: #95a5a6;
            color: white;
            border-radius: 6px;
            text-decoration: none;
        }
        .button:hover {
            background-color: #7f8c8d;
        }
    </style>

    <h1>🗃️ RDS データベースリスト</h1>
    <ul class="db-list">
    """

    for db in dbs:
        html += f"""
        <li>
            <span class="db-name">📂 {db}</span>
            <span class="actions">
                <a class="open-btn" href="/db/{db}">開く</a>
                <a class="delete-btn" href="/db/{db}/delete">削除</a>
            </span>
        </li>
        """

    html += """
    </ul>
    <a class="create-btn" href="/db/create">🆕 新しいデータベースを作成</a>
    <br>
    <a class="button" href="/">← ホームへ</a>
    </body></html>
    """
    return html

@app.route('/db/<database>')
def db_tables(database):
    try:
        conn = get_rds_connection(database)
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            rows = cursor.fetchall()
        conn.close()

        html = html_header(f"データベース: {database}")

        html += f"""
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f6f9;
                color: #2c3e50;
                padding: 40px;
            }}
            h1 {{
                font-size: 28px;
                margin-bottom: 30px;
                color: #34495e;
            }}
            ul.table-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            ul.table-list li {{
                background: white;
                border-radius: 10px;
                padding: 18px 24px;
                margin-bottom: 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            }}
            .table-name {{
                font-size: 18px;
                font-weight: 500;
            }}
            .actions {{
                display: flex;
                gap: 10px;
            }}
            .actions a {{
                text-decoration: none;
                padding: 6px 14px;
                border-radius: 5px;
                font-size: 14px;
                color: white;
                transition: background-color 0.2s ease;
            }}
            .open-btn {{
                background-color: #3498db;
            }}
            .open-btn:hover {{
                background-color: #2980b9;
            }}
            .delete-btn {{
                background-color: #e74c3c;
            }}
            .delete-btn:hover {{
                background-color: #c0392b;
            }}
            .query-btn, .create-btn {{
                display: inline-block;
                margin-top: 20px;
                text-decoration: none;
                background-color: #2ecc71;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
                margin-right: 10px;
            }}
            .query-btn:hover, .create-btn:hover {{
                background-color: #27ae60;
            }}
            .button {{
                display: inline-block;
                margin-top: 30px;
                padding: 10px 20px;
                background-color: #95a5a6;
                color: white;
                border-radius: 6px;
                text-decoration: none;
            }}
            .button:hover {{
                background-color: #7f8c8d;
            }}
        </style>

        <h1>📂 {database} のテーブルリスト</h1>
        <ul class="table-list">
        """

        if not rows:
            html += "<p>⚠️ 現在、テーブルが存在しません。</p>"
        else:
            if isinstance(rows[0], dict):
                table_key = list(rows[0].keys())[0]
                tables = [row[table_key] for row in rows]
            else:
                tables = [row[0] for row in rows]

            for t in tables:
                html += f"""
                <li>
                    <span class="table-name">📄 {t}</span>
                    <span class="actions">
                        <a class="open-btn" href="/db/{database}/table/{t}">開く</a>
                        <a class="delete-btn" href="/db/{database}/table/{t}/delete">削除</a>
                    </span>
                </li>
                """

        html += f"""
        </ul>
        <a class="query-btn" href="/db/{database}/query">🧠 SQL クエリを実行</a>
        <a class="create-btn" href="/db/{database}/create_table">🆕 新しいテーブルを作成</a>
        <br>
        <a class="button" href="/db">← データベースリストへ</a>
        </body></html>
        """

        return html

    except Exception as e:
        return html_header("エラー") + f"<h1>❌ エラー発生: {str(e)}</h1></body></html>"

@app.route('/db/<database>/table/<table_name>')
def db_table(database, table_name):
    query = request.args.get("q")
    try:
        conn = get_rds_connection(database)
        with conn.cursor() as cursor:
        # 일단 헤더 추출을 위해 쿼리 한번 실행
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 1")
            headers = [desc[0] for desc in cursor.description]

        # 정렬에 쓸 컬럼 지정 (가능하면 id, 없으면 첫 컬럼)
            order_column = "id" if "id" in headers else headers[0]

            if query:
                like = f"'%{query}%'"
                sql = f"""
                    SELECT * FROM `{table_name}`
                    WHERE sender LIKE {like}
                    OR content LIKE {like}
                     OR created_at LIKE {like}
                 ORDER BY `{order_column}` DESC LIMIT 100
                """
            else:
                sql = f"SELECT * FROM `{table_name}` ORDER BY `{order_column}` DESC LIMIT 100"

                cursor.execute(sql)
                rows = cursor.fetchall()
        conn.close()

    except Exception as e:
        return html_header("エラー") + f"<h1>❌ エラー発生: {str(e)}</h1></body></html>"

    html = html_header(f"テーブル: {table_name}")
    html += f"""
    <h1>📄 {database}の{table_name}</h1>
    <a class='button' href='/db/{database}'>← テーブルリストへ</a>
    <form method="get" style="margin: 20px 0;">
        <input type="text" name="q" value="{query or ''}" placeholder="🔍 検索..." />
        <button type="submit">検索</button>
    </form>
    <table><tr>"""
    for h in headers:
        html += f"<th>{h}</th>"
    html += "<th>操作</th></tr>" 

    for row in rows:
        html += "<tr>"
        for h in headers:
            html += f"<td>{row.get(h, '')}</td>"
        key_column = "id" if "id" in headers else headers[0]
        row_key_value = row.get(key_column, '')
        html += f"<td><a href='/db/{database}/table/{table_name}/delete_row/{row_key_value}' style='color:blue;'>🗑️ 削除</a></td>"
        html += "</tr>"
        #row_id = row.get("id", "")#    ----未使用----
        #html += f"<td><a href='/db/{database}/table/{table_name}/delete_row/{row_id}' style='color:red;'>🗑️ 削除</a></td>"#
        #html += "</tr>"#
    html += "</table></body></html>"
    return html

@app.route('/db/<database>/table/<table_name>/delete_row/<row_id>', methods=['GET', 'POST'])
def delete_row(database, table_name, row_id):
    try:
        conn = get_rds_connection(database)
        with conn.cursor() as cursor:
            # 기준 컬럼 결정
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 1")
            headers = [desc[0] for desc in cursor.description]
            key_column = "id" if "id" in headers else headers[0]

        if request.method == 'POST':
            with conn.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM `{table_name}` WHERE `{key_column}` = %s",
                    (row_id,)
                )
                conn.commit()
            conn.close()
            return redirect(f"/db/{database}/table/{table_name}")
    except Exception as e:
        return html_header("削除エラー") + f"<h1>❌ 削除失敗: {str(e)}</h1></body></html>"

    html = html_header("行削除確認")
    html += f"<h1>⚠️ 行削除確認: テーブル {table_name} で {key_column} = {row_id}</h1>"
    html += "<p>この行を本当に削除しますか？</p>"
    html += f"<form method='post'><button type='submit' class='button' style='background:red;'>🗑️ 削除する</button></form>"
    html += f"<a class='button' href='/db/{database}/table/{table_name}'>← 戻る</a></body></html>"
    return html

@app.route('/db/<database>/query', methods=['GET', 'POST'])
def query_runner(database):
    result_html = ""
    sql = ""
    error = ""
    
    if request.method == 'POST':
        sql = request.form.get('sql')
        try:
            conn = get_rds_connection(database)
            with conn.cursor() as cursor:
                cursor.execute(sql)
                if sql.strip().lower().startswith("select"):
                    rows = cursor.fetchall()
                    headers = [desc[0] for desc in cursor.description]
                    result_html += "<table><tr>"
                    for h in headers:
                        result_html += f"<th>{h}</th>"
                    result_html += "</tr>"
                    for row in rows:
                        result_html += "<tr>" + "".join(f"<td>{row.get(h, '')}</td>" for h in headers) + "</tr>"
                    result_html += "</table>"
                else:
                    conn.commit()
                    result_html = f"<p><b>✅ クエリ成功</b> – 影響を受けた行数: {cursor.rowcount}</p>"
            conn.close()
        except Exception as e:
            error = str(e)

    html = html_header(f"{database} SQL クエリ")
    html += f"<h1>🧠 SQL クエリを実行 ({database})</h1>"
    html += f"""
        <form method="post" style="margin-bottom: 20px;">
            <textarea name="sql" rows="6" style="width:100%; font-family:monospace;" placeholder="SQL を入力してください">{sql}</textarea><br/>
            <button type="submit" class="button">▶ 実行</button>
        </form>
    """
    if error:
        html += f"<p style='color:red;'>❌ エラー: {error}</p>"
    html += result_html
    html += f"<a class='button' href='/db/{database}'>← テーブルリストへ</a></body></html>"
    return html

@app.route('/db/create', methods=['GET', 'POST'])
def create_database():
    message = ""
    if request.method == 'POST':
        new_db = request.form.get('dbname')
        if new_db:
            try:
                conn = get_rds_connection()
                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE `{new_db}`")
                    conn.commit()
                conn.close()
                return redirect(f"/db/{new_db}")
            except Exception as e:
                message = f"❌ 作成失敗: {str(e)}"
        else:
            message = "⚠️ データベース名を入力してください。"

    html = html_header("新しいデータベース作成")
    html += "<h1>🆕 新しい データベースを作成</h1>"
    html += """
        <form method="post">
            <input type="text" name="dbname" placeholder="データベース名" />
            <button type="submit" class="button">作成</button>
        </form>
    """
    if message:
        html += f"<p>{message}</p>"
    html += "<a class='button' href='/db'>← データベースリストへ</a></body></html>"
    return html

@app.route('/db/<database>/delete', methods=['GET', 'POST'])
def delete_database(database):
    message = ""
    if request.method == 'POST':
        try:
            conn = get_rds_connection()
            with conn.cursor() as cursor:
                cursor.execute(f"DROP DATABASE `{database}`")
                conn.commit()
            conn.close()
            return redirect('/db')
        except Exception as e:
            message = f"❌ 削除失敗: {str(e)}"

    html = html_header("データベース削除確認")
    html += f"<h1>⚠️ データベース削除確認 : {database}を削除しますか？</h1>"
    html += f"<form method='post'><button type='submit' class='button' style='background:red;'>🗑️ 本当に削除する</button></form>"
    html += f"<p style='color:red;'>{message}</p>"
    html += f"<a class='button' href='/db/{database}'>← 戻る</a></body></html>"
    return html

@app.route('/db/<database>/create_table', methods=['GET', 'POST'])
def create_table(database):
    message = ""
    if request.method == 'POST':
        table_name = request.form.get('table_name')
        columns = request.form.get('columns')  # 예: id INT PRIMARY KEY, name VARCHAR(100)
        if table_name and columns:
            try:
                conn = get_rds_connection(database)
                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE TABLE `{table_name}` ({columns})")
                    conn.commit()
                conn.close()
                return redirect(f"/db/{database}")
            except Exception as e:
                message = f"❌ 作成失敗: {str(e)}"
        else:
            message = "⚠️ テーブル名とカラム定義を入力してください。"

    html = html_header("テーブル作成")
    html += f"<h1>🆕 {database} にテーブルを作成</h1>"
    html += f"""
        <form method="post">
            <input type="text" name="table_name" placeholder="テーブル名"><br><br>
            <textarea name="columns" rows="4" style="width:100%" placeholder="例: id INT PRIMARY KEY, name VARCHAR(100)"></textarea><br><br>
            <button type="submit" class="button">作成</button>
        </form>
    """
    if message:
        html += f"<p>{message}</p>"
    html += f"<a class='button' href='/db/{database}'>← テーブルリストへ</a></body></html>"
    return html

@app.route('/db/<database>/table/<table_name>/delete', methods=['GET', 'POST'])
def delete_table(database, table_name):
    message = ""
    if request.method == 'POST':
        try:
            conn = get_rds_connection(database)
            with conn.cursor() as cursor:
                cursor.execute(f"DROP TABLE `{table_name}`")
                conn.commit()
            conn.close()
            return redirect(f"/db/{database}")
        except Exception as e:
            message = f"❌ 削除失敗: {str(e)}"

    html = html_header("テーブル削除確認")
    html += f"<h1>⚠️ テーブル削除確認 : {database}の{table_name}を削除しますか？</h1>"
    html += f"<form method='post'><button type='submit' class='button' style='background:red;'>🗑️ 本当に削除する</button></form>"
    html += f"<p style='color:red;'>{message}</p>"
    html += f"<a class='button' href='/db/{database}/table/{table_name}'>← 戻る</a></body></html>"
    return html

# ---------- 管理者メニュー セクション ----------

app.secret_key = 'your_secret_key_here'
access_logs = []

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect('/admin')
    
    error = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'PASSW0RD':
            session['admin_logged_in'] = True
            session['login_time'] = int(time.time())    #ログイン時間を記録
            session_id = request.cookies.get("session")
            admin_sessions[session_id] = {
                'login_time': session['login_time'],
                'ip': request.headers.get('X-Forwarded-For', request.remote_addr)
            }
            return redirect('/admin')
        else:
            error = '⚠️ ログイン情報が正しくありません。'

    html = html_header("管理者ログイン")
    html += f"""
    <style>
        .login-container {{
            max-width: 400px;
            margin: 100px auto;
            padding: 30px;
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h2 {{
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        input[type="text"], input[type="password"] {{
            width: 100%;
            padding: 12px 15px;
            margin: 10px 0;
            border: 1px solid #ccc;
            border-radius: 5px;
        }}
        button {{
            width: 100%;
            padding: 12px;
            background-color: #2c3e50;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
        }}
        button:hover {{
            background-color: #1a242f;
        }}
        .admin-contact {{
            display: block;
            text-align: center;
            margin-top: 15px;
            color: #3498db;
        }}
        .warning {{
            background-color: #ffe6e6;
            border: 1px solid #ff4d4d;
            padding: 12px;
            border-radius: 5px;
            color: #b30000;
            margin-bottom: 15px;
            font-weight: bold;
            text-align: center;
        }}
        .error-msg {{
            color: red;
            text-align: center;
            margin-top: 10px;
        }}
    </style>

    <div class="login-container">
        <h2>🔐 管理者ログイン</h2>
        <div class="warning">管理者以外のアクセス時にすべての試みが記録され、必ず報告されます。</div>

        <form method="POST">
            <input type="text" name="username" placeholder="管理者 ID" required>
            <input type="password" name="password" placeholder="パスワード" required>
            <button type="submit">ログイン</button>
        </form>
        <a class="admin-contact" href="mailto:j.junbeom@reach-out.co.jp?subject=管理者へのお問い合わせ">管理者にお問い合わせ</a>
        {'<div class="error-msg">' + error + '</div>' if error else ''}
    </div>
    </body></html>
    """
    return html

@app.before_request
def log_request_info():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '不明')
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    access_logs.append({
        'time': timestamp,
        'ip': ip,
        'user_agent': user_agent,
        'path': request.path
    })

    # Logの数が多くならないように制限
    if len(access_logs) > 2000:
        access_logs.pop(0)

@app.after_request
def add_no_cache_headers(response):  # 🔒 Cache防止Header追加
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route('/admin')
def admin_menu():
    if not session.get('admin_logged_in'):
        return redirect('/admin_login')

    # 세션 타임아웃 30분
    login_time = session.get('login_time')
    if not login_time or time.time() - login_time > 1800:
        # 세션 삭제 및 admin_sessions에서도 제거
        session_id = request.cookies.get("session")
        admin_sessions.pop(session_id, None)
        session.clear()
        return redirect('/admin_login')
    
    remaining_sec = max(0, 1800 - int(time.time() - login_time))
    minutes = remaining_sec // 60
    seconds = remaining_sec % 60

    # 관리자 접속중 목록
    session_list_html = ''
    now = time.time()
    # 30분 이상 경과한 세션은 자동 삭제
    expired_sessions = []
    for sid, info in admin_sessions.items():
        if now - info['login_time'] > 1800:
            expired_sessions.append(sid)
        else:
            lt = datetime.datetime.fromtimestamp(info['login_time']).strftime('%Y-%m-%d %H:%M:%S')
            session_list_html += f"<tr><td>{sid}</td><td>{info['ip']}</td><td>{lt}</td></tr>"
    for sid in expired_sessions:
        admin_sessions.pop(sid, None)

    html = html_header("管理者メニュー")
    html += f"""
    <div style="position: fixed; top: 10px; right: 20px; font-size: 14px; color: #333; background-color: #f0f0f0; padding: 8px 12px; border-radius: 5px;">
        ✅ 管理者接続中・残り <span id="countdown">{minutes:02d}:{seconds:02d}</span>
    </div>

    <script>
    let remaining = {remaining_sec};
    const countdown = document.getElementById('countdown');
    const timer = setInterval(() => {{
        if (--remaining <= 0) {{
            clearInterval(timer);
            window.location.href = '/logout';
        }} else {{
            const m = String(Math.floor(remaining / 60)).padStart(2, '0');
            const s = String(remaining % 60).padStart(2, '0');
            countdown.textContent = `${{m}}:${{s}}`;
        }}
    }}, 1000);
    </script>

    <h1>管理者メニュー</h1>

    <div style="display: flex; gap: 30px; flex-wrap: wrap;">
        <a href="/admin/access_logs" class="button" style="padding: 20px; font-size: 18px; flex: 1; min-width: 250px;">🌐 アクセスログ確認</a>
        <a href="/admin/active_sessions" class="button" style="padding: 20px; font-size: 18px; flex: 1; min-width: 250px;">👥 接続中管理者一覧</a>
        <a href="/admin/approvals" class="button" style="padding: 20px; font-size: 18px; flex: 1; min-width: 250px;">✅ 利用者承認管理</a>
        <a href="/logout" class="button" style="padding: 20px; font-size: 18px; background-color: #e74c3c; flex: 1; min-width: 250px;">ログアウト</a>
    </div>

    <h2 style="margin-top: 40px;">現在接続中の管理者セッション一覧</h2>
    <table style="width: 100%; border-collapse: collapse; box-shadow: 0 0 15px rgba(0,0,0,0.05);">
        <thead style="background-color: #f2f2f2;">
            <tr>
                <th>Session ID</th>
                <th>IP アドレス</th>
                <th>ログイン時間</th>
            </tr>
        </thead>
        <tbody>
            {session_list_html if session_list_html else '<tr><td colspan="3" style="text-align:center;">接続中の管理者はいません。</td></tr>'}
        </tbody>
    </table>

    <div style="margin-top: 40px;">
        <a class="button" href="/" style="background-color: #2c3e50; color: white; padding: 12px 20px; border-radius: 6px; font-size: 16px;">← ホームへ戻る</a>
    </div>

    </body></html>
    """
    return html

@app.route('/admin/access_logs')
def admin_access_logs():
    if not session.get('admin_logged_in'):
        return redirect('/admin_login')
    # 기존 접근로그 표시 기능을 분리

    login_time = session.get('login_time')
    if not login_time or time.time() - login_time > 1800:
        session_id = request.cookies.get("session")
        admin_sessions.pop(session_id, None)
        session.clear()
        return redirect('/admin_login')

    remaining_sec = max(0, 1800 - int(time.time() - login_time))
    minutes = remaining_sec // 60
    seconds = remaining_sec % 60

    html = html_header("アクセスログ")
    html += f"""
    <div style="position: fixed; top: 10px; right: 20px; font-size: 14px; color: #333; background-color: #f0f0f0; padding: 8px 12px; border-radius: 5px;">
        ✅ 管理者接続中・残り <span id="countdown">{minutes:02d}:{seconds:02d}</span>
    </div>

    <script>
    let remaining = {remaining_sec};
    const countdown = document.getElementById('countdown');
    const timer = setInterval(() => {{
        if (--remaining <= 0) {{
            clearInterval(timer);
            window.location.href = '/logout';
        }} else {{
            const m = String(Math.floor(remaining / 60)).padStart(2, '0');
            const s = String(remaining % 60).padStart(2, '0');
            countdown.textContent = `${{m}}:${{s}}`;
        }}
    }}, 1000);
    </script>

    <h1>🌐 アクセスログ一覧</h1>
    <p>最近の訪問者情報（最大2000件まで）を表示します。</p>

    <table style="width: 100%; border-collapse: collapse; box-shadow: 0 0 15px rgba(0,0,0,0.05);">
        <thead style="background-color: #f2f2f2;">
            <tr>
                <th>アクセス時刻</th>
                <th>IP アドレス</th>
                <th>User-Agent</th>
                <th>アクセスパス</th>
            </tr>
        </thead>
        <tbody>
    """

    for log in reversed(access_logs):
        html += f"""
        <tr>
            <td>{log['time']}</td>
            <td>{log['ip']}</td>
            <td>{log['user_agent']}</td>
            <td>{log['path']}</td>
        </tr>
        """

    html += """
        </tbody>
    </table>

    <div style="margin-top: 30px;">
        <a class="button" href="/admin">← 管理者メニューへ戻る</a>
        <a class="button" style="background-color:#e74c3c; margin-left: 10px;" href="/logout">ログアウト</a>
    </div>
    </body></html>
    """
    return html


# 접속중인 관리자 목록 별도 페이지 (재사용 가능)
@app.route('/admin/active_sessions')
def admin_active_sessions():
    if not session.get('admin_logged_in'):
        return redirect('/admin_login')

    login_time = session.get('login_time')
    if not login_time or time.time() - login_time > 1800:
        session_id = request.cookies.get("session")
        admin_sessions.pop(session_id, None)
        session.clear()
        return redirect('/admin_login')

    remaining_sec = max(0, 1800 - int(time.time() - login_time))
    minutes = remaining_sec // 60
    seconds = remaining_sec % 60

    session_list_html = ''
    now = time.time()
    expired_sessions = []
    for sid, info in admin_sessions.items():
        if now - info['login_time'] > 1800:
            expired_sessions.append(sid)
        else:
            lt = datetime.datetime.fromtimestamp(info['login_time']).strftime('%Y-%m-%d %H:%M:%S')
            session_list_html += f"<tr><td>{sid}</td><td>{info['ip']}</td><td>{lt}</td></tr>"
    for sid in expired_sessions:
        admin_sessions.pop(sid, None)

    html = html_header("接続中管理者一覧")
    html += f"""
    <div style="position: fixed; top: 10px; right: 20px; font-size: 14px; color: #333; background-color: #f0f0f0; padding: 8px 12px; border-radius: 5px;">
        ✅ 管理者接続中・残り <span id="countdown">{minutes:02d}:{seconds:02d}</span>
    </div>

    <script>
    let remaining = {remaining_sec};
    const countdown = document.getElementById('countdown');
    const timer = setInterval(() => {{
        if (--remaining <= 0) {{
            clearInterval(timer);
            window.location.href = '/logout';
        }} else {{
            const m = String(Math.floor(remaining / 60)).padStart(2, '0');
            const s = String(remaining % 60).padStart(2, '0');
            countdown.textContent = `${{m}}:${{s}}`;
        }}
    }}, 1000);
    </script>

    <h1>👥 接続中管理者一覧</h1>
    <table style="width: 100%; border-collapse: collapse; box-shadow: 0 0 15px rgba(0,0,0,0.05);">
        <thead style="background-color: #f2f2f2;">
            <tr>
                <th>Session ID</th>
                <th>IP アドレス</th>
                <th>ログイン時間</th>
            </tr>
        </thead>
        <tbody>
            {session_list_html if session_list_html else '<tr><td colspan="3" style="text-align:center;">接続中の管理者はいません。</td></tr>'}
        </tbody>
    </table>

    <div style="margin-top: 30px;">
        <a class="button" href="/admin">← 管理者メニューへ戻る</a>
        <a class="button" style="background-color:#e74c3c; margin-left: 10px;" href="/logout">ログアウト</a>
    </div>
    </body></html>
    """
    return html
@app.route('/admin/approvals')
def admin_approvals():
    if not session.get('admin_logged_in'):
        return redirect('/admin_login')

    login_time = session.get('login_time')
    if not login_time or time.time() - login_time > 1800:
        session_id = request.cookies.get("session")
        admin_sessions.pop(session_id, None)
        session.clear()
        return redirect('/admin_login')

    remaining_sec = max(0, 1800 - int(time.time() - login_time))
    minutes = remaining_sec // 60
    seconds = remaining_sec % 60

    # 승인 대기/승인 사용자 구분
    pending_users = [u for u, approved in user_approvals.items() if not approved]
    approved_users = [u for u, approved in user_approvals.items() if approved]

    # HTML 생성
    pending_html = ''.join(
        f"""
        <tr>
            <td>{user}</td>
            <td>
                <a href="/admin/approve_user/{user}" style="color:green; font-weight:bold; margin-right: 10px;">承認</a>
                <a href="/admin/reject_user/{user}" style="color:red; font-weight:bold;">拒否</a>
            </td>
        </tr>
        """ for user in pending_users
    ) or '<tr><td colspan="2" style="text-align:center;">承認待ちの利用者はいません。</td></tr>'

    approved_html = ''.join(
        f"<tr><td>{user}</td><td>承認済み</td></tr>" for user in approved_users
    ) or '<tr><td colspan="2" style="text-align:center;">承認済み利用者がまだいません。</td></tr>'

    html = html_header("利用者承認管理")
    html += f"""
    <div style="position: fixed; top: 10px; right: 20px; font-size: 14px; color: #333; background-color: #f0f0f0; padding: 8px 12px; border-radius: 5px;">
        ✅ 管理者接続中・残り <span id="countdown">{minutes:02d}:{seconds:02d}</span>
    </div>

    <script>
    let remaining = {remaining_sec};
    const countdown = document.getElementById('countdown');
    const timer = setInterval(() => {{
        if (--remaining <= 0) {{
            clearInterval(timer);
            window.location.href = '/logout';
        }} else {{
            const m = String(Math.floor(remaining / 60)).padStart(2, '0');
            const s = String(remaining % 60).padStart(2, '0');
            countdown.textContent = `${{m}}:${{s}}`;
        }}
    }}, 1000);
    </script>

    <h1>✅ 利用者承認管理</h1>

    <h2>承認待ち利用者</h2>
    <table>
        <tr><th>ユーザーID</th><th>操作</th></tr>
        {pending_html}
    </table>

    <h2 style="margin-top:40px;">承認済み利用者</h2>
    <table>
        <tr><th>ユーザーID</th><th>状態</th></tr>
        {approved_html}
    </table>

    <div style="margin-top: 30px;">
        <a class="button" href="/admin">← 管理者メニューへ戻る</a>
        <a class="button" style="background-color:#e74c3c; margin-left: 10px;" href="/logout">ログアウト</a>
    </div>
    </body></html>
    """
    return html

@app.route('/admin/approve_user/<user_id>')
def approve_user(user_id):
    if session.get('admin_logged_in') and user_id in user_approvals:
        user_approvals[user_id] = True
    return redirect('/admin/approvals')


@app.route('/admin/reject_user/<user_id>')
def reject_user(user_id):
    if session.get('admin_logged_in') and user_id in user_approvals:
        user_approvals.pop(user_id, None)
    return redirect('/admin/approvals')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/admin_login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
