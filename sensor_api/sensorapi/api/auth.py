import flask
from typing import Tuple, Optional
import requests
from .model import User
from .const import NICEDAY_ME_URL
from werkzeug.datastructures import ImmutableMultiDict
import functools
import connexion

def require_token(f):
  @functools.wraps(f)
  def decorated_function(*args, **kwargs):
    data = connexion.request.json
    ok, user = validate_login(data["token"])
    if not ok:
      flask.abort(405, "Invalid Token")
    data["user"] = user
    params = ImmutableMultiDict(data)
    if flask.request.method == 'GET':
        flask.request.args = params
    elif flask.request.method == 'POST':
        flask.request.form = params
    return f(*args, **kwargs)
  return decorated_function

def validate_login(token: str) -> Tuple[bool, Optional[User]]:
    rep = requests.get(NICEDAY_ME_URL, 
    headers={"Authorization": f"Token {token}"})
    rep_json = rep.json()
    if rep.status_code == 401 or rep_json["hash_id"] != flask.request.json["user"]:
        return False, None
    else:
        return True, User(
            id=rep_json["id"], 
            hash_id=rep_json["hash_id"])



