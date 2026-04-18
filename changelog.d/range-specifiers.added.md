`certify_data_release_compatibility` now accepts full PEP 440 version
specifiers (`>=1.637.0,<2.0.0`, `~=1.637`, etc.) in a data release
manifest's `compatible_model_packages`, not only `==X.Y.Z`. This lets
the US data package declare a range of compatible `policyengine-us`
versions when the `data_build_fingerprint` is known to be stable
across them, avoiding the need to regenerate the dataset for every
model patch release. Adds `packaging>=23.0` as a direct dependency.
