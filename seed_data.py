"""
Script de siembra de datos ficticios para RespiraKids.
Ejecutar UNA sola vez con: python seed_data.py
"""

from datetime import date, datetime, timedelta
from app import create_app, db
from app.models import Cuidador, Profesional, Nino, RegistroSintomas, Evaluacion, PatologiaBase, Autorizacion
from app.semaforo import clasificar_riesgo

app = create_app()

with app.app_context():

    if Cuidador.query.filter_by(correo='ana.cuidadora@test.com').first():
        print("⚠️ Los datos de prueba ya existen. Aborta para evitar duplicados.")
        exit()

    # ---------- CUIDADORES ----------
    cuidadores_data = [
        ("Ana Torres", "ana.cuidadora@test.com", "3001112233"),
        ("Carlos Pérez", "carlos.cuidador@test.com", "3002223344"),
        ("María Gómez", "maria.cuidadora@test.com", "3003334455"),
        ("José Ramírez", "jose.cuidador@test.com", "3004445566"),
    ]
    cuidadores = []
    for nombre, correo, tel in cuidadores_data:
        c = Cuidador(nombre=nombre, correo=correo, telefono=tel, rol='cuidador')
        c.set_password("Cuidador123*")
        db.session.add(c)
        cuidadores.append(c)
    db.session.commit()

    # ---------- PROFESIONALES ----------
    profesionales_data = [
        ("Dra. Laura Gómez", "dra.gomez@respirakids.test", "Pediatría", "PED-0001"),
        ("Dr. Andrés Ramírez", "dr.ramirez@respirakids.test", "Neumología Pediátrica", "NEU-0002"),
        ("Dra. Paola Torres", "dra.torres@respirakids.test", "Alergología", "ALE-0003"),
        ("Dr. Felipe Medina", "dr.medina@respirakids.test", "Medicina Familiar", "MED-0004"),
        ("Dra. Camila Vargas", "dra.vargas@respirakids.test", "Pediatría General", "PED-0005"),
    ]
    profesionales = []
    for nombre, correo, esp, lic in profesionales_data:
        p = Profesional(nombre=nombre, correo=correo, especialidad=esp, numero_licencia=lic, rol='profesional')
        p.set_password("Doctora123*")
        db.session.add(p)
        profesionales.append(p)
    db.session.commit()

    # ---------- NIÑOS ----------
    ninos_data = [
        ("Sofía Martínez", date(2018, 3, 12), "F", 0),
        ("Mateo Rodríguez", date(2021, 7, 5), "M", 0),
        ("Valentina López", date(2023, 11, 20), "F", 0),
        ("Elena Gómez", date(2016, 2, 9), "F", 1),
        ("Diego Ramírez", date(2020, 5, 30), "M", 1),
        ("Isabella Castro", date(2019, 9, 14), "F", 1),
        ("Samuel Herrera", date(2022, 1, 25), "M", 2),
        ("Camila Ortiz", date(2017, 6, 2), "F", 2),
        ("Lucas Fernández", date(2015, 10, 18), "M", 3),
        ("Martina Silva", date(2024, 4, 8), "F", 3),
    ]
    ninos = []
    for nombre, fnac, sexo, idx_cuidador in ninos_data:
        n = Nino(nombre_ficticio=nombre, fecha_nacimiento=fnac, sexo=sexo, cuidador_id=cuidadores[idx_cuidador].id, estado='activo')
        db.session.add(n)
        ninos.append(n)
    db.session.commit()

    # ---------- CONDICIONES DE BASE ----------
    db.session.add(PatologiaBase(nino_id=ninos[0].id, nombre="Asma", descripcion="Diagnosticada hace 2 años", fecha_diagnostico=date(2023, 5, 1)))
    db.session.add(PatologiaBase(nino_id=ninos[3].id, nombre="Antecedente de bronquiolitis", descripcion="Episodio a los 8 meses"))
    db.session.add(PatologiaBase(nino_id=ninos[8].id, nombre="Alergias respiratorias", descripcion="Sensible a ácaros y polvo"))
    db.session.commit()

    # ---------- AUTORIZACIONES (cruzadas) ----------
    asignaciones = [
        (0, [0, 1]), (1, [0]), (2, [1]), (3, [0, 2]), (4, [1, 3]),
        (5, [2]), (6, [3]), (7, [0, 4]), (8, [1, 4]), (9, [4]),
    ]
    for idx_nino, idxs_prof in asignaciones:
        for idx_prof in idxs_prof:
            db.session.add(Autorizacion(nino_id=ninos[idx_nino].id, profesional_id=profesionales[idx_prof].id))
    db.session.commit()

    # ---------- REGISTROS DE SÍNTOMAS + EVALUACIONES ----------
    def crear_registro(nino, dias_atras, **kwargs):
        fecha = datetime.utcnow() - timedelta(days=dias_atras)
        r = RegistroSintomas(nino_id=nino.id, fecha=fecha, **kwargs)
        db.session.add(r)
        db.session.flush()  # Para obtener r.id antes del commit

        nivel, motivo, recomendaciones = clasificar_riesgo(r)
        ev = Evaluacion(nino_id=nino.id, registro_sintomas_id=r.id, nivel_riesgo=nivel,
                        fecha=fecha, motivo=motivo, recomendaciones=recomendaciones)
        db.session.add(ev)

    # Sofía: caso rojo reciente (asma + dificultad respiratoria)
    crear_registro(ninos[0], 5, tos=True, temperatura=37.8, severidad=4, inicio_sintomas='2_3_dias')
    crear_registro(ninos[0], 1, tos=True, dificultad_respiratoria=True, respiracion_rapida=True,
                    temperatura=38.9, severidad=8, inicio_sintomas='hoy', condicion_asma=True)

    # Mateo: caso amarillo
    crear_registro(ninos[1], 3, tos=True, congestion_nasal=True, temperatura=38.2, severidad=5, inicio_sintomas='ayer')

    # Valentina: caso verde
    crear_registro(ninos[2], 2, decaimiento=False, severidad=1, inicio_sintomas='hoy')

    # Elena: amarillo, con estornudos e irritabilidad
    crear_registro(ninos[3], 4, estornudos=True, irritabilidad=True, congestion_nasal=True, severidad=6, inicio_sintomas='mas_3_dias')

    # Diego: rojo (fiebre alta)
    crear_registro(ninos[4], 1, tos=True, temperatura=39.5, decaimiento=True, perdida_apetito=True, severidad=9, inicio_sintomas='hoy')

    # Isabella: verde
    crear_registro(ninos[5], 6, tos=False, severidad=2, inicio_sintomas='hoy')

    # Samuel: amarillo (gastrointestinal)
    crear_registro(ninos[6], 2, vomito=True, diarrea=True, severidad=5, inicio_sintomas='ayer')

    # Camila: verde, control de rutina
    crear_registro(ninos[7], 10, severidad=1, inicio_sintomas='hoy')

    # Lucas: amarillo (alergias)
    crear_registro(ninos[8], 3, estornudos=True, congestion_nasal=True, secrecion_nasal=True,
                    severidad=4, inicio_sintomas='2_3_dias', condicion_alergias=True)

    # Martina: rojo (bebé con dificultad respiratoria)
    crear_registro(ninos[9], 1, tos=True, dificultad_respiratoria=True, temperatura=38.7,
                    decaimiento=True, severidad=8, inicio_sintomas='hoy')

    db.session.commit()

    print("✅ Datos de prueba creados exitosamente.")
    print(f"   {len(cuidadores)} cuidadores, {len(profesionales)} profesionales, {len(ninos)} niños.")