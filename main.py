"""TaskMate 1.0 — sua vida escolar organizada.
Your School. Your Tasks. Your Success.
"""
import calendar as pycalendar
import dataclasses
import importlib
import logging
import os
import sqlite3
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from contextlib import contextmanager
from dataclasses import dataclass
from tkinter import messagebox
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence

try:
    import customtkinter as ctk  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:
    raise SystemExit(
        "customtkinter não encontrado. Ative o ambiente virtual e execute:\n"
        "python -m pip install customtkinter==5.2.2 Pillow==11.0.0"
    ) from exc

try:
    Image = importlib.import_module("PIL.Image")
    ImageDraw = importlib.import_module("PIL.ImageDraw")
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Pillow não encontrado. Ative o ambiente virtual e execute:\n"
        "python -m pip install Pillow==11.0.0"
    ) from exc

logger = logging.getLogger("taskmate")
# Arquivo único: telas do CustomTkinter têm muitos atributos, argumentos e
# linhas por natureza. Os limites abaixo são desativados de propósito.
# pylint: disable=too-many-instance-attributes,too-many-arguments
# pylint: disable=too-many-positional-arguments,too-many-locals
# pylint: disable=too-many-statements,too-many-branches,too-many-lines
# pylint: disable=too-few-public-methods,protected-access
# ==========================================================================
# 1. ÍCONES (desenhados na 1ª execução, sem arquivos externos)
# ==========================================================================
SIZE = 64

ICON_COLORS = {
    "white": "#FFFFFF",
    "primary": "#2D6CF6",
    "muted": "#7C8DA8",
    "danger": "#E5484D",
    "success": "#1F9D6B",
    "warning": "#F5A524",
    "sidebar": "#A9BEDD",
}
ICONS = {
    "home": ["white", "primary", "muted", "sidebar"],
    "tasks": ["white", "primary", "muted", "sidebar"],
    "calendar": ["white", "primary", "muted", "sidebar"],
    "book": ["white", "primary", "muted", "sidebar"],
    "plus": ["white", "primary", "muted"],
    "check": ["white", "primary", "muted", "success", "danger"],
    "edit": ["primary", "muted", "white"],
    "trash": ["primary", "muted", "danger", "white"],
    "clock": ["primary", "muted", "white", "danger", "warning"],
    "search": ["muted", "primary"],
    "chevron-left": ["muted", "primary", "white"],
    "chevron-right": ["muted", "primary", "white"],
    "alert": ["danger", "warning", "primary"],
    "user": ["primary", "muted", "white"],
    "refresh": ["muted", "primary"],
    "flag": ["primary", "muted", "white"],
}


def stroke(draw: Any, points, color: str, width: int) -> None:
    """Desenha uma polilinha com cantos e pontas arredondadas."""
    draw.line(points, fill=color, width=width, joint="curve")
    r = width / 2
    for x, y in (points[0], points[-1]):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def round_rect(draw, box, radius, color, width=None):
    """Desenha um retângulo arredondado."""
    if width:
        draw.rounded_rectangle(box, radius=radius, outline=color, width=width)
    else:
        draw.rounded_rectangle(box, radius=radius, fill=color)


def draw_icon(name: str, color: Any) -> Any:
    """Desenha um ícone 64x64 na cor indicada."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 5
    if name == "home":
        stroke(d, [(12, 30), (32, 13), (52, 30)], color, w)
        stroke(d, [(18, 28), (18, 50), (46, 50), (46, 28)], color, w)
        stroke(d, [(27, 50), (27, 38), (37, 38), (37, 50)], color, w)
    elif name == "tasks":
        round_rect(d, (14, 10, 50, 54), 7, color, width=w)
        stroke(d, [(24, 9), (24, 15), (40, 15), (40, 9)], color, w)
        for y in (25, 35, 45):
            d.ellipse([20, y - 3, 26, y + 3], fill=color)
            stroke(d, [(31, y), (44, y)], color, w - 1)
    elif name == "calendar":
        round_rect(d, (10, 14, 54, 52), 8, color, width=w)
        stroke(d, [(10, 24), (54, 24)], color, w - 1)
        stroke(d, [(21, 9), (21, 18)], color, w)
        stroke(d, [(43, 9), (43, 18)], color, w)
        for cx in (21, 32, 43):
            for cy in (33, 43):
                d.ellipse([cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5], fill=color)
    elif name == "book":
        stroke(d, [(32, 20), (32, 50)], color, w)
        stroke(
            d,
            [(32, 20), (16, 17), (10, 20), (10, 48), (16, 45), (32, 48)],
            color,
            w,
        )
        stroke(
            d,
            [(32, 20), (48, 17), (54, 20), (54, 48), (48, 45), (32, 48)],
            color,
            w,
        )
    elif name == "plus":
        stroke(d, [(32, 14), (32, 50)], color, w + 1)
        stroke(d, [(14, 32), (50, 32)], color, w + 1)
    elif name == "check":
        stroke(d, [(15, 34), (27, 46), (50, 19)], color, w + 1)
    elif name == "edit":
        stroke(
            d,
            [(16, 48), (19, 37), (43, 13), (51, 21), (27, 45), (16, 48)],
            color,
            w - 1,
        )
        stroke(d, [(40, 16), (48, 24)], color, w - 1)
    elif name == "trash":
        stroke(d, [(12, 18), (52, 18)], color, w)
        stroke(d, [(26, 18), (26, 11), (38, 11), (38, 18)], color, w)
        stroke(d, [(18, 18), (21, 52), (43, 52), (46, 18)], color, w)
        stroke(d, [(28, 26), (29, 45)], color, w - 2)
        stroke(d, [(36, 26), (35, 45)], color, w - 2)
    elif name == "clock":
        d.ellipse([10, 10, 54, 54], outline=color, width=w)
        stroke(d, [(32, 20), (32, 33), (42, 39)], color, w)
    elif name == "search":
        d.ellipse([10, 10, 42, 42], outline=color, width=w)
        stroke(d, [(38, 38), (52, 52)], color, w + 1)
    elif name == "chevron-left":
        stroke(d, [(38, 14), (22, 32), (38, 50)], color, w)
    elif name == "chevron-right":
        stroke(d, [(26, 14), (42, 32), (26, 50)], color, w)
    elif name == "alert":
        stroke(d, [(32, 12), (56, 52), (8, 52), (32, 12)], color, w - 1)
        stroke(d, [(32, 26), (32, 38)], color, w - 1)
        d.ellipse([29, 42, 35, 48], fill=color)
    elif name == "user":
        d.ellipse([22, 11, 42, 31], outline=color, width=w)
        stroke(
            d,
            [(11, 53), (11, 50), (14, 40), (50, 40), (53, 50), (53, 53)],
            color,
            w,
        )
    elif name == "refresh":
        d.arc([12, 12, 52, 52], start=40, end=330, fill=color, width=w)
        stroke(d, [(44, 10), (44, 24), (30, 24)], color, w)
    elif name == "flag":
        stroke(d, [(17, 10), (17, 54)], color, w)
        stroke(
            d, [(17, 13), (47, 13), (40, 25), (47, 37), (17, 37)], color, w - 1
        )
    return img


def draw_logo(primary="#2D6CF6", white="#FFFFFF") -> Any:
    """Desenha o logotipo do aplicativo."""
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, 127, 127], radius=32, fill=primary)
    stroke(d, [(30, 66), (54, 92), (98, 38)], white, 12)
    return img


def _ensure_icons_dir() -> Path:
    """Gera os PNG em data/icons na primeira execução e reutiliza o cache."""
    target = Path(__file__).resolve().parent / "data" / "icons"
    target.mkdir(parents=True, exist_ok=True)
    if (target / "logo.png").exists():
        return target
    for name, colors in ICONS.items():
        for color in colors:
            path = target / f"{name}-{color}.png"
            if not path.exists():
                draw_icon(name, ICON_COLORS[color]).save(path)
    lanczos = Image.Resampling.LANCZOS
    draw_logo().resize((256, 256), lanczos).save(target / "logo.png")
    return target


# ==========================================================================
# 2. CONFIGURAÇÃO
# ==========================================================================
APP_NAME = "TaskMate"
APP_VERSION = "1.0.0"
APP_SLOGAN = "Your School. Your Tasks. Your Success."
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = _ensure_icons_dir()  # gerados na 1ª execução
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = Path(os.environ.get("TASKMATE_DB", DATA_DIR / "taskmate.db"))
WINDOW_WIDTH = 1240
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 1040
WINDOW_MIN_HEIGHT = 680
SIDEBAR_WIDTH = 236
CONTENT_PADDING = 28
CARD_RADIUS = 16
DATE_FORMAT_INPUT = "%d/%m/%Y"
DATE_FORMAT_DB = "%Y-%m-%d"
TIME_FORMAT_DB = "%H:%M"
DEFAULT_SUBJECTS = [
    ("Matemática", "#2D6CF6"),
    ("Português", "#7B61FF"),
    ("Ciências", "#1F9D6B"),
    ("História", "#C77D2B"),
    ("Geografia", "#0EA5A5"),
    ("Inglês", "#E5484D"),
    ("Arte", "#D9469E"),
]
# ==========================================================================
# 3. TEMA (cores, fontes, espaçamentos)
# ==========================================================================
COLORS = {
    # Neutros
    "bg": "#F3F6FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFE",
    "border": "#E3EAF5",
    "border_strong": "#D3DEED",
    "text": "#0F1B2D",
    "text_muted": "#6B7B93",
    "text_faint": "#98A6BB",
    # Marca
    "primary": "#2D6CF6",
    "primary_hover": "#1F58D6",
    "primary_dark": "#123C9E",
    "primary_soft": "#E8F0FF",
    # Menu lateral
    "sidebar": "#0E2A55",
    "sidebar_soft": "#173A6B",
    "sidebar_hover": "#1C457F",
    "sidebar_active": "#2D6CF6",
    "sidebar_text": "#C2D4EF",
    "sidebar_text_muted": "#7C97C2",
    # Estados
    "danger": "#E5484D",
    "danger_hover": "#C93A3F",
    "danger_soft": "#FDECEC",
    "success": "#1F9D6B",
    "success_hover": "#187A54",
    "success_soft": "#E6F6EF",
    "warning": "#F5A524",
    "warning_soft": "#FFF4E0",
    "info": "#2D6CF6",
    "info_soft": "#E8F0FF",
    "neutral_soft": "#EEF2F9",
}
PRIORITIES = {
    "baixa": {
        "label": "Baixa",
        "color": COLORS["success"],
        "soft": COLORS["success_soft"],
    },
    "media": {
        "label": "Média",
        "color": "#B47600",
        "soft": COLORS["warning_soft"],
    },
    "alta": {
        "label": "Alta",
        "color": COLORS["danger"],
        "soft": COLORS["danger_soft"],
    },
}
FONT_FAMILY = "Segoe UI"
FONT_FALLBACKS = (
    "Segoe UI",
    "Inter",
    "Helvetica Neue",
    "Arial",
    "DejaVu Sans",
)


@lru_cache(maxsize=1)
def font_family() -> str:
    """Escolhe a primeira família de fonte disponível no sistema."""
    try:
        available = set(tkfont.families())
    except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        available = set()
    for family in FONT_FALLBACKS:
        if family in available:
            return family
    return FONT_FAMILY


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    """Cria uma fonte do tema com tamanho e peso."""
    return ctk.CTkFont(family=font_family(), size=size, weight=weight)


def apply_appearance() -> None:
    """Define o tema claro e a cor de fundo padrão do CustomTkinter."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
# ==========================================================================
# 4. CARREGAMENTO DOS ÍCONES
# ==========================================================================w


@lru_cache(maxsize=256)
def _open(path: str) -> Any:
    """Abre a imagem em RGBA (com cache)."""
    return Image.open(path).convert("RGBA")


def icon(name: str, color: str = "primary", size: int = 20) -> ctk.CTkImage:
    """Devolve um CTkImage pronto para uso em botões e rótulos."""
    path = ICONS_DIR / f"{name}-{color}.png"
    if not path.exists():  # fallback: tenta a variante branca
        path = ICONS_DIR / f"{name}-white.png"
    if not path.exists():
        raise FileNotFoundError(f"Ícone não encontrado: {path.name}")
    image = _open(str(path))
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def logo(size: int = 34) -> ctk.CTkImage:
    """Devolve o logotipo como CTkImage."""
    image = _open(str(ICONS_DIR / "logo.png"))
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


