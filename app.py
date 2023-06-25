from flask import Flask, render_template, request, redirect, session
import secrets
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
current_year = datetime.now().year

# Configuración de la base de datos
client = MongoClient('mongodb://localhost:27017')
db = client['Usuarios']
collection = db['users']


def is_admin():
    if 'username' in session:
        username = session['username']
        user = collection.find_one({'usuarios': {'$elemMatch': {'username': username}}})
        if user:
            for u in user['usuarios']:
                if u['username'] == username:
                    return u['rank'] == 'admin'
    return False

@app.route('/eliminar_usuario', methods=['GET','POST'])
def eliminar_archivos():
    if not is_admin():
        return redirect('/')

    usuarios_eliminar = request.form.getlist('usuarios_eliminar')

    # Eliminar usuarios seleccionados
    usuarios_eliminados = []
    for usuario in usuarios_eliminar:
        if usuario != 'admin':
            # Eliminar usuario de la base de datos
            collection.update_one({}, {'$pull': {'usuarios': {'username': usuario}}})
            usuarios_eliminados.append(usuario)

    mensaje = None
    if usuarios_eliminados:
        mensaje = "Los siguientes usuarios han sido eliminados exitosamente: {}".format(", ".join(usuarios_eliminados))

    usuarios = get_usuarios()
    return render_template('pages/eliminar_usuario.html', usuarios=usuarios, mensaje=mensaje)


def get_usuarios():
    usuarios = []
    users = collection.find({})
    for user in users:
        for usuario in user['usuarios']:
            usuarios.append(usuario['username'])
    return usuarios



@app.route('/crear_usuario', methods=['GET', 'POST'])

def crear_usuario():
    if not is_admin():
        return render_template('pages/crear_usuario.html', error_message='No tienes acceso para crear usuarios')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rank = request.form['rank']

        # Verificar si el usuario ya existe en la base de datos
        existing_user = collection.find_one({'usuarios': {'$elemMatch': {'username': username}}})
        if existing_user:
            return render_template('pages/crear_usuario.html', error_message='El usuario ya existe')

        # Crear el nuevo usuario
        new_user = {
            'username': username,
            'password': password,
            'rank': rank
        }

        # Agregar el nuevo usuario a la base de datos
        collection.insert_one({'usuarios': [new_user]})

        return render_template('pages/crear_usuario.html', success_message='Usuario creado exitosamente')

    return render_template('pages/crear_usuario.html', error_message=None, success_message=None)

@app.route('/gestor_usuarios', methods=['GET', 'POST'])
def gestor_usuarios():
    if not is_admin():
        return redirect('/')

    if request.method == 'POST':
        if 'crear_usuario' in request.form:
            return redirect('/crear_usuario')
        elif 'eliminar_usuario' in request.form:
            return redirect('/eliminar_usuario')

    return render_template('pages/gestor_usuarios.html')

def get_rank(username):
    user = collection.find_one({'usuarios': {'$elemMatch': {'username': username}}})
    if user:
        for u in user['usuarios']:
            if u['username'] == username:
                return u['rank']
    return None


@app.context_processor
def inject_current_user():
    if 'username' in session:
        username = session['username']
        rank = get_rank(username)
    else:
        username = None
        rank = None
    return {'username': username, 'rank': rank, 'current_year': current_year}


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = collection.find_one({'usuarios': {'$elemMatch': {'username': username, 'password': password}}})

        if user:
            session['authenticated'] = True
            session['username'] = username
            return redirect('/inicio')
        else:
            error_message = 'Credenciales incorrectas'

    return render_template('pages/login.html', error_message=error_message)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/inicio')
def index():
    if not session.get('authenticated'):
        return redirect('/login')
    return render_template('pages/index.html')


if __name__ == '__main__':
    app.run(debug=True)