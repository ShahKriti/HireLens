import os, json, hashlib
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_jwt_extended import create_access_token
from .db import get_db
from .auth import roles, current_user
from .parsing import extract_text, parse_profile, ALLOWED
from .scoring import score_cv

api=Blueprint("api",__name__)

def rowdict(row): return dict(row) if row else None
def log_view(user_id,candidate_id,action):
    get_db().execute("INSERT INTO audit_logs(user_id,candidate_id,action) VALUES(?,?,?)",(user_id,candidate_id,action))

@api.post("/auth/login")
def login():
    data=request.get_json(silent=True) or {}
    user=get_db().execute("SELECT * FROM users WHERE email=?",(data.get("email","").lower().strip(),)).fetchone()
    if not user or not check_password_hash(user["password_hash"],data.get("password","")):
        return jsonify(error="Invalid email or password"),401
    token=create_access_token(identity=str(user["id"]))
    return jsonify(token=token,user={"id":user["id"],"name":user["name"],"role":user["role"]})

@api.post("/auth/register")
def register():
    data=request.get_json(silent=True) or {}
    if data.get("role") not in ("recruiter","client"): return jsonify(error="Invalid role"),400
    if not all(data.get(k) for k in ("name","email","password")): return jsonify(error="Name, email and password are required"),400
    db=get_db()
    try:
        cur=db.execute("INSERT INTO users(name,email,password_hash,role,client_id) VALUES(?,?,?,?,?)",
          (data["name"].strip(),data["email"].lower().strip(),generate_password_hash(data["password"]),data["role"],data.get("client_id")))
        db.commit()
        return jsonify(id=cur.lastrowid),201
    except Exception: return jsonify(error="Email already exists or invalid account"),409

@api.get("/me")
@roles()
def me(): 
    u=current_user()
    return jsonify(user={"id":u["id"],"name":u["name"],"email":u["email"],"role":u["role"]})

@api.get("/dashboard")
@roles("recruiter","delivery")
def dashboard():
    db=get_db()
    return jsonify(requisitions=db.execute("SELECT COUNT(*) n FROM requisitions WHERE status='open'").fetchone()["n"],
      candidates=db.execute("SELECT COUNT(*) n FROM candidates WHERE deleted=0").fetchone()["n"],
      submitted=db.execute("SELECT COUNT(*) n FROM applications WHERE submitted=1").fetchone()["n"],
      interviews=db.execute("SELECT COUNT(*) n FROM applications WHERE status='interview'").fetchone()["n"])

@api.get("/requisitions")
@roles("recruiter","client","delivery")
def requisitions():
    db=get_db()
    rows=db.execute("SELECT * FROM requisitions ORDER BY id DESC").fetchall()
    return jsonify(items=[rowdict(x) for x in rows])

