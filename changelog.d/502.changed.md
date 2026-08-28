PolicyEngine.py now materializes managed datasets from the exact Hugging Face
repository type, immutable revision, and SHA-256 certified by its release
bundle. Bundle installation and US and UK calculation entry points share this
implementation, while explicitly unmanaged local and Hugging Face sources
remain opt-in.
