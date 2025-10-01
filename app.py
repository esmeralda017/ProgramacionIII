import os
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
import mysql.connector
from werkzeug.utils import secure_filename

# -------- CONFIG ----------
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'uploads', 'projects')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = "clave_super_secreta_cambiaesto"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB por request

# ---------- DB CONNECTION (ajusta si tu usuario/clave son otros) ----------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",         # <- pon tu contraseña si existe
        database="feria_logros"
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

# ------------------- ROUTES -------------------

# Home / Login
@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario").strip()
        password = request.form.get("password").strip()
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s AND password=%s", (usuario, password))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user:
            session['user_id'] = user['id']
            session['usuario'] = user['usuario']
            session['rol'] = user['rol']
            flash("Bienvenido " + user['usuario'])
            if user['rol'] == 'juez':
                return redirect(url_for('dashboard_juez'))
            else:
                return redirect(url_for('dashboard_participante'))
        else:
            return render_template('login.html', error="Usuario o contraseña incorrecta")
    return render_template('login.html')

# Registro simple (opcional)
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        usuario = request.form.get("usuario").strip()
        password = request.form.get("password").strip()
        rol = request.form.get("rol")
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO usuarios (usuario, password, rol) VALUES (%s,%s,%s)", (usuario, password, rol))
            conn.commit()
            flash("Usuario registrado. Inicia sesión.")
            return redirect(url_for('login'))
        except Exception as e:
            flash("Error: " + str(e))
            return render_template('register.html')
        finally:
            cur.close(); conn.close()
    return render_template('register.html')

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# Participant dashboard
@app.route("/dashboard_participante")
def dashboard_participante():
    if 'usuario' not in session or session.get('rol') != 'participante':
        return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(dictionary=True)
    # Get teams where this user is member
    cur.execute("""
        SELECT t.id, t.nombre, t.codigo
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.id
        JOIN usuarios u ON tm.user_id = u.id
        WHERE u.id = %s
    """, (session['user_id'],))
    teams = cur.fetchall()
    # Retrieve project (if any) for each team
    projects = []
    for t in teams:
        cur.execute("SELECT * FROM proyectos WHERE team_id=%s", (t['id'],))
        p = cur.fetchone()
        p_entry = p if p else None
        projects.append({'team': t, 'project': p_entry})
    cur.close(); conn.close()
    return render_template('dashboard_participante.html', usuario=session['usuario'], projects=projects)

# Create Team (leader)
@app.route("/create_team", methods=["GET","POST"])
def create_team():
    if 'usuario' not in session or session.get('rol') != 'participante':
        return redirect(url_for('login'))
    if request.method == "POST":
        nombre = request.form.get('nombre').strip()
        codigo = request.form.get('codigo').strip()
        team_pw = request.form.get('team_password').strip()
        conn = get_db(); cur = conn.cursor()
        # Insert team with lider_id = current user's id
        cur.execute("INSERT INTO teams (nombre, codigo, password, lider_id) VALUES (%s,%s,%s,%s)",
                    (nombre, codigo, team_pw, session['user_id']))
        team_id = cur.lastrowid
        # add leader as member
        cur.execute("INSERT INTO team_members (team_id, user_id, rol_en_equipo) VALUES (%s,%s,%s)",
                    (team_id, session['user_id'], 'lider'))
        conn.commit()
        cur.close(); conn.close()
        flash("Equipo creado. Comparte el código con tus integrantes.")
        return redirect(url_for('dashboard_participante'))
    return render_template('create_team.html')

