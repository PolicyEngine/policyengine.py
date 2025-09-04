from importlib.metadata import version as _pkg_version, PackageNotFoundError


def get_model_version(country: str):
    """Get installed package version for the country model without pkg_resources warnings."""
    package_name = f"policyengine_{country}"
    try:
        return _pkg_version(package_name)
    except PackageNotFoundError:
        try:
            # Fallback if importlib.metadata is unavailable/old env
            import pkg_resources  # type: ignore

            return pkg_resources.get_distribution(package_name).version  # noqa: F401
        except Exception:
            return "unknown"
