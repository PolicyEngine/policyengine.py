from policyengine.utils.errors import (
    create_error,
    format_conditional_error_detail,
)


def test_create_error_returns_requested_error_type():
    error = create_error(ValueError, "Example failure")

    assert isinstance(error, ValueError)
    assert str(error) == "Example failure"


def test_format_conditional_error_detail():
    assert (
        format_conditional_error_detail("Missing model variables", {"beta", "alpha"})
        == "Missing model variables: alpha, beta"
    )
    assert format_conditional_error_detail("Missing model variables", set()) is None
