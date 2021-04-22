from pathlib import Path


def ensure_extension(filename, extension):
    return Path(filename).with_suffix(f".{extension}")
