Two small follow-ups surfaced by the v4 audit:

- ``Simulation.save()`` now raises a helpful ``ValueError`` when ``output_dataset`` is still ``None`` (run or ensure was never called), instead of the raw ``AttributeError: 'NoneType' object has no attribute 'save'``.
- New ``scripts/check_data_staleness.py`` prints a one-line verdict per country comparing the bundled release manifest's pinned model version against the installed country package; exits non-zero when any country is stale. Drop into CI to get automated "bundle is behind" alerts without waiting for a human to notice.

Also clarified the ``load()`` docstring — ``created_at``/``updated_at`` are filesystem ``ctime``/``mtime`` approximations, not a true round-trip of the original timestamps.
