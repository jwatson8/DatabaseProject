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


if __name__ == "__main__":
    app.run(debug=True)
