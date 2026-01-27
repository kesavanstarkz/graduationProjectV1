from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from app.database import engine
from app.models import Base
from app.routers import upload, validate, issues, report, auth, stats


Base.metadata.create_all(bind=engine)


app = FastAPI(title="Clinical Data Quality Checker")

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(validate.router)
app.include_router(issues.router)
app.include_router(report.router)
app.include_router(stats.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard")
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
