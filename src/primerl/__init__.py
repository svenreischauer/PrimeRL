from importlib import import_module

from . import ensembl_adapter
from . import export_naming
from . import golden
from . import io_fasta
from . import parity
from . import primer3_qpcr
from . import spidey_adapter

__all__ = [
    "export_naming",
    "primer3_qpcr",
    "ensembl_adapter",
    "spidey_adapter",
    "io_fasta",
    "parity",
    "gui",
    "golden",
]


def __getattr__(name: str):
    if name == "gui":
        mod = import_module(".gui", __name__)
        globals()["gui"] = mod
        return mod
    raise AttributeError(name)
