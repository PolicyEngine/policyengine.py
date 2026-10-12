"""Compare compiled code with source, ignoring where it was compiled.

A code object records the file it was compiled from and its line numbers.
Two compilations of the same source in different checkouts differ only
there, so :func:`code_shape` leaves both out; everything that changes what
the code does (instructions, names, constants, nested code) stays in.
"""

from __future__ import annotations

import importlib.util
import marshal
import os
from pathlib import Path
from types import CodeType
from typing import Any, Optional

__all__ = ["CompiledFile", "code_shape", "compiled_file", "compile_source"]

#: ``compile()`` optimisation level held by each bytecode cache name suffix
#: (``x.cpython-313.pyc``, ``x.cpython-313.opt-1.pyc``, ``...opt-2.pyc``).
OPTIMIZATION_LEVELS = {"": 0, "1": 1, "2": 2}

_HEADER = 16
_HASH_BASED = 0b01
_CHECK_SOURCE = 0b10


def _constant(value: Any) -> tuple[Any, ...]:
    """A code constant with its exact type, so equal-but-different values differ.

    ``(1,) == (1.0,)``, ``True == 1`` and ``0.0 == -0.0`` in Python, but code
    holding one behaves differently from code holding the other, so tuples
    and frozensets are encoded item by item and floats by their bits.
    """

    kind = type(value)
    if kind is float:
        return (kind, value.hex())
    if kind is complex:
        return (kind, value.real.hex(), value.imag.hex())
    if kind is tuple:
        return (kind, tuple(_constant(item) for item in value))
    if kind is frozenset:
        return (kind, tuple(sorted((_constant(item) for item in value), key=repr)))
    if isinstance(value, CodeType):
        return (CodeType, code_shape(value))
    if kind in (type(None), type(Ellipsis)):
        return (kind,)
    return (kind, value)


def code_shape(code: CodeType) -> tuple[Any, ...]:
    """A code object without where it was compiled: no file, no line numbers."""

    return (
        code.co_name,
        code.co_qualname,
        code.co_argcount,
        code.co_posonlyargcount,
        code.co_kwonlyargcount,
        code.co_flags,
        code.co_stacksize,
        code.co_code,
        code.co_names,
        code.co_varnames,
        code.co_freevars,
        code.co_cellvars,
        code.co_exceptiontable,
        tuple(_constant(const) for const in code.co_consts),
    )


def compile_source(
    source: str | bytes, filename: str, *, flags: int = 0, optimize: int = -1
) -> Optional[CodeType]:
    """``source`` compiled as a module, or ``None`` when it does not compile."""

    try:
        compiled: CodeType = compile(
            source, filename, "exec", flags=flags, dont_inherit=True, optimize=optimize
        )
    except (SyntaxError, ValueError):
        return None
    return compiled


class CompiledFile:
    """What a bytecode cache file holds and whether the interpreter loads it."""

    def __init__(self, status: str, detail: str = "") -> None:
        #: ``matches`` (loaded, and compiles from the source), ``differs``
        #: (loaded, but does not), ``inert`` (the interpreter would ignore it
        #: and compile the source instead) or ``invalid``.
        self.status = status
        self.detail = detail


def compiled_file(pyc: Path, source: Path, optimization: str) -> CompiledFile:
    """Check a ``__pycache__`` file against the source it caches.

    The interpreter loads a timestamp-based cache only while its recorded
    source modification time and size match the source, and a checked
    hash-based cache only while its recorded source hash matches; otherwise
    it compiles the source and the cache is ``inert``. A checked cache is
    treated as loaded whatever its hash, because ``--check-hash-based-pycs
    never`` loads it unchecked, and an unchecked one is always loaded. A
    loaded cache must compile from the source at its optimisation level. The
    cache is unmarshalled, never executed.
    """

    level = OPTIMIZATION_LEVELS.get(optimization)
    if level is None:
        return CompiledFile("invalid", f"optimisation level {optimization!r}")
    try:
        data = pyc.read_bytes()
        source_bytes = source.read_bytes()
    except OSError as exc:
        # The interpreter ignores a cache it cannot read and compiles the source.
        return CompiledFile("inert", f"unreadable ({type(exc).__name__})")
    if len(data) < _HEADER or data[:4] != importlib.util.MAGIC_NUMBER:
        return CompiledFile("inert", "written for another interpreter")
    flags = int.from_bytes(data[4:8], "little")
    if flags & ~(_HASH_BASED | _CHECK_SOURCE):
        # importlib refuses unknown flag bits and falls back to the source.
        return CompiledFile("inert", "unknown header flags")
    if not flags & _HASH_BASED:
        # Timestamp-based, whatever the check-source bit says (importlib
        # reads that bit only for hash-based caches).
        stat = os.stat(source)
        recorded = (
            int.from_bytes(data[8:12], "little"),
            int.from_bytes(data[12:16], "little"),
        )
        current = (int(stat.st_mtime) & 0xFFFFFFFF, stat.st_size & 0xFFFFFFFF)
        if recorded != current:
            return CompiledFile("inert", "stale timestamp")
    try:
        loaded = marshal.loads(data[_HEADER:])
    except (EOFError, ValueError, TypeError):
        return CompiledFile("differs", "unreadable bytecode")
    compiled = compile_source(source_bytes, str(source), optimize=level)
    if (
        not isinstance(loaded, CodeType)
        or compiled is None
        or code_shape(loaded) != code_shape(compiled)
    ):
        return CompiledFile("differs", "does not compile from the verified source")
    return CompiledFile("matches")
