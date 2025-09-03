import pkg_resources

def get_model_version(country: str):
    # get package version of policyengine_{country}
    package_name = f"policyengine_{country}"
    return pkg_resources.get_distribution(package_name).version
