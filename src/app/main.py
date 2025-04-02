from fastapi import FastAPI, HTTPException, Depends, Request, Response, status, BackgroundTasks
from pydantic import BaseModel, validator
from asyncpg.exceptions import UniqueViolationError
from datetime import datetime
import secrets
#from database import get_connection
from src.app.database import get_connection  # Стало
from typing import Optional, Union
import redis
import traceback
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from passlib.context import CryptContext
import uuid
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from urllib.parse import urlparse, urlunparse 
import re

class LinkCreate(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

    @validator('expires_at', pre=True)
    def parse_expires_at(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", ""))
        return value

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

app = FastAPI()

# Настройки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Location"]
)

from urllib.parse import urlparse, urlunparse
import re

async def validate_and_fix_url(url: str) -> str:
    """Простая, но надежная валидация URL"""
    if not url or not url.strip():
        raise ValueError("URL cannot be empty")
    
    url = url.strip()
    
    # Простейшая проверка - должен содержать точку и не содержать пробелов
    if ' ' in url or '.' not in url:
        raise ValueError("Invalid URL")
    
    # Добавляем https:// если нет схемы
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    # Базовый parse/unparse для нормализации
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    
    return urlunparse(parsed)


# Redis setup
try:
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    redis_client.ping()
except redis.ConnectionError:
    redis_client = None
    print("Warning: Redis is not available. Using in-memory sessions.")
    sessions = {}

# Auth utils
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def get_current_user(request: Request, conn=Depends(get_connection)) -> Optional[dict]:
    """Получает текущего пользователя по session_id из cookies"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    
    try:
        # Получаем user_id из Redis или памяти
        if redis_client:
            user_id = redis_client.get(f"session:{session_id}")
        else:
            user_id = sessions.get(session_id)
        
        if not user_id:
            return None
            
        # Получаем данные пользователя из БД
        user = await conn.fetchrow(
            "SELECT id, email, created_at FROM users WHERE id = $1", 
            int(user_id)
        )  
        
        return dict(user) if user else None
        
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None

async def get_authenticated_user(request: Request, conn=Depends(get_connection)) -> dict:
    user = await get_current_user(request, conn)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user




# метод для очистки неиспользованных ссылок, которые заведены более чем 5 дней назад и имеюю 0 кликов (0 редиректов)
async def cleanup_unused_links(conn: asyncpg.Connection):
    """Удаляет ссылки, созданные более 5 дней назад с 0 кликов"""
    await conn.execute(
        "DELETE FROM links WHERE created_at < NOW() - INTERVAL '5 days' AND clicks = 0"
    )


@app.on_event("startup")
async def startup_event():
    # При старте приложения создаем соединение и выполняем очистку
    conn = await get_connection()
    await cleanup_unused_links(conn)
    await conn.close()


# Auth endpoints
@app.post("/register")
async def register(user: UserCreate, conn=Depends(get_connection)):
    if await conn.fetchrow("SELECT 1 FROM users WHERE email = $1", user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    await conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES ($1, $2, $3)",
        user.email,
        pwd_context.hash(user.password),
        datetime.now()
    )
    return {"message": "User registered successfully"}

@app.post("/login")
async def login(user: UserLogin, response: Response, conn=Depends(get_connection)):
    db_user = await conn.fetchrow("SELECT * FROM users WHERE email = $1", user.email)
    if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    session_id = str(uuid.uuid4())
    if redis_client:
        redis_client.set(f"session:{session_id}", db_user["id"], ex=86400)
    else:
        sessions[session_id] = db_user["id"]
    
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400,
        secure=False
    )
    return {"message": "Logged in successfully"}

@app.post("/logout")
async def logout(response: Response, request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        if redis_client:
            redis_client.delete(f"session:{session_id}")
        else:
            sessions.pop(session_id, None)
    response.delete_cookie("session_id")
    return {"message": "Logged out successfully"}

@app.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_authenticated_user)):
    """Get current user info (requires authentication)
    
    Returns:
    - id: User ID
    - email: User email
    - created_at: Account creation timestamp
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "created_at": current_user["created_at"]
    }

