"""Curated teaching/demo metadata. Not official counter or win-rate statistics."""
import json
from pathlib import Path
from functools import lru_cache
from typing import Any
import httpx

ROOT = Path(__file__).resolve().parent.parent
FALLBACK_VERSION = '16.18.1'

@lru_cache

def local_champions() -> list[dict[str, Any]]:
    return json.loads((ROOT / 'data/champions.json').read_text(encoding='utf-8'))


def lookup() -> dict[str, dict]:
    return {c['id']: c for c in local_champions()}


def catalog() -> dict:
    """Static curated roster is bundled and works without network/API credentials."""
    return {'champions': local_champions(), 'version': FALLBACK_VERSION,
            'source': 'curated demonstration metadata',
            'disclaimer': '조합 특성은 교육용 수작업 정의 데이터입니다. 실시간 승률·카운터 통계가 아닙니다.'}


def riot_latest_version() -> str:
    try:
        r = httpx.get('https://ddragon.leagueoflegends.com/api/versions.json', timeout=2.0)
        r.raise_for_status()
        return r.json()[0]
    except Exception:
        return FALLBACK_VERSION
