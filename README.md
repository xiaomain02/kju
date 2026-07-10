# kju

Kanban API на FastAPI и статический frontend в стиле VK dark.

## Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

API будет доступен на `http://127.0.0.1:8000`.

По умолчанию SQLite база хранится вне папки OneDrive: `%LOCALAPPDATA%\KJU\kanban.db` на Windows. Если нужен другой путь, задай `DATABASE_URL` или `KJU_DATA_DIR` перед запуском.

## Frontend

```powershell
cd client
python -m http.server 5173
```

Открой `http://127.0.0.1:5173`. В поле API оставь `http://127.0.0.1:8000`, если backend запущен локально.
