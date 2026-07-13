from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, boards, columns, cards, comments, audit

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Kanban Board API",
    description="API для управления канбан-доской",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(columns.router)
app.include_router(cards.router)
app.include_router(comments.router)
app.include_router(audit.router)

@app.get("/")
async def root():
    return {
        "message": "Kanban Board API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}