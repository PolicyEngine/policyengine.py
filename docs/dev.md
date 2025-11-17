# Development principles

General principles for developing this package's codebase go here.

1. **STRONG** preference for simplicity. Let's make this package as simple as it possibly can be.
2. Remember the goal of this package: to make it easy to create, run, save and analyse PolicyEngine simulations. When considering further features, always ask: can we instead *make it super easy* for people to do this outside the package?
3. Be consistent about property names. `name` = human readable few words you could put as the noun in a sentence without fail. `id` = unique identifier, ideally a UUID. `description` = longer human readable text that describes the object. `created_at` and `updated_at` = timestamps for when the object was created and last updated.
4. Constraints can be good. We should set constraints where they help us simplify the codebase and usage, but not where they unnecessarily block useful functionality.