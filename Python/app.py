import os
import json
import decimal
import base64
import datetime
from flask import Flask, redirect, url_for, session, request, render_template, abort, jsonify
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
from functools import wraps
import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash, check_password_hash

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI") 
PORT = os.environ.get("PORT")

AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

app = Flask(__name__)

def _init_db():
    conn = get_db_connection()
    if conn:
        try:
            ensure_pedido_schema(conn)
        finally:
            conn.close()
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key-change-me")

DB_CONFIG = {
    'host': os.getenv("DB_HOST", '127.0.0.1'),
    'port': 3306,
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'database': os.getenv("DB_NAME", 'mydb')
}

def get_db_connection():
    """Tenta conectar ao banco de dados e retorna a conexão."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MySQL: {err}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_info' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
ADMIN_EMAILS = {
    'atelierdigital@gmail.com',
}

def admin_required(f):
    """Permite acesso apenas para usuários logados cujo e-mail esteja em ADMIN_EMAILS."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_info' not in session:
            return abort(403)
        if session['user_info'].get('email') not in ADMIN_EMAILS:
            return abort(403)
        return f(*args, **kwargs)
    return wrapper

def get_google_auth():
    if CLIENT_ID is None or CLIENT_SECRET is None:
        raise Exception("As variáveis de ambiente GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET devem ser definidas.")
    
    return OAuth2Session(
        CLIENT_ID,
        scope=SCOPES,
        redirect_uri=REDIRECT_URI
    )

@app.route("/")
def index():
    """ROTA PRINCIPAL (Login): Se logado, vai para a home. Se não, mostra o login."""
    if 'user_info' in session:
        return redirect(url_for('home')) 
    return render_template('login.html') 

@app.route("/login")
def login():
    """ROTA DE INTEGRAÇÃO GOOGLE: Inicia o fluxo de OAuth."""
    google = get_google_auth()
    authorization_url, state = google.authorization_url(
        AUTH_BASE_URL,
        access_type="offline",
        prompt="select_account"
    )
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    """Rota que recebe a resposta do Google e finaliza o login."""
    if 'oauth_state' not in session or session['oauth_state'] != request.args.get('state'):
        return "Erro de segurança: Estado OAuth inválido.", 401

    google = get_google_auth()
    try:
        token = google.fetch_token(
            TOKEN_URL,
            client_secret=CLIENT_SECRET,
            authorization_response=request.url
        )
    except Exception as e:
        return f"Erro ao obter o token: {e}", 500

    session['oauth_token'] = token
    google_token_session = OAuth2Session(CLIENT_ID, token=token)
    userinfo_response = google_token_session.get(USERINFO_URL)
    user_info = userinfo_response.json()
    session['user_info'] = user_info
    
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    """Termina a sessão do usuário."""
    session.clear() 
    return redirect(url_for("index"))

@app.route("/cadastro", methods=["GET"])
def cadastro():
    """Exibe a página de cadastro."""
    return render_template('cadastro.html')

@app.route("/cadastro-traditional", methods=["POST"])
def cadastro_traditional():
    """Processa o formulário de cadastro tradicional e SALVA NO BANCO."""
    email = request.form.get('email')
    nome = request.form.get('nome')
    senha = request.form.get('senha')

    if not email or not nome or not senha:
        return "Erro: Todos os campos são obrigatórios.", 400

    senha_hash = generate_password_hash(senha)

    conn = get_db_connection()
    if conn is None:
        return "Erro: Não foi possível conectar ao banco de dados.", 500
    
    cursor = conn.cursor()

    create_q = (
        "CREATE TABLE IF NOT EXISTS cliente (\n"
        "  id INT AUTO_INCREMENT PRIMARY KEY,\n"
        "  nome VARCHAR(120),\n"
        "  nome_completo VARCHAR(120),\n"
        "  email VARCHAR(120) UNIQUE,\n"
        "  senha_hash VARCHAR(255),\n"
        "  cpf VARCHAR(20),\n"
        "  endereco VARCHAR(255),\n"
        "  celular VARCHAR(20)\n"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    cursor.execute(create_q)

    query = "INSERT INTO cliente (nome, nome_completo, email, senha_hash) VALUES (%s, %s, %s, %s)"
    
    try:
        cursor.execute(query, (nome, nome, email, senha_hash))
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
             return "Erro: Este email já está cadastrado.", 409
        return f"Erro ao cadastrar: {err}", 500
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))


