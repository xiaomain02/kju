from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, boards, columns, cards, comments

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Kanban Board API",
    description="API для управления канбан-доской",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # потом заменим на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(columns.router)
app.include_router(cards.router)
app.include_router(comments.router)

@app.get("/")
async def root():
    return {
        "message": "Kanban Board API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}