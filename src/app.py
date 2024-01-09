from flask import Flask, render_template, request, redirect, url_for,session, flash, get_flashed_messages, make_response
from config import config
from random import sample
from flask_paginate import Pagination
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from MySQLdb import OperationalError
from flask_migrate import Migrate
from logging import getLogger, FileHandler, Formatter, DEBUG
from flask import send_from_directory
from passlib.hash import sha256_crypt
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from flask import abort
from flask import jsonify, abort
from sqlalchemy import or_ , Boolean,  and_
from flask_mail import Mail
from flask_mail import Message
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
import io, time
import os
import re
from sqlalchemy.orm import aliased
import schedule
import threading

from werkzeug.security import generate_password_hash, check_password_hash

app_logger = getLogger('my_flask_app')
file_handler = FileHandler('app.log')
file_handler.setLevel(DEBUG)
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
app_logger.addHandler(file_handler)

app = Flask(__name__)

app.secret_key = '97110c78ae51a45af397be6534caef90ebb9b1dcb3380af008f90b23a5d1616bf19bc29098105da20fe'
app.config['UPLOAD_FOLDER'] = 'uploads'

tipo =''
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Reemplaza con tu servidor SMTP
app.config['MAIL_PORT'] = 587  # Reemplaza con el puerto de tu servidor SMTP
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'udenardeportes226@gmail.com'  # Reemplaza con tu dirección de correo
app.config['MAIL_PASSWORD'] = 'glqb dnmc feqe vcqo'  # Reemplaza con tu contraseña de correo

mail = Mail(app)

def dataLoginSesion():
    inforLogin = {
        "idLogin"             :session['id'],
        "tipoLogin"           :session['tipo_user'],
        "nombre"              :session['nombre'],
        "apellido"            :session['apellido'],
        "emailLogin"          :session['email'],
        "telefono"             :session['telefono']
    }
    return inforLogin




app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/juegosdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#########################################################################
#                                                                       #
#                modelo bases de datos                                  #
#                                                                       #
#########################################################################

class Juego(db.Model):
    __tablename__ = 'juego'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    horai = db.Column(db.String(5), nullable=False)
    horaf = db.Column(db.String(5), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    cupos = db.Column(db.Integer, nullable=False, default=0)
    id_usuario = db.Column(db.Integer, db.ForeignKey('registro.id'))

    id_lugar = db.Column(db.Integer, db.ForeignKey('lugar.id'))

    # Nueva columna para la ruta de la imagen
    imagen = db.Column(db.String(255))

    eliminado = db.Column(Boolean, default=False)

    # Corrige la relación utilizando back_populates
    registro = db.relationship('Registro', back_populates='juegos')
    lugar = db.relationship('Lugar', back_populates='juegos')

class Noticias(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String(255), nullable=False)
    fecha_publicacion = db.Column(db.Date, default=datetime.now().date())
    imagen = db.Column(db.String(255))
    descripcion = db.Column(db.Text)


 
class Lugar(db.Model):
    __tablename__ = 'lugar'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)

    juegos = db.relationship('Juego', back_populates='lugar')



class Inscrito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False)
    semestre = db.Column(db.String(10), nullable=False)
    carrera = db.Column(db.String(100), nullable=False)
     # Agregar un campo de relación con Juego
    juego_id = db.Column(db.Integer, db.ForeignKey('juego.id'))
    juego = db.relationship('Juego', backref='inscritos')

    id_usuario = db.Column(db.Integer, db.ForeignKey('registro.id'))

    registro = db.relationship('Registro', back_populates='inscritos')

class Registro(db.Model):
    __tablename__ = 'registro'
    id = db.Column(db.Integer, primary_key=True)
    tipo_user = db.Column(db.Integer)
    nombre = db.Column(db.String(255))
    apellido = db.Column(db.String(255))
    email = db.Column(db.String(255))
    telefono = db.Column(db.String(15))  # Ajusta la longitud según sea necesario
    password = db.Column(db.String(255))
    
    # Corrige la relación utilizando back_populates
    juegos = db.relationship('Juego', back_populates='registro')
    inscritos = db.relationship('Inscrito', back_populates='registro')


