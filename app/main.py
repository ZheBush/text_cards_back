import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from app.routers import auth, cards, card_lists, groups, files, weather

app = FastAPI(title="cards from text")


@app.get("/sitemap.xml")
async def sitemap():
    base_url = "https://fleshcards.com"
    pages = [
        {"loc": base_url + "/", "lastmod": datetime.now().isoformat(), "priority": "1.0"},
        {"loc": base_url + "/login", "priority": "0.6"},
        {"loc": base_url + "/register", "priority": "0.6"}
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in pages:
        xml += '<url>\n'
        xml += f'  <loc>{p["loc"]}</loc>\n'
        if "lastmod" in p:
            xml += f'  <lastmod>{p["lastmod"]}</lastmod>\n'
        xml += f'  <priority>{p.get("priority", "0.5")}</priority>\n'
        xml += '</url>\n'
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")


@app.get("/robots.txt")
async def robots():
    content = """User-agent: *
Allow: /
Disallow: /history
Disallow: /groups
Disallow: /cards/*
Sitemap: https://flashcards.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


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
app.include_router(weather.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
