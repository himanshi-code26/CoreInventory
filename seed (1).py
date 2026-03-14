from main import engine, Base, Session, User, Warehouse, Product
Base.metadata.create_all(engine)
db = Session()
try:
    db.add(User(username="admin", password="admin123", role="manager"))
    db.add(User(username="staff", password="staff123", role="staff"))
    db.commit()
    wh1 = Warehouse(name="Main Warehouse", short_code="WH", location="Building A")
    db.add(wh1); db.commit()
    db.add(Product(name="[DESK001] Desk", sku="DESK001", category="Furniture", unit_of_measure="units", unit_cost=3000, current_stock=50, reorder_level=10))
    db.add(Product(name="Steel Rods", sku="STL001", category="Raw Materials", unit_of_measure="kg", unit_cost=150, current_stock=100, reorder_level=20))
    db.add(Product(name="Office Chair", sku="CHR001", category="Furniture", unit_of_measure="units", unit_cost=1200, current_stock=5, reorder_level=10))
    db.add(Product(name="Bolts M10", sku="HW001", category="Hardware", unit_of_measure="units", unit_cost=5, current_stock=8, reorder_level=50))
    db.commit()
    print("Done! Login: admin/admin123")
except Exception as e:
    print(f"Note: {e}")
finally:
    db.close()
