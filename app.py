from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'

ADMIN_PASSWORD = "AdminContraseña"

# -------------------------------------------------------------------------
# BASE DE DATOS LOCAL
# -------------------------------------------------------------------------
def iniciar_base_datos():
    conexion = sqlite3.connect("tienda_tenis.db")
    cursor = conexion.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha_nacimiento TEXT NOT NULL,
            contrasena TEXT NOT NULL,
            celular TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            productos TEXT NOT NULL,
            total REAL NOT NULL,
            regalo TEXT,
            fecha_hora DATETIME NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')
    conexion.commit()
    conexion.close()

CATALOGO = {
    "1": {"nombre": "Nuevo Balance 'Henequén & Azul'", "precio": 800},
    "2": {"nombre": 'Ardida "Samba del Coraje"', "precio": 800},
    "3": {"nombre": 'Supérame Boost 350 "Alucín Premium"', "precio": 800},
    "4": {"nombre": 'Fali "Disruptor de Expectativas"', "precio": 800},
    "5": {"nombre": 'Armadura Dura "Tanque Urbano"', "precio": 800},
    "6": {"nombre": 'Skinners "Suela Invisible"', "precio": 1000},
    "7": {"nombre": 'Jaguar "Fiera Prehispánica"', "precio": 1000},
    "8": {"nombre": 'Fuchi "Huele Raro"', "precio": 1000},
    "9": {"nombre": 'Karlos "Rey de la K"', "precio": 1300},
    "10": {"nombre": 'Carlitos "El Patrón" Active"', "precio": 1300}
}

# -------------------------------------------------------------------------
# RUTAS DE CLIENTES
# -------------------------------------------------------------------------
@app.route('/')
def home():
    return render_template('menu.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    fecha_nac = request.form['fecha_nacimiento']
    contrasena = request.form['contrasena']
    celular = request.form['celular']
    correo = request.form['correo']
    
    conexion = sqlite3.connect("tienda_tenis.db")
    cursor = conexion.cursor()
    try:
        cursor.execute('''
            INSERT INTO clientes (nombre, fecha_nacimiento, contrasena, celular, correo)
            VALUES (?, ?, ?, ?, ?)
        ''', (nombre, fecha_nac, contrasena, celular, correo))
        conexion.commit()
        flash("¡Registro exitoso! Ya puedes iniciar sesión.", "success")
    except sqlite3.IntegrityError:
        flash("Error: El correo ya está registrado.", "error")
    finally:
        conexion.close()
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    correo = request.form['correo']
    contrasena = request.form['contrasena']
    
    conexion = sqlite3.connect("tienda_tenis.db")
    cursor = conexion.cursor()
    cursor.execute('SELECT id, nombre FROM clientes WHERE correo = ? AND contrasena = ?', (correo, contrasena))
    cliente = cursor.fetchone()
    conexion.close()
    
    if cliente:
        session['cliente_id'] = cliente[0]
        session['cliente_nombre'] = cliente[1]
        session['carrito'] = []
        return redirect(url_for('tienda'))
    else:
        flash("Contraseña o correo incorrectos.", "error")
        return redirect(url_for('home'))

@app.route('/tienda')
def tienda():
    if 'cliente_id' not in session:
        return redirect(url_for('home'))
    
    total_prov = sum(CATALOGO[item['id']]['precio'] for item in session['carrito'])
    return render_template('tienda.html', catalogo=CATALOGO, carrito=session['carrito'], total_prov=total_prov)

@app.route('/agregar/<id_producto>', methods=['POST'])
def agregar(id_producto):
    if 'cliente_id' in session and id_producto in CATALOGO:
        talla = request.form.get('talla')
        carrito = session['carrito']
        carrito.append({"id": id_producto, "talla": talla})
        session['carrito'] = carrito
    return redirect(url_for('tienda'))

@app.route('/limpiar')
def limpiar():
    if 'cliente_id' in session:
        session['carrito'] = []
    return redirect(url_for('tienda'))

@app.route('/pagar')
def pagar():
    if 'cliente_id' not in session or not session['carrito']:
        return redirect(url_for('tienda'))
    
    productos_comprados = []
    total = 0
    for item in session['carrito']:
        prod_info = CATALOGO[item['id']]
        productos_comprados.append(f"{prod_info['nombre']} (Talla: {item['talla']})")
        total += prod_info['precio']
    
    regalo = "Camisa de la Selección Mexicana" if total >= 1500 else None
    fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conexion = sqlite3.connect("tienda_tenis.db")
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO compras (cliente_id, productos, total, regalo, fecha_hora)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['cliente_id'], ", ".join(productos_comprados), total, regalo, fecha_actual))
    
    compra_id = cursor.lastrowid
    conexion.commit()
    conexion.close()

    session['ticket_actual'] = {
        'id': compra_id,
        'cliente': session.get('cliente_nombre', 'Cliente'),
        'productos': productos_comprados,
        'total': total,
        'regalo': regalo,
        'fecha_hora': fecha_actual
    }
    session['carrito'] = []
    return redirect(url_for('ticket'))

