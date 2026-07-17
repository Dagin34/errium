from flask import Flask, request
from pydantic import BaseModel

from errium_flask import ErriumFlask

app = Flask(__name__)

ErriumFlask(app)


class UserCreate(BaseModel):
    email: str
    password: str


@app.post("/users")
def create_user():
    payload = UserCreate.model_validate(request.get_json())
    return payload.model_dump()
