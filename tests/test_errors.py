from policyengine.utils.errors import format_conditional_error_detail


def test_format_conditional_error_detail():
    assert (
        format_conditional_error_detail("Missing model variables", {"beta", "alpha"})
        == "Missing model variables: alpha, beta"
    )
    assert format_conditional_error_detail("Missing model variables", set()) is None