@app.route("/login-traditional", methods=["POST"])
def login_traditional():
    """Processa o formulário de login tradicional (email/senha)."""
    email = request.form.get('email')
    senha = request.form.get('senha')
    
    conn = get_db_connection()
    if conn is None:
        return "Erro: Falha no banco de dados.", 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("ALTER TABLE cliente ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY")
    except mysql.connector.Error:
        pass
    query = "SELECT * FROM cliente WHERE email = %s"
    
    try:
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user['senha_hash'], senha):
            session['user_info'] = {
                'id': user.get('id'),
                'name': user['nome'],
                'email': user['email'],
                'cpf': user.get('cpf'),
                'endereco': user.get('endereco'),
                'celular': user.get('celular')
            }
            if user['email'] in ADMIN_EMAILS:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        else:
            return "Email ou senha inválidos.", 401
            
    except Exception as e:
        return f"Erro no login: {e}", 500
    finally:
        cursor.close()
        conn.close()

@app.route("/home")
@login_required
def home():
    """Página principal para usuários logados"""
    user = session['user_info']
    cart = session.get('cart', [])
    return render_template("index_simplificado.html", user=user, cart=cart)

@app.route('/menu')
def menu_public():
    """Cardápio acessível sem login (visitante)."""
    user = session.get('user_info')
    cart = session.get('cart', []) if user else []
    return render_template("index_simplificado.html", user=user, cart=cart)
    return render_template("index_simplificado.html", user=user, cart=cart)

