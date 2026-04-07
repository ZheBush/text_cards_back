import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, cards, card_lists, groups, files

app = FastAPI(title="cards from text")


origins = [
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(card_lists.router, prefix="/card_lists", tags=["card_lists"])
app.include_router(cards.router, prefix="/cards", tags=["cards"])
app.include_router(groups.router, prefix="/groups", tags=["groups"])
app.include_router(files.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