#########################################################################
#                                                                       #
#                configuraciones bascicas                               #
#                                                                       #
#########################################################################
def enviar_correo_inscripcion(usuario_email, juego_nombre):
    asunto = 'Inscripción Exitosa'
    cuerpo = f'Hola,\n\nTe has inscrito con éxito en el juego "{juego_nombre}". ¡Buena suerte!'
    mensaje = Message(asunto, sender='udenardeportes@gmail.com', recipients=[usuario_email])
    mensaje.body = cuerpo
    mail.send(mensaje)
    
def obtener_lista_de_juegos():
    # Retorna la lista de juegos, similar a como lo haces en la ruta /eventos
    return Juego.query.join(Registro).all()

def obtener_juego_por_id(id):
    
    juego = Juego.query.get(id)
    return juego

def obtener_inscritos_del_juego(id):
    
    juego = obtener_juego_por_id(id)

    if not juego:
        abort(404, description="Juego no encontrado")  # Puedes personalizar el mensaje de error según tus necesidades

    inscritos = Inscrito.query.filter_by(juego_id=id).all()
    return inscritos

def eliminar_juegos_pasados_schedule():
    try:
        with app.app_context():
            juegos_pasados = Juego.query.filter(
                or_(
                    Juego.fecha < datetime.now().date(),
                    and_(Juego.fecha == datetime.now().date(), Juego.horaf < datetime.now().time())
                ),
                Juego.eliminado == False
            ).all()

            for juego_pasado in juegos_pasados:
                db.session.delete(juego_pasado)
                db.session.commit()

        print("Schedule ejecutado correctamente")
    except Exception as e:
        print(f"Error en el schedule: {e}")

# Configurar schedule para ejecutarse cada 2 minutos
schedule.every(2).minutes.do(eliminar_juegos_pasados_schedule)

# Función para ejecutar el schedule en un hilo
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)  # Añadido para reducir la carga de la CPU

