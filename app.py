from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/order", methods=["POST"])
def order():
    name = request.form["name"]
    phone = request.form["phone"]
    service = request.form["service"]
    appointment_time = datetime.fromisoformat(request.form["datetime"])

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