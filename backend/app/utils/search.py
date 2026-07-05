# Search helpers for building safe SQL LIKE/ILIKE patterns.

# Escape the LIKE special characters so user input is matched literally. Order
# matters: the escape char (\) must be escaped first, then the wildcards.
def escape_like(value: str) -> str:
    """Escape %, _ and \\ so ``value`` is treated literally inside a LIKE pattern.

    Pair with ``.ilike(f"%{escape_like(v)}%", escape="\\\\")``.
    """
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
