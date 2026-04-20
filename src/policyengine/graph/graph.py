"""NetworkX-backed variable dependency graph.

Separated from the extractor so the data structure is easy to test
independently, easy to serialize/deserialize, and easy to enrich with
additional edge types (parameter reads, cross-jurisdiction links) in
later versions.
"""

from __future__ import annotations

from typing import Iterable, Optional

try:
    import networkx as nx
except ImportError as exc:  # pragma: no cover - trivial guard
    raise ImportError(
        "policyengine.graph requires networkx. "
        "Install the optional extra: pip install 'policyengine[graph]'."
    ) from exc


class VariableGraph:
    """Directed graph of PolicyEngine variable dependencies.

    Nodes are variable names (strings). Edges run from a *dependency*
    to a *dependent*: ``A -> B`` means "computing B reads A". With
    this orientation, ``impact(A)`` is the set of downstream nodes
    reachable from A, and ``deps(B)`` is the set of upstream nodes
    that reach into B.

    The constructor accepts an optional pre-built graph for testing
    and deserialization; normal callers will get instances via the
    extractor.
    """

    def __init__(self, digraph: Optional[nx.DiGraph] = None) -> None:
        self._g = digraph if digraph is not None else nx.DiGraph()

    # ------------------------------------------------------------------
    # Construction helpers (used by the extractor)
    # ------------------------------------------------------------------

    def add_variable(self, name: str, file_path: Optional[str] = None) -> None:
        """Register a variable as a node. Safe to call repeatedly."""
        if name in self._g:
            if file_path and "file_path" not in self._g.nodes[name]:
                self._g.nodes[name]["file_path"] = file_path
            return
        self._g.add_node(name, file_path=file_path)

    def add_edge(self, dependency: str, dependent: str) -> None:
        """Record that ``dependent`` reads ``dependency`` in a formula."""
        # Auto-register the dependency node if it wasn't declared yet;
        # this is common when a formula references a variable defined
        # in a file the extractor hasn't reached yet, or a variable
        # whose class lives in a different subpackage.
        if dependency not in self._g:
            self._g.add_node(dependency, file_path=None)
        if dependent not in self._g:
            self._g.add_node(dependent, file_path=None)
        self._g.add_edge(dependency, dependent)

    # ------------------------------------------------------------------
    # Query surface
    # ------------------------------------------------------------------

    def has_variable(self, name: str) -> bool:
        """True iff ``name`` was registered as an explicitly-defined variable.

        Nodes that only exist because some formula *references* them —
        but whose class definition was never seen — are excluded.
        """
        if name not in self._g:
            return False
        return self._g.nodes[name].get("file_path") is not None

    def deps(self, name: str) -> Iterable[str]:
        """Return variables that ``name``'s formula reads directly.

        Order follows networkx's insertion order, so the caller can
        expect a deterministic sequence for a given extraction run.
        """
        if name not in self._g:
            return iter(())
        return list(self._g.predecessors(name))

    def impact(self, name: str) -> Iterable[str]:
        """Return variables that transitively depend on ``name``.

        Equivalent to the descendants set in the graph's natural
        orientation (edges run dep → dependent). Excludes ``name``
        itself. Empty for leaf variables that nothing reads.
        """
        if name not in self._g:
            return iter(())
        return list(nx.descendants(self._g, name))

    def path(self, src: str, dst: str) -> Optional[list[str]]:
        """Return a shortest dependency chain from ``src`` to ``dst``.

        Returns the node list including both endpoints, or ``None`` if
        no such path exists.
        """
        if src not in self._g or dst not in self._g:
            return None
        try:
            return nx.shortest_path(self._g, src, dst)
        except nx.NetworkXNoPath:
            return None

    # ------------------------------------------------------------------
    # Introspection for callers that want the raw structure
    # ------------------------------------------------------------------

    @property
    def nx_graph(self) -> nx.DiGraph:
        """The underlying NetworkX DiGraph (read-only-by-convention)."""
        return self._g

    def __contains__(self, name: str) -> bool:
        return name in self._g

    def __len__(self) -> int:
        return self._g.number_of_nodes()

    def __repr__(self) -> str:
        return (
            f"VariableGraph({self._g.number_of_nodes()} variables, "
            f"{self._g.number_of_edges()} edges)"
        )
