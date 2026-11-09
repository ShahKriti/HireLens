import tempfile, os
from app import create_app

def test_health():
    fd,path=tempfile.mkstemp();os.close(fd)
    app=create_app({"TESTING":True,"DATABASE":path,"JWT_SECRET_KEY":"test","UPLOAD_FOLDER":tempfile.mkdtemp()})
    c=app.test_client()
    assert c.get("/api/health").json["status"]=="ok"
    os.unlink(path)
