from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ── DATABASE ──────────────────────────────
engine = create_engine("sqlite:///coreinventory.db", connect_args={"check_same_thread": False})
Base = declarative_base()
Session = sessionmaker(bind=engine)

# ── MODELS ────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True)
    username   = Column(String, unique=True)
    password   = Column(String)
    role       = Column(String, default="staff")
    created_at = Column(DateTime, default=datetime.utcnow)

class Warehouse(Base):
    __tablename__ = "warehouses"
    id         = Column(Integer, primary_key=True)
    name       = Column(String, unique=True)
    short_code = Column(String, default="WH")
    location   = Column(String)

class Product(Base):
    __tablename__ = "products"
    id              = Column(Integer, primary_key=True)
    name            = Column(String)
    sku             = Column(String, unique=True)
    category        = Column(String)
    unit_of_measure = Column(String)
    unit_cost       = Column(Float, default=0)
    current_stock   = Column(Float, default=0)
    reorder_level   = Column(Float, default=10)
    warehouse_id    = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

class Receipt(Base):
    __tablename__ = "receipts"
    id            = Column(Integer, primary_key=True)
    reference     = Column(String, unique=True)
    receive_from  = Column(String)
    schedule_date = Column(String)
    responsible   = Column(String)
    status        = Column(String, default="Draft")
    warehouse_id  = Column(Integer, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    validated_at  = Column(DateTime, nullable=True)
    lines         = relationship("ReceiptLine", back_populates="receipt")

class ReceiptLine(Base):
    __tablename__ = "receipt_lines"
    id           = Column(Integer, primary_key=True)
    receipt_id   = Column(Integer, ForeignKey("receipts.id"))
    product_name = Column(String)
    quantity     = Column(Float, default=0)
    receipt      = relationship("Receipt", back_populates="lines")

class Delivery(Base):
    __tablename__ = "deliveries"
    id               = Column(Integer, primary_key=True)
    reference        = Column(String, unique=True)
    delivery_address = Column(String)
    schedule_date    = Column(String)
    responsible      = Column(String)
    status           = Column(String, default="Draft")
    warehouse_id     = Column(Integer, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    validated_at     = Column(DateTime, nullable=True)
    lines            = relationship("DeliveryLine", back_populates="delivery")

class DeliveryLine(Base):
    __tablename__ = "delivery_lines"
    id           = Column(Integer, primary_key=True)
    delivery_id  = Column(Integer, ForeignKey("deliveries.id"))
    product_name = Column(String)
    quantity     = Column(Float, default=0)
    delivery     = relationship("Delivery", back_populates="lines")

class Adjustment(Base):
    __tablename__ = "adjustments"
    id         = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    old_stock  = Column(Float)
    new_stock  = Column(Float)
    reason     = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class MoveHistory(Base):
    __tablename__ = "move_history"
    id             = Column(Integer, primary_key=True)
    reference      = Column(String)
    operation_type = Column(String)
    contact        = Column(String)
    from_location  = Column(String)
    to_location    = Column(String)
    product_name   = Column(String)
    quantity       = Column(Float, default=0)
    status         = Column(String, default="Done")
    created_at     = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ── AUTH ──────────────────────────────────
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    db = Session()
    user = db.query(User).filter(User.username == data["username"]).first()
    db.close()
    if not user or user.password != data["password"]:
        return jsonify({"detail": "Invalid credentials"}), 401
    return jsonify({"message": "Login successful", "user": {"id": user.id, "username": user.username, "role": user.role}})

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json
    db = Session()
    if db.query(User).filter(User.username == data["username"]).first():
        db.close()
        return jsonify({"detail": "Username already exists"}), 400
    user = User(username=data["username"], password=data["password"], role=data.get("role", "staff"))
    db.add(user); db.commit()
    result = {"id": user.id, "username": user.username, "role": user.role}
    db.close()
    return jsonify(result)

# ── DASHBOARD ─────────────────────────────
@app.route("/dashboard/kpis")
def dashboard_kpis():
    db = Session()
    total    = db.query(Product).count()
    low      = db.query(Product).filter(Product.current_stock <= Product.reorder_level).count()
    pending_r = db.query(Receipt).filter(Receipt.status.in_(["Draft","Ready"])).count()
    pending_d = db.query(Delivery).filter(Delivery.status.in_(["Draft","Waiting","Ready"])).count()
    db.close()
    return jsonify({"total_products": total, "low_stock_items": low, "pending_receipts": pending_r, "pending_deliveries": pending_d})

# ── PRODUCTS ──────────────────────────────
@app.route("/products", methods=["GET"])
def get_products():
    db = Session()
    products = db.query(Product).all()
    result = [{"id": p.id, "name": p.name, "sku": p.sku, "category": p.category,
               "unit_of_measure": p.unit_of_measure, "unit_cost": p.unit_cost,
               "current_stock": p.current_stock, "reorder_level": p.reorder_level,
               "warehouse_id": p.warehouse_id} for p in products]
    db.close()
    return jsonify(result)

@app.route("/products", methods=["POST"])
def create_product():
    data = request.json
    db = Session()
    p = Product(name=data["name"], sku=data.get("sku",""), category=data.get("category",""),
                unit_of_measure=data.get("unit_of_measure",""), unit_cost=data.get("unit_cost",0),
                current_stock=data.get("current_stock",0), reorder_level=data.get("reorder_level",10),
                warehouse_id=data.get("warehouse_id"))
    db.add(p); db.commit()
    result = {"id": p.id, "name": p.name, "sku": p.sku, "category": p.category,
              "unit_of_measure": p.unit_of_measure, "unit_cost": p.unit_cost,
              "current_stock": p.current_stock, "reorder_level": p.reorder_level,
              "warehouse_id": p.warehouse_id}
    db.close()
    return jsonify(result)

@app.route("/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    db = Session()
    p = db.query(Product).filter(Product.id == pid).first()
    if p: db.delete(p); db.commit()
    db.close()
    return jsonify({"message": "Deleted"})

# ── WAREHOUSES ────────────────────────────
@app.route("/warehouses", methods=["GET"])
def get_warehouses():
    db = Session()
    warehouses = db.query(Warehouse).all()
    result = [{"id": w.id, "name": w.name, "short_code": w.short_code, "location": w.location} for w in warehouses]
    db.close()
    return jsonify(result)

@app.route("/warehouses", methods=["POST"])
def create_warehouse():
    data = request.json
    db = Session()
    w = Warehouse(name=data["name"], short_code=data.get("short_code","WH"), location=data.get("location",""))
    db.add(w); db.commit()
    result = {"id": w.id, "name": w.name, "short_code": w.short_code, "location": w.location}
    db.close()
    return jsonify(result)

# ── RECEIPTS ──────────────────────────────
@app.route("/receipts", methods=["GET"])
def get_receipts():
    db = Session()
    receipts = db.query(Receipt).order_by(Receipt.created_at.desc()).all()
    result = [{"id": r.id, "reference": r.reference, "receive_from": r.receive_from,
               "schedule_date": r.schedule_date, "responsible": r.responsible,
               "status": r.status, "warehouse_id": r.warehouse_id,
               "created_at": r.created_at.isoformat(),
               "lines": [{"id": l.id, "product_name": l.product_name, "quantity": l.quantity} for l in r.lines]}
              for r in receipts]
    db.close()
    return jsonify(result)

@app.route("/receipts", methods=["POST"])
def create_receipt():
    data = request.json
    db = Session()
    r = Receipt(reference=data["reference"], receive_from=data.get("receive_from",""),
                schedule_date=data.get("schedule_date"), responsible=data.get("responsible"),
                warehouse_id=data.get("warehouse_id"), status="Draft")
    db.add(r); db.flush()
    for line in data.get("lines", []):
        db.add(ReceiptLine(receipt_id=r.id, product_name=line["product_name"], quantity=line["quantity"]))
    db.commit()
    result = {"id": r.id, "reference": r.reference, "receive_from": r.receive_from,
              "schedule_date": r.schedule_date, "responsible": r.responsible,
              "status": r.status, "warehouse_id": r.warehouse_id,
              "created_at": r.created_at.isoformat(), "lines": []}
    db.close()
    return jsonify(result)

@app.route("/receipts/<int:rid>/validate", methods=["POST"])
def validate_receipt(rid):
    db = Session()
    r = db.query(Receipt).filter(Receipt.id == rid).first()
    if not r or r.status == "Done":
        db.close()
        return jsonify({"detail": "Not found or already done"}), 404
    for line in r.lines:
        p = db.query(Product).filter(Product.name == line.product_name).first()
        if p: p.current_stock += line.quantity
    r.status = "Done"; r.validated_at = datetime.utcnow()
    total = sum(l.quantity for l in r.lines)
    names = ", ".join(l.product_name for l in r.lines)
    db.add(MoveHistory(reference=r.reference, operation_type="Receipt", contact=r.receive_from,
                       from_location="Vendor", to_location="WH/Stock", product_name=names, quantity=total))
    db.commit(); db.close()
    return jsonify({"message": "Validated"})

# ── DELIVERIES ────────────────────────────
@app.route("/deliveries", methods=["GET"])
def get_deliveries():
    db = Session()
    deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).all()
    result = [{"id": d.id, "reference": d.reference, "delivery_address": d.delivery_address,
               "schedule_date": d.schedule_date, "responsible": d.responsible,
               "status": d.status, "warehouse_id": d.warehouse_id,
               "created_at": d.created_at.isoformat(),
               "lines": [{"id": l.id, "product_name": l.product_name, "quantity": l.quantity} for l in d.lines]}
              for d in deliveries]
    db.close()
    return jsonify(result)

@app.route("/deliveries", methods=["POST"])
def create_delivery():
    data = request.json
    db = Session()
    d = Delivery(reference=data["reference"], delivery_address=data.get("delivery_address",""),
                 schedule_date=data.get("schedule_date"), responsible=data.get("responsible"), status="Draft")
    db.add(d); db.flush()
    for line in data.get("lines", []):
        db.add(DeliveryLine(delivery_id=d.id, product_name=line["product_name"], quantity=line["quantity"]))
    db.commit()
    result = {"id": d.id, "reference": d.reference, "delivery_address": d.delivery_address,
              "schedule_date": d.schedule_date, "responsible": d.responsible,
              "status": d.status, "warehouse_id": d.warehouse_id,
              "created_at": d.created_at.isoformat(), "lines": []}
    db.close()
    return jsonify(result)

@app.route("/deliveries/<int:did>/validate", methods=["POST"])
def validate_delivery(did):
    db = Session()
    d = db.query(Delivery).filter(Delivery.id == did).first()
    if not d or d.status == "Done":
        db.close()
        return jsonify({"detail": "Not found or already done"}), 404
    for line in d.lines:
        p = db.query(Product).filter(Product.name == line.product_name).first()
        if p and p.current_stock >= line.quantity:
            p.current_stock -= line.quantity
    d.status = "Done"; d.validated_at = datetime.utcnow()
    total = sum(l.quantity for l in d.lines)
    names = ", ".join(l.product_name for l in d.lines)
    db.add(MoveHistory(reference=d.reference, operation_type="Delivery", contact=d.delivery_address,
                       from_location="WH/Stock", to_location="Customer", product_name=names, quantity=total))
    db.commit(); db.close()
    return jsonify({"message": "Validated"})

# ── ADJUSTMENTS ───────────────────────────
@app.route("/adjustments", methods=["POST"])
def create_adjustment():
    data = request.json
    db = Session()
    p = db.query(Product).filter(Product.id == data["product_id"]).first()
    if not p:
        db.close()
        return jsonify({"detail": "Product not found"}), 404
    old = p.current_stock
    p.current_stock = data["new_stock"]
    adj = Adjustment(product_id=p.id, old_stock=old, new_stock=data["new_stock"], reason=data.get("reason",""))
    db.add(adj)
    db.add(MoveHistory(reference="ADJ", operation_type="Adjustment", contact="Internal",
                       from_location="System", to_location="System", product_name=p.name,
                       quantity=data["new_stock"] - old))
    db.commit()
    result = {"id": adj.id, "product_id": adj.product_id, "old_stock": adj.old_stock,
              "new_stock": adj.new_stock, "reason": adj.reason}
    db.close()
    return jsonify(result)

# ── HISTORY ───────────────────────────────
@app.route("/history", methods=["GET"])
def get_history():
    db = Session()
    history = db.query(MoveHistory).order_by(MoveHistory.created_at.desc()).limit(200).all()
    result = [{"id": h.id, "reference": h.reference, "operation_type": h.operation_type,
               "contact": h.contact, "from_location": h.from_location, "to_location": h.to_location,
               "product_name": h.product_name, "quantity": h.quantity,
               "status": h.status, "created_at": h.created_at.isoformat()} for h in history]
    db.close()
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