# Join team (step 1: enter team code and username of the member to join)
@app.route("/join_team", methods=["GET","POST"])
def join_team():
    if 'usuario' not in session or session.get('rol') != 'participante':
        return redirect(url_for('login'))
    if request.method == "POST":
        codigo = request.form.get('codigo').strip()
        usuario_buscar = request.form.get('usuario_buscar').strip()
        conn = get_db(); cur = conn.cursor(dictionary=True)
        # find team
        cur.execute("SELECT * FROM teams WHERE codigo=%s", (codigo,))
        team = cur.fetchone()
        if not team:
            flash("Código de equipo inválido.")
            cur.close(); conn.close()
            return render_template('join_team.html')
        # find user by username
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s", (usuario_buscar,))
        user = cur.fetchone()
        if not user:
            flash("Usuario buscado no existe. Debe registrarse primero.")
            cur.close(); conn.close()
            return render_template('join_team.html')
        # check if user already in any team
        cur.execute("SELECT * FROM team_members WHERE user_id=%s", (user['id'],))
        existing = cur.fetchall()
        if existing:
            flash("El usuario ya pertenece a un equipo.")
            cur.close(); conn.close()
            return render_template('join_team.html')
        # store temp info in session and redirect to confirm (ask for team pw)
        session['join_team_code'] = codigo
        session['join_team_user'] = usuario_buscar
        cur.close(); conn.close()
        return redirect(url_for('confirm_join'))
    return render_template('join_team.html')

# Confirm join (enter team password)
@app.route("/confirm_join", methods=["GET","POST"])
def confirm_join():
    if 'usuario' not in session or session.get('rol') != 'participante':
        return redirect(url_for('login'))
    codigo = session.get('join_team_code')
    username = session.get('join_team_user')
    if not codigo or not username:
        return redirect(url_for('join_team'))
    if request.method == "POST":
        team_pw = request.form.get('team_password').strip()
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM teams WHERE codigo=%s", (codigo,))
        team = cur.fetchone()
        if not team:
            flash("Equipo no encontrado.")
            cur.close(); conn.close()
            return redirect(url_for('join_team'))
        if team['password'] != team_pw:
            flash("Contraseña de equipo incorrecta.")
            cur.close(); conn.close()
            return render_template('confirm_join.html', codigo=codigo, username=username)
        # add user to team
        cur.execute("SELECT id FROM usuarios WHERE usuario=%s", (username,))
        user = cur.fetchone()
        if not user:
            flash("Usuario no encontrado.")
            cur.close(); conn.close()
            return redirect(url_for('join_team'))
        user_id = user['id']
        # count members
        cur.execute("SELECT COUNT(*) as cnt FROM team_members WHERE team_id=%s", (team['id'],))
        cnt = cur.fetchone()['cnt']
        if cnt >= 5:
            flash("El equipo ya tiene 5 integrantes.")
            cur.close(); conn.close()
            return redirect(url_for('join_team'))
        cur.execute("INSERT INTO team_members (team_id, user_id, rol_en_equipo) VALUES (%s,%s,%s)",
                    (team['id'], user_id, 'integrante'))
        conn.commit()
        # cleanup
        session.pop('join_team_code', None)
        session.pop('join_team_user', None)
        cur.close(); conn.close()
        flash("Usuario agregado al equipo.")
        return redirect(url_for('dashboard_participante'))
    return render_template('confirm_join.html', codigo=codigo, username=username)

# Edit project (only members of team can edit)
@app.route("/project/<int:team_id>/edit", methods=["GET","POST"])
def edit_project(team_id):
    if 'usuario' not in session or session.get('rol') != 'participante':
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    conn = get_db(); cur = conn.cursor(dictionary=True)
    # verify membership
    cur.execute("SELECT * FROM team_members WHERE team_id=%s AND user_id=%s", (team_id, user_id))
    member = cur.fetchone()
    if not member:
        cur.close(); conn.close()
        flash("No tienes permiso para editar este proyecto.")
        return redirect(url_for('dashboard_participante'))
    # get project
    cur.execute("SELECT * FROM proyectos WHERE team_id=%s", (team_id,))
    project = cur.fetchone()
    if request.method == "POST":
        titulo = request.form.get('titulo').strip()
        descripcion = request.form.get('descripcion').strip()
        if not project:
            cur.execute("INSERT INTO proyectos (team_id, titulo, descripcion) VALUES (%s,%s,%s)", (team_id, titulo, descripcion))
            conn.commit()
            cur.execute("SELECT * FROM proyectos WHERE team_id=%s", (team_id,))
            project = cur.fetchone()
        else:
            cur.execute("UPDATE proyectos SET titulo=%s, descripcion=%s WHERE id=%s", (titulo, descripcion, project['id']))
            conn.commit()
        # handle files
        files = request.files.getlist("photos")
        for f in files:
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                # make unique
                filename = f"{team_id}_{int(os.times()[4])}_{filename}"
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                f.save(path)
                cur.execute("INSERT INTO project_files (project_id, filename) VALUES (%s,%s)", (project['id'] if project else cur.lastrowid, filename))
        conn.commit()
        cur.close(); conn.close()
        flash("Proyecto guardado.")
        return redirect(url_for('view_project', team_id=team_id))
    # GET
    cur.execute("SELECT pf.* FROM project_files pf JOIN proyectos p ON pf.project_id=p.id WHERE p.team_id=%s", (team_id,))
    files = cur.fetchall()
    cur.close(); conn.close()
    return render_template('edit_project.html', project=project, files=files, team_id=team_id)

