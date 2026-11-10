# Native text measurement

This API now includes source-indexed line and grapheme geometry for caret
placement, selection and pointer hit testing. See
[Native text and typography — 2.6](native-text-editor.md) for the current
measurement, fallback-font and editor APIs.

The core supports common combining-mark sequences, emoji modifiers, ZWJ emoji,
regional-indicator flags and Indic virama conjuncts as single editing clusters.
The segmenter is not a complete UAX #29 implementation. Skia text metrics and
fallback font runs are used for measurement; complete bidi/complex-script
shaping and Unicode line-breaking remain explicit platform/text-engine work.
