from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import db
from app.routers import auth, org

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.connect()
    yield
    # Shutdown
    db.close()

app = FastAPI(title="Multi-Tenant Backend", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(org.router)

@app.get("/")
async def root():
    return {"message": "Multi-Tenant Service Running"}
