from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from flask_mail import Mail, Message
import secrets
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bibliotecatomaslago@gmail.com'
app.config['MAIL_PASSWORD'] = 'dehursreirrhrhap'

mail = Mail(app)

# Función de conexión a PostgreSQL
def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=5432
    )

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            curso TEXT,
            correo TEXT,
            libro TEXT,
            tiempo_prestamo TEXT,
            fecha_prestamo TEXT,
            token TEXT,
            verificado INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS libros (
            id SERIAL PRIMARY KEY,
            titulo TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ✅ NUEVA FUNCIÓN PARA AGREGAR COLUMNA STOCK
def actualizar_tabla_libros():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE libros ADD COLUMN stock INTEGER DEFAULT 1;")
        conn.commit()
        print("Columna 'stock' añadida correctamente.")
    except psycopg2.errors.DuplicateColumn:
        print("La columna 'stock' ya existe.")
        conn.rollback()
    conn.close()

@app.route('/')
def index():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT titulo FROM libros ORDER BY titulo")
    libros = [libro[0] for libro in c.fetchall()]
    conn.close()
    return render_template('registro.html', libros=libros)

@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    curso = request.form['curso']
    correo = request.form['correo']
    libro = request.form['libro']
    tiempo = 14
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    token = secrets.token_urlsafe(16)

    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO registros (nombre, curso, correo, libro, tiempo_prestamo, fecha_prestamo, token) VALUES (%s, %s, %s, %s, %s, %s, %s)",
              (nombre, curso, correo, libro, tiempo, fecha, token))
    conn.commit()
    conn.close()

    msg = Message('Verifica tu préstamo de libro',
                  sender='bibliotecatomaslago@gmail.com',
                  recipients=[correo])
    link = f"https://biblioteca-web-mgmi.onrender.com/verificar/{token}"
    msg.body = f"Hola {nombre}, haz clic aquí para verificar tu préstamo: {link}"
    mail.send(msg)

    return "Te enviamos un correo para verificar tu préstamo."

@app.route('/verificar/<token>')
def verificar(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT verificado FROM registros WHERE token = %s", (token,))
    fila = c.fetchone()

    if fila is None:
        mensaje = "Token inválido."
    elif fila[0] == 1:
        mensaje = "El préstamo ya fue verificado anteriormente."
    else:
        c.execute("UPDATE registros SET verificado = 1 WHERE token = %s", (token,))
        conn.commit()
        mensaje = "¡Préstamo verificado correctamente! Gracias por confirmar."

    conn.close()
    return mensaje

@app.route('/admin')
def admin():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT nombre, curso, correo, libro, tiempo_prestamo, fecha_prestamo, verificado FROM registros")
    datos = c.fetchall()
    conn.close()
    return render_template('admin.html', registros=datos)

@app.route('/admin/libros', methods=['GET', 'POST'])
def admin_libros():
    conn = get_connection()
    c = conn.cursor()
    mensaje = ""

    if request.method == 'POST':
        if 'eliminar_id' in request.form:
            libro_id = request.form['eliminar_id']
            c.execute("DELETE FROM libros WHERE id = %s", (libro_id,))
            conn.commit()
            mensaje = "Libro eliminado correctamente."
        elif 'nuevo_libro' in request.form:
            nuevo_libro = request.form['nuevo_libro']
            try:
                c.execute("INSERT INTO libros (titulo) VALUES (%s)", (nuevo_libro,))
                conn.commit()
                mensaje = "Libro agregado correctamente."
            except psycopg2.IntegrityError:
                conn.rollback()
                mensaje = "El libro ya existe."

    termino_busqueda = request.args.get('buscar', '')
    if termino_busqueda:
        c.execute("SELECT id, titulo FROM libros WHERE titulo ILIKE %s ORDER BY titulo", ('%' + termino_busqueda + '%',))
    else:
        c.execute("SELECT id, titulo FROM libros ORDER BY titulo")

    libros = c.fetchall()
    conn.close()
    return render_template('admin_libros.html', libros=libros, mensaje=mensaje, buscar=termino_busqueda)

if __name__ == '__main__':
    init_db()
    from os import environ
    app.run(host='0.0.0.0', port=int(environ.get("PORT", 5000)), debug=True)
