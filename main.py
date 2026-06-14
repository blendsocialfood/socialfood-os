from flask import Flask, request, session, redirect, send_from_directory
import os, hmac, hashlib, time, json, requests as http_requests
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'sf-os-secret-2026')

AUTH_SECRET = 'blendsf-auth-2026'

UNITY_URL = 'https://positive-appreciation-production.up.railway.app'
FIRST_TOUCH_URL = 'https://blend-first-touch-production.up.railway.app'
COPILOT_URL = 'https://web-production-2131c.up.railway.app'
BOT_URL = 'https://web-production-76938.up.railway.app'
PIXEL_URL = 'https://heroic-enjoyment-production-4350.up.railway.app'
PRISM_URL = 'https://blend-prism-production.up.railway.app'
DROP_URL = 'https://blend-drop-production.up.railway.app'
# Blend Covers backend (local en dev; Railway en prod). Override por env COVERS_URL.
COVERS_URL = os.environ.get('COVERS_URL', 'http://localhost:8011')

# Fallback: if First Touch is down, use these to avoid lockout
USERS_FALLBACK = {
    'nico':  {'password': 'Losblend2026', 'role': 'admin',   'name': 'Nicolás'},
    'cris':  {'password': 'Losblend2026', 'role': 'admin',   'name': 'Cristóbal'},
}

