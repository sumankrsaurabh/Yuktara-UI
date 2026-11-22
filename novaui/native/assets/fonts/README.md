# Optional font assets

Inter is the framework's only implicit/default font. No other font family is
loaded as an automatic fallback.

Additional font families are opt-in: an application must explicitly select
the family with FontConfig(family=...) and provide any required font file
through font_path / font_files. The optional Yuktara Sans files may be
placed in this directory and selected explicitly as Yuktara Sans or
Yuktara Sans Display. Alternatively, set YUKTARA_UI_FONT_DIR to the
directory containing the licensed OTF files.

When redistributing Yuktara Sans, retain its supplied Inter Open Font License
and upstream copyright/attribution notices.