def ensure_produto_schema(conn):
    """Cria/ajusta tabela 'produtos'."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS produtos (
              id INT AUTO_INCREMENT PRIMARY KEY,
              nome VARCHAR(120),
              descricao TEXT,
              valor DECIMAL(10,2),
              categoria VARCHAR(120),
              foto VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute("SHOW COLUMNS FROM produtos LIKE 'preco'")
        has_preco = cur.fetchone() is not None
        cur.execute("SHOW COLUMNS FROM produtos LIKE 'valor'")
        has_valor = cur.fetchone() is not None
        if has_preco and not has_valor:
            cur.execute("ALTER TABLE produtos CHANGE preco valor DECIMAL(10,2)")
        elif has_preco and has_valor:
            cur.execute("ALTER TABLE produtos DROP COLUMN preco")
        required = {
            'nome': 'VARCHAR(120)',
            'descricao': 'TEXT',
            'valor': 'DECIMAL(10,2)',
            'categoria': 'VARCHAR(120)',
            'foto': 'MEDIUMTEXT'
        }
    
        cur.execute("SHOW KEYS FROM produtos WHERE Key_name='PRIMARY'")
        pk_row = cur.fetchone()
        pk_field = pk_row[4] if pk_row else None

    
        cur.execute("SHOW COLUMNS FROM produtos WHERE Extra LIKE '%auto_increment%'")
        auto_row = cur.fetchone()

        cur.execute("SHOW COLUMNS FROM produtos LIKE 'id_produtos'")
        legacy_row = cur.fetchone()
        if auto_row is None:
            if legacy_row:
                extra = legacy_row[5]
                if pk_field == 'id_produtos':
                    if 'auto_increment' not in extra:
                        cur.execute("ALTER TABLE produtos MODIFY id_produtos INT AUTO_INCREMENT")
                elif pk_field is None:
                    try:
                        cur.execute("ALTER TABLE produtos MODIFY id_produtos INT AUTO_INCREMENT PRIMARY KEY")
                    except mysql.connector.Error as err:
                        if err.errno == errorcode.ER_MULTIPLE_PRI_KEY:
                            cur.execute("ALTER TABLE produtos MODIFY id_produtos INT AUTO_INCREMENT")
                        else:
                            raise
            else:
                cur.execute("SHOW COLUMNS FROM produtos LIKE 'id'")
                if cur.fetchone() is None:
                    cur.execute("ALTER TABLE produtos ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST")

        cur.execute("SHOW KEYS FROM produtos WHERE Key_name='PRIMARY'")
        if cur.fetchone() is None:
            cur.execute("SHOW COLUMNS FROM produtos WHERE Extra LIKE '%auto_increment%'")
            row = cur.fetchone()
            if row:
                fld = row[0]
                try:
                    cur.execute(f"ALTER TABLE produtos ADD PRIMARY KEY (`{fld}`)")
                except mysql.connector.Error as err:
                    if err.errno != errorcode.ER_MULTIPLE_PRI_KEY:
                        raise
        
        for col, ddl in required.items():
            cur.execute("SHOW COLUMNS FROM produtos LIKE %s", (col,))
            info = cur.fetchone()
            if info is None:
                cur.execute(f"ALTER TABLE produtos ADD COLUMN {col} {ddl}")
            else:
                if col=='foto' and 'varchar' in info[1].lower():
                    cur.execute("ALTER TABLE produtos MODIFY foto MEDIUMTEXT")
        conn.commit()
    finally:
        cur.close()
def ensure_pedido_schema(conn):
    """
    Garante que a tabela `pedido` exista e contenha as colunas usadas
    pelo código (id_pedido / id, cliente_nome etc.).
    Executa apenas comandos idempotentes.
    """
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pedido (
          id_pedido INT AUTO_INCREMENT PRIMARY KEY,
          user_email    VARCHAR(255),
          cliente_nome  VARCHAR(120),
          itens         LONGTEXT,
          total         DECIMAL(10,2),
          metodo        VARCHAR(20),
          criado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("SHOW COLUMNS FROM pedido LIKE 'id'")
    if cur.fetchone():
        cur.execute("SHOW COLUMNS FROM pedido LIKE 'id_pedido'")
        if not cur.fetchone():
            cur.execute(
              "ALTER TABLE pedido CHANGE id id_pedido INT AUTO_INCREMENT PRIMARY KEY")
    cur.execute("SHOW COLUMNS FROM pedido LIKE 'cliente_nome'")
    if cur.fetchone() is None:
        cur.execute("ALTER TABLE pedido ADD COLUMN cliente_nome VARCHAR(120) AFTER user_email")
    cur.execute("SHOW COLUMNS FROM pedido LIKE 'id_pedido'")
    if cur.fetchone() is None:
        cur.execute("SHOW COLUMNS FROM pedido LIKE 'id'")
        if cur.fetchone():
            cur.execute("ALTER TABLE pedido ADD COLUMN id_pedido INT")
            cur.execute("UPDATE pedido SET id_pedido = id")
        else:
            cur.execute("ALTER TABLE pedido ADD COLUMN id_pedido INT AUTO_INCREMENT PRIMARY KEY FIRST")
    try:
        cur.execute("ALTER TABLE pedido MODIFY id_pedido INT AUTO_INCREMENT PRIMARY KEY")
    except mysql.connector.Error as err:
        pass

    cur.execute("SHOW COLUMNS FROM pedido LIKE 'total'")
    info = cur.fetchone()
    if info and info[2] == 'NO':
        cur.execute("ALTER TABLE pedido MODIFY total DECIMAL(10,2) NULL")
    conn.commit()
    cur.close()
@app.route('/api/produtos', methods=['GET'])
def api_produtos():
    """Lista todos produtos."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({'erro':'db'}),500
    ensure_produto_schema(conn)
    cur = conn.cursor(dictionary=True)
    cur.execute('SELECT * FROM produtos')
    rows = cur.fetchall()
    for r in rows:
        if 'id' not in r:
            for pk_alt in ('id_produtos','id_produto','produto_id'):
                if pk_alt in r:
                    r['id'] = r[pk_alt]
                    break
        for k, v in r.items():
            if isinstance(v, decimal.Decimal):
                r[k] = float(v)
            elif isinstance(v, (bytes, bytearray)):
                r[k] = base64.b64encode(v).decode('ascii')
            elif isinstance(v, (datetime.date, datetime.datetime)):
                r[k] = v.isoformat()
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/produtos/add', methods=['POST'])
@login_required
@admin_required
def api_produto_add():
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    desc = (data.get('descricao') or '').strip()
    raw_val = str(data.get('valor', '')).replace(',', '.').strip()
    try:
        valor = float(raw_val)
    except ValueError:
        return jsonify({'erro': 'valor invalido'}), 400
    cat = (data.get('categoria') or '').strip()
    foto = data.get('foto')
    if not nome:
        return jsonify({'erro':'nome vazio'}),400
    conn=get_db_connection(); ensure_produto_schema(conn)
    cur=conn.cursor()
    cur.execute('INSERT INTO produtos (nome,descricao,valor,categoria,foto) VALUES (%s,%s,%s,%s,%s)',(nome,desc,valor,cat,foto))
    pid=cur.lastrowid; conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'id':pid})