def generate_token(username, role):
    ts = str(int(time.time()))
    msg = f"{username}:{role}:{ts}"
    sig = hmac.new(AUTH_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{username}:{role}:{ts}:{sig}"


def generate_frog_token():
    """Token compatible con Frog /sso?t=<ts>.<sha256(secret,ts)> max 60s."""
    ts = str(int(time.time()))
    sig = hmac.new(AUTH_SECRET.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"

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

        # 1) Check staff users via First Touch DB
        try:
            r = http_requests.post(f'{FIRST_TOUCH_URL}/api/usuarios/auth',
                json={'username': username, 'password': password}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                session['user'] = data['username']
                session['role'] = data['role']
                session['name'] = data['name']
                session['client_name'] = ''
                return redirect('/admin')
        except Exception:
            # Fallback: if First Touch is down, check admin-only backup
            fb = USERS_FALLBACK.get(username)
            if fb and fb['password'] == password:
                session['user'] = username
                session['role'] = fb['role']
                session['name'] = fb['name']
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
                session['covers_slug'] = data.get('covers_slug') or ''
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
    # Re-auth via token from cross-app navigation
    incoming_token = request.args.get('token', '')
    if incoming_token and 'user' not in session:
        result = verify_token(incoming_token)
        if result and result['role'] != 'cliente':
            # Restore Flask session from token
            session['user'] = result['username']
            session['role'] = result['role']
            session['name'] = result['username'].capitalize()
            session['client_name'] = ''
    if 'user' not in session:
        return redirect('/login')
    token = generate_token(session['user'], session['role'])
    frog_token = generate_frog_token()
    with open('admin.html', 'r') as f:
        html = f.read()
    sf_user = json.dumps({"username": session["user"], "name": session["name"], "role": session["role"], "token": token, "frog_token": frog_token})
    user_script = f"<script>\nconst SF_USER = {sf_user};\n</script>"
    html = html.replace('</head>', user_script + '\n</head>')
    return html

@app.route('/cliente')
def cliente():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role') != 'cliente':
        return redirect('/admin')
    token = generate_token(session['user'], session['role'])
    with open('cliente_v2.html', 'r') as f:
        html = f.read()
    sf_user = json.dumps({"username": session["user"], "name": session["name"], "role": session["role"], "token": token, "client_name": session.get("client_name", ""), "covers_slug": session.get("covers_slug", "")})
    user_script = f"<script>\nconst SF_USER = {sf_user};\n</script>"
    html = html.replace('</head>', user_script + '\n</head>')
    return html

@app.route('/mission-control')
def mission_control():
    if 'user' not in session:
        return redirect('/login')
    token = generate_token(session['user'], session['role'])
    frog_token = generate_frog_token()
    with open('mission_control.html', 'r') as f:
        html = f.read()
    sf_user = json.dumps({"username": session["user"], "name": session["name"], "role": session["role"], "token": token, "frog_token": frog_token})
    user_script = f"<script>\nconst SF_USER = {sf_user};\n</script>"
    html = html.replace('</head>', user_script + '\n</head>')
    return html

@app.route('/api/health')
def health_check():
    if 'user' not in session:
        return {'error': 'unauthorized'}, 401
    services = [
        ('unity', UNITY_URL),
        ('copilot', COPILOT_URL),
        ('prism', PRISM_URL),
        ('bot', BOT_URL),
        ('pixel', PIXEL_URL),
        ('firsttouch', FIRST_TOUCH_URL),
        ('drop', DROP_URL),
    ]
    def check(item):
        name, url = item
        try:
            start = time.time()
            r = http_requests.get(url, timeout=10, allow_redirects=False)
            ms = int((time.time() - start) * 1000)
            return name, {'status': 'online', 'code': r.status_code, 'ms': ms}
        except Exception:
            return name, {'status': 'offline', 'code': 0, 'ms': 0}
    with ThreadPoolExecutor(max_workers=7) as pool:
        results = dict(pool.map(check, services))
    return results

# Dev-only: login mock como cliente para probar el portal sin Unity.
# Activado solo si SFOS_DEV=1.
@app.route('/dev-login-cliente/<slug>')
def dev_login_cliente(slug):
    if os.environ.get('SFOS_DEV') != '1':
        return {'error': 'dev mode off'}, 403
    session['user'] = slug
    session['role'] = 'cliente'
    session['name'] = 'Restaurante Demo'
    session['client_name'] = 'Restaurante Demo'
    return redirect('/cliente')


# Dev-only: sirve cliente_v2.html con SF_USER mock SIN requerir sesión (para tests/captura).
@app.route('/dev-cliente/<slug>')
def dev_cliente(slug):
    if os.environ.get('SFOS_DEV') != '1':
        return {'error': 'dev mode off'}, 403
    token = generate_token(slug, 'cliente')
    with open('cliente_v2.html', 'r') as f:
        html = f.read()
    sf_user = json.dumps({"username": slug, "name": "Restaurante Demo",
                          "role": "cliente", "token": token, "client_name": "Restaurante Demo"})
    user_script = f"<script>\nconst SF_USER = {sf_user};\n</script>"
    html = html.replace('</head>', user_script + '\n</head>')
    # Setear sesion temporal para que el proxy /api/covers/data autorice las llamadas del JS.
    session['user'] = slug
    session['role'] = 'cliente'
    session['name'] = 'Restaurante Demo'
    session['client_name'] = 'Restaurante Demo'
    session['covers_slug'] = slug
    return html


@app.route('/api/verify-token')
def verify_token_endpoint():
    token = request.args.get('token', '')
    result = verify_token(token)
    if result:
        return result
    return {'error': 'invalid token'}, 401


# ===== Blend Covers — proxy autenticado por sesión Flask =====
# El JS del portal pega aquí; nosotros llamamos al backend de Covers con AUTH_SECRET.
@app.route('/api/covers/data')
def covers_data_proxy():
    if 'user' not in session:
        return {'error': 'unauthorized'}, 401
    # El restaurante se identifica por su covers_slug (de Unity), no por el usuario
    # de login. Server-side: el dueño solo ve SU restaurante (se ignora el ?cliente= del JS).
    cliente = session.get('covers_slug') or session.get('user', '')
    if not cliente:
        return {'error': 'sin cliente'}, 400
    try:
        r = http_requests.get(
            f'{COVERS_URL}/api/covers/data',
            params={'cliente': cliente,
                    'desde': request.args.get('desde', ''),
                    'hasta': request.args.get('hasta', '')},
            headers={'Authorization': f'Bearer {AUTH_SECRET}'},
            timeout=8,
        )
        return (r.text, r.status_code, {'Content-Type': r.headers.get('Content-Type', 'application/json')})
    except Exception as e:
        return {'error': f'backend covers no disponible: {e}'}, 502


# ===== Covers — entrada STAFF (hub admin → lista de clientes → panel del cliente) =====
def _is_staff():
    return 'user' in session and session.get('role') != 'cliente'


@app.route('/admin/covers')
def admin_covers_lista():
    if not _is_staff():
        return redirect('/login')
    from html import escape as _esc
    try:
        r = http_requests.get(f'{COVERS_URL}/api/covers/clientes',
                              headers={'Authorization': f'Bearer {AUTH_SECRET}'}, timeout=8)
        clientes = r.json() if r.status_code == 200 else []
    except Exception:
        clientes = []
    filas = ''.join(
        f"<a class='cl' href='/admin/covers/{_esc(c['slug'])}?initial=covers'>"
        f"<span class='nm'>{_esc(c['nombre'])}</span>"
        f"<span class='rv'>{c['reservas']} reserva{'s' if c['reservas'] != 1 else ''}</span>"
        f"<span class='go'>→</span></a>"
        for c in clientes
    ) or "<p style='color:#777;font-size:14px;'>No hay clientes en Covers todavía.</p>"
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Covers — Clientes</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
  body{{margin:0;background:#0B0B0B;color:#F5EFE6;font-family:'Poppins',sans-serif;min-height:100vh;padding:48px 24px;}}
  .wrap{{max-width:640px;margin:0 auto;}}
  .kicker{{font-size:10px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#E55420;margin-bottom:10px;}}
  h1{{font-weight:900;letter-spacing:-2px;font-size:clamp(34px,6vw,52px);margin:0 0 6px;}}
  .sub{{color:#9A9A9A;font-size:13px;margin-bottom:34px;}}
  .cl{{display:flex;align-items:center;gap:14px;padding:18px 4px;border-bottom:1px solid #242424;text-decoration:none;color:#F5EFE6;transition:background .15s;}}
  .cl:hover{{background:#141414;}}
  .nm{{flex:1;font-weight:700;font-size:16px;}}
  .rv{{color:#9A9A9A;font-size:12px;font-feature-settings:'tnum';}}
  .go{{color:#E55420;font-weight:900;}}
  .back{{display:inline-block;margin-bottom:26px;color:#9A9A9A;text-decoration:none;font-size:13px;}}
  .back:hover{{color:#F5EFE6;}}
</style></head><body><div class="wrap">
  <a class="back" href="/admin">← Volver al hub</a>
  <div class="kicker">Blend Covers</div>
  <h1>Clientes</h1>
  <div class="sub">Entra al panel de reservas de cualquier restaurante (vista del dueño).</div>
  {filas}
</div></body></html>'''


@app.route('/admin/covers/<slug>')
def admin_covers_panel(slug):
    if not _is_staff():
        return redirect('/login')
    # Nombre real del cliente (para el header del panel)
    nombre = slug
    try:
        r = http_requests.get(f'{COVERS_URL}/api/covers/clientes',
                              headers={'Authorization': f'Bearer {AUTH_SECRET}'}, timeout=8)
        for c in (r.json() if r.status_code == 200 else []):
            if c.get('slug') == slug:
                nombre = c.get('nombre') or slug
                break
    except Exception:
        pass
    # El proxy /api/covers/data usa session['covers_slug'] → el staff "mira como" este restaurante.
    session['covers_slug'] = slug
    token = generate_token(session['user'], session['role'])
    with open('cliente_v2.html', 'r') as f:
        html = f.read()
    sf_user = json.dumps({"username": session['user'], "name": nombre,
                          "role": "cliente", "token": token, "client_name": nombre})
    user_script = f"<script>\nconst SF_USER = {sf_user};\n</script>"
    return html.replace('</head>', user_script + '\n</head>')


@app.route('/api/covers/sentada', methods=['POST'])
def covers_sentada_proxy():
    if 'user' not in session:
        return {'error': 'unauthorized'}, 401
    body = request.get_json(silent=True) or {}
    try:
        r = http_requests.post(
            f'{COVERS_URL}/api/covers/sentada',
            json=body,
            headers={'Authorization': f'Bearer {AUTH_SECRET}', 'Content-Type': 'application/json'},
            timeout=8,
        )
        return (r.text, r.status_code, {'Content-Type': r.headers.get('Content-Type', 'application/json')})
    except Exception as e:
        return {'error': f'backend covers no disponible: {e}'}, 502

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
