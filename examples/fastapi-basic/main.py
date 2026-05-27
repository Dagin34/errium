from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from errium import ErriumMiddleware
from errium.handlers.validation_handler import validation_exception_handler

app = FastAPI()

app.add_middleware(ErriumMiddleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


class UserCreate(BaseModel):
    email: str
    password: str


@app.post("/users")
async def create_user(payload: UserCreate):
    return payload