@app.route('/ticket')
def ticket():
    if 'ticket_actual' not in session:
        return redirect(url_for('tienda'))
    return render_template('ticket.html', ticket=session['ticket_actual'])

# -------------------------------------------------------------------------
# RUTAS DE ADMINISTRADOR (EXCLUSIVO)
# -------------------------------------------------------------------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        clave = request.form.get('password')
        if clave == ADMIN_PASSWORD:
            session['es_admin'] = True
            return redirect(url_for('panel_admin'))
        else:
            flash("Contraseña de Administrador incorrecta.", "error")
            
    return render_template('admin_login.html')

@app.route('/admin', methods=['GET'])
def panel_admin():
    # Proteger para que solo entre el admin
    if not session.get('es_admin'):
        return redirect(url_for('admin_login'))

    buscar_cliente = request.args.get('buscar_cliente', '').strip()
    buscar_mes = request.args.get('buscar_mes', '').strip()

    conexion = sqlite3.connect("tienda_tenis.db")
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()

    # 1. Obtener lista de todos los meses con ventas (para el desplegable)
    cursor.execute("SELECT DISTINCT strftime('%Y-%m', fecha_hora) AS mes FROM compras ORDER BY mes DESC")
    meses_disponibles = [row['mes'] for row in cursor.fetchall()]

    # 2. Información detallada del cliente si se buscó uno
    info_cliente = None
    if buscar_cliente:
        cursor.execute("SELECT * FROM clientes WHERE nombre LIKE ?", (f'%{buscar_cliente}%',))
        info_cliente = cursor.fetchall()

    # 3. Consulta flexible de compras según filtros
    query = '''
        SELECT 
            strftime('%Y-%m', c.fecha_hora) AS mes,
            c.id AS ticket_id,
            cl.nombre AS cliente,
            cl.correo,
            cl.celular,
            c.productos,
            c.total,
            c.regalo,
            c.fecha_hora
        FROM compras c
        JOIN clientes cl ON c.cliente_id = cl.id
        WHERE 1=1
    '''
    params = []

    if buscar_cliente:
        query += " AND cl.nombre LIKE ?"
        params.append(f'%{buscar_cliente}%')

    if buscar_mes:
        query += " AND strftime('%Y-%m', c.fecha_hora) = ?"
        params.append(buscar_mes)

    query += " ORDER BY c.fecha_hora DESC"

    cursor.execute(query, params)
    compras = cursor.fetchall()

    # Calcular total en dinero de la búsqueda actual
    total_acumulado = sum(row['total'] for row in compras)

    conexion.close()

    return render_template(
        'admin.html', 
        compras=compras, 
        info_cliente=info_cliente, 
        meses_disponibles=meses_disponibles,
        buscar_cliente=buscar_cliente,
        buscar_mes=buscar_mes,
        total_acumulado=total_acumulado
    )

@app.route('/admin_logout')
def admin_logout():
    session.pop('es_admin', None)
    return redirect(url_for('home'))

@app.route('/salir')
def salir():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    iniciar_base_datos()
    app.run(debug=True)
