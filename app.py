from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time, timedelta
from functools import wraps
from flask import session
from datetime import date as date_cls

MAX_BOOKING_DAYS = 30  # wie weit im Voraus gebucht werden darf
WORK_START = time(8, 0)
WORK_END = time(19, 0)
SLOT_MINUTES = 15

SERVICES = {
    "haircut": "Haarschnitt",
    "beard": "Bart trimmen",
    "both": "Haarschnitt + Bart",
    "kids": "Kinderhaarschnitt",
}


ORDER_STATUSES = ["angefragt", "bestätigt", "erledigt", "storniert", "nicht erschienen"]
ACTIVE_STATUSES = ["angefragt", "bestätigt"]


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///barbershop.db"
db = SQLAlchemy(app)

app.config["SECRET_KEY"] = "Asizsf9629oizsASIOZois08972oihS908iu98zs987"
ADMIN_PASSWORD = "Vorzeigen"


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    service = db.Column(db.String(50), nullable=False)
    appointment_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="angefragt")

    def __repr__(self):
        return f"<Order {self.id}: {self.name}, {self.service}, {self.appointment_time}>"

SORT_COLUMNS = {
    "date": Order.appointment_time,
    "name": Order.name,
    "phone": Order.phone,
    "service": Order.service,
    "status": Order.status,
}

def generate_time_slots(start, end, step_minutes):
    slots = []
    current = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    while current <= end_dt:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=step_minutes)
    return slots

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    time_slots = generate_time_slots(WORK_START, WORK_END, SLOT_MINUTES)
    today = date.today()
    max_date = today + timedelta(days=MAX_BOOKING_DAYS)
    return render_template(
        "index.html",
        today=today.isoformat(),
        max_date=max_date.isoformat(),
        time_slots=time_slots,
        services=SERVICES,
        now_iso=datetime.now().isoformat()
    )

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin_orders"))
        else:
            error = "Falsches Passwort"
    return render_template("login.html", error=error)

@app.route("/admin/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/order", methods=["POST"])
def order():
    name = request.form["name"]

    phone_prefix = request.form["phone_prefix"]
    phone_number = request.form["phone_number"]
    if not phone_number.isdigit():
        return "Telefonnummer darf nur Ziffern enthalten", 400
    phone = f"{phone_prefix} {phone_number}"

    service = request.form["service"]

    order_date = date.fromisoformat(request.form["date"])
    order_time = time.fromisoformat(request.form["time"])

    today = date.today()
    max_date = today + timedelta(days=MAX_BOOKING_DAYS)

    if not (today <= order_date <= max_date):
        return f"Datum muss zwischen heute und {max_date.strftime('%d.%m.%Y')} liegen", 400

    if not (WORK_START <= order_time <= WORK_END):
        return "Uhrzeit liegt außerhalb der Öffnungszeiten (08:00–19:00)", 400

    appointment_time = datetime.combine(order_date, order_time)

    if appointment_time < datetime.now():
        return "Der gewählte Termin liegt in der Vergangenheit", 400

    new_order = Order(
        name=name,
        phone=phone,
        service=service,
        appointment_time=appointment_time
    )
    db.session.add(new_order)
    db.session.commit()

    return redirect(url_for("order_success"))

@app.route("/order/success")
def order_success():
    return render_template("order_success.html")


@app.route("/admin/orders")
@login_required
def admin_orders():
    query = Order.query.filter(Order.status.in_(ACTIVE_STATUSES))

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(
            db.or_(
                Order.name.ilike(f"%{search}%"),
                Order.phone.ilike(f"%{search}%")
            )
        )

    sort = request.args.get("sort", "date")
    direction = request.args.get("dir", "asc")
    sort_column = SORT_COLUMNS.get(sort, Order.appointment_time)

    if direction == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    orders = query.all()

    today = date_cls.today()
    today_orders = [o for o in orders if o.appointment_time.date() == today]
    upcoming_orders = [o for o in orders if o.appointment_time.date() != today]

    return render_template(
        "admin_orders.html",
        today_orders=today_orders,
        upcoming_orders=upcoming_orders,
        services=SERVICES,
        statuses=ORDER_STATUSES,
        now=datetime.now(),
        search=search,
        sort=sort,
        direction=direction
    )



@app.route("/admin/orders/archived")
@login_required
def admin_orders_archived():
    query = Order.query.filter(~Order.status.in_(ACTIVE_STATUSES))

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(
            db.or_(
                Order.name.ilike(f"%{search}%"),
                Order.phone.ilike(f"%{search}%")
            )
        )

    sort = request.args.get("sort", "date")
    direction = request.args.get("dir", "desc")
    sort_column = SORT_COLUMNS.get(sort, Order.appointment_time)

    if direction == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    orders = query.all()

    return render_template(
        "admin_orders_archived.html",
        orders=orders,
        services=SERVICES,
        statuses=ORDER_STATUSES,
        search=search,
        sort=sort,
        direction=direction
    )

@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@login_required
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form["status"]

    if new_status not in ORDER_STATUSES:
        return "Ungültiger Status", 400

    order.status = new_status
    db.session.commit()

    return redirect(url_for("admin_orders"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)