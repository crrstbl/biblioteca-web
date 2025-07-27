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
        edad INTEGER,
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
    edad = request.form['edad']
    correo = request.form['correo']
    libro = request.form['libro']
    tiempo = request.form['tiempo']
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Validar correo institucional
    if not correo.endswith('@colegio.edu'):
        return "El correo debe ser institucional (@colegio.edu)", 400

    token = secrets.token_urlsafe(16)

    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("INSERT INTO registros (nombre, edad, correo, libro, tiempo_prestamo, fecha_prestamo, token, verificado) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
              (nombre, edad, correo, libro, tiempo, fecha, token))
    conn.commit()
    conn.close()

    # Enviar correo de verificación
    verify_url = url_for('verify', token=token, _external=True)
    msg = Message(subject="Verifica tu correo - Biblioteca",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[correo])
    msg.body = f"Hola {nombre},\n\nGracias por registrarte. Para confirmar tu correo, haz clic en el siguiente enlace:\n\n{verify_url}\n\nSi no hiciste este registro, ignora este mensaje."
    mail.send(msg)

    return "Registro recibido. Por favor, revisa tu correo institucional para confirmar."

@app.route('/verify/<token>')
def verify(token):
    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("SELECT verificado FROM registros WHERE token = ?", (token,))
    fila = c.fetchone()
    if fila is None:
        mensaje = "Token inválido."
    elif fila[0] == 1:
        mensaje = "Correo ya verificado."
    else:
        c.execute("UPDATE registros SET verificado = 1 WHERE token = ?", (token,))
        conn.commit()
        mensaje = "Correo verificado exitosamente. Ahora puedes pedir libros."
    conn.close()
    return mensaje

@app.route('/admin')
def admin():
    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("SELECT nombre, edad, correo, libro, tiempo_prestamo, fecha_prestamo, verificado FROM registros")
    datos = c.fetchall()
    conn.close()
    return render_template('admin.html', registros=datos)

if __name__ == '__main__':
    from os import environ
    init_db()
    app.run(host='0.0.0.0', port=int(environ.get("PORT", 5000)), debug=True)