@app.post("/links/shorten")
async def create_short_link(
    link: LinkCreate,
    request: Request,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Создание короткой ссылки с автоматической очисткой неиспользованных"""
    try:
        # Валидируем URL
        validated_url = await validate_and_fix_url(link.original_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Остальной код функции без изменений
    await cleanup_unused_links(conn)
    short_code = link.custom_alias or secrets.token_urlsafe(6)
    
    if await conn.fetchrow("SELECT 1 FROM links WHERE short_code = $1", short_code):
        raise HTTPException(status_code=400, detail="Alias already exists")
    
    await conn.execute(
        """
        INSERT INTO links (
            original_url, 
            short_code, 
            custom_alias,
            expires_at, 
            user_id
        ) VALUES ($1, $2, $3, $4, $5)
        """,
        validated_url,  # Используем validated_url вместо link.original_url
        short_code,
        link.custom_alias,
        link.expires_at,
        current_user["id"] if current_user else None
    )
    
    return {
        "short_url": f"{request.base_url}{short_code}",
        "short_code": short_code
    }

    
@app.get("/{short_code}")
async def universal_redirect(
    short_code: str,
    request: Request,
    conn: asyncpg.Connection = Depends(get_connection),
    background_tasks: BackgroundTasks = None
):
    try:
        if background_tasks:
            background_tasks.add_task(cleanup_unused_links, conn)
        
        link = await conn.fetchrow(
            "SELECT original_url, expires_at FROM links WHERE short_code = $1",
            short_code.lower()
        )
        
        if not link:
            raise HTTPException(status_code=404, detail="Short URL not found")

        # 2. Проверяем URL
        target_url = link["original_url"].strip()
        if not target_url.startswith(('http://', 'https://')):
            target_url = f'https://{target_url}'

        # 3. Проверка срока действия
        if link["expires_at"] and link["expires_at"] < datetime.now():
            raise HTTPException(status_code=410, detail="This short URL has expired")

        # 4. Обновляем статистику
        await conn.execute(
            "UPDATE links SET clicks = clicks + 1 WHERE short_code = $1",
            short_code
        )

        # 5. Определяем тип клиента
        user_agent = request.headers.get("user-agent", "").lower()
        is_browser = any(browser in user_agent for browser in [
            'chrome', 'firefox', 'safari','edge', 'opera', 'msie'  # Internet Explorer
        ])

        # Для браузеров - HTML с редиректом
        if is_browser:
            return HTMLResponse(f"""url={target_url}""", media_type="text/html")

        # Для остальных - HTTP редирект
        return RedirectResponse(url=target_url, status_code=307)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Other endpoints
@app.get("/links/search")
async def search_link(original_url: str, conn=Depends(get_connection)):
    links = await conn.fetch("SELECT * FROM links WHERE original_url = $1", original_url)
    if not links:
        raise HTTPException(status_code=404, detail="No links found")
    return [dict(link) for link in links]

@app.get("/links/{short_code}/stats")
async def get_link_stats(short_code: str, conn=Depends(get_connection)):
    link = await conn.fetchrow("SELECT * FROM links WHERE short_code = $1", short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return dict(link)

@app.delete("/links/{short_code}")
async def delete_link(
    short_code: str,
    conn=Depends(get_connection),
    current_user: dict = Depends(get_authenticated_user)
):
    existing_link = await conn.fetchrow(
        "SELECT 1 FROM links WHERE short_code = $1 AND user_id = $2",
        short_code,
        current_user["id"]
    )
    if not existing_link:
        raise HTTPException(status_code=404, detail="Link not found or access denied")
    
    await conn.execute("DELETE FROM links WHERE short_code = $1", short_code)
    return {"message": "Link deleted successfully"}

@app.put("/links/{short_code}")
async def update_link(
    short_code: str,
    link: LinkCreate,
    conn=Depends(get_connection),
    current_user: dict = Depends(get_authenticated_user)
):
    existing_link = await conn.fetchrow(
        "SELECT 1 FROM links WHERE short_code = $1 AND user_id = $2",
        short_code,
        current_user["id"]
    )
    if not existing_link:
        raise HTTPException(status_code=404, detail="Link not found or access denied")

    try:
        await conn.execute(
            """
            UPDATE links
            SET original_url = $1, custom_alias = $2, expires_at = $3
            WHERE short_code = $4
            """,
            link.original_url,
            link.custom_alias,
            link.expires_at,
            short_code
        )
        return {"message": "Link updated successfully"}
    except UniqueViolationError:
        raise HTTPException(status_code=400, detail="This custom alias is already in use")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"Error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "detail": str(exc),
            "traceback": traceback.format_exc()
        }
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the URL shortener service!"}


@app.get("/links/expired", tags=["links"])
async def get_expired_links(
    conn: asyncpg.Connection = Depends(get_connection)
):
    """Получение списка всех истекших ссылок (доступно всем)
    
    Возвращает:
    - id: ID ссылки
    - original_url: Оригинальный URL
    - short_code: Короткий код
    - expires_at: Дата истечения
    - clicks: Количество переходов
    - created_at: Дата создания
    """
    try:
        expired_links = await conn.fetch(
            """
            SELECT id, original_url, short_code, expires_at, clicks, created_at
            FROM links
            WHERE expires_at < NOW()
            ORDER BY expires_at DESC
            """
        )
        return [dict(link) for link in expired_links]
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching expired links: {str(e)}"
        )





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)