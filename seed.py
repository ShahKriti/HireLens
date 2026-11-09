from app import create_app
from app.db import get_db
from werkzeug.security import generate_password_hash
import json
app=create_app()
with app.app_context():
    db=get_db()
    for name,email,role,client in [
      ("Demo Recruiter","recruiter@hirelens.demo","recruiter",None),
      ("Demo Client","client@hirelens.demo","client",1),
      ("Delivery Head","delivery@hirelens.demo","delivery",None)]:
        if not db.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone():
            db.execute("INSERT INTO users(name,email,password_hash,role,client_id) VALUES(?,?,?,?,?)",
              (name,email,generate_password_hash("HireLens@123"),role,client))
    db.commit()
    print("Demo users created. Sign in and click Seed demo data in the dashboard if sample data is not present.")
