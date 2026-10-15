"""Area x record weights.

Two layouts hold the same thing. In the label layout each record sits in one
area with one weight. In the matrix layout a record can carry weight in many
areas. The rules read both through the same operations, so they are written
once. Which rules apply depends on how the data was given, not on what it
holds: weights given as a matrix keep the weight-matrix rules.
"""

from collections.abc import Iterable, Sequence
from typing import Optional

import numpy as np
import pandas as pd

UNASSIGNED = ""


def normalise_area_codes(area_codes: object) -> np.ndarray:
    """Return codes as stripped strings, with missing codes as ``""``."""

    def _one(value: object) -> str:
        if value is None:
            return UNASSIGNED
        if isinstance(value, bytes):
            return value.decode("utf-8").strip()
        if isinstance(value, float) and np.isnan(value):
            return UNASSIGNED
        if value is pd.NA:
            return UNASSIGNED
        return str(value).strip()

    return np.array([_one(value) for value in pd.Series(area_codes)], dtype=object)


def _validated_weights(weights: object) -> np.ndarray:
    array = np.asarray(weights, dtype=float)
    if array.ndim != 1:
        raise ValueError("Weights must be one-dimensional.")
    if not np.isfinite(array).all():
        raise ValueError("Weights must be finite.")
    if (array < 0).any():
        raise ValueError("Weights must be non-negative.")
    return array