@app.route('/api/produtos/<int:pid>', methods=['PUT'])
@login_required
@admin_required
def api_produto_update(pid):
    data=request.get_json() or {}
    cols={k:v for k,v in data.items() if k in {'nome','descricao','valor','categoria','foto'}}
    if not cols:
        return jsonify({'erro':'payload vazio'}),400
    conn=get_db_connection(); ensure_produto_schema(conn)
    cur=conn.cursor(); set_clause=', '.join(f"{k}=%s" for k in cols)
    # Descobre qual coluna é o PRIMARY KEY
    cur.execute("SHOW KEYS FROM produtos WHERE Key_name='PRIMARY'")
    pk_row = cur.fetchone()
    pk_col = pk_row[4] if pk_row else 'id'
    cur.execute(f'UPDATE produtos SET {set_clause} WHERE {pk_col}=%s', tuple(cols.values())+(pid,))
    conn.commit(); cur.close(); conn.close(); return jsonify({'ok':True})

@app.route('/api/produtos/<int:pid>', methods=['DELETE'])
@login_required
@admin_required
def api_produto_delete(pid):
    conn=get_db_connection(); ensure_produto_schema(conn)
    cur=conn.cursor();
    cur.execute("SHOW KEYS FROM produtos WHERE Key_name='PRIMARY'")
    pk_row = cur.fetchone()
    pk_col = pk_row[4] if pk_row else 'id'
    cur.execute(f'DELETE FROM produtos WHERE {pk_col}=%s',(pid,));
    conn.commit(); cur.close(); conn.close(); return jsonify({'ok':True})

