from flask import Flask, request, session, redirect, send_from_directory
import os, hmac, hashlib, time, requests as http_requests

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'sf-os-secret-2026')

AUTH_SECRET = 'blendsf-auth-2026'

UNITY_URL = 'https://positive-appreciation-production.up.railway.app'

# Staff users (hardcoded) — clients authenticate via Unity DB
USERS = {
    'nico':  {'password': 'Losblend2026', 'role': 'admin',   'name': 'Nicolás'},
    'cris':  {'password': 'Losblend2026', 'role': 'admin',   'name': 'Cristóbal'},
    'paula': {'password': 'Pauliña123',   'role': 'unity',   'name': 'Paula'},
    'juan':  {'password': 'Juanitomachine123', 'role': 'unity', 'name': 'Juan'},
    'seba':  {'password': 'Sebads123',    'role': 'unity+copilot', 'name': 'Sebastián'},
}

def generate_token(username, role):
    ts = str(int(time.time()))
    msg = f"{username}:{role}:{ts}"
    sig = hmac.new(AUTH_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{username}:{role}:{ts}:{sig}"

def verify_token(token, max_age=300):
    try:
        parts = token.split(':')
        if len(parts) != 4:
            return None
        username, role, ts, sig = parts
        expected = hmac.new(AUTH_SECRET.encode(), f"{username}:{role}:{ts}".encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        if time.time() - int(ts) > max_age:
            return None
        return {'username': username, 'role': role}
    except Exception:
        return None

@app.after_request
def add_no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').lower().strip()
        password = request.form.get('password', '')

        # 1) Check staff users (hardcoded)
        user = USERS.get(username)
        if user and user['password'] == password:
            session['user'] = username
            session['role'] = user['role']
            session['name'] = user['name']
            session['client_name'] = ''
            return redirect('/admin')

        # 2) Check client users via Unity DB
        try:
            r = http_requests.post(f'{UNITY_URL}/api/auth-client',
                json={'username': username, 'password': password}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                session['user'] = username
                session['role'] = 'cliente'
                session['name'] = data['name']
                session['client_name'] = data['client_name']
                return redirect('/cliente')
        except Exception:
            pass

        return login_page(error='Usuario o contraseña incorrectos')
    return login_page()

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin():
    if 'user' not in session:
        return redirect('/login')
    token = generate_token(session['user'], session['role'])
    with open('admin.html', 'r') as f:
        html = f.read()
    user_script = f"""<script>
const SF_USER = {{username:'{session["user"]}',name:'{session["name"]}',role:'{session["role"]}',token:'{token}'}};
</script>"""
    html = html.replace('</head>', user_script + '\n</head>')
    return html

@app.route('/cliente')
def cliente():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role') != 'cliente':
        return redirect('/admin')
    token = generate_token(session['user'], session['role'])
    with open('cliente.html', 'r') as f:
        html = f.read()
    user_script = f"""<script>
const SF_USER = {{username:'{session["user"]}',name:'{session["name"]}',role:'{session["role"]}',token:'{token}',client_name:'{session.get("client_name","")}'}};
</script>"""
    html = html.replace('</head>', user_script + '\n</head>')
    return html

@app.route('/api/verify-token')
def verify_token_endpoint():
    token = request.args.get('token', '')
    result = verify_token(token)
    if result:
        return result
    return {'error': 'invalid token'}, 401

def login_page(error=''):
    error_html = f'<div class="error">{error}</div>' if error else ''
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Social Food - Login</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family:'Inter',-apple-system,sans-serif;
  background:#030303; color:#f5f5f5;
  min-height:100vh; display:flex;
  align-items:center; justify-content:center;
}}
.ambient {{
  position:fixed; inset:0; z-index:0; pointer-events:none;
}}
.orb {{
  position:absolute; border-radius:50%; filter:blur(120px);
  animation: drift 18s ease-in-out infinite;
}}
.orb-1 {{
  width:700px; height:700px;
  background:radial-gradient(circle, rgba(234,88,12,0.15) 0%, transparent 65%);
  top:-300px; left:50%; transform:translateX(-50%);
}}
.orb-2 {{
  width:400px; height:400px;
  background:radial-gradient(circle, rgba(234,88,12,0.08) 0%, transparent 70%);
  bottom:-150px; right:10%;
  animation-delay:-8s;
}}
@keyframes drift {{
  0%,100% {{ transform:translate(0,0) scale(1); }}
  50% {{ transform:translate(20px,-15px) scale(1.05); }}
}}
.login-box {{
  position:relative; z-index:2;
  background:linear-gradient(170deg, rgba(18,18,18,0.95), rgba(8,8,8,0.95));
  border:1px solid rgba(255,255,255,0.08);
  border-radius:28px; padding:48px 40px;
  width:100%; max-width:400px;
  backdrop-filter:blur(20px);
  box-shadow:0 40px 100px rgba(0,0,0,0.5), 0 0 80px rgba(234,88,12,0.06);
}}
.logo {{
  text-align:center; margin-bottom:32px;
}}
.logo-icon {{
  display:inline-flex; align-items:center; justify-content:center;
  width:64px; height:64px;
  background:linear-gradient(145deg,#151515,#0d0d0d);
  border:1px solid rgba(255,255,255,0.1);
  border-radius:22px; margin-bottom:12px;
  box-shadow:0 0 50px rgba(234,88,12,0.15);
}}
.logo-letters {{
  font-size:28px; font-weight:900; letter-spacing:-1px; color:#fff;
}}
.logo-dot {{
  display:inline-block; width:8px; height:8px;
  background:#EA580C; border-radius:50%;
  margin-left:1px; box-shadow:0 0 15px rgba(234,88,12,0.8);
  vertical-align:baseline;
}}
.logo-text {{
  font-size:10px; font-weight:700; letter-spacing:4px;
  text-transform:uppercase; color:#EA580C;
}}
.title {{
  text-align:center; font-size:20px; font-weight:800;
  margin-bottom:8px; letter-spacing:-0.5px;
}}
.subtitle {{
  text-align:center; font-size:13px; color:#666;
  margin-bottom:28px;
}}
.field {{
  margin-bottom:16px;
}}
.field label {{
  display:block; font-size:11px; font-weight:600;
  text-transform:uppercase; letter-spacing:1.5px;
  color:#555; margin-bottom:8px;
}}
.field input {{
  width:100%; padding:14px 16px;
  background:rgba(255,255,255,0.04);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:14px; color:#fff;
  font-family:'Inter',sans-serif; font-size:14px;
  outline:none; transition:border-color 0.3s;
}}
.field input:focus {{
  border-color:rgba(234,88,12,0.5);
  box-shadow:0 0 20px rgba(234,88,12,0.08);
}}
.field input::placeholder {{ color:#333; }}
.btn {{
  width:100%; padding:14px;
  background:linear-gradient(135deg, #EA580C, #fb923c);
  border:none; border-radius:14px;
  color:#fff; font-family:'Inter',sans-serif;
  font-size:14px; font-weight:700;
  cursor:pointer; transition:all 0.3s;
  margin-top:8px;
}}
.btn:hover {{
  box-shadow:0 0 30px rgba(234,88,12,0.4);
  transform:translateY(-2px);
}}
.error {{
  background:rgba(248,113,113,0.1);
  border:1px solid rgba(248,113,113,0.2);
  border-radius:10px; padding:10px 14px;
  font-size:12px; color:#f87171;
  text-align:center; margin-bottom:16px;
}}
.back {{
  display:block; text-align:center;
  margin-top:20px; font-size:12px;
  color:#444; text-decoration:none;
  transition:color 0.3s;
}}
.back:hover {{ color:#888; }}
</style>
</head>
<body>
<div class="ambient">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
</div>
<div class="login-box">
  <div class="logo">
    <div class="logo-icon"><span class="logo-letters">SF<span class="logo-dot"></span></span></div>
    <div class="logo-text">Social Food</div>
  </div>
  <div class="title">Iniciar sesion</div>
  <div class="subtitle">Accede a tu torre de control</div>
  {error_html}
  <form method="POST" action="/login">
    <div class="field">
      <label>Usuario</label>
      <input type="text" name="username" placeholder="Tu nombre de usuario" autocomplete="username" autofocus>
    </div>
    <div class="field">
      <label>Contrasena</label>
      <input type="password" name="password" placeholder="Tu contrasena" autocomplete="current-password">
    </div>
    <button type="submit" class="btn">Entrar</button>
  </form>
  <a href="/" class="back">Volver al inicio</a>
</div>
</body>
</html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
