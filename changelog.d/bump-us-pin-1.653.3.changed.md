Bump the bundled US release manifest to `policyengine-us==1.653.3` (from
1.647.0) to unblock downstream projects that want to pin the latest
working model version through `policyengine.py`. The dataset stays at
`policyengine-us-data==1.73.0` (the latest US data release tagged on
Hugging Face); certification is now
`matching_data_build_fingerprint` with `built_with_model_version`
recording the 1.647.0 that actually produced the data. Both bundled
manifests (`us.json`, `uk.json`) update `policyengine_version` and
`bundle_id` to 3.5.0 to match the current package version.
