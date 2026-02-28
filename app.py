import os
import json
import uuid
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://clinicapiresmed-gif.github.io"}})

# Configurações de Pastas e Arquivos
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_USERS = 'users.json'
DB_POSTS = 'posts.json'

# --- CONFIGURAÇÃO DE E-MAIL CORRIGIDA (Para Outlook/Hotmail) ---
SMTP_SERVER = "smtp.gmail.com" 
SMTP_PORT = 587
SMTP_EMAIL = "clinicapiresmed@ogmail.com"
SMTP_PASSWORD = "pqnk aaog rpwy lthr" # Certifique-se que esta senha está correta

# --- Funções Auxiliares ---
def load_json(filename, default_val):
    if not os.path.exists(filename):
        return default_val
    with open(filename, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return default_val

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# Criar usuário admin padrão
users = load_json(DB_USERS, {})
if not users:
    users['admin@clinicapires.com.br'] = {
        'password': generate_password_hash('senha123'),
        'recovery_token': None
    }
    save_json(DB_USERS, users)

# --- ROTAS ---

@app.route('/')
def home():
    return render_template('clinicapires.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ROTA DE CADASTRO CORRIGIDA
@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    users = load_json(DB_USERS, {})
    
    if not email or not password:
        return jsonify({"success": False, "message": "Preencha todos os campos!"}), 400

    if email in users:
        return jsonify({"success": False, "message": "E-mail já cadastrado!"}), 400
    
    # Agora dentro da função e indentado corretamente
    users[email] = {
        'password': generate_password_hash(password),
        'recovery_token': None
    }
    save_json(DB_USERS, users)
    return jsonify({"success": True, "message": "Cadastro realizado com sucesso!"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    users = load_json(DB_USERS, {})
    
    if email in users and check_password_hash(users[email]['password'], password):
        token = str(uuid.uuid4())
        users[email]['token'] = token
        save_json(DB_USERS, users)
        return jsonify({"success": True, "token": token, "email": email})
    return jsonify({"success": False, "message": "Credenciais inválidas"}), 401

@app.route('/api/esqueci-senha', methods=['POST'])
def esqueci_senha():
    email = request.json.get('email')
    users = load_json(DB_USERS, {})
    
    if email in users:
        token = str(uuid.uuid4())[:8]
        users[email]['recovery_token'] = token
        save_json(DB_USERS, users)
        
        try:
            msg = EmailMessage()
            msg.set_content(f"Seu código de recuperação é: {token}")
            msg['Subject'] = "Recuperação de Senha - Clínica Pires"
            msg['From'] = SMTP_EMAIL
            msg['To'] = email
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            return jsonify({"success": True, "message": "E-mail enviado!"})
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro no e-mail: {str(e)}"}), 500
            
    return jsonify({"success": False, "message": "E-mail não encontrado."}), 404

@app.route('/api/redefinir-senha', methods=['POST'])
def redefinir_senha():
    data = request.json
    email = data.get('email')
    token = data.get('token')
    nova_senha = data.get('nova_senha')
    users = load_json(DB_USERS, {})
    
    if email in users and users[email].get('recovery_token') == token:
        users[email]['password'] = generate_password_hash(nova_senha)
        users[email]['recovery_token'] = None
        save_json(DB_USERS, users)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Token inválido"}), 400

@app.route('/api/posts', methods=['GET', 'POST'])
def manage_posts():
    if request.method == 'GET':
        posts = load_json(DB_POSTS, [])
        return jsonify(posts)
        
    if request.method == 'POST':
        token = request.headers.get('Authorization')
        users = load_json(DB_USERS, {})
        is_authenticated = any(u.get('token') == token for u in users.values())
        
        if not is_authenticated:
            return jsonify({"success": False, "message": "Não autorizado"}), 401

        texto = request.form.get('texto', '')
        file = request.files.get('file')
        file_url = None
        file_type = None

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_url = f"/uploads/{filename}"
            file_type = "video" if filename.lower().endswith(('.mp4', '.webm')) else "image"

        posts = load_json(DB_POSTS, [])
        new_post = {"id": str(uuid.uuid4()), "texto": texto, "file_url": file_url, "file_type": file_type}
        posts.insert(0, new_post)
        save_json(DB_POSTS, posts)
        return jsonify({"success": True, "post": new_post})

if __name__ == '__main__':
    app.run()


