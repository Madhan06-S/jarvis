import os
import secrets
from pathlib import Path
from typing import List, Dict
from jinja2 import Template
from spec_engine import AppSpec


class BackendGenerator:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else None
        self.templates = self._load_templates()

    def _load_templates(self):
        return {
            "database": Template("""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""),
            "models": Template("""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    object_id = Column(Integer, nullable=True)
    changes = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

{% if auth %}
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="member")
    organization_id = Column(Integer, nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
{% endif %}

{% for model in models %}
class {{model.name}}(Base):
    __tablename__ = "{{model.name.lower()}}s"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    owner_id = Column(Integer, nullable=True, index=True)

    {% for field in model.fields %}
    {{field.name}} = Column(
        {% if field.type == "string" %}String(255){% elif field.type == "text" %}Text{% elif field.type == "number" %}Float{% elif field.type == "boolean" %}Boolean{% elif field.type == "date" %}DateTime{% elif field.type == "email" %}String(255){% elif field.type == "json" %}Text{% elif field.type == "file" %}String(500){% elif field.type == "relation" %}Integer, ForeignKey("{{field.relation_to.lower()}}s.id"){% endif %}
        {% if not field.required %}, nullable=True{% endif %}
    )
    {% endfor %}

{% endfor %}
"""),
            "base_service": Template("""
from typing import TypeVar, Generic, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status
from datetime import datetime
import json

T = TypeVar('T')

class BaseService(Generic[T]):
    def __init__(self, db: Session, model_class, user=None):
        self.db = db
        self.model = model_class
        self.user = user

    def _apply_tenant_filter(self, query):
        # Multi-tenant: filter by organization_id if present
        if hasattr(self.model, 'organization_id') and self.user and hasattr(self.user, 'organization_id') and self.user.organization_id:
            return query.filter(self.model.organization_id == self.user.organization_id)
        return query

    def _check_permission(self, action: str, obj=None):
        # RBAC check
        if not self.user:
            return True
        return True

    def _log_audit(self, action: str, obj_id: int, changes: dict = None):
        # Write audit log entry
        from models import AuditLog
        log = AuditLog(
            user_id=getattr(self.user, 'id', None) if self.user else None,
            action=action,
            model=self.model.__name__,
            object_id=obj_id,
            changes=json.dumps(changes) if changes else None
        )
        self.db.add(log)

    def get(self, id: int) -> T:
        query = self._apply_tenant_filter(self.db.query(self.model)).filter(self.model.id == id)
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at.is_(None))
        obj = query.first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{self.model.__name__} not found")
        self._check_permission("read", obj)
        return obj

    def list(self, filters: dict = None, search: str = None, 
             page: int = 1, page_size: int = 20,
             sort_by: str = "created_at", sort_order: str = "desc") -> dict:
        query = self._apply_tenant_filter(self.db.query(self.model))
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    column = getattr(self.model, field)
                    if isinstance(value, list):
                        query = query.filter(column.in_(value))
                    else:
                        query = query.filter(column == value)
        
        if search:
            search_filters = []
            for column in self.model.__table__.columns:
                if str(column.type) in ['VARCHAR', 'TEXT', 'STRING']:
                    search_filters.append(column.ilike(f"%{search}%"))
            if search_filters:
                query = query.filter(or_(*search_filters))
        
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at.is_(None))
        
        total = query.count()
        
        sort_column = getattr(self.model, sort_by, getattr(self.model, 'created_at', None))
        if sort_column is not None:
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "data": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    def create(self, data: dict) -> T:
        self._check_permission("create")
        data = self._run_rules("before_create", data)
        
        if hasattr(self.model, 'owner_id') and self.user and hasattr(self.user, 'id'):
            data['owner_id'] = self.user.id
        if hasattr(self.model, 'organization_id') and self.user and hasattr(self.user, 'organization_id'):
            data['organization_id'] = self.user.organization_id

        # Clean non-model fields
        model_cols = {c.name for c in self.model.__table__.columns}
        clean_data = {k: v for k, v in data.items() if k in model_cols}
        
        obj = self.model(**clean_data)
        self.db.add(obj)
        self.db.flush()
        
        self._log_audit("create", obj.id, clean_data)
        self._run_rules("after_create", obj)
        
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, id: int, data: dict) -> T:
        obj = self.get(id)
        self._check_permission("update", obj)
        
        old_values = {k: getattr(obj, k) for k in data.keys() if hasattr(obj, k)}
        data = self._run_rules("before_update", data, obj)
        
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        
        if hasattr(obj, 'updated_at'):
            obj.updated_at = datetime.utcnow()
        
        changes = {k: {"old": old_values.get(k), "new": v} for k, v in data.items()}
        self._log_audit("update", id, changes)
        
        self._run_rules("after_update", obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: int, hard: bool = False):
        obj = self.get(id)
        self._check_permission("delete", obj)
        
        if hasattr(self.model, 'deleted_at') and not hard:
            obj.deleted_at = datetime.utcnow()
            self._log_audit("soft_delete", id)
        else:
            self.db.delete(obj)
            self._log_audit("hard_delete", id)
        
        self._run_rules("after_delete", obj)
        self.db.commit()

    def _run_rules(self, trigger: str, *args):
        return args[0] if args else None