# View project
@app.route("/project/<int:team_id>/view")
def view_project(team_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT p.*, t.nombre as equipo FROM proyectos p JOIN teams t ON p.team_id=t.id WHERE t.id=%s", (team_id,))
    project = cur.fetchone()
    if not project:
        cur.close(); conn.close()
        flash("Proyecto no encontrado.")
        return redirect(url_for('dashboard_participante'))
    cur.execute("SELECT * FROM project_files WHERE project_id=%s", (project['id'],))
    files = cur.fetchall()
    # determine if current user is member to show score
    can_view_score = False
    if 'user_id' in session:
        cur.execute("SELECT * FROM team_members WHERE team_id=%s AND user_id=%s", (team_id, session['user_id']))
        if cur.fetchone():
            can_view_score = True
    # get average score if any
    cur.execute("SELECT AVG(nota_total) as promedio FROM evaluaciones WHERE id_proyecto=%s", (project['id'],))
    avg = cur.fetchone()
    promedio = avg['promedio'] if avg and avg['promedio'] is not None else None
    cur.close(); conn.close()
    return render_template('view_project.html', project=project, files=files, can_view_score=can_view_score, promedio=promedio)

# Serve uploads
@app.route('/uploads/projects/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Juez: list projects and evaluate form
@app.route("/evaluate/<int:project_id>", methods=["GET","POST"])
def evaluate_project(project_id):
    if 'usuario' not in session or session.get('rol') != 'juez':
        return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(dictionary=True)
    # get project
    cur.execute("SELECT p.*, t.nombre as equipo FROM proyectos p JOIN teams t ON p.team_id=t.id WHERE p.id=%s", (project_id,))
    proyecto = cur.fetchone()
    if not proyecto:
        cur.close(); conn.close()
        flash("Proyecto no encontrado.")
        return redirect(url_for('dashboard_juez'))
    # get criterios
    cur.execute("SELECT * FROM criterios")
    criterios = cur.fetchall()
    if request.method == "POST":
        # insert evaluation
        cur.execute("INSERT INTO evaluaciones (id_proyecto, id_juez, nota_total) VALUES (%s,%s,%s)", (project_id, session['user_id'], 0))
        eval_id = cur.lastrowid
        total = 0.0
        for c in criterios:
            key = f"criterio_{c['id']}"
            puntaje = float(request.form.get(key, 0) or 0)
            cur.execute("INSERT INTO evaluacion_items (evaluacion_id, criterio_id, puntaje) VALUES (%s,%s,%s)", (eval_id, c['id'], puntaje))
            total += puntaje * float(c['peso'])
        # update total
        cur.execute("UPDATE evaluaciones SET nota_total=%s WHERE id=%s", (total, eval_id))
        conn.commit()
        cur.close(); conn.close()
        flash("Evaluación guardada.")
        return redirect(url_for('dashboard_juez'))
    cur.close(); conn.close()
    return render_template('evaluate.html', proyecto=proyecto, criterios=criterios)

# Juez dashboard: list projects
@app.route("/dashboard_juez")
def dashboard_juez():
    if 'usuario' not in session or session.get('rol') != 'juez':
        return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT p.id, p.titulo, t.nombre as equipo, p.anio FROM proyectos p JOIN teams t ON p.team_id=t.id")
    proyectos = cur.fetchall()
    cur.close(); conn.close()
    return render_template('dashboard_juez.html', usuario=session['usuario'], proyectos=proyectos)

# Results page (all averages)
@app.route("/resultados")
def resultados():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.id, p.titulo, t.nombre as equipo, IFNULL(AVG(e.nota_total),0) as promedio
        FROM proyectos p
        JOIN teams t ON p.team_id=t.id
        LEFT JOIN evaluaciones e ON e.id_proyecto=p.id
        GROUP BY p.id ORDER BY promedio DESC
    """)
    resultados = cur.fetchall()
    cur.close(); conn.close()
    return render_template('resultados.html', resultados=resultados)

# Publish winners (only juez can)
@app.route("/publicar_ganadores", methods=["POST"])
def publicar_ganadores():
    if 'usuario' not in session or session.get('rol') != 'juez':
        return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    # get top3 projects by average
    cur.execute("""
        SELECT p.id, IFNULL(AVG(e.nota_total),0) as promedio
        FROM proyectos p
        LEFT JOIN evaluaciones e ON e.id_proyecto=p.id
        GROUP BY p.id
        ORDER BY promedio DESC LIMIT 3
    """)
    top3 = cur.fetchall()
    # clear existing winners for that year - we will insert as historial with current year
    import datetime
    year = datetime.date.today().year
    # optional: clear existing winners for that year
    cur.execute("DELETE FROM ganadores_historial WHERE anio=%s", (year,))
    place = 1
    for row in top3:
        project_id = row[0]
        cur.execute("INSERT INTO ganadores_historial (proyecto_id, anio, puesto) VALUES (%s,%s,%s)", (project_id, year, place))
        place += 1
    # flip config flag publicar_ganadores to 1
    cur.execute("UPDATE configuracion SET valor='1' WHERE clave='publicar_ganadores'")
    conn.commit()
    cur.close(); conn.close()
    flash("Ganadores publicados.")
    return redirect(url_for('ganadores'))

# Ganadores page (public)
@app.route("/ganadores")
def ganadores():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    # check flag
    cur.execute("SELECT valor FROM configuracion WHERE clave='publicar_ganadores'")
    flag = cur.fetchone()
    publicar = flag and flag['valor'] == '1'
    winners = []
    if publicar:
        cur.execute("""
            SELECT gh.puesto, p.titulo, t.nombre as equipo, gh.anio
            FROM ganadores_historial gh
            JOIN proyectos p ON gh.proyecto_id=p.id
            JOIN teams t ON p.team_id=t.id
            ORDER BY gh.anio DESC, gh.puesto ASC
            LIMIT 3
        """)
        winners = cur.fetchall()
    cur.close(); conn.close()
    return render_template('ganadores.html', publicar=publicar, winners=winners)

# Historial
@app.route("/historial")
def historial():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT DISTINCT anio FROM proyectos ORDER BY anio DESC")
    anios = [r[0] for r in cur.fetchall()]
    historial = {}
    for a in anios:
        cur.execute("SELECT p.titulo, t.nombre as equipo FROM proyectos p JOIN teams t ON p.team_id=t.id WHERE p.anio=%s", (a,))
        proyectos = cur.fetchall()
        cur.execute("SELECT gh.puesto, p.titulo, t.nombre as equipo FROM ganadores_historial gh JOIN proyectos p ON gh.proyecto_id=p.id JOIN teams t ON p.team_id=t.id WHERE gh.anio=%s ORDER BY gh.puesto ASC", (a,))
        ganadores = cur.fetchall()
        historial[a] = {'proyectos': proyectos, 'ganadores': ganadores}
    cur.close(); conn.close()
    return render_template('historial.html', historial=historial)

# Run
if __name__ == "__main__":
    # Port 3000 as you requested
    app.run(debug=True, port=3000)
