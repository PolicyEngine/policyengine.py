"""Area x record weights in the label and the matrix layout. Synthetic data."""

import numpy as np
import pytest

from policyengine.disclosure import UNASSIGNED, AreaWeights


def _labels_and_matrix():
    codes = np.array(["B", "A", "B", "C", "A", "C", "B"], dtype=object)
    weights = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0])
    order = ["A", "B", "C"]
    matrix = np.zeros((3, len(codes)))
    for record, (code, weight) in enumerate(zip(codes, weights)):
        matrix[order.index(code), record] = weight
    return codes, weights, order, matrix


def test_labels_and_a_one_nonzero_matrix_are_the_same_data():
    codes, weights, order, matrix = _labels_and_matrix()
    values = np.arange(1.0, 8.0)
    multipliers = np.random.default_rng(0).poisson(1.0, size=(5, 7)).astype(np.uint8)

    from_labels = AreaWeights.from_labels(codes, weights)
    from_matrix = AreaWeights.from_matrix(matrix, order)

    assert from_labels.one_area_per_record
    assert from_labels.area_codes == from_matrix.area_codes == ("A", "B", "C")
    assert np.array_equal(from_labels.labels, from_matrix.labels)
    assert np.allclose(from_labels.totals(values), from_matrix.totals(values))
    assert np.allclose(
        from_labels.totals(values, multipliers),
        from_matrix.totals(values, multipliers),
    )


def test_weights_given_as_a_matrix_keep_the_matrix_rules():
    """One row of a dense matrix looks like labels, but is not label data."""
    one_row = AreaWeights.from_matrix(np.array([[5.0, 0.0, 2.0, 1.0]]), ["A"])

    assert not one_row.one_area_per_record
    assert one_row.labels.tolist() == ["A", UNASSIGNED, "A", "A"]
    assert one_row.totals(np.ones(4)).tolist() == [8.0]


def test_totals_equal_a_direct_weighted_sum():
    codes, weights, _, _ = _labels_and_matrix()
    values = np.arange(1.0, 8.0)
    areas = AreaWeights.from_labels(codes, weights)

    totals = areas.totals(values)

    assert totals.tolist() == [
        float((weights * values)[codes == code].sum()) for code in ("A", "B", "C")
    ]


def test_dense_matrix_totals_match_the_matrix_product():
    rng = np.random.default_rng(1)
    matrix = rng.uniform(0.0, 2.0, size=(4, 30)).astype(np.float32)
    values = rng.normal(size=30)
    multipliers = rng.poisson(1.0, size=(6, 30)).astype(np.uint8)

    areas = AreaWeights.from_matrix(matrix, ["a", "b", "c", "d"])

    assert not areas.one_area_per_record
    assert np.shares_memory(areas._matrix, matrix)
    assert np.allclose(areas.totals(values), matrix @ values, rtol=1e-5)
    expected = matrix @ (multipliers * values).T
    assert np.allclose(areas.totals(values, multipliers), expected, rtol=1e-5)
    with pytest.raises(ValueError, match="single area"):
        _ = areas.labels


def test_area_records_and_record_weights():
    codes, weights, _, matrix = _labels_and_matrix()
    areas = AreaWeights.from_labels(codes, weights)

    records, record_weights = areas.area_records("B")

    assert sorted(records.tolist()) == [0, 2, 6]
    assert sorted(record_weights.tolist()) == [10.0, 30.0, 70.0]
    assert areas.record_weights(["A", "C"]).tolist() == [0, 20, 0, 40, 50, 60, 0]
    dense = AreaWeights.from_matrix(matrix + 1.0, ["A", "B", "C"])
    assert (
        dense.record_weights(["A", "C"]).tolist()
        == (matrix[0] + matrix[2] + 2).tolist()
    )


def test_blank_codes_stay_as_unassigned_records():
    areas = AreaWeights.from_labels(
        ["A", "", None, b"A", " B ", float("nan")], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    )

    assert areas.area_codes == ("A", "B")
    assert areas.labels.tolist() == ["A", UNASSIGNED, UNASSIGNED, "A", "B", UNASSIGNED]
    assert areas.record_weights([], include_unassigned=True).tolist() == [
        0.0,
        2.0,
        3.0,
        0.0,
        0.0,
        6.0,
    ]
    assert areas.totals(np.ones(6)).tolist() == [5.0, 5.0]


def test_an_area_with_no_weight_is_not_an_area():
    areas = AreaWeights.from_labels(["A", "Z", "A"], [1.0, 0.0, 2.0])

    assert areas.area_codes == ("A",)
    assert areas.labels.tolist() == ["A", UNASSIGNED, "A"]


@pytest.mark.parametrize(
    "weights", [[1.0, -1.0], [1.0, float("nan")], [[1.0, 2.0]], [1.0, float("inf")]]
)
def test_bad_weights_raise(weights):
    with pytest.raises(ValueError):
        AreaWeights.from_labels(["A", "A"], weights)


def test_bad_matrices_raise():
    with pytest.raises(ValueError, match="one row per area"):
        AreaWeights.from_matrix(np.ones((2, 3)), ["A"])
    with pytest.raises(ValueError, match="unique"):
        AreaWeights.from_matrix(np.ones((2, 3)), ["A", "A"])
    with pytest.raises(ValueError, match="non-negative"):
        AreaWeights.from_matrix(-np.ones((2, 3)), ["A", "B"])
    with pytest.raises(ValueError, match="one entry per record"):
        AreaWeights.from_labels(["A", "A"], [1.0, 1.0]).totals(np.ones(3))
