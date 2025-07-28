from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
from flask_mail import Mail, Message
import secrets

app = Flask(__name__)

# Configuración Flask-Mail (ajusta con tus datos)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bibliotecatomaslago@gmail.com'       # Cambia aquí
app.config['MAIL_PASSWORD'] = 'dehursreirrhrhap'             # Cambia aquí

mail = Mail(app)

# Crear la base de datos con campos para verificación
def init_db():
    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        curso TEXT,
        correo TEXT,
        libro TEXT,
        tiempo_prestamo TEXT,
        fecha_prestamo TEXT,
        token TEXT,
        verificado INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('registro.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    curso = request.form['curso']  # Ahora tomamos el curso
    correo = request.form['correo']
    libro = request.form['libro']
    tiempo = request.form['tiempo']
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    token = secrets.token_urlsafe(16)

    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("INSERT INTO registros (nombre, curso, correo, libro, tiempo_prestamo, fecha_prestamo, token) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (nombre, curso, correo, libro, tiempo, fecha, token))
    conn.commit()
    conn.close()

    # Enviar email de verificación
    msg = Message('Verifica tu préstamo de libro',
                  sender='tucorreo@gmail.com',
                  recipients=[correo])
    link = f"https://biblioteca-web-mgmi.onrender.com/verificar/{token}"
    msg.body = f"Hola {nombre}, haz clic aquí para verificar tu préstamo: {link}"
    mail.send(msg)

    return "Te enviamos un correo para verificar tu préstamo."

@app.route('/verificar/<token>')
def verificar(token):
    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("SELECT verificado FROM registros WHERE token = ?", (token,))
    fila = c.fetchone()

    if fila is None:
        mensaje = "Token inválido."
    elif fila[0] == 1:
        mensaje = "El préstamo ya fue verificado anteriormente."
    else:
        c.execute("UPDATE registros SET verificado = 1 WHERE token = ?", (token,))
        conn.commit()
        mensaje = "¡Préstamo verificado correctamente! Gracias por confirmar."

    conn.close()
    return mensaje

@app.route('/admin')
def admin():
    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("SELECT nombre, curso, correo, libro, tiempo_prestamo, fecha_prestamo, verificado FROM registros")
    datos = c.fetchall()
    conn.close()
    return render_template('admin.html', registros=datos)

if __name__ == '__main__':
    from os import environ
    init_db()
    app.run(host='0.0.0.0', port=int(environ.get("PORT", 5000)), debug=True)
