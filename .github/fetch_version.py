def fetch_version():
    try:
        import pkg_resources

        version = pkg_resources.get_distribution("policyengine").version
        return version
    except Exception as e:
        print(f"Error fetching version: {e}")
        return None


if __name__ == "__main__":
    print(fetch_version())
