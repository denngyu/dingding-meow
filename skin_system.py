"""猫咪皮肤发现、校验与设置持久化。"""

from dataclasses import dataclass
import json
from pathlib import Path

from settings_store import read_settings, update_settings


DEFAULT_SKIN_ID = "classic"
SKIN_SETTING_KEY = "skin_id"
REQUIRED_SPRITES = (
    "idle",
    "watch",
    "tail",
    "over",
    "hold_cup",
    "drink",
    "away",
    "sleep",
)


@dataclass(frozen=True)
class SkinInfo:
    skin_id: str
    label: str
    sprite_dir: Path


def _complete_sprite_dir(path):
    path = Path(path)
    return path.is_dir() and all((path / (key + ".png")).is_file() for key in REQUIRED_SPRITES)


def discover_skins(asset_root):
    asset_root = Path(asset_root)
    found = []
    classic_dir = asset_root / "assets" / "cat_sprites"
    if _complete_sprite_dir(classic_dir):
        found.append(SkinInfo(DEFAULT_SKIN_ID, "银灰经典", classic_dir))

    skins_root = asset_root / "assets" / "skins"
    if skins_root.is_dir():
        for folder in sorted(skins_root.iterdir(), key=lambda path: path.name.lower()):
            sprite_dir = folder / "cat_sprites"
            if not folder.is_dir() or not _complete_sprite_dir(sprite_dir):
                continue
            label = folder.name
            manifest = folder / "skin.json"
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if isinstance(data, dict) and str(data.get("label", "")).strip():
                    label = str(data["label"]).strip()
            except (OSError, ValueError, TypeError):
                pass
            found.append(SkinInfo(folder.name, label, sprite_dir))
    return tuple(found)


def skin_map(asset_root):
    return {skin.skin_id: skin for skin in discover_skins(asset_root)}


def resolve_skin(asset_root, skin_id):
    skins = skin_map(asset_root)
    return skins.get(str(skin_id), skins.get(DEFAULT_SKIN_ID))


def load_skin(settings_path, asset_root):
    selected = read_settings(settings_path).get(SKIN_SETTING_KEY, DEFAULT_SKIN_ID)
    skin = resolve_skin(asset_root, selected)
    return skin.skin_id if skin is not None else DEFAULT_SKIN_ID


def save_skin(settings_path, asset_root, skin_id):
    skin = resolve_skin(asset_root, skin_id)
    if skin is None or skin.skin_id != str(skin_id):
        raise ValueError("unknown or incomplete skin: %s" % skin_id)
    update_settings(settings_path, **{SKIN_SETTING_KEY: skin.skin_id})
    return skin.skin_id
