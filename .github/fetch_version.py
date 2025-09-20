def fetch_version():
    try:
        import importlib

        return importlib.import_module("policyengine").__version__
    except Exception as e:
        print(f"Error fetching version: {e}")
        return None


if __name__ == "__main__":
    print(fetch_version())
