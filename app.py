# app.py
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

DATABASE = "therapy_practice.sqlite"
SECRET_KEY = "change-this-to-a-random-secret"

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


# --------- DB HELPER ---------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --------- AUTH HELPERS ---------
def login_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(**kwargs)

    return wrapped_view


# --------- ROUTES: AUTH ---------
@app.route("/login", methods=["GET", "POST"])
def login():
    db = get_db()
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = db.execute(
            "SELECT user_id, username, password_hash, role FROM USERS WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None:
            flash("Invalid username or password.", "danger")
        else:
            # In your sample data, password_hash is just 'hash1', 'hash2', etc.
            # For class purposes, we will accept any password that matches the stored string.
            # If you want real hashing, generate_password_hash and check_password_hash.
            stored = user["password_hash"]
            if password == stored:  # simple for class demo
                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------- ROUTES: DASHBOARD + CHART ---------
@app.route("/")
@login_required
def dashboard():
    db = get_db()
    # Example data: number of appointments per service
    rows = db.execute(
        """
        SELECT S.service_name AS service_name,
               COUNT(A.appointment_id) AS num_appointments
        FROM SERVICES S
        LEFT JOIN APPOINTMENTS A ON A.service_id = S.service_id
        GROUP BY S.service_id
        ORDER BY S.service_name;
        """
    ).fetchall()

    labels = [row["service_name"] for row in rows]
    values = [row["num_appointments"] for row in rows]

    return render_template("dashboard.html", labels=labels, values=values)


# --------- ROUTES: CLIENTS CRUD ---------
@app.route("/clients")
@login_required
def clients_list():
    db = get_db()
    clients = db.execute(
        "SELECT * FROM CLIENTS ORDER BY last_name, first_name"
    ).fetchall()
    return render_template("clients_list.html", clients=clients)


@app.route("/clients/new", methods=["GET", "POST"])
@login_required
def client_create():
    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        dob = request.form["date_of_birth"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()
        address = request.form["address"].strip()
        ec_name = request.form["emergency_contact_name"].strip()
        ec_phone = request.form["emergency_contact_phone"].strip()

        db = get_db()
        db.execute(
            """
            INSERT INTO CLIENTS
            (first_name, last_name, date_of_birth, phone, email, address,
             emergency_contact_name, emergency_contact_phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (first_name, last_name, dob, phone, email, address, ec_name, ec_phone),
        )
        db.commit()
        return redirect(url_for("clients_list"))

    return render_template("client_form.html", client=None)


@app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def client_edit(client_id):
    db = get_db()
    client = db.execute(
        "SELECT * FROM CLIENTS WHERE client_id = ?", (client_id,)
    ).fetchone()

    if client is None:
        return "Client not found", 404

    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        dob = request.form["date_of_birth"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()
        address = request.form["address"].strip()
        ec_name = request.form["emergency_contact_name"].strip()
        ec_phone = request.form["emergency_contact_phone"].strip()

        db.execute(
            """
            UPDATE CLIENTS
            SET first_name = ?, last_name = ?, date_of_birth = ?, phone = ?,
                email = ?, address = ?, emergency_contact_name = ?, emergency_contact_phone = ?
            WHERE client_id = ?
            """,
            (first_name, last_name, dob, phone, email, address, ec_name, ec_phone, client_id),
        )
        db.commit()
        return redirect(url_for("clients_list"))

    return render_template("client_form.html", client=client)


@app.route("/clients/<int:client_id>/delete", methods=["POST"])
@login_required
def client_delete(client_id):
    db = get_db()
    db.execute("DELETE FROM CLIENTS WHERE client_id = ?", (client_id,))
    db.commit()
    return redirect(url_for("clients_list"))


# --------- ROUTES: SERVICES CRUD ---------
@app.route("/services")
@login_required
def services_list():
    db = get_db()
    services = db.execute(
        "SELECT * FROM SERVICES ORDER BY service_name"
    ).fetchall()
    return render_template("services_list.html", services=services)


@app.route("/services/new", methods=["GET", "POST"])
@login_required
def service_create():
    if request.method == "POST":
        name = request.form["service_name"].strip()
        db = get_db()
        db.execute(
            "INSERT INTO SERVICES (service_name) VALUES (?)",
            (name,),
        )
        db.commit()
        return redirect(url_for("services_list"))
    return render_template("service_form.html", service=None)


@app.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@login_required
def service_edit(service_id):
    db = get_db()
    service = db.execute(
        "SELECT * FROM SERVICES WHERE service_id = ?", (service_id,)
    ).fetchone()

    if service is None:
        return "Service not found", 404

    if request.method == "POST":
        name = request.form["service_name"].strip()
        db.execute(
            "UPDATE SERVICES SET service_name = ? WHERE service_id = ?",
            (name, service_id),
        )
        db.commit()
        return redirect(url_for("services_list"))

    return render_template("service_form.html", service=service)


@app.route("/services/<int:service_id>/delete", methods=["POST"])
@login_required
def service_delete(service_id):
    db = get_db()
    db.execute("DELETE FROM SERVICES WHERE service_id = ?", (service_id,))
    db.commit()
    return redirect(url_for("services_list"))


# --------- ROUTES: APPOINTMENTS CRUD ---------
@app.route("/appointments")
@login_required
def appointments_list():
    db = get_db()
    appointments = db.execute(
        """
        SELECT A.appointment_id,
               A.start_datetime AS start_time,
               A.end_datetime AS end_time,
               A.notes,
               C.client_id, C.first_name, C.last_name,
               S.service_id, S.service_name
        FROM APPOINTMENTS A
        LEFT JOIN CLIENTS C ON A.client_id = C.client_id
        LEFT JOIN SERVICES S ON A.service_id = S.service_id
        ORDER BY A.start_datetime DESC
        """
    ).fetchall()
    return render_template("appointments_list.html", appointments=appointments)


@app.route("/appointments/new", methods=["GET", "POST"])
@login_required
def appointment_create():
    db = get_db()
    clients = db.execute(
        "SELECT client_id, first_name, last_name FROM CLIENTS ORDER BY last_name, first_name"
    ).fetchall()
    services = db.execute(
        "SELECT service_id, service_name FROM SERVICES ORDER BY service_name"
    ).fetchall()

    if request.method == "POST":
        client_id = request.form["client_id"]
        service_id = request.form["service_id"]
        # datetime-local sends 'YYYY-MM-DDTHH:MM' — store as 'YYYY-MM-DD HH:MM'
        start_time = request.form["start_time"].strip().replace("T", " ")
        end_time = request.form.get("end_time", "").strip()
        end_time = end_time.replace("T", " ") if end_time else None
        notes = request.form.get("notes", "").strip()

        db.execute(
            "INSERT INTO APPOINTMENTS (client_id, service_id, start_datetime, end_datetime, notes) VALUES (?, ?, ?, ?, ?)",
            (client_id, service_id, start_time, end_time, notes),
        )
        db.commit()
        return redirect(url_for("appointments_list"))

    return render_template("appointment_form.html", appointment=None, clients=clients, services=services)


@app.route("/appointments/<int:appointment_id>/edit", methods=["GET", "POST"])
@login_required
def appointment_edit(appointment_id):
    db = get_db()
    appointment = db.execute(
        """
        SELECT appointment_id, client_id, service_id,
               start_datetime AS start_time,
               end_datetime AS end_time,
               notes
        FROM APPOINTMENTS
        WHERE appointment_id = ?
        """,
        (appointment_id,),
    ).fetchone()

    if appointment is None:
        return "Appointment not found", 404

    clients = db.execute(
        "SELECT client_id, first_name, last_name FROM CLIENTS ORDER BY last_name, first_name"
    ).fetchall()
    services = db.execute(
        "SELECT service_id, service_name FROM SERVICES ORDER BY service_name"
    ).fetchall()

    if request.method == "POST":
        client_id = request.form["client_id"]
        service_id = request.form["service_id"]
        start_time = request.form["start_time"].strip().replace("T", " ")
        end_time = request.form.get("end_time", "").strip()
        end_time = end_time.replace("T", " ") if end_time else None
        notes = request.form.get("notes", "").strip()

        db.execute(
            "UPDATE APPOINTMENTS SET client_id = ?, service_id = ?, start_datetime = ?, end_datetime = ?, notes = ? WHERE appointment_id = ?",
            (client_id, service_id, start_time, end_time, notes, appointment_id),
        )
        db.commit()
        return redirect(url_for("appointments_list"))

    return render_template("appointment_form.html", appointment=appointment, clients=clients, services=services)


@app.route("/appointments/<int:appointment_id>/delete", methods=["POST"])
@login_required
def appointment_delete(appointment_id):
    db = get_db()
    db.execute("DELETE FROM APPOINTMENTS WHERE appointment_id = ?", (appointment_id,))
    db.commit()
    return redirect(url_for("appointments_list"))


# --------- ROUTES: INVOICES CRUD ---------
@app.route("/invoices")
@login_required
def invoices_list():
    db = get_db()
    invoices = db.execute("SELECT * FROM INVOICES ORDER BY invoice_id DESC").fetchall()
    return render_template("invoices_list.html", invoices=invoices)


def _invoice_columns(db):
    cols = db.execute("PRAGMA table_info('INVOICES')").fetchall()
    # return list of column names excluding primary invoice_id
    return [c["name"] for c in cols if c["name"] != "invoice_id"]


@app.route("/invoices/new", methods=["GET", "POST"])
@login_required
def invoice_create():
    db = get_db()
    invoice_cols = _invoice_columns(db)

    # helpful lists for selects (if those columns exist)
    clients = db.execute("SELECT client_id, first_name, last_name FROM CLIENTS ORDER BY last_name, first_name").fetchall()
    appointments = db.execute("SELECT appointment_id, start_datetime FROM APPOINTMENTS ORDER BY start_datetime DESC").fetchall()

    if request.method == "POST":
        keys = []
        vals = []
        for col in invoice_cols:
            # map form names: use same names as columns; 'paid' checkbox handled specially
            if col == "paid":
                v = 1 if request.form.get("paid") else 0
            else:
                v = request.form.get(col)
                if isinstance(v, str) and "T" in v and ("issued_date" in col or "date" in col or "time" in col):
                    v = v.replace("T", " ")
            # include only provided values (allow NULL if blank)
            keys.append(col)
            vals.append(v if v != "" else None)

        if keys:
            placeholders = ",".join(["?"] * len(keys))
            q = f"INSERT INTO INVOICES ({', '.join(keys)}) VALUES ({placeholders})"
            db.execute(q, tuple(vals))
            db.commit()
        return redirect(url_for("invoices_list"))

    return render_template("invoice_form.html", invoice=None, invoice_cols=invoice_cols, clients=clients, appointments=appointments)


@app.route("/invoices/<int:invoice_id>/edit", methods=["GET", "POST"])
@login_required
def invoice_edit(invoice_id):
    db = get_db()
    invoice = db.execute("SELECT * FROM INVOICES WHERE invoice_id = ?", (invoice_id,)).fetchone()
    if invoice is None:
        return "Invoice not found", 404

    invoice_cols = _invoice_columns(db)
    clients = db.execute("SELECT client_id, first_name, last_name FROM CLIENTS ORDER BY last_name, first_name").fetchall()
    appointments = db.execute("SELECT appointment_id, start_datetime FROM APPOINTMENTS ORDER BY start_datetime DESC").fetchall()

    if request.method == "POST":
        sets = []
        vals = []
        for col in invoice_cols:
            if col == "paid":
                v = 1 if request.form.get("paid") else 0
            else:
                v = request.form.get(col)
                if isinstance(v, str) and "T" in v and ("issued_date" in col or "date" in col or "time" in col):
                    v = v.replace("T", " ")
            sets.append(f"{col} = ?")
            vals.append(v if v != "" else None)

        if sets:
            q = f"UPDATE INVOICES SET {', '.join(sets)} WHERE invoice_id = ?"
            vals.append(invoice_id)
            db.execute(q, tuple(vals))
            db.commit()
        return redirect(url_for("invoices_list"))

    return render_template("invoice_form.html", invoice=invoice, invoice_cols=invoice_cols, clients=clients, appointments=appointments)


@app.route("/invoices/<int:invoice_id>/delete", methods=["POST"])
@login_required
def invoice_delete(invoice_id):
    db = get_db()
    db.execute("DELETE FROM INVOICES WHERE invoice_id = ?", (invoice_id,))
    db.commit()
    return redirect(url_for("invoices_list"))


if __name__ == "__main__":
    app.run(debug=True)
