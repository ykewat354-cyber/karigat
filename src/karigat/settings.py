"""Optional user defaults, never credentials or arbitrary provider origins."""
import os
from pathlib import Path
import tomllib
from .cloud import PROVIDERS as ROUTES


def path():return Path(os.getenv('XDG_CONFIG_HOME') or Path.home()/'.config')/'karigat/config.toml'


def read():
    file=path()
    if not file.exists():return {}
    data=tomllib.loads(file.read_text())
    if data.get('provider') not in (None,*ROUTES) or data.get('planner') not in (None,*ROUTES):raise ValueError('Config names an unknown hosted provider')
    if data.get('pack') not in (None,'general','change','create'):raise ValueError('Unknown workflow pack')
    return data


def init():
    f=path();f.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if not f.exists():
        with f.open('x') as stream: stream.write('# Karigat user preferences. API keys belong in your environment.\nprovider = "openrouter"\n# planner = "gemini"\n# pack = "general"\n')
    return f
