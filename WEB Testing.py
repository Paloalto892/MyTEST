from flask import Flask, request, redirect, url_for, Response
import boto3
import pymysql
import os

app = Flask(__name__)

# ---------- 共通 ----------
S3_BUCKET = 's3buck-any'
REGION = 'ap-northeast-1'
LOCAL_DOWNLOAD_DIR = '/home/ec2-user/tmpdownload'  # EC2内 Download経路

s3 = boto3.client('s3', region_name=REGION)

def html_header(title):
    return f"""
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background-color: #f9f9fb;
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
    </head>
    <body>
    """

@app.route('/')
def home():
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
        <a class="menu-item" href="#">
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
        html += f"<h1>📂 {database} のテーブルリスト</h1><ul>"

        if not rows:
            html += "<p>⚠️ 現在、テーブルが存在しません。</p>"
        else:
            if isinstance(rows[0], dict):
                table_key = list(rows[0].keys())[0]
                tables = [row[table_key] for row in rows]
            else:
                tables = [row[0] for row in rows]

            for t in tables:
                html += f'<li><a href="/db/{database}/table/{t}">📄 {t}</a> - <a href="/db/{database}/table/{t}/delete" style="color:red;">🗑️ 削除</a></li>'
            html += f'<li><a href="/db/{database}/query">🧠 SQL クエリを実行</a></li>'

        html += f'<li><a href="/db/{database}/create_table">🆕 新しい テーブルを作成</a></li>'
        html += "</ul><a class='button' href='/db'>← データベースリストへ</a></body></html>"
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
    <h1>📄 {database}.{table_name}</h1>
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
    html += f"<h1>⚠️ データベース削除確認: {database}</h1>"
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
    html += f"<h1>⚠️ テーブル削除確認: {database}.{table_name}</h1>"
    html += f"<form method='post'><button type='submit' class='button' style='background:red;'>🗑️ 本当に削除する</button></form>"
    html += f"<p style='color:red;'>{message}</p>"
    html += f"<a class='button' href='/db/{database}/table/{table_name}'>← 戻る</a></body></html>"
    return html

# ---------- 管理者メニュー セクション ----------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)