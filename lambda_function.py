from fastapi import FastAPI
from app.routes import Userauth,Orders
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(Userauth.router)
app.include_router(Orders.router)

# AWS Lambda handler
handler = Mangum(app)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI JWT MongoDB setup!"}