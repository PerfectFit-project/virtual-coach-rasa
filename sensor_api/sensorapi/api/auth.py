import flask
from datetime import datetime
from typing import Tuple, Optional
import requests
from model import User
from const import NICEDAY_ME_URL
from werkzeug.datastructures import ImmutableMultiDict
import functools

def require_token(f):
  @functools.wraps(f)
  def decorated_function(*args, **kwargs):
    if flask.request.method == 'GET':
        params = flask.request.args
    elif flask.request.method == 'POST':
        params = flask.request.form
    else:
        flask.abort(502, 'Auth Decorator Not Support')
    data = params.to_dict()
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
    if rep.status_code == 401:
        return False, None
    else:
        return True, User(
            rep.json["id"], 
            rep.json["hash_id"])