def ensure_pedido_schema(conn):
    """Garante que a tabela e as colunas mínimas de 'pedido' existam."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido (
              id INT AUTO_INCREMENT PRIMARY KEY,
              user_email VARCHAR(255),
              itens LONGTEXT,
              total DECIMAL(10,2),
              metodo VARCHAR(20),
              entrega VARCHAR(20),
              status  VARCHAR(20) DEFAULT 'Pendente',
              criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cur.execute("SHOW COLUMNS FROM pedido LIKE 'valor_total'")
        has_vtotal = cur.fetchone() is not None
        cur.execute("SHOW COLUMNS FROM pedido LIKE 'total'")
        has_total = cur.fetchone() is not None
        if has_vtotal and not has_total:
            cur.execute("ALTER TABLE pedido CHANGE valor_total total DECIMAL(10,2)")

        needed_cols = {
            'user_email': 'VARCHAR(255)',
            'itens': 'LONGTEXT',
            'total': 'DECIMAL(10,2)',
            'metodo': 'VARCHAR(20)',
            'entrega': 'VARCHAR(20)',
            'status':  "VARCHAR(20) DEFAULT 'Pendente'",
            'criado_em': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        for col, ddl in needed_cols.items():
            cur.execute("SHOW COLUMNS FROM pedido LIKE %s", (col,))
            if cur.fetchone() is None:
                try:
                    cur.execute(f"ALTER TABLE pedido ADD COLUMN {col} {ddl}")
                except mysql.connector.Error as err:
                    if err.errno == 1060:
                        pass
                    else:
                        print(f'Erro ao adicionar coluna {col}: {err.msg}')
        conn.commit()
    except mysql.connector.Error as err:
        print(f"ensure_pedido_schema error: {err}")
    finally:
        cur.close()


@app.route("/perfil")
@login_required
def perfil():
    """Exibe a página de perfil do usuário, sempre buscando dados completos no BD."""
    user = session['user_info']
    email = user.get('email')
    if email:
        conn = get_db_connection()
        if conn:
            ensure_pedido_schema(conn)
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute("SELECT cpf, endereco, celular FROM cliente WHERE email=%s", (email,))
                row = cur.fetchone()
                if row:
                    user.update({k: row[k] for k in ['cpf','endereco','celular'] if row.get(k) is not None})
                    session['user_info'] = user
            finally:
                cur.close()
                conn.close()
    pedidos = []
    email = user.get('email')
    if email:
        conn = get_db_connection()
        if conn:
            ensure_pedido_schema(conn)
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute("SHOW COLUMNS FROM pedido LIKE 'forma_pagamento'")
                has_forma = cur.fetchone() is not None
                metodo_col = 'forma_pagamento' if has_forma else 'metodo'
                cur.execute("SHOW COLUMNS FROM pedido LIKE 'itens'")
                has_itens = cur.fetchone() is not None
                select_cols = f"itens, COALESCE(total,0) AS total, {metodo_col} AS metodo, COALESCE(entrega,'Retirada') AS entrega, criado_em" if has_itens else f"COALESCE(total,0) AS total, {metodo_col} AS metodo, COALESCE(entrega,'Retirada') AS entrega, criado_em"
                cur.execute(f"SELECT {select_cols} FROM pedido WHERE user_email=%s ORDER BY criado_em DESC", (email,))
                rows = cur.fetchall()
                import json
                for r in rows:
                    try:
                        r['itens_list'] = json.loads(r.get('itens', '[]')) if r.get('itens') else []
                    except Exception:
                        r['itens_list'] = []
                    if not r.get('total') and r['itens_list']:
                        r['total'] = sum(float(it.get('price',0))*int(it.get('qty',1)) for it in r['itens_list'])
                pedidos = rows
            finally:
                cur.close(); conn.close()
    return render_template('perfil.html', user=user, pedidos=pedidos)
@app.route("/perfil/update", methods=["POST"])
@login_required
def perfil_update():
    data = request.get_json() or {}
    nome = data.get("name", "").strip()
    cpf = data.get("cpf", "").strip()
    endereco = data.get("address", "").strip()
    celular = data.get("phone", "").strip()

    if not nome:
        return jsonify({"erro": "Nome é obrigatório."}), 400

    user_session = session.get("user_info", {})
    email = user_session.get("email")
    if not email:
        return jsonify({"erro": "Sessão inválida."}), 401

    conn = get_db_connection()
    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco."}), 500

    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS cliente (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(120),
            nome_completo VARCHAR(120),
            email VARCHAR(120) UNIQUE,
            senha_hash VARCHAR(255),
            cpf VARCHAR(20),
            endereco VARCHAR(255),
            celular VARCHAR(20)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    for col, tipo in {"nome": "VARCHAR(120)", "nome_completo": "VARCHAR(120)", "cpf": "VARCHAR(20)", "endereco": "VARCHAR(255)", "celular": "VARCHAR(20)"}.items():
        try:
            cursor.execute(f"ALTER TABLE cliente ADD COLUMN {col} {tipo}")
        except mysql.connector.Error:
            pass

    try:
        cursor.execute(
            "UPDATE cliente SET nome=%s, nome_completo=%s, cpf=%s, endereco=%s, celular=%s WHERE email=%s",
            (nome, nome, cpf, endereco, celular, email)
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO cliente (nome, nome_completo, email, cpf, endereco, celular) VALUES (%s,%s,%s,%s,%s,%s)",
                (nome, nome, email, cpf, endereco, celular)
            )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"erro": f"Erro ao salvar: {err.msg}"}), 500
    finally:
        cursor.close(); conn.close()

    user_session.update({"name": nome, "cpf": cpf, "endereco": endereco, "celular": celular})
    session["user_info"] = user_session

    return jsonify({"msg": "Perfil atualizado com sucesso."})

@app.route("/cart/add", methods=["POST"])
@login_required
def cart_add():
    """Adiciona ou incrementa item no carrinho salvo em session."""
    data = request.get_json() or {}
    name = data.get("name")
    price = float(data.get("price", 0))
    qty   = int(data.get("qty", 1))
    if not name:
        return jsonify({"erro": "nome vazio"}), 400

    cart = session.get('cart', [])
    for item in cart:
        if item['name'] == name:
            item['qty'] += qty
            break
    else:
        cart.append({"name": name, "price": price, "qty": qty})
    session['cart'] = cart
    return jsonify({"count": sum(i['qty'] for i in cart)})

@app.route("/cart/update", methods=["POST"])
@login_required
def cart_update():
    data = request.get_json() or {}
    name = data.get("name")
    delta = int(data.get("delta", 0))
    cart = session.get('cart', [])
    for item in cart:
        if item['name'] == name:
            item['qty'] += delta
            if item['qty'] <= 0:
                cart.remove(item)
            break
    session['cart'] = cart
    return jsonify({"count": sum(i['qty'] for i in cart)})
@app.route("/cart/remove", methods=["POST"])
@login_required
def cart_remove():
    data = request.get_json() or {}
    name = data.get("name")
    cart = [i for i in session.get('cart', []) if i['name'] != name]
    session['cart'] = cart
    return jsonify({"count": sum(i['qty'] for i in cart)})

@app.route("/cart/items")
@login_required
def cart_items():
    return jsonify(session.get('cart', []))

@app.route("/carrinho")
@login_required
def carrinho():
    """Exibe o carrinho de compras."""
    user = session['user_info']
    cart = session.get('cart', [])
    if cart:
        names = tuple({it['name'] for it in cart})
        conn = get_db_connection()
        if conn and names:
            cur = conn.cursor(dictionary=True)
            fmt = ','.join(['%s'] * len(names))
            cur.execute(f"SELECT nome,foto FROM produtos WHERE nome IN ({fmt})", names)
            fotos = {r['nome']: r['foto'] for r in cur.fetchall()}
            cur.close(); conn.close()
            for it in cart:
                it['image'] = fotos.get(it['name'])
    subtotal = sum(item['price'] * item['qty'] for item in cart)
    return render_template('carrinho_simplificado.html', user=user, cart=cart, subtotal=subtotal)

@app.route("/pagamento")
@login_required
def pagamento():
    """Exibe a página de pagamento. Se usuário solicitar entrega mas não possuir endereço, redireciona para perfil."""
    user = session['user_info']
    cart = session.get('cart', [])
    return render_template('pagamento.html', user=user, cart=cart)

@app.route('/pagamento/confirm', methods=['POST'])
@login_required
def pagamento_confirm():
    """Recebe JSON {method,total} e salva o pedido no BD."""
    data = request.get_json() or {}
    metodo_slug = (data.get('method') or '').lower()
    metodo_map = {
        'credito':'Cartão de Crédito',
        'debito':'Cartão de Débito',
        'pix':'PIX',
        'dinheiro':'Dinheiro'
    }
    metodo = metodo_map.get(metodo_slug, metodo_slug.capitalize() if metodo_slug else None)
    entrega = (data.get('delivery') or 'Retirada').strip()
    if entrega.lower() != 'retirada' and not user.get('endereco'):
        return jsonify({'erro': 'sem_endereco'}), 400
    cart   = session.get('cart', [])
    try:
        total = float(str(data.get('total', 0)).replace(',', '.'))
    except ValueError:
        total = 0.0
    if (not total) and cart:
        total = sum(float(it['price']) * int(it['qty']) for it in cart)
    user   = session['user_info']

    conn = get_db_connection()
    if conn is None:
        return jsonify({'erro':'db fail'}), 500
    ensure_pedido_schema(conn)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pedido (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_email VARCHAR(255),
          itens LONGTEXT,
          total DECIMAL(10,2),
          metodo VARCHAR(20),
          entrega VARCHAR(20),
          status  VARCHAR(20) DEFAULT 'Pendente',
          criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print('[DEBUG pedido]', {'user':user.get('email'), 'total': total, 'metodo': metodo, 'items': cart}, flush=True)
    cur_meta = conn.cursor()
    cur_meta.execute("SHOW COLUMNS FROM pedido LIKE 'valor_total'")
    has_vtotal = cur_meta.fetchone() is not None
    cur_meta.execute("SHOW COLUMNS FROM pedido LIKE 'forma_pagamento'")
    has_forma = cur_meta.fetchone() is not None
    cur_meta.close()

    col_total  = 'valor_total' if has_vtotal else 'total'
    col_metodo = 'forma_pagamento' if has_forma else 'metodo'

    sql = f"INSERT INTO pedido (user_email,itens,{col_total},{col_metodo},entrega,status) VALUES (%s,%s,%s,%s,%s,%s)"
    cur.execute(sql, (user.get('email'), json.dumps(cart), total, metodo, entrega, 'Confirmado'))
    order_id = cur.lastrowid
    conn.commit()
    cur.close(); conn.close()
    session.pop('cart', None)
    return jsonify({'ok': True, 'id': order_id})

@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    user = session['user_info']
    conn = get_db_connection(); vendas_mes=0; faturamento_mes=0; renda_total=0
    if conn:
        ensure_pedido_schema(conn)
        cur = conn.cursor(dictionary=True)
        import datetime, decimal
        first_day = datetime.date.today().replace(day=1)
        cur.execute("SHOW COLUMNS FROM pedido LIKE 'valor_total'")
        has_vtotal = cur.fetchone() is not None
        col_total = 'valor_total' if has_vtotal else 'total'
        cur.execute(f"SELECT COALESCE({col_total},0) AS t FROM pedido WHERE criado_em >= %s", (first_day,))
        rows = cur.fetchall(); vendas_mes=len(rows)
        faturamento_mes = 7500.00
        cur2 = conn.cursor()
        cur2.execute(f"SELECT COALESCE(SUM({col_total}),0) FROM pedido")
        row = cur2.fetchone(); renda_total = float(row[0]) if row and row[0] is not None else 0
        cur_not = conn.cursor(dictionary=True)
        cur_not.execute("SELECT criado_em FROM pedido ORDER BY criado_em DESC LIMIT 5")
        notificacoes = cur_not.fetchall(); cur_not.close()
        cur2.close(); cur.close(); conn.close()
    return render_template('admin-dashboard.html', user=user, vendas_mes=vendas_mes, faturamento_mes=faturamento_mes, renda_atual=renda_total, notificacoes=notificacoes)
@app.route("/admin/cardapio")
@login_required
@admin_required
def admin_cardapio():
    """Exibe a página de admin do cardápio, já com os produtos do BD."""
    user = session['user_info']
    produtos = []

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM produtos")
            produtos = cursor.fetchall()
        except Exception as e:
            print(f"Erro ao buscar produtos para admin: {e}")
        finally:
            cursor.close()
            conn.close()
    return render_template('admin-cardapio.html', user=user, produtos=produtos)

@app.route("/admin/pedidos")
@login_required
@admin_required
@login_required
def admin_pedidos():
    user = session['user_info']
    pedidos=[]
    conn=get_db_connection()
    if conn:
        ensure_pedido_schema(conn)
        cur_cols = conn.cursor()
        cur_cols.execute("SHOW COLUMNS FROM pedido")
        cols = [row[0] for row in cur_cols.fetchall()]
        cur_cols.close()
        id_col = 'id_pedido' if 'id_pedido' in cols else 'id'
        cur = conn.cursor(dictionary=True)
        query = f"""
            SELECT p.{id_col} AS id,
                   p.user_email,
                   COALESCE(c.nome, p.user_email) AS cliente,
                   p.itens,
                   COALESCE(p.total,0) AS total,
                   p.metodo,
                   COALESCE(c.endereco, p.entrega, 'Retirada') AS entrega,
                   p.status,
                   c.celular AS telefone,
                   c.celular AS telefone,
                   p.criado_em
              FROM pedido p
              LEFT JOIN cliente c ON c.email = p.user_email
              ORDER BY p.criado_em DESC
        """
        cur.execute(query)
        rows = cur.fetchall(); cur.close(); conn.close()
        import json
        for r in rows:
            try:
                itens=json.loads(r['itens'])
            except Exception:
                itens=[]
            r['itens_str']=', '.join(f"{it['qty']}x {it['name']}" for it in itens)[:60]
            if not r['total']:
                r['total']=sum(it['price']*it['qty'] for it in itens)
            r['cliente']=r.get('cliente') or r['user_email']
            pedidos.append(r)
    return render_template('admin-pedidos.html', user=user, pedidos=pedidos)

@app.route('/api/combos/add', methods=['POST'])
@login_required
@admin_required
def api_combo_add():
    data = request.get_json() or {}
    nome = (data.get('name') or '').strip()
    itens = data.get('items') or []
    try:
        valor = float(data.get('price'))
    except (TypeError, ValueError):
        return jsonify({'erro':'preço inválido'}),400
    if not nome or not itens:
        return jsonify({'erro':'nome/itens vazios'}),400
    desc = '\n'.join(f"{it['qty']}x {it['name']}" for it in itens)
    foto = data.get('foto')
    conn = get_db_connection(); ensure_produto_schema(conn)
    cur = conn.cursor()
    if foto:
        cur.execute('INSERT INTO produtos (nome,descricao,valor,categoria,foto) VALUES (%s,%s,%s,%s,%s)', (nome, desc, valor, 'Combos', foto))
    else:
        cur.execute('INSERT INTO produtos (nome,descricao,valor,categoria) VALUES (%s,%s,%s,%s)', (nome, desc, valor, 'Combos'))
    pid = cur.lastrowid; conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'id':pid})

@app.route('/api/pedido/<int:pid>/status', methods=['PUT'])
@login_required
@admin_required
def api_pedido_update_status(pid):
    data = request.get_json() or {}
    status = (data.get('status') or '').capitalize()
    if status not in {'Pendente','Confirmado','Preparando','Pronto','Entregue','Cancelado'}:
        return jsonify({'erro':'status invalido'}),400
    conn = get_db_connection(); ensure_pedido_schema(conn)
    cur = conn.cursor()
    try:
        cur.execute("SHOW COLUMNS FROM pedido LIKE 'id_pedido'")
        has_id_pedido = cur.fetchone() is not None
        id_col = 'id_pedido' if has_id_pedido else 'id'
        cur.execute(f"UPDATE pedido SET status=%s WHERE {id_col}=%s", (status, pid))
        conn.commit()
        return jsonify({'ok':True})
    finally:
        cur.close(); conn.close()
    ensure_pedido_schema(conn)
    cur_cols = conn.cursor()
    cur_cols.execute("SHOW COLUMNS FROM pedido")
    cols = [row[0] for row in cur_cols.fetchall()]
    cur_cols.close()
    id_col = 'id_pedido' if 'id_pedido' in cols else 'id'

    cur = conn.cursor(dictionary=True)
    query = f"""
        SELECT p.{id_col} AS id,
               p.user_email,
               COALESCE(c.nome, p.user_email) AS cliente,
               p.itens,
               COALESCE(p.total,0) AS total,
               p.metodo,
               c.celular AS telefone,
               p.criado_em,
               COALESCE(c.endereco, p.entrega, 'Retirada') AS entrega,
               c.celular AS telefone,
               p.criado_em
          FROM pedido p
          LEFT JOIN cliente c ON c.email = p.user_email
          ORDER BY p.criado_em DESC
    """
    cur.execute(query)
    rows = cur.fetchall(); cur.close(); conn.close()
    serial = []
    for r in rows:
        try:
            itens = json.loads(r.get('itens') or '[]')
        except Exception:
            itens = []
        r['itens_list'] = itens
        r['itens_str']  = ', '.join(f"{it['qty']}x {it['name']}" for it in itens)
        if (not r.get('total')) and itens:
            try:
                r['total'] = sum(float(it.get('price',0))*int(it.get('qty',1)) for it in itens)
            except Exception:
                pass
        if isinstance(r['total'], decimal.Decimal):
            r['total'] = float(r['total'])
        if isinstance(r['criado_em'], (datetime.date, datetime.datetime)):
            r['criado_em'] = r['criado_em'].isoformat()
        serial.append(r)
    return jsonify(serial)
if __name__ == "__main__":
    if PORT is None:
        print("A variável PORT não está definida no .env. Usando a porta 8000 por padrão.")
        port_num = 8000
    else:
        port_num = int(PORT)
        
    app.run(host="0.0.0.0", port=port_num, debug=True)