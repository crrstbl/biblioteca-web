from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import secrets
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'bibliotecatomaslago@gmail.com'
app.config['MAIL_PASSWORD'] = 'dehursreirrhrhap'

mail = Mail(app)

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
            tiempo_prestamo INTEGER,
            fecha_prestamo TIMESTAMP,
            token TEXT,
            verificado INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS libros (
            id SERIAL PRIMARY KEY,
            titulo TEXT UNIQUE NOT NULL,
            stock INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

@app.template_filter('todatetime')
def todatetime_filter(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


@app.route('/')
def index():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT titulo, stock FROM libros ORDER BY titulo")
    libros_raw = c.fetchall()
    conn.close()

    libros = [{"nombre": libro[0], "stock": libro[1]} for libro in libros_raw]
    return render_template('registro.html', libros=libros)

@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    curso = request.form['curso']
    correo = request.form['correo']
    libro = request.form['libro']
    tiempo = 14
    fecha = datetime.now()
    token = secrets.token_urlsafe(16)

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO registros (nombre, curso, correo, libro, tiempo_prestamo, fecha_prestamo, token) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (nombre, curso, correo, libro, tiempo, fecha, token)
    )
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
    c.execute("SELECT verificado, libro FROM registros WHERE token = %s", (token,))
    fila = c.fetchone()

    if fila is None:
        mensaje = "Token inválido."
    elif fila[0] == 1:
        mensaje = "El préstamo ya fue verificado anteriormente."
    else:
        libro = fila[1]
        c.execute("SELECT stock FROM libros WHERE titulo = %s", (libro,))
        resultado = c.fetchone()
        if resultado is None:
            mensaje = "El libro no existe."
        elif resultado[0] <= 0:
            mensaje = "No hay stock disponible para este libro."
        else:
            c.execute("UPDATE registros SET verificado = 1 WHERE token = %s", (token,))
            c.execute("UPDATE libros SET stock = stock - 1 WHERE titulo = %s", (libro,))
            conn.commit()
            mensaje = "¡Préstamo verificado correctamente! El stock ha sido actualizado."

    conn.close()
    return mensaje

@app.route('/admin')
def admin():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nombre, curso, correo, libro, tiempo_prestamo, fecha_prestamo, verificado FROM registros ORDER BY fecha_prestamo DESC")
    datos = c.fetchall()
    conn.close()

    now = datetime.now()
    # Pasamos now para cálculo en plantilla
    return render_template('admin.html', registros=datos, now=now)

@app.route('/admin/eliminar_registro', methods=['POST'])
def eliminar_registro():
    registro_id = request.form.get('registro_id')
    if not registro_id:
        flash("ID de registro no proporcionado.", "danger")
        return redirect(url_for('admin'))

    conn = get_connection()
    c = conn.cursor()

    # Primero recuperamos el libro para reponer stock si estaba verificado
    c.execute("SELECT libro, verificado FROM registros WHERE id = %s", (registro_id,))
    fila = c.fetchone()
    if not fila:
        flash("Registro no encontrado.", "danger")
        conn.close()
        return redirect(url_for('admin'))

    libro, verificado = fila

    # Si estaba verificado, aumentamos stock
    if verificado == 1:
        c.execute("UPDATE libros SET stock = stock + 1 WHERE titulo = %s", (libro,))

    # Borramos el registro
    c.execute("DELETE FROM registros WHERE id = %s", (registro_id,))
    conn.commit()
    conn.close()

    flash("Registro eliminado y stock actualizado si correspondía.", "success")
    return redirect(url_for('admin'))


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

        elif 'nuevo_libro' in request.form and 'stock_libro' in request.form:
            nuevo_libro = request.form['nuevo_libro']
            stock_libro = request.form['stock_libro']
            try:
                c.execute("INSERT INTO libros (titulo, stock) VALUES (%s, %s)", (nuevo_libro, stock_libro))
                conn.commit()
                mensaje = "Libro agregado correctamente."
            except psycopg2.IntegrityError:
                conn.rollback()
                mensaje = "El libro ya existe."

        elif 'actualizar_stock_id' in request.form:
            libro_id = request.form['actualizar_stock_id']
            nuevo_stock = int(request.form['nuevo_stock'])
            c.execute("UPDATE libros SET stock = %s WHERE id = %s", (nuevo_stock, libro_id))
            conn.commit()
            mensaje = "Stock actualizado correctamente."

    termino_busqueda = request.args.get('buscar', '')
    if termino_busqueda:
        c.execute("SELECT id, titulo, stock FROM libros WHERE titulo ILIKE %s ORDER BY titulo", ('%' + termino_busqueda + '%',))
    else:
        c.execute("SELECT id, titulo, stock FROM libros ORDER BY titulo")

    libros = c.fetchall()
    conn.close()
    return render_template('admin_libros.html', libros=libros, mensaje=mensaje, buscar=termino_busqueda)


# Función para enviar correos a usuarios con 1 día restante
def enviar_recordatorios_1_dia():
    conn = get_connection()
    c = conn.cursor()
    ahora = datetime.now()
    un_dia = timedelta(days=1)

    # Seleccionar registros verificados donde faltan 1 día para vencer (tiempo_prestamo=14 días)
    c.execute("""
        SELECT nombre, correo, libro, fecha_prestamo
        FROM registros
        WHERE verificado = 1
    """)
    registros = c.fetchall()

    for nombre, correo, libro, fecha_prestamo in registros:
        fecha_prestamo_dt = fecha_prestamo if isinstance(fecha_prestamo, datetime) else datetime.strptime(fecha_prestamo, '%Y-%m-%d %H:%M:%S')
        fecha_vencimiento = fecha_prestamo_dt + timedelta(days=14)
        dias_restantes = (fecha_vencimiento - ahora).days

        if dias_restantes == 1:
            # Enviar correo recordatorio
            msg = Message('Recordatorio: Entrega tu libro',
                          sender='bibliotecatomaslago@gmail.com',
                          recipients=[correo])
            msg.body = (f"Hola {nombre},\n\n"
                        f"Te recordamos que debes entregar el libro '{libro}' dentro de 1 día.\n"
                        "Por favor, hazlo a tiempo para que otros puedan disfrutarlo.\n\n"
                        "Gracias.")
            mail.send(msg)

    conn.close()

# Para llamar esta función puedes usar un scheduler externo (cron, celery, etc.)
# Por ejemplo, la puedes llamar al iniciar app para pruebas (¡solo una vez!):
# enviar_recordatorios_1_dia()

if __name__ == '__main__':
    init_db()
    from os import environ
    app.run(host='0.0.0.0', port=int(environ.get("PORT", 5000)), debug=True)
