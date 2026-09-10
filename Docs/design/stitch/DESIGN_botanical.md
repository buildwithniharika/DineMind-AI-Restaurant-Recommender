---
name: Botanical Culinary Minimal
colors:
  surface: '#f8f9ff'
  surface-dim: '#d1dbec'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dfe9fa'
  surface-container-highest: '#d9e3f4'
  on-surface: '#121c28'
  on-surface-variant: '#57423b'
  inverse-surface: '#27313e'
  inverse-on-surface: '#eaf1ff'
  outline: '#8a726a'
  outline-variant: '#dec0b7'
  surface-tint: '#a23e18'
  primary: '#9f3c16'
  on-primary: '#ffffff'
  primary-container: '#bf542c'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb59c'
  secondary: '#555f6f'
  on-secondary: '#ffffff'
  secondary-container: '#d6e0f3'
  on-secondary-container: '#596373'
  tertiary: '#006578'
  on-tertiary: '#ffffff'
  tertiary-container: '#008097'
  on-tertiary-container: '#f9fdff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbcf'
  primary-fixed-dim: '#ffb59c'
  on-primary-fixed: '#390c00'
  on-primary-fixed-variant: '#822801'
  secondary-fixed: '#d9e3f6'
  secondary-fixed-dim: '#bdc7d9'
  on-secondary-fixed: '#121c2a'
  on-secondary-fixed-variant: '#3d4756'
  tertiary-fixed: '#adecff'
  tertiary-fixed-dim: '#72d4ee'
  on-tertiary-fixed: '#001f26'
  on-tertiary-fixed-variant: '#004e5d'
  background: '#f8f9ff'
  on-background: '#121c28'
  surface-variant: '#d9e3f4'
typography:
  display:
    fontFamily: Epilogue
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-mobile:
    fontFamily: Epilogue
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Epilogue
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Epilogue
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Epilogue
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Epilogue
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  title-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
  title-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Hanken Grotesk
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Hanken Grotesk
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  space-2xs: 0.25rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
  space-3xl: 4rem
  space-4xl: 6rem
  gutter-mobile: 1rem
  gutter-tablet: 1.5rem
  gutter-desktop: 2rem
  margin-mobile: 1.25rem
  margin-tablet: 2.5rem
  margin-desktop: 4rem
---

## Brand & Style
This design system pairs architectural minimalism with warm, organic precision. Crafted for elevated culinary platforms, fine dining tools, and artisanal gastronomy, the visual narrative centers on intentional reduction: pristine white canvases, structural hairline rules, rich charcoal typography, and disciplined strokes of warm terracotta. 

The aesthetic eschews photographic excess in favor of bespoke, vector-drawn botanical and culinary line art. Elements convey stillness, clarity, and uncompromising taste. The user experience feels like a curated architectural menu—tactile, direct, and distraction-free.

## Colors
The palette relies on absolute contrast and measured accents:

- **Base Surfaces**: `#FFFFFF` serves as the universal foundation across all tiers. Surface contrast is established through line separation rather than grey fill shifts.
- **Brand Accent**: `#C85A32` (warm terracotta / cinnabar) is reserved strictly for focal interactions, primary actions, and fine typographical highlights. Never dilute it across large solid fills outside of intentional primary buttons.
- **Text & Content**:
  - Primary text: `#111827` (deep rich charcoal)
  - Secondary / Supporting: `#1F2937`
  - Tertiary / Captions / Meta: `#4B5563`
- **Boundaries & Dividers**:
  - Primary structural rules: `#E5E7EB`
  - Subtle secondary rules & inset strokes: `#F3F4F6`

## Typography
Typographic rhythm balances the sculptural, deliberate weight of Epilogue with the rational, Swiss-adjacent clarity of Hanken Grotesk. 

Headings carry tighter letter spacing to maintain graphic structure. Body text relies on open line heights to maximize air and legibility on pure white backdrops. Labels and metadata adopt uppercase tracking when rendering categories, measurements, or botanical indexing.

## Layout & Spacing
The layout follows a disciplined fixed-grid structure with generous vertical pauses:

- **Breakpoints**: Mobile (up to `640px`), Tablet (`641px` to `1024px`), Desktop (`1025px+`).
- **Grid Layout**: A 12-column architectural grid on desktop with `2rem` gutters and minimum `4rem` outer frame margins. On mobile, elements collapse into a 4-column framework with hairline horizontal rules functioning as content separators.
- **Rhythm**: Generous vertical whitespace (`space-3xl` and `space-4xl`) structures distinct content segments, framing iconography and text like museum plates.

## Elevation & Depth
Elevation is achieved exclusively through **low-contrast outlines and micro-hairlines**. Drop shadows, skeuomorphic shading, and colored backdrops are prohibited.

- **Surface Levels**: All surfaces are `#FFFFFF`. Hierarchical layering is rendered via crisp 1px borders using `#E5E7EB` for standard containment and `#F3F4F6` for internal cell dividers.
- **Overlay & Popovers**: Floating modals, flyouts, and dropdowns sit atop the base with a sharp 1px `#E5E7EB` border. If depth separation is strictly needed over busy line elements, apply a discrete blur backdrop (`backdrop-filter: blur(8px)`) with `rgba(255, 255, 255, 0.92)` surface opacity.

## Shapes
Geometry is tailored, understated, and architectural. The system adheres to **Soft (`1`)** rounding:

- **Base Radius**: `0.25rem` (4px) for controls, input fields, badges, and small containers.
- **Structural Radius**: `0.5rem` (8px) for cards, sheets, and dialogs.
- Avoid large circular or pill treatments unless denoting distinct monochrome botanical icon containers or status dots.

## Components

### Buttons
- **Primary**: Background `#C85A32`, text `#FFFFFF`, border `1px solid transparent`, radius `0.25rem`. On hover: subtle darkening to `#B34E2A`.
- **Secondary / Outline**: Background `#FFFFFF`, text `#111827`, border `1px solid #E5E7EB`, radius `0.25rem`. On hover: border color transitions to `#111827`.
- **Tertiary / Ghost**: Background transparent, text `#1F2937`, radius `0.25rem`. Hover triggers an underline or `#F3F4F6` faint tint.

### Inputs & Selects
- Pure `#FFFFFF` fill, `1px solid #E5E7EB` frame, text `#111827`, placeholder text `#9CA3AF`.
- Active focus state cleanly switches the border to `1px solid #C85A32` without diffuse glow rings.

### Cards & Tile Panels
- Unbroken `#FFFFFF` surfaces bounded by `1px solid #E5E7EB` borders.
- Padding uses `space-lg` to `space-xl`.
- Headers, meta lines, and details are partitioned with fine horizontal hairpins (`#F3F4F6`).

### Chips & Tags
- Height: `28px`. Background `#FFFFFF`, border `1px solid #E5E7EB`, font `label-md`, text `#4B5563`.
- Selected state: Border shifts to `#C85A32`, text shifts to `#C85A32`.

### Checkboxes & Radio Controls
- Base: Unchecked has `#FFFFFF` fill and a crisp `1px solid #E5E7EB` boundary.
- Checked: Fill `#C85A32`, border `#C85A32`, featuring a pure white hairline check or central dot.

### Iconography
- **Strictly Vector Line Work**: Solid fills, photos, and raster graphics are prohibited.
- **Botanical & Culinary Assets**: Stroke width must maintain an even 1.25px to 1.5px weight, drawn using `#111827` or `#C85A32`. Elements include precise linework of branches, leaves, seeds, heirloom vegetables, mortar & pestle, and chef's knives.