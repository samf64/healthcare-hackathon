from pathlib import Path

from app.config import settings


def _library_dir() -> Path:
    path = Path(settings.template_library_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_template_files() -> list[str]:
    files = [p.name for p in _library_dir().glob("*.pdf") if p.is_file()]
    files.sort()
    return files


def resolve_template_file(name: str) -> Path:
    if not name or name.strip() != name:
        raise ValueError("Invalid template name.")
    if "/" in name or "\\" in name:
        raise ValueError("Invalid template name.")

    path = (_library_dir() / name).resolve()
    if path.parent != _library_dir().resolve():
        raise ValueError("Invalid template path.")
    if not path.exists():
        raise FileNotFoundError(name)
    return path

