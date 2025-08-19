import random
from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Simpele in-memory storage (vervang door database in productie)
users = {}  # username: {password_hash, role, restaurant_id}
restaurants = {}  # restaurant_id: {name, employees, rosters}
availabilities = {}  # username: [dates]
reservations = {}  # restaurant_id: {date: n_reservations}
rosters = {} # restaurant_id: {date: [{username, shift}]}
open_shifts = {} # restaurant_id: {date: [shift_details]}

def predict_busy_level(restaurant_id, date):
    """Voorspel drukte op basis van dag, weer, reserveringen (dummy versie)."""
    day = date.weekday()
    # Dummy: weekend = drukker
    busy = 10 if day in [4,5,6] else 5
    busy += reservations.get(restaurant_id, {}).get(date.strftime('%Y-%m-%d'), 0) // 10
    # Dummy: weer (random)
    weather_bonus = random.choice([0,2])
    busy += weather_bonus
    return busy

def generate_roster(restaurant_id, date):
    busy_level = predict_busy_level(restaurant_id, date)
    employee_list = restaurants[restaurant_id]["employees"]
    available_employees = [u for u in employee_list if date.strftime('%Y-%m-%d') in availabilities.get(u, [])]
    required = min(len(available_employees), max(1, busy_level // 3))
    shifts = []
    for i, user in enumerate(available_employees[:required]):
        shifts.append({"username": user, "shift": "16:00-22:00"})
    open_slots = busy_level - required
    open_shifts[restaurant_id][date.strftime('%Y-%m-%d')] = []
    for i in range(open_slots):
        open_shifts[restaurant_id][date.strftime('%Y-%m-%d')].append({"shift": "16:00-22:00"})
    rosters[restaurant_id][date.strftime('%Y-%m-%d')] = shifts

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and check_password_hash(users[username]["password_hash"], password):
            session["username"] = username
            session["role"] = users[username]["role"]
            session["restaurant_id"] = users[username].get("restaurant_id")
            return redirect(url_for("dashboard"))
        else:
            flash("Login mislukt, probeer opnieuw.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]  # "employee", "restaurant", "admin"
        restaurant_id = request.form.get("restaurant_id")
        if username in users:
            flash("Gebruikersnaam bestaat al.", "danger")
            return redirect(url_for("register"))
        users[username] = {
            "password_hash": generate_password_hash(password),
            "role": role,
            "restaurant_id": restaurant_id,
        }
        if role == "employee" and restaurant_id:
            restaurants[restaurant_id]["employees"].append(username)
        flash("Registratie succesvol! Log nu in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", restaurants=restaurants)

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    role = session["role"]
    restaurant_id = session.get("restaurant_id")
    return render_template("dashboard.html", username=username, role=role, restaurant_id=restaurant_id, restaurants=restaurants)

@app.route("/availability", methods=["GET", "POST"])
def availability():
    if "username" not in session or session["role"] != "employee":
        return redirect(url_for("login"))
    username = session["username"]
    if request.method == "POST":
        dates = request.form.getlist("dates")
        availabilities[username] = dates
        flash("Beschikbaarheid opgeslagen!", "success")
        return redirect(url_for("dashboard"))
    # Toon komende 7 dagen
    days = [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    return render_template("availability.html", days=days, selected=availabilities.get(username, []))

@app.route("/generate_roster/<date>")
def generate_roster_page(date):
    if "username" not in session or session["role"] not in ["admin", "restaurant"]:
        return redirect(url_for("login"))
    restaurant_id = session["restaurant_id"]
    if restaurant_id not in rosters:
        rosters[restaurant_id] = {}
    if restaurant_id not in open_shifts:
        open_shifts[restaurant_id] = {}
    generate_roster(restaurant_id, datetime.strptime(date, "%Y-%m-%d"))
    flash(f"Rooster gegenereerd voor {date}!", "success")
    return redirect(url_for("view_roster", date=date))

@app.route("/roster/<date>")
def view_roster(date):
    if "username" not in session:
        return redirect(url_for("login"))
    restaurant_id = session["restaurant_id"]
    shifts = rosters.get(restaurant_id, {}).get(date, [])
    open_slots = open_shifts.get(restaurant_id, {}).get(date, [])
    return render_template("roster.html", shifts=shifts, open_slots=open_slots, date=date)

@app.route("/claim_shift/<date>/<shift_id>")
def claim_shift(date, shift_id):
    if "username" not in session or session["role"] != "employee":
        return redirect(url_for("login"))
    restaurant_id = session["restaurant_id"]
    shift = open_shifts[restaurant_id][date].pop(int(shift_id))
    rosters[restaurant_id][date].append({"username": session["username"], "shift": shift["shift"]})
    flash("Dienst geclaimd!", "success")
    return redirect(url_for("view_roster", date=date))

@app.route("/restaurants", methods=["GET", "POST"])
def manage_restaurants():
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form["name"]
        restaurant_id = str(len(restaurants)+1)
        restaurants[restaurant_id] = {"name": name, "employees": [], "rosters": {}}
        flash("Restaurant toegevoegd!", "success")
    return render_template("restaurants.html", restaurants=restaurants)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    restaurants["1"] = {"name": "Demo Restaurant", "employees": [], "rosters": {}}
    app.run(debug=True)