@api.post("/requisitions")
@roles("recruiter")
def create_requisition():
    d=request.get_json(silent=True) or {}
    required=["title","client_name","location","min_experience","max_experience","must_have","max_notice"]
    if any(k not in d for k in required): return jsonify(error="Missing required scorecard fields"),400
    try:
        skills=d["must_have"] if isinstance(d["must_have"],list) else [x.strip() for x in d["must_have"].split(",") if x.strip()]
        if float(d["min_experience"])<0 or float(d["max_experience"])<float(d["min_experience"]): raise ValueError()
        cur=get_db().execute("""INSERT INTO requisitions(title,client_name,location,min_experience,max_experience,must_have,max_notice,min_ctc,max_ctc,created_by)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",(d["title"],d["client_name"],d["location"],float(d["min_experience"]),float(d["max_experience"]),json.dumps(skills),int(d["max_notice"]),d.get("min_ctc"),d.get("max_ctc"),current_user()["id"]))
        get_db().commit()
        return jsonify(id=cur.lastrowid),201
    except (ValueError,TypeError): return jsonify(error="Invalid experience or notice values"),400

@api.post("/requisitions/<int:rid>/upload")
@roles("recruiter")
def upload(rid):
    db=get_db()
    req=db.execute("SELECT * FROM requisitions WHERE id=?",(rid,)).fetchone()
    if not req: return jsonify(error="Requisition not found"),404
    files=request.files.getlist("files")
    if not files: return jsonify(error="Choose at least one PDF or DOCX file"),400
    if len(files)>500: return jsonify(error="Maximum 500 files per batch"),400
    results=[]
    scorecard={"must_have":json.loads(req["must_have"]),"min_experience":req["min_experience"],"max_experience":req["max_experience"],"max_notice":req["max_notice"]}
    for f in files:
        filename=secure_filename(f.filename or "")
        ext=os.path.splitext(filename)[1].lower()
        if not filename or ext not in ALLOWED:
            results.append({"file":f.filename,"status":"error","message":"Only PDF and DOCX are supported"}); continue
        path=os.path.join(current_app.config["UPLOAD_FOLDER"],hashlib.sha256((filename+str(os.path.getsize(current_app.config["UPLOAD_FOLDER"]) if os.path.exists(current_app.config["UPLOAD_FOLDER"]) else 0)).encode()).hexdigest()[:12]+"_"+filename)
        f.save(path)
        try:
            text=extract_text(path)
            if not text:
                results.append({"file":filename,"status":"error","message":"No selectable text found. Scanned PDFs need OCR; please review manually."}); os.remove(path); continue
            profile=parse_profile(text,filename)
            digest=hashlib.sha256(text.encode("utf-8",errors="ignore")).hexdigest()
            duplicate=db.execute("SELECT id FROM candidates WHERE cv_text_hash=?",(digest,)).fetchone()
            if duplicate:
                results.append({"file":filename,"status":"duplicate","candidate_id":duplicate["id"]}); os.remove(path); continue
            code="CND-"+digest[:8].upper()
            cur=db.execute("""INSERT INTO candidates(candidate_code,name,current_role,experience,skills,notice_days,email,phone,cv_text,cv_text_hash,file_name,consent)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,0)""",(code,profile["name"],None,profile["experience"],json.dumps(profile["skills"]),None,profile["email"],profile["phone"],text,digest,filename))
            cid=cur.lastrowid
            scored=score_cv(text,scorecard)
            db.execute("INSERT INTO applications(requisition_id,candidate_id,score,score_details) VALUES(?,?,?,?)",(rid,cid,scored["score"],json.dumps(scored)))
            results.append({"file":filename,"status":"parsed","candidate_id":cid,"score":scored["score"]})
            os.remove(path)
        except Exception as e:
            if os.path.exists(path): os.remove(path)
            results.append({"file":filename,"status":"error","message":str(e)[:180]})
    db.commit()
    return jsonify(results=results),200

@api.get("/requisitions/<int:rid>/candidates")
@roles("recruiter","delivery")
def ranked(rid):
    db=get_db()
    rows=db.execute("""SELECT a.*,c.candidate_code,c.name,c.current_role,c.experience,c.skills,c.notice_days,c.location,c.file_name,c.id cid
    FROM applications a JOIN candidates c ON c.id=a.candidate_id WHERE a.requisition_id=? AND c.deleted=0 ORDER BY a.score DESC""",(rid,)).fetchall()
    items=[]
    for r in rows:
        log_view(current_user()["id"],r["cid"],"viewed_ranked_profile")
        items.append({"application_id":r["id"],"candidate_id":r["cid"],"candidate_code":r["candidate_code"],"name":r["name"],"current_role":r["current_role"],"experience":r["experience"],"skills":json.loads(r["skills"] or "[]"),"score":r["score"],"details":json.loads(r["score_details"] or "{}"),"status":r["status"],"submitted":r["submitted"]})
    db.commit()
    return jsonify(items=items)

@api.get("/candidates/<int:cid>")
@roles("recruiter","delivery")
def candidate_detail(cid):
    db=get_db()
    c=db.execute("SELECT * FROM candidates WHERE id=? AND deleted=0",(cid,)).fetchone()
    if not c: return jsonify(error="Candidate not found"),404
    log_view(current_user()["id"],cid,"opened_original_cv")
    db.commit()
    return jsonify(candidate={"id":c["id"],"name":c["name"],"cv_text":c["cv_text"],"file_name":c["file_name"],"email":c["email"],"phone":c["phone"],"consent":bool(c["consent"])})

@api.post("/applications/<int:aid>/submit")
@roles("recruiter")
def submit_candidate(aid):
    db=get_db()
    a=db.execute("SELECT * FROM applications WHERE id=?",(aid,)).fetchone()
    if not a:return jsonify(error="Application not found"),404
    db.execute("UPDATE applications SET submitted=1,status='submitted',updated_at=CURRENT_TIMESTAMP WHERE id=?",(aid,))
    db.commit()
    return jsonify(ok=True)

@api.get("/client/shortlist")
@roles("client")
def client_shortlist():
    # Demo client users are scoped to their client_id. Null client_id sees demo client records only.
    uid=current_user()
    db=get_db()
    rows=db.execute("""SELECT a.id application_id,a.status,a.score,a.score_details,a.rejection_reason,a.interview_slot,
      c.candidate_code,c.current_role,c.experience,c.skills,c.id cid,r.title,r.client_name
      FROM applications a JOIN candidates c ON c.id=a.candidate_id JOIN requisitions r ON r.id=a.requisition_id
      WHERE a.submitted=1 AND c.deleted=0 AND (? IS NULL OR a.client_id=? OR r.client_name='Northstar Bank')
      ORDER BY a.updated_at DESC""",(uid["client_id"],uid["client_id"])).fetchall()
    items=[]
    for r in rows:
        items.append({"application_id":r["application_id"],"status":r["status"],"score":r["score"],"details":json.loads(r["score_details"] or "{}"),"rejection_reason":r["rejection_reason"],"interview_slot":r["interview_slot"],"candidate_code":r["candidate_code"],"current_role":r["current_role"],"experience":r["experience"],"skills":json.loads(r["skills"] or "[]"),"job_title":r["title"]})
    return jsonify(items=items)

@api.post("/client/applications/<int:aid>/decision")
@roles("client")
def client_decision(aid):
    d=request.get_json(silent=True) or {}
    status=d.get("status")
    if status not in ("shortlisted","rejected","interview"):return jsonify(error="Invalid decision"),400
    if status=="rejected" and not d.get("reason","").strip():return jsonify(error="A rejection reason is required"),400
    if status=="interview" and not d.get("slot","").strip():return jsonify(error="Propose an interview slot"),400
    db=get_db()
    a=db.execute("""SELECT a.* FROM applications a JOIN requisitions r ON r.id=a.requisition_id
      WHERE a.id=? AND a.submitted=1 AND (? IS NULL OR a.client_id=? OR r.client_name='Northstar Bank')""",(aid,current_user()["client_id"],current_user()["client_id"])).fetchone()
    if not a:return jsonify(error="Application not found or not accessible"),404
    db.execute("UPDATE applications SET status=?,rejection_reason=?,interview_slot=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(status,d.get("reason"),d.get("slot"),aid))
    db.commit()
    return jsonify(ok=True)

@api.get("/requisitions/<int:rid>/pipeline")
@roles("recruiter","delivery")
def pipeline(rid):
    rows=get_db().execute("""SELECT a.id,a.status,a.score,c.candidate_code,c.name,c.current_role
      FROM applications a JOIN candidates c ON c.id=a.candidate_id WHERE a.requisition_id=? AND c.deleted=0 ORDER BY a.updated_at DESC""",(rid,)).fetchall()
    return jsonify(items=[rowdict(r) for r in rows])

@api.post("/candidates/<int:cid>/consent")
@roles("recruiter")
def consent(cid):
    d=request.get_json(silent=True) or {}
    if "consent" not in d:return jsonify(error="Consent value required"),400
    cur=get_db().execute("UPDATE candidates SET consent=? WHERE id=? AND deleted=0",(1 if d["consent"] else 0,cid))
    get_db().commit()
    return (jsonify(ok=True),200) if cur.rowcount else (jsonify(error="Candidate not found"),404)

@api.delete("/candidates/<int:cid>")
@roles("recruiter")
def delete_candidate(cid):
    db=get_db()
    db.execute("UPDATE candidates SET deleted=1,name='Deleted candidate',email=NULL,phone=NULL,cv_text='',skills='[]' WHERE id=?",(cid,))
    db.execute("DELETE FROM applications WHERE candidate_id=?",(cid,))
    db.commit()
    return jsonify(ok=True,message="Candidate personal data deleted from the active system")

@api.get("/audit")
@roles("recruiter","delivery")
def audit():
    rows=get_db().execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200").fetchall()
    return jsonify(items=[rowdict(r) for r in rows])

@api.post("/demo/seed")
@roles("recruiter")
def seed():
    db=get_db()
    # Seed is idempotent and only adds synthetic examples.
    if db.execute("SELECT COUNT(*) n FROM requisitions").fetchone()["n"]==0:
        rid=db.execute("""INSERT INTO requisitions(title,client_name,location,min_experience,max_experience,must_have,max_notice,created_by)
          VALUES('Senior Java Developer','Northstar Bank','Noida',5,8,?,60,?)""",(json.dumps(["Java","Spring Boot","Microservices"]),current_user()["id"])).lastrowid
    else: rid=db.execute("SELECT id FROM requisitions ORDER BY id LIMIT 1").fetchone()["id"]
    samples=[
      ("CND-91022","Ritika Bansal","Senior Java Developer",6.5,["Java","Spring Boot","Microservices"],60,"Ritika has 6.5 years of experience building Java applications using Spring Boot and microservices. Notice period is 60 days."),
      ("CND-91047","Arjun Rawat","KYC Analyst",3.0,["KYC","AML checks","Excel"],30,"Arjun has 3 years of experience in KYC, AML checks and Excel operations. Notice period is 30 days."),
      ("CND-91088","Pooja Nair","Java Developer",4.0,["Java","Hibernate","REST APIs"],90,"Pooja has 4 years of experience in Java, Hibernate and REST APIs. Notice period is 90 days.")
    ]
    for code,name,role,exp,skills,notice,cv in samples:
        if db.execute("SELECT id FROM candidates WHERE candidate_code=?",(code,)).fetchone():continue
        cid=db.execute("""INSERT INTO candidates(candidate_code,name,current_role,experience,skills,notice_days,cv_text,file_name,consent)
          VALUES(?,?,?,?,?,?,?,?,1)""",(code,name,role,exp,json.dumps(skills),notice,cv,"synthetic_sample.txt")).lastrowid
        score=score_cv(cv,{"must_have":["Java","Spring Boot","Microservices"],"min_experience":5,"max_notice":60})
        aid=db.execute("INSERT INTO applications(requisition_id,candidate_id,score,score_details) VALUES(?,?,?,?)",(rid,cid,score["score"],json.dumps(score))).lastrowid
        if code=="CND-91022":
            db.execute("UPDATE applications SET submitted=1,client_id=1 WHERE id=?",(aid,))
    db.commit()
    return jsonify(ok=True,requisition_id=rid)

@api.get("/health")
def health(): return jsonify(status="ok")