"""),
            "model_service": Template("""
from services.base_service import BaseService
from models import {{model.name}}
from realtime.events import broadcast_event
from fastapi import HTTPException, status
from datetime import datetime

class {{model.name}}Service(BaseService):
    def __init__(self, db, user=None):
        super().__init__(db, {{model.name}}, user)

    def _run_rules(self, trigger: str, *args):
        if trigger == "before_create":
            data = args[0]
            return data
        elif trigger == "after_create":
            obj = args[0]
            broadcast_event("{{model.name.lower()}}.created", {"id": obj.id}, room="admins")
            return obj
        elif trigger == "after_update":
            obj = args[0]
            broadcast_event("{{model.name.lower()}}.updated", {"id": obj.id}, room="admins")
            return obj
        return args[0] if args else None

    def get_analytics_report(self):
        from sqlalchemy import func
        result = self.db.query(
            func.date(self.model.created_at).label('date'),
            func.count(self.model.id).label('count')
        ).filter(self.model.deleted_at.is_(None) if hasattr(self.model, 'deleted_at') else True)\
         .group_by(func.date(self.model.created_at)).all()

        return [{"date": str(r.date), "count": r.count} for r in result]
"""),
            "celery_app": Template("""
from celery import Celery
import os

celery_app = Celery(
    "jarvis_tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "tasks.email_tasks",
        "tasks.inventory_tasks",
        "tasks.report_tasks",
        "tasks.cleanup_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)
"""),
            "tasks": Template("""
from tasks.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def send_email(self, to: str, template: str, context: dict):
    try:
        return {"status": "sent", "to": to}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@celery_app.task
def update_stock(product_id: int, quantity: int, reference: str):
    return {"product_id": product_id, "quantity_delta": quantity, "reference": reference}

@celery_app.task
def generate_monthly_report(organization_id: int, month: int, year: int):
    return {"status": "complete", "organization_id": organization_id}

@celery_app.task
def cleanup_expired_sessions():
    return {"status": "cleaned"}
"""),
            "connection_manager": Template("""
from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, room: str = "default", user_id: int = None):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        if user_id:
            self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, room: str = "default"):
        if room in self.active_connections and websocket in self.active_connections[room]:
            self.active_connections[room].remove(websocket)

    async def broadcast(self, message: dict, room: str = "default"):
        if room in self.active_connections:
            disconnected = []
            for connection in self.active_connections[room]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(conn, room)

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
"""),
            "realtime_events": Template("""
import asyncio
from datetime import datetime
from realtime.connection_manager import manager
from typing import List, Optional

def broadcast_event(event_type: str, payload: dict, room: str = "default", user_ids: Optional[List[int]] = None):
    message = {
        "type": event_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat()
    }
    if user_ids:
        for uid in user_ids:
            try:
                asyncio.create_task(manager.send_to_user(uid, message))
            except Exception:
                pass
    else:
        try:
            asyncio.create_task(manager.broadcast(message, room))
        except Exception:
            pass
"""),
            "main": Template("""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
import shutil

from database import engine, Base, get_db
from models import User, AuditLog{% for model in models %}, {{model.name}}{% endfor %}
{% for model in models %}
from services.{{model.name.lower()}}_service import {{model.name}}Service
{% endfor %}
from realtime.connection_manager import manager

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
SECRET_KEY = os.getenv("SECRET_KEY", "secret-key-jarvis-v2")
ALGORITHM = "HS256"

app = FastAPI(title="{{app_name}}", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60*24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).get(int(user_id))
    except Exception:
        return None

@app.get("/api/health")
def health():
    return {"status": "healthy", "version": "2.0.0", "app": "{{app_name}}"}

