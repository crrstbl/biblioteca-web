from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Crear la base de datos
def init_db():
    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        edad INTEGER,
        libro TEXT,
        tiempo_prestamo TEXT,
        fecha_prestamo TEXT
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
    libro = request.form['libro']
    tiempo = request.form['tiempo']
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("INSERT INTO registros (nombre, edad, libro, tiempo_prestamo, fecha_prestamo) VALUES (?, ?, ?, ?, ?)",
              (nombre, edad, libro, tiempo, fecha))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/admin')
def admin():
    conn = sqlite3.connect('biblioteca.db')
    c = conn.cursor()
    c.execute("SELECT * FROM registros")
    datos = c.fetchall()
    conn.close()
    return render_template('admin.html', registros=datos)

if __name__ == '__main__':
    from os import environ
    app.run(host='0.0.0.0', port=int(environ.get("PORT", 5000)))