class AreaWeights:
    """The weight of every record in every area of one geography level."""

    def __init__(
        self,
        *,
        area_codes: Sequence[str],
        n_records: int,
        label_index: Optional[np.ndarray] = None,
        weights: Optional[np.ndarray] = None,
        matrix: Optional[np.ndarray] = None,
        from_matrix: bool = False,
    ) -> None:
        self.area_codes = tuple(area_codes)
        self._from_matrix = from_matrix or matrix is not None
        self.n_records = int(n_records)
        self._position = {code: i for i, code in enumerate(self.area_codes)}
        # The label layout fills the first two; the matrix layout the third.
        self._label_index = (
            np.empty(0, dtype=int) if label_index is None else label_index
        )
        self._weights = np.empty(0) if weights is None else weights
        self._matrix = matrix
        if label_index is not None:
            # Records sorted by area, so each area is one slice.
            assigned = np.flatnonzero(label_index >= 0)
            order = assigned[np.argsort(label_index[assigned], kind="stable")]
            self._order = order
            counts = np.bincount(label_index[assigned], minlength=len(self.area_codes))
            self._starts = np.concatenate(([0], np.cumsum(counts)[:-1])).astype(int)
            self._counts = counts

    @classmethod
    def from_labels(cls, area_codes: object, weights: object) -> "AreaWeights":
        """One area and one weight per record. Blank codes stay unassigned."""
        codes = normalise_area_codes(area_codes)
        weight_array = _validated_weights(weights)
        if len(codes) != len(weight_array):
            raise ValueError("Area codes and weights differ in length.")
        return cls._from_codes(codes, weight_array)

    @classmethod
    def _from_codes(
        cls,
        codes: np.ndarray,
        weights: np.ndarray,
        order: Optional[Sequence[str]] = None,
        from_matrix: bool = False,
    ) -> "AreaWeights":
        weighted = {code for code in codes[weights > 0] if code != UNASSIGNED}
        ordered = order if order is not None else sorted(weighted)
        area_codes = [code for code in ordered if code in weighted]
        position = {code: i for i, code in enumerate(area_codes)}
        # A record with no code, or in an area with no weight, is unassigned.
        label_index = np.array([position.get(code, -1) for code in codes], dtype=int)
        return cls(
            area_codes=area_codes,
            n_records=len(codes),
            label_index=label_index,
            weights=weights,
            from_matrix=from_matrix,
        )

    @classmethod
    def from_matrix(cls, matrix: object, area_codes: Sequence[object]) -> "AreaWeights":
        """An areas x records weight matrix. The matrix is not copied.

        Data given as a matrix keeps the weight-matrix rules whatever it
        holds. One row of a dense matrix has one weight per record, yet every
        record of the nation still sits in that area.
        """
        array = np.asarray(matrix)
        if array.ndim != 2:
            raise ValueError("A weight matrix must be two-dimensional.")
        codes = [str(code).strip() for code in normalise_area_codes(area_codes)]
        if array.shape[0] != len(codes):
            raise ValueError("A weight matrix needs one row per area code.")
        if len(set(codes)) != len(codes) or UNASSIGNED in codes:
            raise ValueError("Matrix area codes must be unique and non-blank.")
        if not np.isfinite(array).all():
            raise ValueError("Weights must be finite.")
        if (array < 0).any():
            raise ValueError("Weights must be non-negative.")
        if array.shape[0] and np.count_nonzero(array, axis=0).max(initial=0) <= 1:
            # One non-zero per record: store it as labels, which is faster.
            # The rules still treat it as a weight matrix.
            weights = array.max(axis=0).astype(float)
            row = array.argmax(axis=0)
            labels = np.array(
                [codes[r] if w > 0 else UNASSIGNED for r, w in zip(row, weights)],
                dtype=object,
            )
            return cls._from_codes(labels, weights, order=codes, from_matrix=True)
        return cls(area_codes=codes, n_records=array.shape[1], matrix=array)

    @property
    def n_areas(self) -> int:
        return len(self.area_codes)

    @property
    def one_area_per_record(self) -> bool:
        """Whether the data was given as one area and one weight per record."""
        return not self._from_matrix

    @property
    def labels(self) -> np.ndarray:
        """The area code of each record (``""`` if unassigned)."""
        if self._matrix is not None:
            raise ValueError("A weight matrix has no single area per record.")
        codes = np.array(self.area_codes + (UNASSIGNED,), dtype=object)
        return np.asarray(codes[self._label_index])

    def area_records(self, area: str) -> tuple[np.ndarray, np.ndarray]:
        """The records with weight in one area, and their weights."""
        position = self._position[area]
        if self._matrix is not None:
            row = self._matrix[position]
            records = np.flatnonzero(row)
            return records, row[records].astype(float)
        start = self._starts[position]
        records = self._order[start : start + self._counts[position]]
        weights = self._weights[records]
        keep = weights > 0
        return records[keep], weights[keep]

    def record_weights(
        self, areas: Iterable[str], *, include_unassigned: bool = False
    ) -> np.ndarray:
        """Each record's weight, summed over the given areas."""
        positions = [self._position[area] for area in areas]
        if self._matrix is not None:
            if not positions:
                return np.zeros(self.n_records)
            return self._matrix[positions].sum(axis=0, dtype=float)
        mask = np.isin(self._label_index, positions)
        if include_unassigned:
            mask |= self._label_index < 0
        return np.where(mask, self._weights, 0.0)

    def totals(
        self, values: object, multipliers: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """Weighted sums of a per-record value, by area.

        With ``multipliers`` (replicates x records) the result has one column
        per replicate.
        """
        value_array = np.asarray(values, dtype=float)
        if value_array.shape != (self.n_records,):
            raise ValueError("Values must have one entry per record.")
        if self._matrix is not None:
            dtype = self._matrix.dtype
            if multipliers is None:
                return np.asarray(self._matrix @ value_array.astype(dtype), dtype=float)
            # One product per chunk of replicates; no matrix-sized temporary.
            scaled = np.ascontiguousarray(
                (multipliers * value_array[None, :]).T, dtype=dtype
            )
            return np.asarray(self._matrix @ scaled, dtype=float)
        weighted = self._weights * value_array
        if multipliers is None:
            return np.bincount(
                self._label_index[self._order],
                weights=weighted[self._order],
                minlength=self.n_areas,
            )
        if self.n_areas == 0:
            return np.zeros((0, multipliers.shape[0]))
        by_area = multipliers[:, self._order] * weighted[self._order]
        return np.asarray(np.add.reduceat(by_area, self._starts, axis=1).T)