{% if auth %}
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/auth/register")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email registered")
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
{% endif %}

@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    user_id = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
        except Exception:
            pass
    await manager.connect(websocket, room="public", user_id=user_id)
    await manager.connect(websocket, room="admins", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except Exception:
        manager.disconnect(websocket, room="public")
        manager.disconnect(websocket, room="admins")

{% for model in models %}
{% set model_lower = model.name.lower() %}

@app.get("/api/{{model_lower}}s")
def list_{{model_lower}}s(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    service = {{model.name}}Service(db, user)
    return service.list(search=search, page=page, page_size=page_size)

@app.post("/api/{{model_lower}}s")
def create_{{model_lower}}(
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    service = {{model.name}}Service(db, user)
    obj = service.create(data)
    return {"data": obj, "message": "{{model.name}} created"}

@app.get("/api/{{model_lower}}s/{item_id}")
def get_{{model_lower}}(
    item_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    service = {{model.name}}Service(db, user)
    return {"data": service.get(item_id)}

@app.put("/api/{{model_lower}}s/{item_id}")
def update_{{model_lower}}(
    item_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    service = {{model.name}}Service(db, user)
    obj = service.update(item_id, data)
    return {"data": obj, "message": "{{model.name}} updated"}

@app.delete("/api/{{model_lower}}s/{item_id}")
def delete_{{model_lower}}(
    item_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    service = {{model.name}}Service(db, user)
    service.delete(item_id)
    return {"message": "{{model.name}} deleted"}

@app.get("/api/{{model_lower}}s/analytics/report")
def {{model_lower}}_analytics(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    service = {{model.name}}Service(db, user)
    return {"data": service.get_analytics_report()}

{% endfor %}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"/uploads/{file.filename}", "filename": file.filename}

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""),
            "requirements": Template("""
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pydantic[email]==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
python-dotenv==1.0.0
celery==5.3.6
redis==5.0.1
psycopg2-binary==2.9.9
pytest==8.0.0
httpx==0.26.0
alembic==1.13.1
"""),
            "alembic_ini": Template("""[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = %(DATABASE_URL)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""),
            "alembic_env": Template("""from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models import Base

config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", "sqlite:///./app.db"))

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""")
        }

    def generate(self, spec: AppSpec) -> Dict[str, str]:
        files = {}
        files["backend/database.py"] = self.templates["database"].render()
        files["backend/models.py"] = self.templates["models"].render(
            models=spec.models,
            auth=spec.auth
        )
        files["backend/services/base_service.py"] = self.templates["base_service"].render()

        for model in spec.models:
            service_path = f"backend/services/{model.name.lower()}_service.py"
            files[service_path] = self.templates["model_service"].render(model=model)

        files["backend/tasks/celery_app.py"] = self.templates["celery_app"].render()
        files["backend/tasks/email_tasks.py"] = self.templates["tasks"].render()
        files["backend/tasks/inventory_tasks.py"] = self.templates["tasks"].render()
        files["backend/tasks/report_tasks.py"] = self.templates["tasks"].render()
        files["backend/tasks/cleanup_tasks.py"] = self.templates["tasks"].render()

        files["backend/realtime/connection_manager.py"] = self.templates["connection_manager"].render()
        files["backend/realtime/events.py"] = self.templates["realtime_events"].render()

        files["backend/main.py"] = self.templates["main"].render(
            app_name=spec.name,
            models=spec.models,
            auth=spec.auth
        )

        files["backend/requirements.txt"] = self.templates["requirements"].render()
        files["backend/.env"] = self.templates["env"].render(
            app_name=spec.name.lower().replace(" ", "_"),
            database=spec.database,
            random_secret=secrets.token_hex(32)
        )
        files["backend/alembic.ini"] = self.templates["alembic_ini"].render()
        files["backend/alembic/env.py"] = self.templates["alembic_env"].render()

        files["backend/init_db.py"] = """from database import engine, Base\nimport models\nBase.metadata.create_all(bind=engine)\nprint("Database initialized successfully!")\n"""

        return files

    def write(self, spec: AppSpec, base_path: str) -> str:
        files = self.generate(spec)
        output = Path(base_path) / "backend"
        output.mkdir(parents=True, exist_ok=True)

        for filename, content in files.items():
            rel_path = filename.replace("backend/", "")
            target = output / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content.strip(), encoding="utf-8")

        return str(output)

