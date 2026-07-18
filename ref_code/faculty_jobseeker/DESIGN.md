---
name: Minimalist High-End Education
colors:
  surface: '#fcf8ff'
  surface-dim: '#dcd8e5'
  surface-bright: '#fcf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f2ff'
  surface-container: '#f0ecf9'
  surface-container-high: '#eae6f4'
  surface-container-highest: '#e4e1ee'
  on-surface: '#1b1b24'
  on-surface-variant: '#464555'
  inverse-surface: '#302f39'
  inverse-on-surface: '#f3effc'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4d44e3'
  primary: '#3525cd'
  on-primary: '#ffffff'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#c3c0ff'
  secondary: '#712ae2'
  on-secondary: '#ffffff'
  secondary-container: '#8a4cfc'
  on-secondary-container: '#fffbff'
  tertiary: '#7e3000'
  on-tertiary: '#ffffff'
  tertiary-container: '#a44100'
  on-tertiary-container: '#ffd2be'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#eaddff'
  secondary-fixed-dim: '#d2bbff'
  on-secondary-fixed: '#25005a'
  on-secondary-fixed-variant: '#5a00c6'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb695'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7b2f00'
  background: '#fcf8ff'
  on-background: '#1b1b24'
  surface-variant: '#e4e1ee'
typography:
  display-xl:
    fontSize: 64px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  display-lg:
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.03em
  headline-lg:
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.3'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontSize: 28px
    fontWeight: '700'
    lineHeight: '1.3'
    letterSpacing: -0.02em
  headline-md:
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  body-lg:
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-md:
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  label-md:
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.02em
  caption:
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: '0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 0.5rem
  sm: 1rem
  md: 1.5rem
  lg: 2.5rem
  xl: 4rem
  2xl: 8rem
  container_max: 1280px
  gutter: 24px
  margin_mobile: 20px
---

## Brand & Style

The design system is anchored in the "Minimal Luxury" movement, blending the precision of high-end SaaS (Stripe/Linear) with the whitespace and typographic elegance of editorial fashion magazines. It targets a discerning audience that values clarity, speed, and status.

The visual language is defined by extreme cleanliness, high-quality typography, and a "less but better" philosophy. Every element is intentional, avoiding decorative clutter in favor of functional elegance. The goal is to evoke a sense of calm authority and premium quality, making the complex process of career advancement feel effortless and sophisticated.

## Colors

The palette is rooted in a sophisticated "Off-White" base (`#FCFCFD`) to reduce eye strain while maintaining a crisp, premium feel. 

- **Primary & Secondary:** An Indigo-to-Violet spectrum provides the "SaaS-Quality" professional aesthetic. Use these for high-intent actions and brand-defining moments.
- **Accent:** A soft Teal is used sparingly for success states, badges, and progress indicators to provide a refreshing contrast to the cooler primary tones.
- **Typography:** Deep Slate-900 is used instead of pure black to maintain a softer, more expensive appearance.
- **Gradients:** Use subtle, low-opacity pastel gradients for background sections to add depth without introducing visual noise.

## Typography

Plus Jakarta Sans is the sole typeface, utilized for its modern, geometric structure and approachable roundness. 

- **Display Scales:** Use `-0.04em` letter spacing for larger headings to create a tight, "locked-in" editorial look.
- **Hierarchy:** Maintain significant size steps between headings and body text. A "Label" style (uppercase with slight tracking) should be used for category markers or small metadata to contrast against the fluid body text.
- **Readability:** Body text uses a generous 1.6 line-height to emphasize the "Editorial" feel and ensure long-form educational content is easy to digest.

## Layout & Spacing

The layout philosophy follows a **Fixed Grid** system for content, centered within the viewport, while background elements and decorative gradients may stretch fluently.

- **The Power of Whitespace:** Use `8rem` (2xl) spacing between major landing page sections to give content "room to breathe."
- **Grid:** Use a 12-column grid on desktop (72px columns, 24px gutters). On mobile, collapse to a single column with 20px side margins.
- **Rhythm:** All spacing must be a multiple of the 4px base unit. Component-level padding should lean towards the generous side (e.g., buttons with 24px horizontal padding).

## Elevation & Depth

This design system uses a "Soft Premium Shadow" approach to simulate physical layers of high-quality cardstock.

- **Base Level:** The background is `#FCFCFD`.
- **Level 1 (Cards/Surface):** Pure White (`#FFFFFF`) surfaces with a very soft, diffused shadow: `0 4px 20px -2px rgba(15, 23, 42, 0.05)`.
- **Level 2 (Modals/Popovers):** Higher elevation with more spread: `0 20px 40px -4px rgba(15, 23, 42, 0.1)`.
- **Glassmorphism:** For navigation bars, use a backdrop blur of `20px` with a semi-transparent white fill (`rgba(255, 255, 255, 0.8)`) and a 1px border of `rgba(0, 0, 0, 0.05)` to create a floating, high-tech effect.

## Shapes

The shape language is defined by "Large Rounded Corners." 

- **Primary Cards:** Use a 24px (1.5rem) radius to create a soft, welcoming container.
- **Interactive Elements:** Buttons and inputs use a 12px (0.75rem) radius, providing a distinct but harmonious relationship with the larger containers.
- **Icons:** Icons should be enclosed in "Squircle" or heavily rounded containers when used as primary visual cues.

## Components

- **Buttons:** Primary buttons use the Indigo gradient with white text. Hover states should involve a subtle scale-up (1.02x) and an increased shadow spread rather than a simple color change.
- **Inputs:** Use a soft Slate-100 background for inputs with no initial border. On focus, transition to a white background with a 1px Indigo border and a soft glow shadow.
- **Chips/Badges:** Use the Accent color at 10% opacity for the background and 100% opacity for the text. Keep them pill-shaped (full radius).
- **Cards:** Feature cards should have a 1px subtle border (`#F1F5F9`) and a soft shadow. Avoid "heavy" borders; let the shadow define the edge.
- **Lists:** Use generous vertical padding (16px+) between list items with a hairline divider (`1px solid #F1F5F9`).
- **Educational Progress:** Use "Apple-style" thick progress bars (8px height) with fully rounded ends and a subtle gradient fill.