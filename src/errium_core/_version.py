from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """The installed `errium` distribution version, or a placeholder if unknown."""
    try:
        return version("errium")
    except PackageNotFoundError:
        return "0+unknown"


__version__ = get_version()
