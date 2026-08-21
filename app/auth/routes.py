from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.models import Cuidador, Profesional
from app import db


@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        telefono = request.form.get('telefono')
        password = request.form.get('password')

        existe = Cuidador.query.filter_by(correo=correo).first()
        if existe:
            flash('Ya existe una cuenta con ese correo.', 'danger')
            return redirect(url_for('auth.registro'))

        nuevo_cuidador = Cuidador(nombre=nombre, correo=correo, telefono=telefono)
        nuevo_cuidador.set_password(password)

        db.session.add(nuevo_cuidador)
        db.session.commit()

        flash('Cuenta creada correctamente. Ahora inicia sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')

        cuidador = Cuidador.query.filter_by(correo=correo).first()

        if cuidador and cuidador.check_password(password):
            login_user(cuidador)
            flash('Bienvenido/a de nuevo.', 'success')
            if cuidador.rol == 'admin':
                return redirect(url_for('dashboard.admin'))
            return redirect(url_for('dashboard.cuidador'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login-profesional', methods=['GET', 'POST'])
def login_profesional():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')

        profesional = Profesional.query.filter_by(correo=correo).first()

        if profesional and profesional.check_password(password):
            login_user(profesional)
            flash('Bienvenido/a, profesional.', 'success')
            return redirect(url_for('dashboard.profesional'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('auth/login_profesional.html')
