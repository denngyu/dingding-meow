"""饮水手填值的尺寸约束与校验。"""

WATER_DIALOG_WIDTH = 330
WATER_DIALOG_HEIGHT = 376
MIN_WATER_ML = 1
MAX_WATER_ML = 5000
WATER_PRESETS = (
    ("一口", 50),
    ("半杯", 150),
    ("一杯", 300),
    ("一瓶", 500),
)


def parse_water_amount(raw):
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if not MIN_WATER_ML <= value <= MAX_WATER_ML:
        return None
    return value
