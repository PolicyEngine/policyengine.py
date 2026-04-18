def fetch_version():
    try:
        from importlib.metadata import version

        return version("policyengine")
    except Exception as e:
        print(f"Error fetching version: {e}")
        return None


if __name__ == "__main__":
    print(fetch_version())
