from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time, timedelta

WORK_START = time(8, 0)
WORK_END = time(19, 0)
SLOT_MINUTES = 15

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///barbershop.db"
db = SQLAlchemy(app)


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

def generate_time_slots(start, end, step_minutes):
    slots = []
    current = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    while current <= end_dt:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=step_minutes)
    return slots


@app.route("/")
def index():
    time_slots = generate_time_slots(WORK_START, WORK_END, SLOT_MINUTES)
    return render_template("index.html", today=date.today().isoformat(), time_slots=time_slots)


@app.route("/order", methods=["POST"])
def order():
    name = request.form["name"]
    phone = request.form["phone"]
    service = request.form["service"]

    order_date = date.fromisoformat(request.form["date"])
    order_time = time.fromisoformat(request.form["time"])

    if not (WORK_START <= order_time <= WORK_END):
        return "Uhrzeit liegt außerhalb der Öffnungszeiten (08:00–19:00)", 400

    appointment_time = datetime.combine(order_date, order_time)

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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)