# Claude notes

Claude, please follow these always. These principles are aimed at preventing you from producing AI slop.

1. British English, sentence case
2. No excessive duplication, keep code files as concise as possible to produce the same meaningful value. No excessive printing
3. Don't create multiple files for successive versions. Keep checking: have I added lots of intermediate files which are deprecated? Delete them if so, but ideally don't create them in the first place

## MicroDataFrame

A pandas DataFrame that automatically handles weights for survey microdata. Key features:

- Create with `MicroDataFrame(df, weights='weight_column')`
- All aggregations (sum, mean, etc.) automatically weight results
- Each column is a MicroSeries with weighted operations
- Use `.groupby()` for weighted group statistics
- Built-in poverty analysis: `.poverty_rate()`, `.poverty_gap()`
