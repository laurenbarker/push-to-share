try:
    from .source import *  # noqa
except ImportError as error:
    raise ImportError(
        "No source.py settings file found. Did you remember to copy source-dist.py to source.py?"
    )