@app.route('/favicon.ico')
def favicon():
    return send_from_directory (os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def inicio():
    return render_template('inicio.html')

#########################################################################
#                                                                       #
#               logeo y registro                                        #
#                                                                       #
#########################################################################

@app.route('/registro')
def registro():
        return render_template('auth/registro.html')


@app.route('/login')
def login():
    if 'conectado' in session:
        juegos = obtener_lista_de_juegos()
        return render_template('error3.html', error='Peligro!!')
    else:
        return render_template('auth/login.html')

@app.route('/registro-usuario', methods=['GET', 'POST'])
def registerUser():
    if request.method == 'POST':
        tipo_user = 2
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        password = request.form['password']
        repite_password = request.form['repite_password']
        telefono = request.form['telefono']

        
        # Validación de contraseñas
        if password != repite_password:
            flash('Disculpa, las claves no coinciden!', 'error')
            return redirect(url_for('registro'))

        # Comprobando si ya existe la cuenta de Usuario con respecto al email
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM registro WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            flash('Ya existe el Email!', 'error')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Disculpa, formato de Email incorrecto!', 'error')
        elif not email or not password or not repite_password:
            flash('El formulario no debe estar vacío!', 'error')
        else:
            # La cuenta no existe y los datos del formulario son válidos,
            password_encriptada = sha256_crypt.encrypt(str(password))
            cursor.execute('INSERT INTO registro (tipo_user, nombre, apellido, email, telefono, password) VALUES (%s, %s, %s, %s, %s, %s)',
                           (tipo_user, nombre, apellido, email, telefono, password_encriptada))
            mysql.connection.commit()
            flash('Cuenta creada correctamente!', 'success')
            cursor.close()

            session['flash_messages'] = list(get_flashed_messages())
            # Redirigir al usuario a la página de inicio de sesión
            return redirect(url_for('login'))

    # Si hay algún error, o es una solicitud GET, redirigir a la página de registro
    return redirect(url_for('registro'))

@app.route('/dashboard', methods=['GET', 'POST'])
def loginUser():
    if 'conectado' in session:
            if session['tipo_user'] ==1:
                        juegos = obtener_lista_de_juegos()
                        return redirect(url_for('noticias'))
            elif session['tipo_user'] ==2:
                        juegos = obtener_lista_de_juegos()
                        return redirect(url_for('noticiasusu')) 
    else:
        msg = ''
        if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
            email = str(request.form['email'])
            password = str(request.form['password'])

            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM registro WHERE email = %s", [email])

            # Obtener la información sobre las columnas
            columns = [column[0] for column in cursor.description]

            # Obtener la primera fila del resultado de la consulta
            account = cursor.fetchone()

            if account:
                account_dict = dict(zip(columns, account))  # Convertir la tupla a un diccionario
                if sha256_crypt.verify(password, account_dict['password']):
                    # Crear datos de sesión, para poder acceder a estos datos en otras rutas 
                    session['conectado'] = True
                    session['id'] = account_dict['id']
                    session['tipo_user'] = account_dict['tipo_user']
                    session['nombre'] = account_dict['nombre']
                    session['apellido'] = account_dict['apellido']
                    session['email'] = account_dict['email']
                    session['telefono'] = account_dict['telefono']

                    if session['tipo_user'] ==1:
                        flash("Ha iniciado sesión correctamente admin.", 'success')
                        juegos = obtener_lista_de_juegos()
                        return redirect(url_for('noticias'))
                    elif session['tipo_user'] ==2:
                        flash("Ha iniciado sesión correctamente usuario.", 'success')
                        juegos = obtener_lista_de_juegos()
                        return redirect(url_for('noticiasusu'))
                else:
                    flash('Datos incorrectos, por favor verifique.', 'error')
            else:
                flash('Cuenta no encontrada.', 'error')
            cursor.close()

    return render_template('auth/login.html', messages=get_flashed_messages())


#########################################################################
#                                                                       #
#                   eventos admin                                       #
#                                                                       #
#########################################################################

@app.route('/juego')
def juego():
    if 'conectado' in session:
        lugares = Lugar.query.all()
        return render_template('juego.html', lugares=lugares, dataLogin = dataLoginSesion())
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    
from datetime import datetime

@app.route('/agregar_juego', methods=['POST'])
def agregar_juego():
    if 'conectado' in session:
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        horai = request.form.get('horai')
        horaf = request.form.get('horaf')
        fecha = request.form.get('fecha')
        cupos = request.form.get('cupos')
        id_lugar = request.form['id_lugar']
        lugares = Lugar.query.all()
        id_usuario = session['id']

        # Convertir cadenas de fecha y hora a objetos datetime
        fecha_ingresada = datetime.strptime(fecha, '%Y-%m-%d').date()
        hora_inicio_nuevo = datetime.strptime(horai, '%H:%M').time()
        hora_fin_nuevo = datetime.strptime(horaf, '%H:%M').time()

        # Obtener juegos existentes para el mismo lugar y fecha
        juegos_existentes = Juego.query.filter_by(id_lugar=id_lugar, fecha=fecha_ingresada).all()

        errors = []  # Lista para almacenar mensajes de error

        for juego_existente in juegos_existentes:
            hora_inicio_existente = datetime.combine(fecha_ingresada, datetime.min.time()) + juego_existente.horai
            hora_fin_existente = datetime.combine(fecha_ingresada, datetime.min.time()) + juego_existente.horaf

            # Verificar superposición de horarios
            if not (hora_fin_nuevo <= hora_inicio_existente.time() or hora_inicio_nuevo >= hora_fin_existente.time()):
                errors.append('Ya existe un juego registrado en ese horario y lugar.')
                break

        # Verificar fecha y hora actuales
        if fecha_ingresada < datetime.now().date() or (fecha_ingresada == datetime.now().date() and hora_inicio_nuevo < datetime.now().time()):
            errors.append('No puedes ingresar una hora o fecha anterior a la actual.')

        if not errors:
            # Intentar agregar juego a la base de datos
            if request.files['imagen'] != '':
                file = request.files['imagen']
                imagen = recibeFoto(file)
                juego = Juego(nombre=nombre, cupos=cupos, descripcion=descripcion, horai=horai, horaf=horaf, fecha=fecha, id_lugar=id_lugar, id_usuario=id_usuario, imagen=imagen)
                db.session.add(juego)
                db.session.commit()
                juegos = obtener_lista_de_juegos()
                return redirect(url_for('index'))

        return render_template('juego.html', dataLogin=dataLoginSesion(), lugares=lugares, errors=errors)

    return render_template('auth/login.html')



@app.route('/editar_juego/<int:id>', methods=['GET', 'POST'])
def editar_juego(id):
    if 'conectado' in session:
        lugares = Lugar.query.all()
        juego = Juego.query.get(id)
        errors = []
        if juego is not None:
            if request.method == 'POST':
                juego.nombre = request.form.get('nombre')
                juego.descripcion = request.form.get('descripcion')
                
                juego.cupos = request.form.get('cupos')

                # Utiliza el id del usuario actual de la sesión
                id_usuario = session['id']

                

                if not errors:
                    if 'imagen' in request.files and request.files['imagen']:
                        file = request.files['imagen']  # recibiendo el archivo
                        juego.imagen = recibeFoto(file)  # Llamado la funcion que procesa la imagen
                    db.session.commit()
                    juegos = obtener_lista_de_juegos()
                    return redirect(url_for('index'))
            
                    # Si hay errores, renderiza el formulario con los mensajes de error
            return render_template('juegoedit.html', juego=juego, dataLogin=dataLoginSesion(), lugares=lugares, errors=errors)
        
        else:
            return render_template('error.html', error='Juego no encontrado')
    if errors:
        for error in errors:
         app_logger.error(error)
    
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')

    
@app.route('/eliminar_juego/<int:id>', methods=['DELETE'])
def eliminar_juego(id):
    if 'conectado' in session:
        juego = Juego.query.get(id)

        # Verificar si hay inscritos para este juego
        if Inscrito.query.filter_by(juego_id=id).count() > 0:
            return jsonify({'error': 'No puedes eliminar este juego, hay inscritos.'}), 400  # Código de respuesta 400 Bad Request

        try:
            db.session.delete(juego)
            db.session.commit()
            return jsonify({'message': 'El juego ha sido eliminado exitosamente.'})
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({'error': 'Error al eliminar el juego: {}'.format(str(e))}), 500  # Código de respuesta 500 Internal Server Error
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')

@app.route('/eventos')
def index():
    if 'conectado' in session:
        # Obtener la lista de juegos
        juegos = obtener_lista_de_juegos()
        lugares = Lugar.query.all()

        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        juegos_paginados = Juego.query.order_by(Juego.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
        juegos = juegos_paginados.items

        count = Juego.query.count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('index.html', juegos=juegos, lugares=lugares, dataLogin=dataLoginSesion(), pagination=pagination)
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    
#########################################################################
#                                                                       #
#                   eventos usuarios                                    #
#                                                                       #
#########################################################################

@app.route('/eventosusu')
def indexusu():
    if 'conectado' in session:
        # Obtener la lista de juegos
        juegos = obtener_lista_de_juegos()

        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        juegos_paginados = Juego.query.order_by(Juego.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
        juegos = juegos_paginados.items

        count = Juego.query.count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('indexusu.html', juegos=juegos,  dataLogin=dataLoginSesion(), pagination=pagination)
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    

def restar_cupo_en_juego(juego_id):
    print(f'Antes de restar - Juego ID: {juego_id}')
    juego_alias = aliased(Juego)
    
    with db.session.begin():
        # Restar el cupo
        affected_rows = (
            db.session.query(Juego)
            .filter(Juego.id == juego_id, Juego.cupos > 0)
            .update({Juego.cupos: Juego.cupos - 1})
        )

        if affected_rows == 0:
            # No se restó ningún cupo (juego no existe o no hay cupos)
            return {'success': False, 'error': 'No se pudo restar un cupo al juego. El juego no existe o no hay cupos disponibles.'}

        # Obtener la información más reciente del juego
        juego_actualizado = (
            db.session.query(juego_alias)
            .filter(juego_alias.id == juego_id)
            .one()
        )

    print(f'Después de restar - Cupos disponibles: {juego_actualizado.cupos}')

    return {'success': True, 'message': 'Se restó un cupo al juego exitosamente.'}


@app.route('/inscribirme', methods=['POST'])
def inscribirme():
    if 'conectado' in session and request.method == 'POST':
        codigo = request.form['codigo']
        semestre = request.form['semestre']
        carrera = request.form['carrera']
        juego_id = request.form['juego_id']
        id_usuario = session['id']

        # Verificar si hay cupos disponibles antes de realizar la inscripción
        resultado_restar_cupo = restar_cupo_en_juego(juego_id)

        app.logger.info(f"Resultado restar_cupo: {resultado_restar_cupo}")

        if resultado_restar_cupo.get('success', False):
            # Añadir la inscripción a la base de datos
            inscrito = Inscrito(codigo=codigo, semestre=semestre, carrera=carrera, juego_id=juego_id, id_usuario=id_usuario)
            db.session.add(inscrito)
            db.session.commit()

            # Resto de la lógica para enviar correo, etc.
            juego = obtener_juego_por_id(juego_id)
            enviar_correo_inscripcion(session['email'], juego.nombre)
            
            return jsonify({'message': 'Inscripción exitosa.'})
        else:
            app.logger.error(f"No se pudo restar un cupo al juego. Resultado: {resultado_restar_cupo}")
            # Manejar el caso donde no hay cupos disponibles
            return 'No hay cupos disponibles en este juego.'

    # Manejar el caso donde el usuario no está conectado
    app.logger.error("Usuario no conectado.")
    return abort(401)  # Unauthorized


#########################################################################
#                                                                       #
#                   Noticias admin                                      #
#                                                                       #
#########################################################################

@app.route('/agregar_noticia', methods=['POST'])
def agregar_noticia():
    if 'conectado' in session:
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        fecha_publicacion = request.form.get('fecha_publicacion')
        if request.files['imagen'] != '':
            file = request.files['imagen']  # recibiendo el archivo
            imagen = recibeFoto(file)  # Llamado la funcion que procesa la imagen
            noticias = Noticias(titulo=titulo, descripcion=descripcion, fecha_publicacion=fecha_publicacion, imagen=imagen)
            db.session.add(noticias)
            db.session.commit()
            return redirect(url_for('noticias'))
    else:
        return render_template('login.html')
    
@app.route('/editar_noticia/<int:id>', methods=['POST'])
def editar_noticia(id):
    if 'conectado' in session:
        noticias = Noticias.query.get(id)
        if noticias is not None:
            noticias.titulo = request.form.get('titulo')
            noticias.descripcion = request.form.get('descripcion')
            
            if 'imagen' in request.files and request.files['imagen']:
                file = request.files['imagen']
                noticias.imagen = recibeFoto(file)
            
           
            db.session.commit()
            
            
            return redirect(url_for('noticias'))
        else:
            return render_template('error.html', error='Noticia no encontrada')
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')

@app.route('/eliminar_noticia/<int:id>', methods=['DELETE'])
def eliminar_noticia(id):
    if 'conectado' in session:
        noticias = Noticias.query.get(id)

        try:
            db.session.delete(noticias)
            db.session.commit()
            return jsonify({'message': 'La noticia ha sido eliminado exitosamente.'})
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({'error': 'Error al eliminar el noticia: {}'.format(str(e))}), 500  # Código de respuesta 500 Internal Server Error
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    
    
@app.route('/noticias')
def noticias():
    if 'conectado' in session:
        noticias = Noticias.query.all()

        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        noticias_paginados = Noticias.query.order_by(Noticias.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
        noticias = noticias_paginados.items

        count = Noticias.query.count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('noticias.html', noticias=noticias,  dataLogin=dataLoginSesion(), pagination=pagination)
        
       
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')

#########################################################################
#                                                                       #
#                   Lugares  admin                                      #
#                                                                       #
#########################################################################

@app.route('/lugar')
def lugar():
    try:
        if 'conectado' in session:
            lugares = Lugar.query.all()
            

            page_num = request.args.get('page', 1, type=int)
            per_page = 4

            lugares_paginados = Lugar.query.order_by(Lugar.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
            lugares = lugares_paginados.items

            count = Lugar.query.count()

            start_index = (page_num - 1) * per_page + 1
            end_index = min(start_index + per_page - 1, count)

            pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                    display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

            return render_template('lugar.html', lugares=lugares,  dataLogin = dataLoginSesion(), pagination=pagination)
        else:
            return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    except Exception as e:
        app_logger.error(f"Error en la ruta /lugar: {e}")
        # También puedes registrar el error en un archivo de registro
        return render_template('error2.html', error='Se produjo un error al cargar la página de lugares.')



@app.route('/agregar_lugar', methods=['POST'])
def agregar_lugar():
    if 'conectado' in session:
        nombre = request.form.get('nombre')
        lugar = Lugar(nombre=nombre)
        db.session.add(lugar)
        db.session.commit()
        return redirect(url_for('lugar'))
    else:
        return render_template('login.html')
    

#########################################################################
#                                                                       #
#                   Noticias usuario                                    #
#                                                                       #
#########################################################################
    
    
@app.route('/noticiasusu')
def noticiasusu():
    if 'conectado' in session:
        noticias = Noticias.query.all()

        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        noticias_paginados = Noticias.query.order_by(Noticias.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
        noticias = noticias_paginados.items

        count = Noticias.query.count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('noticiasusu.html', noticias=noticias,  dataLogin=dataLoginSesion(), pagination=pagination)
        
       
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    

#########################################################################
#                                                                       #
#                   perfil admin                                       #
#                                                                       #
#########################################################################

# Ruta para la página de perfil
@app.route('/perfil')
def perfil():
    if 'conectado' in session:
            enlaces = [
            {"url": "http://www.google.com", "icon_class": "fab fa-google"},
            {"url": "http://www.twitter.com", "icon_class": "fab fa-twitter"},
            {"url": "http://www.facebook.com", "icon_class": "fab fa-facebook"},
            # Agrega más enlaces con iconos según sea necesario
            ]
            # Obtén la información del usuario, como el nombre de usuario, la descripción y la URL de la foto de perfil
            user_data = {
                'username': 'Nombre de Usuario',
                'user_description': 'Descripción corta sobre el usuario',
                'user_foto_perfil': url_for('static', filename='uploads/foto_perfil.jpg'),
            }
            return render_template('perfil.html', **user_data, enlaces=enlaces, dataLogin = dataLoginSesion())
    else:
            return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')


#########################################################################
#                                                                       #
#                   perfil usuario                                      #
#                                                                       #
#########################################################################

# Ruta para la página de perfil
@app.route('/perfilusu')
def perfilusu():
    if 'conectado' in session:
            enlaces = [
            {"url": "http://www.google.com", "icon_class": "fab fa-google"},
            {"url": "http://www.twitter.com", "icon_class": "fab fa-twitter"},
            {"url": "http://www.facebook.com", "icon_class": "fab fa-facebook"},
            # Agrega más enlaces con iconos según sea necesario
            ]
            # Obtén la información del usuario, como el nombre de usuario, la descripción y la URL de la foto de perfil
            user_data = {
                'username': 'Nombre de Usuario',
                'user_description': 'Descripción corta sobre el usuario',
                'user_foto_perfil': url_for('static', filename='uploads/foto_perfil.jpg'),
            }
            return render_template('perfilusu.html', **user_data, enlaces=enlaces, dataLogin = dataLoginSesion())
    else:
                return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')

#########################################################################
#                                                                       #
#                   Inscritos admin                                     #
#                                                                       #
#########################################################################
@app.route('/inscritos')
def inscritos():
    if 'conectado' in session:
        inscritos = Inscrito.query.all()

        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        inscritos_paginados = Inscrito.query.order_by(Inscrito.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
        inscritos = inscritos_paginados.items

        count = Inscrito.query.count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('inscritos.html', inscritos=inscritos, dataLogin = dataLoginSesion(), pagination=pagination)
        
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')

@app.route('/juegosadminl')
def juegosadminl():
    if 'conectado' in session:
        
        juegos = obtener_lista_de_juegos()
        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        juegos_paginados = Juego.query.order_by(Juego.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
        juegos = juegos_paginados.items

        count = Juego.query.count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('juegosadminl.html', juegos=juegos, dataLogin = dataLoginSesion(), pagination=pagination)
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    
@app.route('/inscritos_juegoa/<int:id>', methods=['GET'])
def inscritos_juegoa(id):
    if 'conectado' in session:
        juego = obtener_juego_por_id(id)

        if not juego:
            abort(404, description="Juego no encontrado")

        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        # Obtén los inscritos específicos para el juego actual
        inscritos_paginados = Inscrito.query.filter_by(juego_id=id).order_by(Inscrito.id.desc()).paginate(
            page=page_num, per_page=per_page, error_out=False)
        inscritos = inscritos_paginados.items

        count = Inscrito.query.filter_by(juego_id=id).count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('juego_inscritosa.html', inscritos=inscritos, juego=juego, dataLogin=dataLoginSesion(),
                               pagination=pagination)

    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    
#########################################################################
#                                                                       #
#                   Inscritos usuario                                   #
#                                                                       #
#########################################################################
@app.route('/juegosusul')
def juegosusul():
    if 'conectado' in session:
        
        juegos = obtener_lista_de_juegos()
        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        juegos_paginados = Juego.query.order_by(Juego.id.desc()).paginate(page=page_num, per_page=per_page, error_out=False)
        juegos = juegos_paginados.items

        count = Juego.query.count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('juegosusul.html', juegos=juegos, dataLogin = dataLoginSesion(), pagination=pagination)
    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    
@app.route('/inscritos_juego/<int:id>', methods=['GET'])
def inscritos_juego(id):
    if 'conectado' in session:
        juego = obtener_juego_por_id(id)

        if not juego:
            abort(404, description="Juego no encontrado")

        page_num = request.args.get('page', 1, type=int)
        per_page = 4

        # Obtén los inscritos específicos para el juego actual
        inscritos_paginados = Inscrito.query.filter_by(juego_id=id).order_by(Inscrito.id.desc()).paginate(
            page=page_num, per_page=per_page, error_out=False)
        inscritos = inscritos_paginados.items

        count = Inscrito.query.filter_by(juego_id=id).count()

        start_index = (page_num - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, count)

        pagination = Pagination(page=page_num, total=count, per_page=per_page,
                                display_msg=f"Mostrando registros {start_index} - {end_index} de un total de <strong>({count})</strong>")

        return render_template('juego_inscritos.html', inscritos=inscritos, juego=juego, dataLogin=dataLoginSesion(),
                               pagination=pagination)

    else:
        return render_template('error2.html', error='Autenticación obligatoria, Udenar deportes')
    
@app.route('/api/buscar_juegos', methods=['GET'])
def api_buscar_juegos():
    buscar = request.args.get('buscar', '')
    
    # Filtrar juegos según el nombre proporcionado
    juegos = Juego.query.filter(or_(Juego.nombre.contains(buscar), Juego.descripcion.contains(buscar))).all()

    if not juegos:
        mensaje = 'No hay resultados para la búsqueda.'
        return jsonify({'mensaje': mensaje})

    # Convertir resultados a formato JSON
    resultados_json = [
        {
            'id': juego.id,
            'nombre': juego.nombre,
            'fecha': juego.fecha.strftime('%Y-%m-%d'),  # Formatear fecha como string
            'horai': str(juego.horai), 
            'horaf': str(juego.horaf), # Convertir a cadena si es timedelta
            'ver_url': url_for('inscritos_juego', id=juego.id, _external=True)
        }
        for juego in juegos
    ]

    return jsonify({'juegos': resultados_json})
#########################################################################
#                                                                       #
#                   otras configraciones                                  #
#                                                                       #
#########################################################################
@app.route('/exportar_pdf/<juego_id>', methods=['GET'])
def exportar_pdf(juego_id):
    # Obtén la información necesaria para el PDF (ajusta según tus necesidades)
    juego = obtener_juego_por_id(juego_id)
    inscritos = obtener_inscritos_del_juego(juego_id)

    # Crea un buffer de memoria para el PDF
    buffer = io.BytesIO()

    # Crea un objeto PDF con reportlab
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Contenido del PDF
    content = []

    # Agrega el título al PDF
    title = Paragraph(f"<b>Lista de Inscritos - {juego.nombre}</b>", styles['Title'])
    content.append(title)

    # Agrega una tabla para organizar la información de los inscritos
    table_data = [['Nombre', 'Apellido', 'Código', 'Semestre', 'Carrera', 'Teléfono']]

    for inscrito in inscritos:
        table_data.append([
            inscrito.registro.nombre,
            inscrito.registro.apellido,
            inscrito.codigo,
            inscrito.semestre,
            inscrito.carrera,
            inscrito.registro.telefono
        ])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])

    table = Table(table_data, style=table_style)
    content.append(table)

    # Construye el PDF
    doc.build(content)

    # Establece la posición del buffer en el inicio
    buffer.seek(0)

    # Crea una respuesta Flask con el PDF
    response = make_response(buffer.read())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={juego.nombre}_inscritos.pdf'

    return response
    
def recibeFoto(file):
    print(file)
    basepath = os.path.dirname (__file__) #La ruta donde se encuentra el archivo actual
    filename = secure_filename(file.filename) #Nombre original del archivo

    #capturando extensión del archivo ejemplo: (.png, .jpg, .pdf ...etc)
    extension           = os.path.splitext(filename)[1]
    imagen     = stringAleatorio() + extension
    #print(nuevoNombreFile)
        
    upload_path = os.path.join (basepath, 'static/assets/fotos_juego', imagen) 
    file.save(upload_path)

    return imagen

def stringAleatorio():
    string_aleatorio = "0123456789abcdefghijklmnopqrstuvwxyz_"
    longitud         = 20
    secuencia        = string_aleatorio.upper()
    resultado_aleatorio  = sample(secuencia, longitud)
    string_aleatorio     = "".join(resultado_aleatorio)
    return string_aleatorio



app.config['MYSQL_HOST'] = '127.0.0.1'  # Host de la base de datos
app.config['MYSQL_USER'] = 'root'  # Usuario de la base de datos
app.config['MYSQL_PASSWORD'] = ''  # Contraseña de la base de datos
app.config['MYSQL_DB'] = 'juegosdb'  # Nombre de la base de datos

mysql = MySQL(app)

#########################################################################
#                                                                       #
#                   Control de errores                                  #
#                                                                       #
#########################################################################


@app.errorhandler(404)
def page_not_found(error):
 return render_template("error.html",
 error="Página no encontrada..."), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("error4.html", 
    error="Error interno del servidor..."), 500

@app.errorhandler(OperationalError)
def handle_mysql_error(error):
    return render_template("error4.html", error="Error de servidor. Comunicate con Nosotros."), 500



@app.route('/logout')
def logout():
    msgClose = ''
    # Eliminar datos de sesión, esto cerrará la sesión del usuario
    session.pop('conectado', None)
    session.pop('id', None)
    session.pop('email', None)
    msgClose ="La sesión fue cerrada correctamente"
    return render_template('inicio.html', msjAlert = msgClose, typeAlert=1)


    
if __name__ == '__main__':
 app.config.from_object(config['development'])
 schedule_thread = threading.Thread(target=run_schedule)
 schedule_thread.start()
 app.run()