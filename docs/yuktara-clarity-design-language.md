# Yuktara Clarity design language

Yuktara Clarity is an original native design system informed by the restraint,
legibility and platform coherence associated with high-quality operating-system
interfaces. It is not an Apple interface clone and does not use Apple's
proprietary fonts, icons, assets or implementation.

## Design principles

1. **Content first.** Surfaces and chrome should support content, not compete
   with it.
2. **Quiet hierarchy.** Use typography, spacing and surface roles before adding
   borders, shadows or accent colors.
3. **One accent at a time.** Reserve blue for primary actions, links, focus and
   selected states. Semantic colors communicate status only.
4. **Consistent geometry.** Components consume the shared radius, spacing and
   control-size tokens; avoid local magic numbers.
5. **Responsive by composition.** Reflow navigation and content at logical
   breakpoints; never distort text or controls to fit.
6. **Interaction is visible.** Hover, pressed, focused, selected, disabled,
   loading and destructive states must be deliberate and testable.
7. **Accessible by default.** Every actionable control has a meaningful name,
   role, state and keyboard path.

## Typography

Inter is the only implicit typeface. Use the semantic display, headline, title,
body and label roles in NativeTheme. Do not silently substitute platform
fonts. Additional families are allowed only when an application explicitly
configures them.

## Color

The light palette uses a soft neutral canvas, white content surfaces, near-black
primary text, secondary gray text and a restrained blue accent. The dark palette
is independently authored around black and layered charcoal surfaces with
high-contrast text and a brighter blue accent. Components must use semantic
roles rather than embedding palette values.

## Geometry and spacing

Use the 4-point spacing scale and shared shape tokens. Large radii belong to
large surfaces; pill radii are for compact chips and capsule controls. Maintain
the 44-unit minimum interactive target unless a platform-specific compact
density is explicitly requested.

## Component acceptance checklist

A component is not design-system complete until it:
- uses theme tokens for color, typography, spacing and shape;
- has consistent default, hover, pressed, focused, selected and disabled states
  where applicable;
- exposes accessibility role, accessible name, state and keyboard behavior;
- handles constrained widths and window resizing without clipping or stretching;
- has unit tests for configuration validation and interaction behavior;
- appears in the light and dark galleries.

## Rendering boundary

The current CPU Skia renderer does not yet provide a complete shadow compositor,
GPU acceleration, platform-native blur/material effects or certified OS
accessibility bridges. Do not simulate those capabilities with arbitrary
transparency or claim platform parity before those implementations and tests
exist.
