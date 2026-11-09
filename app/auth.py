from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from .db import get_db

def current_user():
    uid = get_jwt_identity()
    if uid is None: return None
    return get_db().execute("SELECT id,name,email,role,client_id FROM users WHERE id=?", (int(uid),)).fetchone()

def roles(*allowed):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if not user: return jsonify(error="User not found"), 401
            if allowed and user["role"] not in allowed:
                return jsonify(error="You do not have permission for this action"), 403
            return fn(*args, **kwargs)
        return wrapped
    return deco