# ==========================================================================
# 5. BANCO DE DADOS (SQLite)
# ==========================================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL COLLATE NOCASE UNIQUE,
    color       TEXT    NOT NULL DEFAULT '#2D6CF6',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    description  TEXT    NOT NULL DEFAULT '',
    subject_id   INTEGER,
    due_date     TEXT,
    due_time     TEXT,
    priority     TEXT    NOT NULL DEFAULT 'media'
                 CHECK (priority IN ('baixa', 'media', 'alta')),
    completed    INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    completed_at TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date  ON tasks (due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_subject   ON tasks (subject_id);
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks (completed);
"""


class DatabaseError(Exception):
    """Erro de acesso ao banco de dados."""


class Database:
    """Encapsula a conexão SQLite e as operações de baixo nível."""

    def __init__(self, path: Path | str = DATABASE_PATH) -> None:
        """Guarda o caminho e prepara a conexão."""
        self.path = Path(path)
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
    # ------------------------------------------------------------------ setup

    def connect(self) -> sqlite3.Connection:
        """Abre a conexão e garante schema e dados iniciais."""
        if self._connection is not None:
            return self._connection
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(str(self.path), timeout=10)
        except (
            sqlite3.Error
        ) as exc:  # pragma: no cover - falha de disco/permissão
            raise DatabaseError(
                f"Não foi possível abrir o banco de dados: {exc}"
            ) from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        self._connection = connection
        self._create_schema()
        self._seed_defaults()
        return connection

    def _create_schema(self) -> None:
        """Cria as tabelas e índices que faltarem."""
        assert self._connection is not None
        with self._lock:
            try:
                self._connection.executescript(SCHEMA)
                self._connection.commit()
            except sqlite3.Error as exc:
                raise DatabaseError(
                    f"Falha ao criar as tabelas: {exc}"
                ) from exc

    def _seed_defaults(self) -> None:
        """Insere as disciplinas iniciais apenas quando a tabela está vazia."""
        assert self._connection is not None
        with self._lock:
            total = self._connection.execute(
                "SELECT COUNT(*) FROM subjects"
            ).fetchone()[0]
            if total:
                return
            now = datetime.now().isoformat(sep=" ", timespec="seconds")
            self._connection.executemany(
                "INSERT INTO subjects (name, color, created_at)"
                " VALUES (?, ?, ?)",
                [(name, color, now) for name, color in DEFAULT_SUBJECTS],
            )
            self._connection.execute(
                "INSERT OR IGNORE INTO settings (key, value)"
                " VALUES ('schema_version', '1')"
            )
            self._connection.commit()
    # -------------------------------------------------------------- operações

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        """Cursor com commit/rollback automáticos e tratamento de erro."""
        connection = self.connect()
        cursor = connection.cursor()
        with self._lock:
            try:
                yield cursor
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                logger.exception("Erro no banco de dados")
                raise DatabaseError(f"Erro no banco de dados: {exc}") from exc
            finally:
                cursor.close()

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Executa um SELECT e devolve todas as linhas."""
        with self.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def query_one(
        self, sql: str, params: Sequence[Any] = ()
    ) -> sqlite3.Row | None:
        """Executa um SELECT e devolve a primeira linha."""
        with self.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Executa um comando e devolve o id inserido na última operação."""
        with self.cursor() as cursor:
            cursor.execute(sql, params)
            return int(cursor.lastrowid or 0)

    def execute_many(self, sql: str, params: Iterable[Sequence[Any]]) -> None:
        """Executa o mesmo comando para vários parâmetros."""
        with self.cursor() as cursor:
            cursor.executemany(sql, params)
    # ------------------------------------------------------------- utilitários

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Lê uma configuração salva no banco."""
        row = self.query_one(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Grava ou atualiza uma configuração."""
        self.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def close(self) -> None:
        """Fecha a conexão com o banco."""
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None


# Instância única usada pelo aplicativo
db = Database()
# ==========================================================================
# 6. MODELOS DE DOMÍNIO
# ==========================================================================
PRIORITY_ORDER = {"alta": 0, "media": 1, "baixa": 2}
WEEKDAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)
MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


@dataclass(slots=True)
class Subject:
    """Disciplina escolar com contadores de tarefas."""
    id: int
    name: str
    color: str = "#2D6CF6"
    task_count: int = 0
    pending_count: int = 0

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Subject":
        """Monta a disciplina a partir de uma linha do SQLite."""
        keys = row.keys()
        return cls(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            task_count=row["task_count"] if "task_count" in keys else 0,
            pending_count=(
                row["pending_count"] if "pending_count" in keys else 0
            ),
        )

    @property
    def initials(self) -> str:
        """Iniciais usadas no avatar da disciplina."""
        parts = [part for part in self.name.split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[1][0]).upper()


@dataclass(slots=True)
class Task:
    """Tarefa escolar com prazo, prioridade e disciplina."""
    id: int | None = None
    title: str = ""
    description: str = ""
    subject_id: int | None = None
    due_date: date | None = None
    due_time: time | None = None
    priority: str = "media"
    completed: bool = False
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    subject_name: str = ""
    subject_color: str = "#2D6CF6"
    # --------------------------------------------------------------- criação

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Task":
        """Monta a tarefa a partir de uma linha do SQLite."""
        keys = row.keys()

        def to_date(value: str | None) -> date | None:
            """Converte o texto do banco em date."""
            return (
                datetime.strptime(value, DATE_FORMAT_DB).date()
                if value
                else None
            )

        def to_time(value: str | None) -> time | None:
            """Converte o texto do banco em time."""
            return (
                datetime.strptime(value, TIME_FORMAT_DB).time()
                if value
                else None
            )

        def to_datetime(value: str | None) -> datetime | None:
            """Converte o texto do banco em datetime."""
            if not value:
                return None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            return None
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            subject_id=row["subject_id"],
            due_date=to_date(row["due_date"]),
            due_time=to_time(row["due_time"]),
            priority=row["priority"],
            completed=bool(row["completed"]),
            completed_at=to_datetime(row["completed_at"]),
            created_at=to_datetime(row["created_at"]),
            updated_at=to_datetime(row["updated_at"]),
            subject_name=(
                row["subject_name"]
                if "subject_name" in keys and row["subject_name"]
                else ""
            ),
            subject_color=(
                row["subject_color"]
                if "subject_color" in keys and row["subject_color"]
                else "#2D6CF6"
            ),
        )
    # ------------------------------------------------------------ propriedades

    @property
    def due_datetime(self) -> datetime | None:
        """Prazo completo (23:59 quando não há horário)."""
        if self.due_date is None:
            return None
        return datetime.combine(self.due_date, self.due_time or time(23, 59))

    @property
    def is_overdue(self) -> bool:
        """Verdadeiro quando o prazo passou e não concluiu."""
        if self.completed:
            return False
        deadline = self.due_datetime
        return deadline is not None and deadline < datetime.now()

    @property
    def is_today(self) -> bool:
        """Verdadeiro quando o prazo é hoje."""
        return self.due_date == date.today()

    @property
    def days_left(self) -> int | None:
        """Dias até o prazo (negativo quando atrasada)."""
        if self.due_date is None:
            return None
        return (self.due_date - date.today()).days

    @property
    def priority_order(self) -> int:
        """Peso da prioridade para ordenação."""
        return PRIORITY_ORDER.get(self.priority, 1)

    @property
    def formatted_due(self) -> str:
        """Ex.: 'Hoje, 14:30' / 'Amanhã' / '12/11/2026'."""
        if self.due_date is None:
            return "Sem prazo"
        days = self.days_left
        if days == 0:
            text = "Hoje"
        elif days == 1:
            text = "Amanhã"
        elif days == -1:
            text = "Ontem"
        elif days is not None and 1 < days < 7:
            text = WEEKDAYS[self.due_date.weekday()].capitalize()
        else:
            text = self.due_date.strftime(DATE_FORMAT_INPUT)
        if self.due_time:
            return f"{text}, {self.due_time.strftime(TIME_FORMAT_DB)}"
        return text

    @property
    def due_input(self) -> str:
        """Prazo no formato dd/mm/aaaa."""
        return (
            self.due_date.strftime(DATE_FORMAT_INPUT) if self.due_date else ""
        )

    @property
    def time_input(self) -> str:
        """Horário no formato hh:mm."""
        return self.due_time.strftime(TIME_FORMAT_DB) if self.due_time else ""

    def matches(self, term: str) -> bool:
        """Verdadeiro quando o termo aparece na tarefa."""
        term = term.strip().lower()
        if not term:
            return True
        return (
            term in self.title.lower()
            or term in self.description.lower()
            or term in self.subject_name.lower()
        )


@dataclass(slots=True)
class DashboardStats:
    """Números exibidos no painel principal."""
    total: int = 0
    completed: int = 0
    pending: int = 0
    overdue: int = 0
    today: int = 0
    week: int = 0
    by_priority: dict[str, int] = dataclasses.field(default_factory=dict)
    completion_rate: float = 0.0

    @property
    def in_progress(self) -> int:
        """Tarefas ainda não concluídas."""
        return self.pending


# ==========================================================================
# 7. REPOSITÓRIO DE TAREFAS
# ==========================================================================
TASK_SELECT = """
SELECT t.*, s.name AS subject_name, s.color AS subject_color
FROM tasks t
LEFT JOIN subjects s ON s.id = t.subject_id
"""
SORT_OPEN_FIRST = """
ORDER BY t.completed ASC,
         CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END ASC,
         t.due_date ASC,
         CASE t.priority WHEN 'alta' THEN 0
                         WHEN 'media' THEN 1 ELSE 2 END ASC,
         t.id DESC
"""


class ValidationError(Exception):
    """Dados inválidos informados pelo usuário."""


def parse_date(value: str, field: str = "Data de entrega") -> date | None:
    """Converte 'dd/mm/aaaa' em date. Vazio devolve None (sem prazo)."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT_INPUT).date()
    except ValueError as exc:
        raise ValidationError(
            f"{field} inválida. Use o formato dd/mm/aaaa (ex.: 25/11/2026)."
        ) from exc


def parse_choice_time(value: str) -> time | None:
    """Converte 'hh:mm' em time; vazio devolve None."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, TIME_FORMAT_DB).time()
    except ValueError as exc:
        raise ValidationError(
            "Horário inválido. Use o formato hh:mm (ex.: 14:30)."
        ) from exc


class TaskRepository:
    """CRUD e consultas de tarefas sobre o SQLite."""

    def __init__(self, database: Database = db) -> None:
        """Recebe o banco usado nas consultas."""
        self.db = database
    # ----------------------------------------------------------------- leitura

    def all(self, include_completed: bool = True) -> list[Task]:
        """Lista as tarefas (todas ou só as pendentes)."""
        sql = TASK_SELECT + SORT_OPEN_FIRST
        if not include_completed:
            sql = TASK_SELECT + " WHERE t.completed = 0 " + SORT_OPEN_FIRST
        return [Task.from_row(row) for row in self.db.query(sql)]

    def get(self, task_id: int) -> Task | None:
        """Busca uma tarefa pelo id."""
        row = self.db.query_one(TASK_SELECT + " WHERE t.id = ?", (task_id,))
        return Task.from_row(row) if row else None

    def filter(
        self,
        *,
        subject_id: int | None = None,
        status: str = "todas",
        priority: str | None = None,
        search: str = "",
    ) -> list[Task]:
        """status: todas | pendentes | concluidas | atrasadas."""
        tasks = self.all()
        today = date.today()
        if subject_id:
            tasks = [task for task in tasks if task.subject_id == subject_id]
        if priority:
            tasks = [task for task in tasks if task.priority == priority]
        if status == "pendentes":
            tasks = [task for task in tasks if not task.completed]
        elif status == "concluidas":
            tasks = [task for task in tasks if task.completed]
        elif status == "atrasadas":
            tasks = [task for task in tasks if task.is_overdue]
        elif status == "hoje":
            tasks = [
                task
                for task in tasks
                if task.due_date == today and not task.completed
            ]
        if search.strip():
            tasks = [task for task in tasks if task.matches(search)]
        return tasks

    def by_date(self, target: date) -> list[Task]:
        """Tarefas com prazo na data informada."""
        rows = self.db.query(
            TASK_SELECT + " WHERE t.due_date = ? " + SORT_OPEN_FIRST,
            (target.strftime(DATE_FORMAT_DB),),
        )
        return [Task.from_row(row) for row in rows]

    def dates_with_tasks(
        self, start: date, end: date
    ) -> dict[date, list[Task]]:
        """Agrupa as tarefas por dia no intervalo."""
        rows = self.db.query(
            TASK_SELECT
            + " WHERE t.due_date BETWEEN ? AND ? "
            + "ORDER BY t.due_date, t.due_time",
            (start.strftime(DATE_FORMAT_DB), end.strftime(DATE_FORMAT_DB)),
        )
        grouped: dict[date, list[Task]] = {}
        for row in rows:
            task = Task.from_row(row)
            if task.due_date:
                grouped.setdefault(task.due_date, []).append(task)
        return grouped

    def upcoming(self, limit: int = 5) -> list[Task]:
        """Próximos prazos: pendentes com data, do mais próximo em diante."""
        today = date.today()
        upper = today + timedelta(days=60)
        rows = self.db.query(
            TASK_SELECT
            + " WHERE t.completed = 0 AND t.due_date IS NOT NULL"
            + " AND t.due_date BETWEEN ? AND ?"
            + " ORDER BY t.due_date ASC, t.due_time ASC,"
            + " CASE t.priority WHEN 'alta' THEN 0"
            + " WHEN 'media' THEN 1 ELSE 2 END"
            + " LIMIT ?",
            (
                today.strftime(DATE_FORMAT_DB),
                upper.strftime(DATE_FORMAT_DB),
                limit,
            ),
        )
        return [Task.from_row(row) for row in rows]

    def recent(self, limit: int = 5) -> list[Task]:
        """Últimas tarefas cadastradas."""
        rows = self.db.query(
            TASK_SELECT + " ORDER BY t.id DESC LIMIT ?", (limit,)
        )
        return [Task.from_row(row) for row in rows]

    def stats(self) -> DashboardStats:
        """Calcula os indicadores do painel."""
        rows = self.db.query(TASK_SELECT)
        tasks = [Task.from_row(row) for row in rows]
        today = date.today()
        stats = DashboardStats(total=len(tasks))
        stats.by_priority = {"alta": 0, "media": 0, "baixa": 0}
        for task in tasks:
            stats.by_priority[task.priority] = (
                stats.by_priority.get(task.priority, 0) + 1
            )
            if task.completed:
                stats.completed += 1
                continue
            stats.pending += 1
            if task.is_overdue:
                stats.overdue += 1
            if task.due_date == today:
                stats.today += 1
            if task.due_date and today <= task.due_date <= today + timedelta(
                days=7
            ):
                stats.week += 1
        if stats.total:
            stats.completion_rate = stats.completed / stats.total * 100
        return stats
    # ---------------------------------------------------------------- escrita

    def create(self, task: Task) -> int:
        """Valida e grava uma nova tarefa."""
        self._validate(task)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.db.execute(
            """
            INSERT INTO tasks (title, description, subject_id, due_date,
                               due_time, priority, completed, completed_at,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.title.strip(),
                task.description.strip(),
                task.subject_id,
                (
                    task.due_date.strftime(DATE_FORMAT_DB)
                    if task.due_date
                    else None
                ),
                (
                    task.due_time.strftime(TIME_FORMAT_DB)
                    if task.due_time
                    else None
                ),
                task.priority,
                1 if task.completed else 0,
                now if task.completed else None,
                now,
                now,
            ),
        )

    def update(self, task: Task) -> None:
        """Valida e atualiza a tarefa existente."""
        if not task.id:
            raise ValidationError("Tarefa inválida: id ausente.")
        self._validate(task)
        self.db.execute(
            """
            UPDATE tasks
               SET title = ?, description = ?, subject_id = ?, due_date = ?,
                   due_time = ?, priority = ?, updated_at = ?
             WHERE id = ?
            """,
            (
                task.title.strip(),
                task.description.strip(),
                task.subject_id,
                (
                    task.due_date.strftime(DATE_FORMAT_DB)
                    if task.due_date
                    else None
                ),
                (
                    task.due_time.strftime(TIME_FORMAT_DB)
                    if task.due_time
                    else None
                ),
                task.priority,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                task.id,
            ),
        )

    def set_completed(self, task_id: int, completed: bool) -> None:
        """Marca ou desmarca a conclusão."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute(
            "UPDATE tasks SET completed = ?, completed_at = ?,"
            " updated_at = ? WHERE id = ?",
            (1 if completed else 0, now if completed else None, now, task_id),
        )

    def toggle_completed(self, task_id: int) -> bool:
        """Inverte a conclusão e devolve o estado."""
        task = self.get(task_id)
        if task is None:
            raise ValidationError("Tarefa não encontrada.")
        self.set_completed(task_id, not task.completed)
        return not task.completed

    def delete(self, task_id: int) -> None:
        """Exclui a tarefa pelo id."""
        self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def count(self) -> int:
        """Quantidade total de tarefas."""
        row = self.db.query_one("SELECT COUNT(*) AS total FROM tasks")
        return int(row["total"]) if row else 0
    # ------------------------------------------------------------- validação

    @staticmethod
    def _validate(task: Task) -> None:
        """Aplica as regras de validação da tarefa."""
        title = (task.title or "").strip()
        if not title:
            raise ValidationError("Informe o título da tarefa.")
        if len(title) < 3:
            raise ValidationError("O título deve ter pelo menos 3 caracteres.")
        if len(title) > 120:
            raise ValidationError(
                "O título deve ter no máximo 120 caracteres."
            )
        if len((task.description or "")) > 1000:
            raise ValidationError(
                "A descrição deve ter no máximo 1000 caracteres."
            )
        if task.priority not in ("baixa", "media", "alta"):
            raise ValidationError("Prioridade inválida.")
        if task.due_time and not task.due_date:
            raise ValidationError(
                "Informe a data de entrega para definir um horário."
            )
        if task.due_date and task.due_date.year < 2000:
            raise ValidationError("Data de entrega inválida.")


# ==========================================================================
# 8. REPOSITÓRIO DE DISCIPLINAS
# ==========================================================================
SUBJECT_SELECT = """
SELECT s.*,
       (SELECT COUNT(*) FROM tasks t WHERE t.subject_id = s.id) AS task_count,
       (SELECT COUNT(*) FROM tasks t
        WHERE t.subject_id = s.id AND t.completed = 0) AS pending_count
FROM subjects s
ORDER BY s.name COLLATE NOCASE
"""


class SubjectRepository:
    """CRUD de disciplinas escolares."""

    def __init__(self, database: Database = db) -> None:
        """Recebe o banco usado nas consultas."""
        self.db = database

    def all(self) -> list[Subject]:
        """Lista as disciplinas com seus contadores."""
        return [Subject.from_row(row) for row in self.db.query(SUBJECT_SELECT)]

    def get(self, subject_id: int) -> Subject | None:
        """Busca uma disciplina pelo id."""
        row = self.db.query_one(
            "SELECT s.*, 0 AS task_count, 0 AS pending_count"
            " FROM subjects s WHERE s.id = ?",
            (subject_id,),
        )
        return Subject.from_row(row) if row else None

    def create(self, name: str, color: str) -> int:
        """Valida e cadastra uma disciplina."""
        name = (name or "").strip()
        if len(name) < 2:
            raise ValueError(
                "O nome da disciplina deve ter pelo menos 2 caracteres."
            )
        if len(name) > 40:
            raise ValueError(
                "O nome da disciplina deve ter no máximo 40 caracteres."
            )
        try:
            return self.db.execute(
                "INSERT INTO subjects (name, color, created_at)"
                " VALUES (?, ?, ?)",
                (name, color, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
        except DatabaseError as exc:
            if "UNIQUE" in str(exc):
                raise ValueError(
                    f'A disciplina "{name}" já está cadastrada.'
                ) from exc
            raise

    def update(self, subject_id: int, name: str, color: str) -> None:
        """Valida e altera nome e cor da disciplina."""
        name = (name or "").strip()
        if len(name) < 2:
            raise ValueError(
                "O nome da disciplina deve ter pelo menos 2 caracteres."
            )
        if len(name) > 40:
            raise ValueError(
                "O nome da disciplina deve ter no máximo 40 caracteres."
            )
        try:
            self.db.execute(
                "UPDATE subjects SET name = ?, color = ? WHERE id = ?",
                (name, color, subject_id),
            )
        except DatabaseError as exc:
            if "UNIQUE" in str(exc):
                raise ValueError(
                    f'A disciplina "{name}" já está cadastrada.'
                ) from exc
            raise

    def delete(self, subject_id: int) -> int:
        """Exclui a disciplina; devolve tarefas que ficaram sem ela."""
        count = self.count_tasks(subject_id)
        self.db.execute(
            "UPDATE tasks SET subject_id = NULL WHERE subject_id = ?",
            (subject_id,),
        )
        self.db.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        return count

    def count_tasks(self, subject_id: int) -> int:
        """Quantas tarefas usam a disciplina."""
        row = self.db.query_one(
            "SELECT COUNT(*) AS total FROM tasks WHERE subject_id = ?",
            (subject_id,),
        )
        return int(row["total"]) if row else 0

    def name_exists(self, name: str, ignore_id: int | None = None) -> bool:
        """Verdadeiro quando o nome já está em uso."""
        row = self.db.query_one(
            "SELECT id FROM subjects WHERE name = ? COLLATE NOCASE"
            " AND id IS NOT ?",
            (name.strip(), ignore_id),
        )
        return row is not None


def is_unique_error(exc: sqlite3.Error) -> bool:
    """Diz se o erro é de nome duplicado."""
    return "UNIQUE" in str(exc)
# ==========================================================================
# 9. BOTÕES
# ==========================================================================


def primary_button(
    master,
    text: str,
    command: Callable[[], None],
    *,
    width: int = 150,
    height: int = 40,
    icon_name: str | None = None,
    icon_color: str = "white",
) -> ctk.CTkButton:
    """Cria um botão primário (ação principal)."""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=10,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="#FFFFFF",
        font=font(13, "bold"),
        image=icon(icon_name, icon_color, 18) if icon_name else None,
        compound="left",
        border_spacing=8,
    )


def secondary_button(
    master,
    text: str,
    command: Callable[[], None],
    *,
    width: int = 130,
    height: int = 40,
    icon_name: str | None = None,
) -> ctk.CTkButton:
    """Cria um botão secundário com borda."""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=10,
        fg_color=COLORS["surface"],
        hover_color=COLORS["primary_soft"],
        text_color=COLORS["text"],
        border_width=1,
        border_color=COLORS["border_strong"],
        font=font(13, "bold"),
        image=icon(icon_name, "primary", 18) if icon_name else None,
        compound="left",
        border_spacing=8,
    )


def ghost_button(
    master,
    text: str,
    command: Callable[[], None],
    *,
    width: int = 110,
    height: int = 38,
) -> ctk.CTkButton:
    """Cria um botão discreto, sem fundo."""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=10,
        fg_color="transparent",
        hover_color=COLORS["neutral_soft"],
        text_color=COLORS["text_muted"],
        font=font(13),
    )


def icon_button(
    master,
    icon_name: str,
    command: Callable[[], None],
    *,
    color: str = "primary",
    icon_color: str = "primary",
    size: int = 34,
) -> ctk.CTkButton:
    """Cria um botão quadrado apenas com ícone."""
    button = ctk.CTkButton(
        master,
        text="",
        command=command,
        width=size,
        height=size,
        corner_radius=9,
        fg_color=COLORS["surface_alt"],
        hover_color=color,
        image=icon(icon_name, icon_color, 18),
    )
    return button


def danger_button(
    master,
    text: str,
    command: Callable[[], None],
    *,
    width: int = 130,
    height: int = 40,
) -> ctk.CTkButton:
    """Cria um botão de ação destrutiva."""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=10,
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        text_color="#FFFFFF",
        font=font(13, "bold"),
    )
# ==========================================================================
# 10. CARTÕES, SELOS E ESTADOS VAZIOS
# ==========================================================================


class Card(ctk.CTkFrame):
    """Superfície branca com cantos arredondados e borda suave."""

    def __init__(
        self, master, radius: int = 16, padding: int = 0, **kwargs
    ) -> None:
        """Cria a superfície do cartão."""
        kwargs.setdefault("fg_color", COLORS["surface"])
        kwargs.setdefault("border_color", COLORS["border"])
        kwargs.setdefault("border_width", 1)
        super().__init__(master, corner_radius=radius, **kwargs)
        self.padding = padding


class SectionHeader(ctk.CTkFrame):
    """Título de seção com subtítulo e eventual ação à direita."""

    def __init__(
        self,
        master,
        title: str,
        subtitle: str = "",
        action_text: str | None = None,
        action: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        """Monta título, subtítulo e ação opcional."""
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            text_frame,
            text=title,
            font=font(16, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                text_frame,
                text=subtitle,
                font=font(12),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(anchor="w", pady=(2, 0))
        if action_text and action:
            ctk.CTkButton(
                self,
                text=action_text,
                command=action,
                width=88,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLORS["primary_soft"],
                text_color=COLORS["primary"],
                font=font(12, "bold"),
            ).grid(row=0, column=1, sticky="e")


class Badge(ctk.CTkFrame):
    """Etiqueta compacta colorida (prioridade, status, disciplina)."""

    def __init__(
        self, master, text: str, color: str, soft: str, **kwargs
    ) -> None:
        """Cria a etiqueta com ponto colorido."""
        super().__init__(master, fg_color=soft, corner_radius=8, **kwargs)
        dot = ctk.CTkFrame(
            self, fg_color=color, width=7, height=7, corner_radius=4
        )
        dot.pack(side="left", padx=(9, 0), pady=1)
        ctk.CTkLabel(
            self, text=text, font=font(11, "bold"), text_color=color, height=20
        ).pack(side="left", padx=(5, 9))


def priority_badge(master, priority: str) -> Badge:
    """Etiqueta colorida da prioridade."""
    data = PRIORITIES.get(priority, PRIORITIES["media"])
    return Badge(master, data["label"], data["color"], data["soft"])


def subject_badge(master, name: str, color: str) -> Badge:
    """Etiqueta colorida da disciplina."""
    return Badge(
        master,
        name or "Sem disciplina",
        color or COLORS["primary"],
        COLORS["neutral_soft"],
    )


class EmptyState(ctk.CTkFrame):
    """Mensagem amigável para listas vazias."""

    def __init__(
        self,
        master,
        title: str,
        message: str,
        icon_name: str = "tasks",
        action_text: str | None = None,
        action: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        """Monta o estado vazio com ícone e ação."""
        super().__init__(master, fg_color="transparent", **kwargs)
        holder = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface_alt"],
            width=62,
            height=62,
            corner_radius=31,
        )
        holder.pack(pady=(18, 12))
        holder.pack_propagate(False)
        ctk.CTkLabel(holder, text="", image=icon(icon_name, "muted", 26)).pack(
            expand=True
        )
        ctk.CTkLabel(
            self, text=title, font=font(14, "bold"), text_color=COLORS["text"]
        ).pack()
        ctk.CTkLabel(
            self,
            text=message,
            font=font(12),
            text_color=COLORS["text_muted"],
            wraplength=360,
            justify="center",
        ).pack(pady=(4, 0))
        if action_text and action:
            ctk.CTkButton(
                self,
                text=action_text,
                command=action,
                height=34,
                width=160,
                corner_radius=9,
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                text_color="#FFFFFF",
                font=font(12, "bold"),
            ).pack(pady=(14, 18))


def divider(master, **kwargs) -> ctk.CTkFrame:
    """Linha fina de separação."""
    return ctk.CTkFrame(master, height=1, fg_color=COLORS["border"], **kwargs)
# ==========================================================================
# 11. CARTÃO DE TAREFA
# ==========================================================================


class TaskCard(ctk.CTkFrame):
    """Linha de tarefa: conclusão, título, disciplina, prazo e ações."""

    def __init__(
        self,
        master,
        task: Task,
        *,
        on_toggle: Callable[[Task], None] | None = None,
        on_edit: Callable[[Task], None] | None = None,
        on_delete: Callable[[Task], None] | None = None,
        compact: bool = False,
        show_subject: bool = True,
        **kwargs,
    ) -> None:
        """Monta a linha da tarefa."""
        super().__init__(
            master,
            fg_color=COLORS["surface"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        self.task = task
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.grid_columnconfigure(1, weight=1)
        priority = PRIORITIES.get(task.priority, PRIORITIES["media"])
        accent = COLORS["text_faint"] if task.completed else priority["color"]
        # Barra de prioridade (tk.Frame garante altura previsível)
        tk.Frame(self, width=4, bg=accent, highlightthickness=0, bd=0).grid(
            row=0, column=0, sticky="ns", padx=(0, 0), pady=10
        )
        # Botão de conclusão
        self.check_button = ctk.CTkButton(
            self,
            text="" if not task.completed else "✓",
            width=26,
            height=26,
            corner_radius=13,
            fg_color=(
                COLORS["success"] if task.completed else COLORS["surface"]
            ),
            hover_color=(
                COLORS["success_soft"]
                if task.completed
                else COLORS["primary_soft"]
            ),
            border_width=2 if not task.completed else 0,
            border_color=COLORS["border_strong"],
            text_color="#FFFFFF",
            font=font(14, "bold"),
            command=self._toggle,
        )
        self.check_button.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(14, 0),
            pady=(0 if compact else 4, 0),
        )
        # Bloco de texto
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(12, 8),
            pady=(10 if compact else 12, 10),
        )
        title_color = (
            COLORS["text_faint"] if task.completed else COLORS["text"]
        )
        self.title_label = ctk.CTkLabel(
            text_frame,
            text=task.title,
            font=font(13, "bold"),
            text_color=title_color,
            anchor="w",
            justify="left",
        )
        self.title_label.pack(anchor="w")
        if task.completed:
            self.title_label.configure(text=self._strike(task.title))
        meta_parts: list[str] = []
        if show_subject and task.subject_name:
            meta_parts.append(task.subject_name)
        if task.due_date:
            meta_parts.append(task.formatted_due)
        if task.description and not compact:
            meta_parts.append(self._shorten(task.description, 60))
        if meta_parts:
            meta_color = (
                COLORS["danger"] if task.is_overdue else COLORS["text_muted"]
            )
            ctk.CTkLabel(
                text_frame,
                text="  •  ".join(meta_parts),
                font=font(11),
                text_color=meta_color,
                anchor="w",
                justify="left",
            ).pack(anchor="w", pady=(2, 0))
        # Selo de prazo crítico
        if task.is_overdue:
            self._status_chip(
                "Atrasada", COLORS["danger"], COLORS["danger_soft"]
            )
        elif task.is_today and not task.completed:
            self._status_chip(
                "Hoje", COLORS["warning"], COLORS["warning_soft"]
            )
        elif task.completed:
            self._status_chip(
                "Concluída", COLORS["success"], COLORS["success_soft"]
            )
        # Ações
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=0, column=3, sticky="e", padx=(0, 12))
        if on_edit:
            ctk.CTkButton(
                actions,
                text="",
                width=30,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLORS["primary_soft"],
                image=icon("edit", "muted", 16),
                command=lambda: self.on_edit and self.on_edit(self.task),
            ).pack(side="left", padx=2)
        if on_delete:
            ctk.CTkButton(
                actions,
                text="",
                width=30,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLORS["danger_soft"],
                image=icon("trash", "muted", 16),
                command=lambda: self.on_delete and self.on_delete(self.task),
            ).pack(side="left", padx=2)
    # ------------------------------------------------------------- auxiliares

    def _status_chip(self, text: str, color: str, soft: str) -> None:
        """Selo de status no canto direito."""
        chip = ctk.CTkFrame(self, fg_color=soft, corner_radius=7, height=22)
        chip.grid(row=0, column=4, sticky="e", padx=(0, 4))
        ctk.CTkLabel(
            chip,
            text=text,
            font=font(10, "bold"),
            text_color=color,
            height=20,
        ).pack(padx=9)

    def _toggle(self) -> None:
        """Avisa a tela do clique no círculo."""
        if self.on_toggle:
            self.on_toggle(self.task)

    @staticmethod
    def _strike(text: str) -> str:
        """Tachado com caracteres combinantes (vale para qualquer fonte)."""
        return "".join(char + "\u0336" for char in text)

    @staticmethod
    def _shorten(text: str, limit: int) -> str:
        """Corta o texto longo com reticências."""
        text = " ".join(text.split())
        return text if len(text) <= limit else text[: limit - 1] + "…"
# ==========================================================================
# 12. JANELAS MODAIS
# ==========================================================================


class BaseDialog(ctk.CTkToplevel):
    """Toplevel modal, centrado sobre a janela principal."""

    def __init__(
        self, master, title: str, subtitle: str = "", width: int = 520
    ) -> None:
        """Monta cabeçalho, corpo e rodapé do modal."""
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)
        self.transient(master)
        self.result = None
        self._on_close: object | None = None
        # Referência ao app: os diálogos usam os repositórios
        self.app = (
            master
            if hasattr(master, "repositories")
            else getattr(master, "app", None)
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        # Cabeçalho
        header = ctk.CTkFrame(
            self, fg_color=COLORS["surface"], corner_radius=0, height=76
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        head_text = ctk.CTkFrame(header, fg_color="transparent")
        head_text.grid(row=0, column=0, sticky="w", padx=24, pady=16)
        ctk.CTkLabel(
            head_text,
            text=title,
            font=font(18, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                head_text,
                text=subtitle,
                font=font(12),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            header,
            text="✕",
            width=32,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLORS["neutral_soft"],
            text_color=COLORS["text_muted"],
            font=font(14),
            command=self._cancel,
        ).grid(row=0, column=1, padx=(0, 16))
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(18, 8))
        self.body.grid_columnconfigure(0, weight=1)
        self.footer = ctk.CTkFrame(
            self, fg_color=COLORS["surface"], corner_radius=0, height=72
        )
        self.footer.grid(row=2, column=0, sticky="ew")
        self.footer.grid_propagate(False)
        self._width = width
        self._center(master, width)
        self.bind("<Escape>", lambda _event: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
    # ------------------------------------------------------------------ layout

    def _center(self, master, width: int) -> None:
        """Centraliza a janela sobre a principal."""
        self.update_idletasks()
        height = self.winfo_reqheight()
        try:
            x = master.winfo_rootx() + (master.winfo_width() - width) // 2
            y = master.winfo_rooty() + max(
                20, (master.winfo_height() - height) // 2
            )
        except tk.TclError:  # janela ainda sem geometria
            x, y = 200, 120
        self.geometry(f"{width}x{height}+{max(20, x)}+{max(20, y)}")

    def add_footer_button(
        self,
        text: str,
        command: Callable[[], None],
        *,
        primary: bool = True,
        icon_name: str | None = None,
    ) -> ctk.CTkButton:
        """Adiciona um botão ao rodapé."""
        button = ctk.CTkButton(
            self.footer,
            text=text,
            command=command,
            width=130,
            height=40,
            corner_radius=10,
            fg_color=COLORS["primary"] if primary else COLORS["surface"],
            hover_color=(
                COLORS["primary_hover"] if primary else COLORS["neutral_soft"]
            ),
            text_color="#FFFFFF" if primary else COLORS["text"],
            border_width=0 if primary else 1,
            border_color=COLORS["border_strong"],
            font=font(13, "bold"),
            image=(
                icon(icon_name, "white" if primary else "primary", 17)
                if icon_name
                else None
            ),
            compound="left",
            border_spacing=6,
        )
        button.pack(side="right", padx=(8, 0), pady=16)
        return button

    def show(self, on_close: Callable[[object], None] | None = None):
        """Exibe a janela e devolve o resultado após fechar."""
        self._on_close = on_close
        self.deiconify()
        self.lift()
        self.grab_set()
        self.after(10, self.focus_force)
        self.wait_window()
        if on_close:
            on_close(self.result)
        return self.result
    # ------------------------------------------------------------------ fechar

    def _finish(self, result: object) -> None:
        """Guarda o resultado e fecha o modal."""
        self.result = result
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def destroy(self) -> None:
        """Cancela tarefas agendadas antes de destruir (evita erro no Tcl)."""
        for after_id in getattr(self, "_after_ids", []):
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        super().destroy()

    def _cancel(self) -> None:
        """Fecha o modal sem resultado."""
        self._finish(None)


class ConfirmDialog(BaseDialog):
    """Confirmação simples com texto e dois botões."""

    def __init__(
        self,
        master,
        title: str,
        message: str,
        confirm_text: str = "Confirmar",
        danger: bool = False,
    ) -> None:
        """Monta a pergunta de confirmação."""
        super().__init__(master, title, width=430)
        ctk.CTkLabel(
            self.body,
            text=message,
            font=font(13),
            text_color=COLORS["text_muted"],
            wraplength=370,
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.add_footer_button(
            confirm_text, lambda: self._finish(True), primary=True
        )
        if danger:
            for child in self.footer.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    child.configure(
                        fg_color=COLORS["danger"],
                        hover_color=COLORS["danger_hover"],
                    )
        self.add_footer_button("Cancelar", self._cancel, primary=False)
        self._center(master, 430)


# ==========================================================================
# 13. FORMULÁRIO DE TAREFA
# ==========================================================================
PRIORITY_LABELS = {"baixa": "Baixa", "media": "Média", "alta": "Alta"}


class TaskDialog(BaseDialog):
    """Formulário modal para criar ou editar uma tarefa."""

    def __init__(self, master, subjects, task: Task | None = None) -> None:
        """Monta o formulário de tarefa."""
        is_edit = task is not None
        super().__init__(
            master,
            "Editar tarefa" if is_edit else "Nova tarefa",
            (
                "Atualize as informações da atividade."
                if is_edit
                else "Registre um trabalho, prova ou exercício."
            ),
            width=560,
        )
        self.task = task or Task()
        self.subjects = subjects
        self._subject_by_name = {
            subject.name: subject.id for subject in subjects
        }
        body = self.body
        row = 0
        # Título
        self._label(body, "Título da tarefa", row)
        self.title_entry = self._entry(
            body, "Ex.: Lista de exercícios – capítulo 5"
        )
        self.title_entry.grid(row=row + 1, column=0, sticky="ew", pady=(0, 12))
        row += 2
        # Disciplina e prioridade lado a lado
        two = ctk.CTkFrame(body, fg_color="transparent")
        two.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        two.grid_columnconfigure((0, 1), weight=1)
        row += 1
        left = ctk.CTkFrame(two, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._label(left, "Disciplina", 0)
        self.subject_menu = ctk.CTkOptionMenu(
            left,
            values=["Sem disciplina"] + [subject.name for subject in subjects],
            height=38,
            corner_radius=9,
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary_soft"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["primary_soft"],
            font=font(12),
            dropdown_font=font(12),
        )
        self.subject_menu.grid(row=1, column=0, sticky="ew")
        right = ctk.CTkFrame(two, fg_color="transparent")
        right.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._label(right, "Prioridade", 0)
        self.priority_switch = ctk.CTkSegmentedButton(
            right,
            values=["Baixa", "Média", "Alta"],
            height=38,
            corner_radius=9,
            fg_color=COLORS["surface_alt"],
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["surface_alt"],
            unselected_hover_color=COLORS["primary_soft"],
            text_color="#FFFFFF",
            text_color_disabled=COLORS["text_muted"],
            font=font(12, "bold"),
        )
        self.priority_switch.grid(row=1, column=0, sticky="ew")
        # Data e hora
        when = ctk.CTkFrame(body, fg_color="transparent")
        when.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        when.grid_columnconfigure((0, 1), weight=1)
        row += 1
        date_box = ctk.CTkFrame(when, fg_color="transparent")
        date_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._label(date_box, "Data de entrega", 0)
        self.date_entry = self._entry(date_box, "dd/mm/aaaa")
        self.date_entry.grid(row=1, column=0, sticky="ew")
        time_box = ctk.CTkFrame(when, fg_color="transparent")
        time_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._label(time_box, "Horário (opcional)", 0)
        self.time_entry = self._entry(time_box, "hh:mm")
        self.time_entry.grid(row=1, column=0, sticky="ew")
        hint = ctk.CTkLabel(
            body,
            text="Deixe a data vazia para uma tarefa sem prazo definido.",
            font=font(10),
            text_color=COLORS["text_faint"],
            anchor="w",
        )
        hint.grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1
        # Descrição
        self._label(body, "Descrição (opcional)", row)
        self.description_box = ctk.CTkTextbox(
            body,
            height=92,
            corner_radius=9,
            border_width=1,
            border_color=COLORS["border_strong"],
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            font=font(12),
            wrap="word",
        )
        self.description_box.grid(
            row=row + 1, column=0, sticky="ew", pady=(0, 6)
        )
        row += 2
        # Mensagem de erro
        self.error_label = ctk.CTkLabel(
            body,
            text="",
            font=font(11, "bold"),
            text_color=COLORS["danger"],
            anchor="w",
        )
        self.error_label.grid(row=row, column=0, sticky="w")
        # Rodapé
        self.add_footer_button(
            "Salvar" if is_edit else "Adicionar tarefa",
            self._save,
            primary=True,
            icon_name="check",
        )
        self.add_footer_button("Cancelar", self._cancel, primary=False)
        self._fill_fields()
        self._center(master, 560)
        self.after(60, self.title_entry.focus_set)
    # ----------------------------------------------------------------- helpers

    def _label(self, master, text: str, row: int) -> None:
        """Rótulo em maiúsculas acima do campo."""
        ctk.CTkLabel(
            master,
            text=text.upper(),
            font=font(10, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(0, 5))

    def _entry(self, master, placeholder: str) -> ctk.CTkEntry:
        """Campo de texto padronizado."""
        return ctk.CTkEntry(
            master,
            placeholder_text=placeholder,
            height=38,
            corner_radius=9,
            border_width=1,
            border_color=COLORS["border_strong"],
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_faint"],
            font=font(12),
        )

    def _fill_fields(self) -> None:
        """Preenche o formulário com a tarefa atual."""
        task = self.task
        if task.title:
            self.title_entry.insert(0, task.title)
        if task.description:
            self.description_box.insert("1.0", task.description)
        if task.due_date:
            self.date_entry.insert(0, task.due_input)
        if task.due_time:
            self.time_entry.insert(0, task.time_input)
        name = task.subject_name or "Sem disciplina"
        self.subject_menu.set(
            name if name in self._subject_by_name else "Sem disciplina"
        )
        self.priority_switch.set(PRIORITY_LABELS.get(task.priority, "Média"))

    def _show_error(self, message: str) -> None:
        """Exibe a mensagem de erro do formulário."""
        self.error_label.configure(text=message)
    # ---------------------------------------------------------------- salvar

    def _save(self) -> None:
        """Valida e grava a tarefa."""
        self.error_label.configure(text="")
        try:
            due_date = parse_date(self.date_entry.get())
            due_time = parse_choice_time(self.time_entry.get())
            priority = {
                label: key for key, label in PRIORITY_LABELS.items()
            }.get(self.priority_switch.get(), "media")
            subject_name = self.subject_menu.get()
            subject_id = self._subject_by_name.get(subject_name)
            candidate = Task(
                id=self.task.id,
                title=self.title_entry.get().strip(),
                description=self.description_box.get("1.0", "end").strip(),
                subject_id=subject_id,
                due_date=due_date,
                due_time=due_time,
                priority=priority,
                completed=self.task.completed,
            )
            repository = self.app.repositories["tasks"]
            if self.task.id:
                repository.update(candidate)
            else:
                repository.create(candidate)
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        except DatabaseError as exc:
            self._show_error(f"Não foi possível salvar: {exc}")
            return
        self._finish(True)


# ==========================================================================
# 14. MENU LATERAL
# ==========================================================================
NAV_ITEMS = [
    ("dashboard", "Painel", "home"),
    ("tasks", "Tarefas", "tasks"),
    ("calendar", "Calendário", "calendar"),
    ("subjects", "Disciplinas", "book"),
]


class SidebarButton(ctk.CTkFrame):
    """Item do menu com ícone, rótulo e estado ativo."""

    def __init__(
        self,
        master,
        key: str,
        label: str,
        icon_name: str,
        command: Callable[[str], None],
    ) -> None:
        """Monta o item do menu."""
        super().__init__(master, fg_color="transparent", height=44)
        self.key = key
        self.command = command
        self.active = False
        self.grid_columnconfigure(1, weight=1)
        self.indicator = ctk.CTkFrame(
            self, width=3, height=22, fg_color="transparent", corner_radius=2
        )
        self.indicator.grid(row=0, column=0, padx=(0, 0), pady=11, sticky="w")
        self.button = ctk.CTkButton(
            self,
            text=label,
            anchor="w",
            height=44,
            corner_radius=10,
            fg_color="transparent",
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["sidebar_text"],
            font=font(13, "bold"),
            image=icon(icon_name, "sidebar", 19),
            compound="left",
            border_spacing=12,
            command=lambda: self.command(self.key),
        )
        self.button.grid(row=0, column=0, columnspan=2, sticky="ew")

    def set_active(self, active: bool) -> None:
        """Aplica o estado ativo ou inativo."""
        self.active = active
        if active:
            self.button.configure(
                fg_color=COLORS["sidebar_active"],
                text_color="#FFFFFF",
                image=icon(self._icon_name(), "white", 19),
            )
            self.indicator.configure(fg_color="#FFFFFF")
        else:
            self.button.configure(
                fg_color="transparent",
                text_color=COLORS["sidebar_text"],
                image=icon(self._icon_name(), "sidebar", 19),
            )
            self.indicator.configure(fg_color="transparent")

    def _icon_name(self) -> str:
        """Nome do ícone deste item."""
        return {key: icon for key, _, icon in NAV_ITEMS}.get(self.key, "home")


class Sidebar(ctk.CTkFrame):
    """Painel de navegação fixo à esquerda."""

    def __init__(
        self, master, on_navigate: Callable[[str], None], **kwargs
    ) -> None:
        """Monta marca, menu e rodapé."""
        super().__init__(
            master,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=COLORS["sidebar"],
            **kwargs,
        )
        self.grid_propagate(False)
        self.grid_rowconfigure(3, weight=1)
        self.buttons: dict[str, SidebarButton] = {}
        self.on_navigate = on_navigate
        # Marca
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 8))
        ctk.CTkLabel(brand, text="", image=logo(38)).pack(side="left")
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            brand_text,
            text="TaskMate",
            font=font(19, "bold"),
            text_color="#FFFFFF",
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_text,
            text=f"v{APP_VERSION}",
            font=font(10),
            text_color=COLORS["sidebar_text_muted"],
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            self,
            text="MENU",
            font=font(10, "bold"),
            text_color=COLORS["sidebar_text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(18, 6))
        # Navegação
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="new", padx=10)
        nav.grid_columnconfigure(0, weight=1)
        for index, (key, label, icon_name) in enumerate(NAV_ITEMS):
            item = SidebarButton(
                nav, key, label, icon_name, self._handle_click
            )
            item.grid(row=index, column=0, sticky="ew", pady=2)
            self.buttons[key] = item
        # Rodapé
        footer = ctk.CTkFrame(
            self, fg_color=COLORS["sidebar_soft"], corner_radius=12
        )
        footer.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 18))
        ctk.CTkLabel(footer, text="", image=icon("book", "sidebar", 18)).pack(
            side="left", padx=(12, 8), pady=12
        )
        footer_text = ctk.CTkFrame(footer, fg_color="transparent")
        footer_text.pack(side="left", pady=8)
        ctk.CTkLabel(
            footer_text,
            text=(
                APP_SLOGAN.split(". ")[1] if ". " in APP_SLOGAN else APP_SLOGAN
            ),
            font=font(10, "bold"),
            text_color=COLORS["sidebar_text"],
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            footer_text,
            text="TaskMate 1.0",
            font=font(9),
            text_color=COLORS["sidebar_text_muted"],
            anchor="w",
        ).pack(anchor="w")

    def _handle_click(self, key: str) -> None:
        """Repassa o clique para o aplicativo."""
        self.on_navigate(key)

    def set_active(self, key: str) -> None:
        """Destaca o item da tela atual."""
        for button_key, button in self.buttons.items():
            button.set_active(button_key == key)
# ==========================================================================
# 15. BASE DAS TELAS
# ==========================================================================


class BaseView(ctk.CTkFrame):
    """Tela com fundo neutro, cabeçalho e área de conteúdo rolável."""
    title = ""
    subtitle = ""

    def __init__(self, master, app) -> None:
        """Monta o cabeçalho e a área de conteúdo."""
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)
        self.app = app
        self.repositories = app.repositories
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        self.header.grid_columnconfigure(0, weight=1)

    def on_show(self) -> None:
        """Chamado sempre que a tela passa a ser exibida."""
        self.refresh()

    def refresh(self) -> None:
        """Recarrega os dados da tela."""
# ==========================================================================
# 16. TELA — PAINEL
# ==========================================================================


class StatCard(Card):
    """Cartão de indicador numérico com ícone e legenda."""

    def __init__(
        self,
        master,
        title: str,
        icon_name: str,
        color: str,
        soft: str,
        caption: str = "",
    ) -> None:
        """Monta o cartão de indicador."""
        super().__init__(master, radius=16)
        self.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 0))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top,
            text=title.upper(),
            font=font(10, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        holder = ctk.CTkFrame(
            top, fg_color=soft, width=36, height=36, corner_radius=10
        )
        holder.grid(row=0, column=1, rowspan=2, sticky="e")
        holder.grid_propagate(False)
        ctk.CTkLabel(holder, text="", image=icon(icon_name, color, 19)).pack(
            expand=True
        )
        self.value_label = ctk.CTkLabel(
            self,
            text="0",
            font=font(30, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        )
        self.value_label.grid(
            row=1, column=0, sticky="w", padx=18, pady=(2, 0)
        )
        self.caption_label = ctk.CTkLabel(
            self,
            text=caption,
            font=font(11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.caption_label.grid(
            row=2, column=0, sticky="w", padx=18, pady=(0, 16)
        )

    def set_value(self, value: int | str, caption: str | None = None) -> None:
        """Atualiza número e legenda."""
        self.value_label.configure(text=str(value))
        if caption is not None:
            self.caption_label.configure(text=caption)


class DashboardView(BaseView):
    """Painel com a visão geral das atividades."""
    title = "Painel"

    def __init__(self, master, app) -> None:
        """Monta cabeçalho, indicadores e cartões."""
        super().__init__(master, app)
        # Cabeçalho
        head = ctk.CTkFrame(self.header, fg_color="transparent")
        head.grid(row=0, column=0, sticky="w")
        self.greeting = ctk.CTkLabel(
            head,
            text="Olá!",
            font=font(24, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        )
        self.greeting.pack(anchor="w")
        self.date_label = ctk.CTkLabel(
            head,
            text="",
            font=font(12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.date_label.pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            self.header,
            text="Nova tarefa",
            command=self.app.open_new_task,
            height=42,
            width=158,
            corner_radius=11,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#FFFFFF",
            font=font(13, "bold"),
            image=icon("plus", "white", 18),
            compound="left",
            border_spacing=8,
        ).grid(row=0, column=1, sticky="e")
        # Área rolável
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 20))
        self.scroll.grid_columnconfigure(
            (0, 1, 2, 3), weight=1, uniform="stats"
        )
        # Indicadores
        self.cards: dict[str, StatCard] = {}
        specs = [
            (
                "total",
                "Total de tarefas",
                "tasks",
                "primary",
                COLORS["primary_soft"],
            ),
            (
                "pending",
                "Pendentes",
                "clock",
                "warning",
                COLORS["warning_soft"],
            ),
            (
                "completed",
                "Concluídas",
                "check",
                "success",
                COLORS["success_soft"],
            ),
            ("overdue", "Atrasadas", "alert", "danger", COLORS["danger_soft"]),
        ]
        for column, (key, title, icon_name, color, soft) in enumerate(specs):
            card = StatCard(
                self.scroll, title, icon_name, color, soft, caption="—"
            )
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 8, 0 if column == 3 else 8),
                pady=(0, 18),
            )
            self.cards[key] = card
        # Linha de conteúdo
        content = ctk.CTkFrame(self.scroll, fg_color="transparent")
        content.grid(row=1, column=0, columnspan=4, sticky="ew")
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        self.deadlines_card = Card(content, radius=16)
        self.deadlines_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.deadlines_card.grid_columnconfigure(0, weight=1)
        self.deadlines_body = ctk.CTkFrame(
            self.deadlines_card, fg_color="transparent"
        )
        self.deadlines_body.grid(
            row=1, column=0, sticky="ew", padx=18, pady=(0, 14)
        )
        self.deadlines_body.grid_columnconfigure(0, weight=1)
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        self.recent_card = Card(right, radius=16)
        self.recent_card.grid(row=0, column=0, sticky="ew")
        self.recent_card.grid_columnconfigure(0, weight=1)
        self.recent_body = ctk.CTkFrame(
            self.recent_card, fg_color="transparent"
        )
        self.recent_body.grid(
            row=1, column=0, sticky="ew", padx=18, pady=(0, 12)
        )
        self.recent_body.grid_columnconfigure(0, weight=1)
        self.progress_card = Card(right, radius=16)
        self.progress_card.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        self.progress_card.grid_columnconfigure(0, weight=1)
        self.progress_body = ctk.CTkFrame(
            self.progress_card, fg_color="transparent"
        )
        self.progress_body.grid(
            row=1, column=0, sticky="ew", padx=18, pady=(0, 18)
        )
        self.progress_body.grid_columnconfigure(0, weight=1)
    # ------------------------------------------------------------------ dados

    def on_show(self) -> None:
        """Atualiza saudação e dados ao entrar."""
        self.update_greeting()
        self.refresh()

    def update_greeting(self) -> None:
        """Escreve a saudação e a data de hoje."""
        now = datetime.now()
        hour = now.hour
        if hour < 12:
            period = "Bom dia"
        elif hour < 18:
            period = "Boa tarde"
        else:
            period = "Boa noite"
        name = self.app.user_name
        self.greeting.configure(
            text=f"{period}, {name}!" if name else f"{period}!"
        )
        today = date.today()
        weekday = WEEKDAYS[today.weekday()].capitalize()
        self.date_label.configure(
            text=(
                f"{weekday}, {today.day} de "
                f"{MONTHS[today.month - 1]} de {today.year}"
            )
        )

    def refresh(self) -> None:
        """Recarrega indicadores, prazos e progresso."""
        repo = self.repositories["tasks"]
        stats = repo.stats()
        self.cards["total"].set_value(stats.total, "atividades cadastradas")
        self.cards["pending"].set_value(
            stats.pending, f"{stats.today} para hoje"
        )
        self.cards["completed"].set_value(
            stats.completed, f"{stats.completion_rate:.0f}% do total"
        )
        self.cards["overdue"].set_value(
            stats.overdue,
            "precisam de atenção" if stats.overdue else "tudo em dia",
        )
        self._render_deadlines(repo.upcoming(5))
        self._render_recent(repo.recent(4))
        self._render_progress(stats)

    def _clear(self, container) -> None:
        """Remove os filhos de um contêiner."""
        for child in container.winfo_children():
            child.destroy()

    def _render_deadlines(self, tasks) -> None:
        """Lista os próximos prazos."""
        self._clear(self.deadlines_body)
        SectionHeader(
            self.deadlines_card,
            "Próximos prazos",
            "Até 60 dias à frente, do mais urgente ao mais distante.",
            "Ver todas",
            lambda: self.app.show_view("tasks"),
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        if not tasks:
            EmptyState(
                self.deadlines_body,
                "Nenhum prazo próximo",
                "Cadastre atividades para ver as datas de entrega aqui.",
                "calendar",
                "Nova tarefa",
                self.app.open_new_task,
            ).grid(row=0, column=0, sticky="ew")
            return
        for index, task in enumerate(tasks):
            card = TaskCard(
                self.deadlines_body,
                task,
                on_toggle=self._toggle_task,
                on_edit=self.app.open_edit_task,
                on_delete=self._delete_task,
                compact=True,
            )
            card.grid(row=index, column=0, sticky="ew", pady=(0, 6))

    def _render_recent(self, tasks) -> None:
        """Lista as tarefas recém-criadas."""
        self._clear(self.recent_body)
        SectionHeader(
            self.recent_card,
            "Adicionadas recentemente",
            "Últimos registros criados.",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        if not tasks:
            ctk.CTkLabel(
                self.recent_body,
                text="Você ainda não cadastrou tarefas.",
                font=font(11),
                text_color=COLORS["text_muted"],
                anchor="w",
                wraplength=280,
                justify="left",
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))
            return
        for index, task in enumerate(tasks):
            row = ctk.CTkFrame(self.recent_body, fg_color="transparent")
            row.grid(row=index, column=0, sticky="ew", pady=4)
            row.grid_columnconfigure(1, weight=1)
            dot_color = (
                COLORS["success"] if task.completed else task.subject_color
            )
            ctk.CTkFrame(
                row, width=8, height=8, corner_radius=4, fg_color=dot_color
            ).grid(row=0, column=0, padx=(0, 9), pady=6)
            ctk.CTkLabel(
                row,
                text=self._shorten(task.title, 34),
                font=font(12, "bold"),
                text_color=(
                    COLORS["text_faint"] if task.completed else COLORS["text"]
                ),
                anchor="w",
            ).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(
                row,
                text=task.subject_name or "Sem disciplina",
                font=font(10),
                text_color=COLORS["text_muted"],
                anchor="e",
            ).grid(row=0, column=2, sticky="e", padx=(6, 0))

    def _render_progress(self, stats) -> None:
        """Mostra a barra e o resumo por prioridade."""
        self._clear(self.progress_body)
        SectionHeader(
            self.progress_card,
            "Progresso do período",
            (
                f"{stats.completed} de {stats.total} atividades concluídas."
                if stats.total
                else "Sem atividades registradas ainda."
            ),
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 12))
        progress_bar = ctk.CTkProgressBar(
            self.progress_body,
            height=10,
            corner_radius=6,
            fg_color=COLORS["neutral_soft"],
            progress_color=(
                COLORS["success"]
                if stats.completion_rate >= 60
                else COLORS["primary"]
            ),
        )
        progress_bar.grid(row=0, column=0, sticky="ew")
        progress_bar.set(stats.completion_rate / 100 if stats.total else 0)
        ctk.CTkLabel(
            self.progress_body,
            text=f"{stats.completion_rate:.0f}% concluído",
            font=font(10, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 12))
        priorities = ctk.CTkFrame(self.progress_body, fg_color="transparent")
        priorities.grid(row=2, column=0, sticky="ew")
        for column, key in enumerate(("alta", "media", "baixa")):
            priorities.grid_columnconfigure(column, weight=1)
            data = PRIORITIES[key]
            box = ctk.CTkFrame(
                priorities, fg_color=data["soft"], corner_radius=9
            )
            box.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 5, 0),
            )
            ctk.CTkLabel(
                box,
                text=str(stats.by_priority.get(key, 0)),
                font=font(17, "bold"),
                text_color=data["color"],
            ).pack(pady=(8, 0))
            ctk.CTkLabel(
                box,
                text=data["label"],
                font=font(9, "bold"),
                text_color=data["color"],
            ).pack(pady=(0, 8))
    # ----------------------------------------------------------------- ações

    def _toggle_task(self, task) -> None:
        """Conclui ou reabre a tarefa e atualiza telas."""
        self.repositories["tasks"].toggle_completed(task.id)
        self.app.refresh_all()

    def _delete_task(self, task) -> None:
        """Pede confirmação e exclui a tarefa."""
        self.app.confirm_delete_task(task)

    @staticmethod
    def _shorten(text: str, limit: int) -> str:
        """Corta o texto longo com reticências."""
        return text if len(text) <= limit else text[: limit - 1] + "…"


# ==========================================================================
# 17. TELA — TAREFAS
# ==========================================================================
STATUS_OPTIONS = {
    "todas": "Todas",
    "pendentes": "Pendentes",
    "hoje": "Hoje",
    "atrasadas": "Atrasadas",
    "concluidas": "Concluídas",
}
PRIORITY_FILTER = {
    "Todas": None,
    "Alta": "alta",
    "Média": "media",
    "Baixa": "baixa",
}


class TasksView(BaseView):
    """Tela de tarefas com filtros e busca."""
    title = "Tarefas"

    def __init__(self, master, app) -> None:
        """Monta cabeçalho, filtros e lista."""
        super().__init__(master, app)
        head = ctk.CTkFrame(self.header, fg_color="transparent")
        head.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head,
            text="Minhas tarefas",
            font=font(24, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")
        self.count_label = ctk.CTkLabel(
            head,
            text="",
            font=font(12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.count_label.pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            self.header,
            text="Nova tarefa",
            command=self.app.open_new_task,
            height=42,
            width=158,
            corner_radius=11,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#FFFFFF",
            font=font(13, "bold"),
            image=icon("plus", "white", 18),
            compound="left",
            border_spacing=8,
        ).grid(row=0, column=1, sticky="e")
        # Filtros
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", padx=28)
        filters.grid_columnconfigure(1, weight=1)
        self.status_switch = ctk.CTkSegmentedButton(
            filters,
            values=list(STATUS_OPTIONS.values()),
            command=lambda _value: self.refresh(),
            height=36,
            corner_radius=9,
            fg_color=COLORS["surface"],
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["surface"],
            unselected_hover_color=COLORS["primary_soft"],
            text_color="#FFFFFF",
            font=font(12, "bold"),
        )
        self.status_switch.set("Todas")
        self.status_switch.grid(row=0, column=0, sticky="w")
        search_box = ctk.CTkFrame(filters, fg_color="transparent")
        search_box.grid(row=0, column=1, sticky="e", padx=(14, 8))
        self.search_entry = ctk.CTkEntry(
            search_box,
            placeholder_text="Buscar tarefa...",
            width=220,
            height=36,
            corner_radius=9,
            border_width=1,
            border_color=COLORS["border_strong"],
            fg_color=COLORS["surface"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_faint"],
            font=font(12),
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda _event: self.refresh())
        self.subject_menu = ctk.CTkOptionMenu(
            filters,
            values=["Todas as disciplinas"],
            command=lambda _value: self.refresh(),
            width=190,
            height=36,
            corner_radius=9,
            fg_color=COLORS["surface"],
            button_color=COLORS["primary_soft"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["primary_soft"],
            font=font(12),
            dropdown_font=font(12),
        )
        self.subject_menu.grid(row=0, column=2, sticky="e")
        self.priority_menu = ctk.CTkOptionMenu(
            filters,
            values=list(PRIORITY_FILTER.keys()),
            command=lambda _value: self.refresh(),
            width=120,
            height=36,
            corner_radius=9,
            fg_color=COLORS["surface"],
            button_color=COLORS["primary_soft"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["primary_soft"],
            font=font(12),
            dropdown_font=font(12),
        )
        self.priority_menu.grid(row=0, column=3, sticky="e", padx=(8, 0))
        self.clear_button = ctk.CTkButton(
            filters,
            text="",
            width=36,
            height=36,
            corner_radius=9,
            fg_color=COLORS["surface"],
            hover_color=COLORS["primary_soft"],
            border_width=1,
            border_color=COLORS["border_strong"],
            image=icon("refresh", "muted", 17),
            command=self.clear_filters,
        )
        self.clear_button.grid(row=0, column=4, sticky="e", padx=(8, 0))
        # Lista
        self.list_card = Card(self, radius=16)
        self.list_card.grid(
            row=2, column=0, sticky="nsew", padx=28, pady=(14, 20)
        )
        self.list_card.grid_columnconfigure(0, weight=1)
        self.list_card.grid_rowconfigure(1, weight=1)
        list_header = ctk.CTkFrame(self.list_card, fg_color="transparent")
        list_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 6))
        list_header.grid_columnconfigure(0, weight=1)
        self.list_title = ctk.CTkLabel(
            list_header,
            text="Todas as tarefas",
            font=font(13, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        )
        self.list_title.grid(row=0, column=0, sticky="w")
        self.scroll = ctk.CTkScrollableFrame(
            self.list_card, fg_color="transparent"
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scroll.grid_columnconfigure(0, weight=1)
    # ------------------------------------------------------------------ dados

    def on_show(self) -> None:
        """Recarrega disciplinas e lista de tarefas."""
        self.reload_subjects()
        self.refresh()

    def reload_subjects(self) -> None:
        """Atualiza as opções do filtro de disciplina."""
        subjects = self.repositories["subjects"].all()
        current = self.subject_menu.get()
        values = ["Todas as disciplinas"] + [
            subject.name for subject in subjects
        ]
        self.subject_menu.configure(values=values)
        self.subject_menu.set(
            current if current in values else "Todas as disciplinas"
        )

    def _selected_subject_id(self) -> int | None:
        """Id da disciplina filtrada (None = todas)."""
        name = self.subject_menu.get()
        if name == "Todas as disciplinas":
            return None
        for subject in self.repositories["subjects"].all():
            if subject.name == name:
                return subject.id
        return None

    def refresh(self) -> None:
        """Aplica os filtros e redesenha a lista."""
        status_key = "todas"
        for key, label in STATUS_OPTIONS.items():
            if label == self.status_switch.get():
                status_key = key
                break
        tasks = self.repositories["tasks"].filter(
            subject_id=self._selected_subject_id(),
            status=status_key,
            priority=PRIORITY_FILTER.get(self.priority_menu.get()),
            search=self.search_entry.get(),
        )
        self.count_label.configure(
            text=(
                f"{len(tasks)} tarefa(s) encontrada(s)"
                if tasks
                else "Nenhuma tarefa com esses filtros"
            )
        )
        self.list_title.configure(
            text=f"{STATUS_OPTIONS[status_key]} • {len(tasks)}"
        )
        for child in self.scroll.winfo_children():
            child.destroy()
        if not tasks:
            EmptyState(
                self.scroll,
                "Nada por aqui",
                "Nenhuma tarefa corresponde a esses filtros. "
                "Ajuste os filtros ou cadastre uma nova atividade.",
                "search",
                "Nova tarefa",
                self.app.open_new_task,
            ).grid(row=0, column=0, sticky="ew", pady=10)
            return
        for index, task in enumerate(tasks):
            card = TaskCard(
                self.scroll,
                task,
                on_toggle=self._toggle_task,
                on_edit=self.app.open_edit_task,
                on_delete=self.app.confirm_delete_task,
            )
            card.grid(row=index, column=0, sticky="ew", pady=(0, 8), padx=6)
    # ----------------------------------------------------------------- ações

    def _toggle_task(self, task) -> None:
        """Conclui ou reabre a tarefa e atualiza telas."""
        self.repositories["tasks"].toggle_completed(task.id)
        self.app.refresh_all()

    def clear_filters(self) -> None:
        """Volta os filtros ao padrão."""
        self.status_switch.set("Todas")
        self.subject_menu.set("Todas as disciplinas")
        self.priority_menu.set("Todas")
        self.search_entry.delete(0, "end")
        self.refresh()


# ==========================================================================
# 18. TELA — CALENDÁRIO
# ==========================================================================
WEEKDAY_SHORT = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")


class DayCell(ctk.CTkFrame):
    """Célula de um dia do calendário."""

    def __init__(self, master, on_select, day: date | None = None) -> None:
        """Monta a célula de um dia do calendário."""
        super().__init__(
            master,
            fg_color=COLORS["surface"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
            height=78,
        )
        self.grid_propagate(False)
        self.day = day
        self.on_select = on_select
        self.selected = False
        self.is_today = day == date.today() if day else False
        if day is None:
            self.configure(
                fg_color=COLORS["surface_alt"],
                border_color=COLORS["surface_alt"],
            )
            return
        self.grid_columnconfigure(0, weight=1)
        self.number = ctk.CTkLabel(
            self,
            text=str(day.day),
            font=font(12, "bold" if self.is_today else "normal"),
            text_color=COLORS["primary"] if self.is_today else COLORS["text"],
            anchor="w",
        )
        self.number.grid(row=0, column=0, sticky="w", padx=9, pady=(6, 0))
        self.dots = ctk.CTkFrame(self, fg_color="transparent")
        self.dots.grid(row=1, column=0, sticky="w", padx=9, pady=(2, 6))
        self.count_label = ctk.CTkLabel(
            self,
            text="",
            font=font(9, "bold"),
            text_color=COLORS["text_muted"],
        )
        self.count_label.grid(row=1, column=0, sticky="e", padx=9, pady=(0, 6))
        for widget in (self, self.number, self.dots, self.count_label):
            widget.bind("<Button-1>", self._click)

    def _click(self, _event=None) -> None:
        """Seleciona o dia clicado."""
        if self.day:
            self.on_select(self.day)

    def set_tasks(self, tasks) -> None:
        """Marca as bolinhas das tarefas do dia."""
        for child in self.dots.winfo_children():
            child.destroy()
        if not tasks:
            self.count_label.configure(text="")
            return
        # Até 3 bolinhas por prioridade/presença
        shown = tasks[:3]
        for task in shown:
            color = (
                COLORS["success"]
                if task.completed
                else PRIORITIES.get(task.priority, PRIORITIES["media"])[
                    "color"
                ]
            )
            ctk.CTkFrame(
                self.dots, width=6, height=6, corner_radius=3, fg_color=color
            ).pack(side="left", padx=(0, 3))
        self.count_label.configure(
            text=str(len(tasks)) if len(tasks) > 1 else ""
        )

    def set_selected(self, selected: bool) -> None:
        """Destaca a célula selecionada."""
        self.selected = selected
        if self.day is None:
            return
        if selected:
            self.configure(
                fg_color=COLORS["primary_soft"],
                border_color=COLORS["primary"],
                border_width=2,
            )
        else:
            self.configure(
                border_width=1,
                border_color=COLORS["border"],
                fg_color=COLORS["surface"],
            )


class CalendarView(BaseView):
    """Calendário mensal com as atividades do dia."""
    title = "Calendário"

    def __init__(self, master, app) -> None:
        """Monta navegação, grade e painel do dia."""
        super().__init__(master, app)
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today
        self.cells: dict[date, DayCell] = {}
        head = ctk.CTkFrame(self.header, fg_color="transparent")
        head.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head,
            text="Calendário escolar",
            font=font(24, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            head,
            text="Provas, entregas e compromissos do mês.",
            font=font(12),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            self.header,
            text="Nova tarefa",
            command=self.app.open_new_task,
            height=42,
            width=158,
            corner_radius=11,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#FFFFFF",
            font=font(13, "bold"),
            image=icon("plus", "white", 18),
            compound="left",
            border_spacing=8,
        ).grid(row=0, column=1, sticky="e")
        # Corpo: calendário + painel do dia
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 20))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2, minsize=340)
        body.grid_rowconfigure(0, weight=1)
        # --- Calendário
        cal_card = Card(body, radius=16)
        cal_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        cal_card.grid_columnconfigure(0, weight=1)
        cal_card.grid_rowconfigure(2, weight=1)
        nav = ctk.CTkFrame(cal_card, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        nav.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            nav,
            text="",
            width=32,
            height=32,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["primary_soft"],
            image=icon("chevron-left", "primary", 16),
            command=lambda: self.change_month(-1),
        ).grid(row=0, column=0)
        self.month_label = ctk.CTkLabel(
            nav, text="", font=font(15, "bold"), text_color=COLORS["text"]
        )
        self.month_label.grid(row=0, column=1)
        ctk.CTkButton(
            nav,
            text="",
            width=32,
            height=32,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["primary_soft"],
            image=icon("chevron-right", "primary", 16),
            command=lambda: self.change_month(1),
        ).grid(row=0, column=2)
        ctk.CTkButton(
            nav,
            text="Hoje",
            width=64,
            height=32,
            corner_radius=8,
            fg_color=COLORS["primary_soft"],
            hover_color=COLORS["border"],
            text_color=COLORS["primary"],
            font=font(11, "bold"),
            command=self.go_today,
        ).grid(row=0, column=3, padx=(8, 0))
        # Cabeçalho dos dias da semana
        week_header = ctk.CTkFrame(cal_card, fg_color="transparent")
        week_header.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        for column, name in enumerate(WEEKDAY_SHORT):
            week_header.grid_columnconfigure(column, weight=1, uniform="week")
            ctk.CTkLabel(
                week_header,
                text=name,
                font=font(9, "bold"),
                text_color=COLORS["text_faint"],
            ).grid(row=0, column=column, sticky="ew")
        self.grid_frame = ctk.CTkFrame(cal_card, fg_color="transparent")
        self.grid_frame.grid(
            row=2, column=0, sticky="nsew", padx=12, pady=(0, 14)
        )
        # --- Painel do dia selecionado
        self.day_card = Card(body, radius=16)
        self.day_card.grid(row=0, column=1, sticky="nsew")
        self.day_card.grid_columnconfigure(0, weight=1)
        self.day_card.grid_rowconfigure(1, weight=1)
        self.day_header = ctk.CTkFrame(self.day_card, fg_color="transparent")
        self.day_header.grid(
            row=0, column=0, sticky="ew", padx=18, pady=(16, 8)
        )
        self.day_header.grid_columnconfigure(0, weight=1)
        self.day_title = ctk.CTkLabel(
            self.day_header,
            text="",
            font=font(15, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        )
        self.day_title.grid(row=0, column=0, sticky="w")
        self.day_subtitle = ctk.CTkLabel(
            self.day_header,
            text="",
            font=font(11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.day_subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.day_scroll = ctk.CTkScrollableFrame(
            self.day_card, fg_color="transparent"
        )
        self.day_scroll.grid(
            row=1, column=0, sticky="nsew", padx=8, pady=(0, 12)
        )
        self.day_scroll.grid_columnconfigure(0, weight=1)
    # ------------------------------------------------------------------ dados

    def on_show(self) -> None:
        """Redesenha o mês atual."""
        self.refresh()

    def refresh(self) -> None:
        """Redesenha o mês atual."""
        self._render_month()

    def _render_month(self) -> None:
        """Desenha a grade do mês e marca tarefas."""
        first = date(self.current_year, self.current_month, 1)
        days_in_month = pycalendar.monthrange(
            self.current_year, self.current_month
        )[1]
        last = date(self.current_year, self.current_month, days_in_month)
        grouped = self.repositories["tasks"].dates_with_tasks(first, last)
        self.month_label.configure(
            text=(
                f"{MONTHS[self.current_month - 1].capitalize()} "
                f"{self.current_year}"
            )
        )
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.cells.clear()
        # Quantas semanas o mês ocupa (segunda como primeiro dia)
        weeks = pycalendar.Calendar(firstweekday=0).monthdayscalendar(
            self.current_year, self.current_month
        )
        for row_index, week in enumerate(weeks):
            self.grid_frame.grid_rowconfigure(row_index, weight=1)
            for column, day_number in enumerate(week):
                self.grid_frame.grid_columnconfigure(
                    column, weight=1, uniform="day"
                )
                day = (
                    date(self.current_year, self.current_month, day_number)
                    if day_number
                    else None
                )
                cell = DayCell(self.grid_frame, self.select_date, day)
                cell.grid(
                    row=row_index, column=column, sticky="nsew", padx=2, pady=2
                )
                if day:
                    self.cells[day] = cell
        # Marca as tarefas depois que todas as células existem
        for day, tasks in grouped.items():
            if day in self.cells:
                self.cells[day].set_tasks(tasks)
        if self.selected_date not in self.cells:
            self.selected_date = date(self.current_year, self.current_month, 1)
        self._highlight_selected()
        self._render_day(self.selected_date)

    def _highlight_selected(self) -> None:
        """Destaca o dia selecionado."""
        for day, cell in self.cells.items():
            cell.set_selected(day == self.selected_date)

    def _render_day(self, day: date) -> None:
        """Lista as atividades da data escolhida."""
        tasks = self.repositories["tasks"].by_date(day)
        weekday = WEEKDAYS[day.weekday()].capitalize()
        self.day_title.configure(
            text=f"{day.day:02d} de {MONTHS[day.month - 1]}"
        )
        if day == date.today():
            self.day_subtitle.configure(text=f"Hoje • {weekday}")
        else:
            self.day_subtitle.configure(
                text=(
                    f"{weekday} • {len(tasks)} atividade(s)"
                    if tasks
                    else f"{weekday} • sem atividades"
                )
            )
        for child in self.day_scroll.winfo_children():
            child.destroy()
        if not tasks:
            EmptyState(
                self.day_scroll,
                "Dia livre",
                "Nenhuma atividade marcada para esta data.",
                "calendar",
                "Adicionar",
                lambda: self.app.open_new_task(default_date=day),
            ).grid(row=0, column=0, sticky="ew")
            return
        for index, task in enumerate(tasks):
            card = TaskCard(
                self.day_scroll,
                task,
                on_toggle=self._toggle_task,
                on_edit=self.app.open_edit_task,
                on_delete=self.app.confirm_delete_task,
                compact=True,
            )
            card.grid(row=index, column=0, sticky="ew", pady=(0, 6), padx=4)
    # ----------------------------------------------------------------- ações

    def select_date(self, day: date) -> None:
        """Seleciona o dia e atualiza o painel."""
        self.selected_date = day
        self._highlight_selected()
        self._render_day(day)

    def change_month(self, delta: int) -> None:
        """Avança ou volta um mês."""
        self.current_month += delta
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        elif self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self._render_month()

    def go_today(self) -> None:
        """Volta ao mês e ao dia de hoje."""
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today
        self._render_month()

    def _toggle_task(self, task) -> None:
        """Conclui ou reabre a tarefa e atualiza telas."""
        self.repositories["tasks"].toggle_completed(task.id)
        self.app.refresh_all()


# ==========================================================================
# 19. TELA — DISCIPLINAS
# ==========================================================================
PALETTE = [
    "#2D6CF6",
    "#7B61FF",
    "#1F9D6B",
    "#C77D2B",
    "#0EA5A5",
    "#E5484D",
    "#D9469E",
    "#6B7B93",
]


class SubjectDialog(BaseDialog):
    """Cadastro/edição de disciplina com seletor de cor."""

    def __init__(self, master, subject=None) -> None:
        """Monta nome e paleta de cores."""
        super().__init__(
            master,
            "Editar disciplina" if subject else "Nova disciplina",
            "Defina o nome e a cor de identificação.",
            width=440,
        )
        self.subject = subject
        self.selected_color = subject.color if subject else PALETTE[0]
        ctk.CTkLabel(
            self.body,
            text="NOME DA DISCIPLINA",
            font=font(10, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.name_entry = ctk.CTkEntry(
            self.body,
            placeholder_text="Ex.: Filosofia",
            height=38,
            corner_radius=9,
            border_width=1,
            border_color=COLORS["border_strong"],
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_faint"],
            font=font(12),
        )
        self.name_entry.grid(row=1, column=0, sticky="ew")
        if subject:
            self.name_entry.insert(0, subject.name)
        ctk.CTkLabel(
            self.body,
            text="COR",
            font=font(10, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(14, 5))
        colors = ctk.CTkFrame(self.body, fg_color="transparent")
        colors.grid(row=3, column=0, sticky="w")
        self.color_buttons: dict[str, ctk.CTkButton] = {}
        for index, color in enumerate(PALETTE):
            button = ctk.CTkButton(
                colors,
                text="",
                width=30,
                height=30,
                corner_radius=15,
                fg_color=color,
                hover_color=color,
                border_width=3,
                border_color=COLORS["surface"],
                command=lambda value=color: self._pick_color(value),
            )
            button.grid(row=0, column=index, padx=(0, 6))
            self.color_buttons[color] = button
        self._pick_color(self.selected_color)
        self.error_label = ctk.CTkLabel(
            self.body,
            text="",
            font=font(11, "bold"),
            text_color=COLORS["danger"],
            anchor="w",
        )
        self.error_label.grid(row=4, column=0, sticky="w", pady=(12, 0))
        self.add_footer_button(
            "Salvar" if subject else "Adicionar",
            self._save,
            primary=True,
            icon_name="check",
        )
        self.add_footer_button("Cancelar", self._cancel, primary=False)
        self._center(master, 440)
        self.after(60, self.name_entry.focus_set)

    def _pick_color(self, color: str) -> None:
        """Marca a cor escolhida."""
        self.selected_color = color
        for value, button in self.color_buttons.items():
            button.configure(
                border_color=(
                    COLORS["text"] if value == color else COLORS["surface"]
                )
            )

    def _save(self) -> None:
        """Valida e grava a disciplina."""
        name = self.name_entry.get().strip()
        repo = self.app.repositories["subjects"]
        try:
            if self.subject:
                repo.update(self.subject.id, name, self.selected_color)
            else:
                repo.create(name, self.selected_color)
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        except DatabaseError as exc:
            self.error_label.configure(text=f"Não foi possível salvar: {exc}")
            return
        self._finish(True)


class SubjectsView(BaseView):
    """Tela de disciplinas em grade."""
    title = "Disciplinas"

    def __init__(self, master, app) -> None:
        """Monta cabeçalho e grade de cartões."""
        super().__init__(master, app)
        head = ctk.CTkFrame(self.header, fg_color="transparent")
        head.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head,
            text="Disciplinas",
            font=font(24, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")
        self.subtitle = ctk.CTkLabel(
            head,
            text="",
            font=font(12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.subtitle.pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            self.header,
            text="Nova disciplina",
            command=self.open_new_subject,
            height=42,
            width=170,
            corner_radius=11,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#FFFFFF",
            font=font(13, "bold"),
            image=icon("plus", "white", 18),
            compound="left",
            border_spacing=8,
        ).grid(row=0, column=1, sticky="e")
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 20))
        self.scroll.grid_columnconfigure(
            (0, 1, 2), weight=1, uniform="subjects"
        )
    # ------------------------------------------------------------------ dados

    def on_show(self) -> None:
        """Recarrega a lista de disciplinas."""
        self.refresh()

    def refresh(self) -> None:
        """Recarrega a lista de disciplinas."""
        subjects = self.repositories["subjects"].all()
        total_tasks = sum(subject.task_count for subject in subjects)
        self.subtitle.configure(
            text=(
                f"{len(subjects)} disciplina(s) • "
                f"{total_tasks} tarefa(s) vinculada(s)"
            )
        )
        for child in self.scroll.winfo_children():
            child.destroy()
        if not subjects:
            EmptyState(
                self.scroll,
                "Nenhuma disciplina",
                "Cadastre suas matérias para organizar as tarefas "
                "por área do conhecimento.",
                "book",
                "Nova disciplina",
                self.open_new_subject,
            ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=20)
            return
        for index, subject in enumerate(subjects):
            card = self._build_card(subject)
            card.grid(
                row=index // 3,
                column=index % 3,
                sticky="nsew",
                padx=(0 if index % 3 == 0 else 8, 0 if index % 3 == 2 else 8),
                pady=(0, 16),
            )

    def _build_card(self, subject) -> Card:
        """Monta o cartão de uma disciplina."""
        card = Card(self.scroll, radius=16)
        card.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))
        top.grid_columnconfigure(1, weight=1)
        avatar = ctk.CTkFrame(
            top, fg_color=subject.color, width=42, height=42, corner_radius=12
        )
        avatar.grid(row=0, column=0, rowspan=2, sticky="w")
        avatar.grid_propagate(False)
        ctk.CTkLabel(
            avatar,
            text=subject.initials,
            font=font(14, "bold"),
            text_color="#FFFFFF",
        ).pack(expand=True)
        ctk.CTkLabel(
            top,
            text=subject.name,
            font=font(13, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))
        ctk.CTkLabel(
            top,
            text=(
                f"{subject.task_count} tarefa(s) • "
                f"{subject.pending_count} pendente(s)"
            ),
            font=font(10),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=(10, 0))
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 14))
        actions.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            actions,
            text="Ver tarefas",
            height=32,
            corner_radius=8,
            fg_color=COLORS["primary_soft"],
            hover_color=COLORS["border"],
            text_color=COLORS["primary"],
            font=font(11, "bold"),
            command=lambda: self._open_subject_tasks(subject),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="",
            width=32,
            height=32,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["primary_soft"],
            image=icon("edit", "muted", 15),
            command=lambda: self.edit_subject(subject),
        ).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="",
            width=32,
            height=32,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["danger_soft"],
            image=icon("trash", "muted", 15),
            command=lambda: self.delete_subject(subject),
        ).grid(row=0, column=2)
        return card
    # ----------------------------------------------------------------- ações

    def open_new_subject(self) -> None:
        """Abre o formulário de nova disciplina."""
        dialog = SubjectDialog(self.winfo_toplevel())
        if dialog.show():
            self.app.refresh_all()

    def edit_subject(self, subject) -> None:
        """Abre o formulário de edição."""
        dialog = SubjectDialog(self.winfo_toplevel(), subject)
        if dialog.show():
            self.app.refresh_all()

    def delete_subject(self, subject) -> None:
        """Confirma e exclui a disciplina."""
        count = self.repositories["subjects"].count_tasks(subject.id)
        message = f'Excluir a disciplina "{subject.name}"?'
        if count:
            message += (
                f"\n\n{count} tarefa(s) ficarão sem disciplina, "
                "mas não serão excluídas."
            )
        dialog = ConfirmDialog(
            self.winfo_toplevel(),
            "Excluir disciplina",
            message,
            "Excluir",
            danger=True,
        )
        if dialog.show():
            self.repositories["subjects"].delete(subject.id)
            self.app.refresh_all()

    def _open_subject_tasks(self, subject) -> None:
        """Abre a tela de tarefas filtrada."""
        self.app.show_view("tasks")
        view = self.app.views["tasks"]
        view.subject_menu.set(subject.name)
        view.status_switch.set("Todas")
        view.refresh()
# ==========================================================================
# 20. JANELA PRINCIPAL E NAVEGAÇÃO
# ==========================================================================


class TaskMateApp(ctk.CTk):
    """Aplicativo TaskMate: janela, navegação e ações compartilhadas."""

    def __init__(self) -> None:
        """Inicializa janela, repositórios e telas."""
        apply_appearance()
        super().__init__()
        self.title(f"{APP_NAME} • {APP_SLOGAN}")
        self.configure(fg_color=COLORS["bg"])
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.repositories = {
            "tasks": TaskRepository(),
            "subjects": SubjectRepository(),
        }
        self.user_name = db.get_setting("user_name", "") or ""
        self.views: dict[str, object] = {}
        self.current_view = ""
        self._set_window_icon()
        self._center_window()
        self._build_layout()
        self.show_view("dashboard")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Control-n>", lambda _event: self.open_new_task())
    # ------------------------------------------------------------------ layout

    def _set_window_icon(self) -> None:
        """Aplica o logotipo como ícone da janela."""
        icon_path = ICONS_DIR / "logo.png"
        if icon_path.exists():
            try:
                self.iconphoto(True, tk.PhotoImage(file=str(icon_path)))
            except (tk.TclError, OSError):  # ícone é opcional
                logger.debug("Não foi possível aplicar o ícone da janela")

    def _center_window(self) -> None:
        """Centraliza a janela na tela."""
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - WINDOW_WIDTH) // 2)
        y = max(0, (self.winfo_screenheight() - WINDOW_HEIGHT) // 3)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _build_layout(self) -> None:
        """Cria o menu lateral e as telas."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = Sidebar(self, self.show_view)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.content = ctk.CTkFrame(
            self, fg_color=COLORS["bg"], corner_radius=0
        )
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        view_classes = {
            "dashboard": DashboardView,
            "tasks": TasksView,
            "calendar": CalendarView,
            "subjects": SubjectsView,
        }
        for key, view_class in view_classes.items():
            view = view_class(self.content, self)
            self.views[key] = view
    # ------------------------------------------------------------- navegação

    def show_view(self, key: str) -> None:
        """Exibe a tela pedida."""
        view = self.views.get(key)
        if view is None:
            return
        if self.current_view == key:
            view.on_show()
            return
        self.current_view = key
        for name, other in self.views.items():
            if name != key:
                other.grid_forget()
        view.grid(row=0, column=0, sticky="nsew")
        self.sidebar.set_active(key)
        view.on_show()

    def refresh_all(self) -> None:
        """Atualiza todas as telas após uma alteração nos dados."""
        for view in self.views.values():
            try:
                view.refresh()
            except Exception:  # pylint: disable=broad-exception-caught
                # uma tela com erro não pode derrubar as outras
                logger.exception("Falha ao atualizar uma tela")

    # ----------------------------------------------------------------- ações
    def open_new_task(self, default_date: date | None = None) -> None:
        """Abre o formulário de nova tarefa."""
        subjects = self.repositories["subjects"].all()
        if not subjects:
            messagebox.showwarning(
                "Nenhuma disciplina",
                "Cadastre ao menos uma disciplina antes de criar tarefas.",
                parent=self,
            )
            return
        task = Task(due_date=default_date)
        dialog = TaskDialog(self, subjects, task if default_date else None)
        if dialog.show():
            self.refresh_all()
            self.show_view("tasks")

    def open_edit_task(self, task: Task) -> None:
        """Abre o formulário de edição."""
        subjects = self.repositories["subjects"].all()
        refreshed = self.repositories["tasks"].get(task.id) or task
        dialog = TaskDialog(self, subjects, refreshed)
        if dialog.show():
            self.refresh_all()

    def confirm_delete_task(self, task: Task) -> None:
        """Confirma e exclui a tarefa."""
        dialog = ConfirmDialog(
            self,
            "Excluir tarefa",
            f'Deseja excluir "{task.title}"?\n\n'
            "Essa ação não pode ser desfeita.",
            "Excluir",
            danger=True,
        )
        if dialog.show():
            self.repositories["tasks"].delete(task.id)
            self.refresh_all()

    def on_close(self) -> None:
        """Fecha o banco e encerra o aplicativo."""
        try:
            db.close()
        except sqlite3.Error:
            logger.exception("Falha ao fechar o banco de dados")
        self.destroy()


def run() -> None:
    """Cria a janela e inicia o laço de eventos."""
    app = TaskMateApp()
    app.mainloop()


# ============================================================================
# 21. PONTO DE ENTRADA
# ============================================================================

def _configure_logging() -> None:
    """Grava o log em data/taskmate.log para facilitar o diagnóstico."""
    log_dir = Path(__file__).resolve().parent / "data"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "taskmate.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> int:
    """Ponto de entrada do aplicativo."""
    _configure_logging()
    try:
        run()
    except Exception:  # pylint: disable=broad-exception-caught
        logging.exception("Erro durante a execução")
        messagebox.showerror(
            "TaskMate",
            "Ocorreu um erro inesperado. Detalhes em data/taskmate.log.",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
