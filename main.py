from fastapi import FastAPI
from app.routes import Userauth,Orders

app = FastAPI()

# Include routers
app.include_router(Userauth.router)
app.include_router(Orders.router)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI JWT MongoDB setup!"}