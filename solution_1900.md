# Fix for Issue #1900: Website: accessibility and motion-preference fixes for the landing page

## Problem
The landing page (`website/`) had several accessibility and motion issues:
1. Missing support for users who have configured system-level reduced motion preferences (`prefers-reduced-motion: reduce`), causing animations to run unprompted.
2. Missing skip-to-content links and improper document landmarks (e.g. hero section outside `<main>`).
3. Heading levels were disjointed and lacked semantic hierarchy.
4. Focus visibility was absent or inconsistent for keyboard navigation.
5. Inadequate contrast ratios for small text against background tokens under WCAG 2.1 AA.

## Solution
1. **WCAG 2.1 AA Motion-Preference Handling (`prefers-reduced-motion: reduce`)**:
   - Integrated live `window.matchMedia("(prefers-reduced-motion: reduce)")` listeners in `website/src/hero-animation.ts` and `website/src/animations.ts`.
   - When reduced motion is requested, animation loops halt immediately and render the static 3-stage preview frame (`drawStatic()`).
   - Added CSS reduced-motion rules setting `scroll-behavior: auto` and disabling unnecessary CSS transitions.
2. **Accessible Landmarks and Semantics**:
   - Added skip-link (`a.skip-link`) directing keyboard focus straight to `#main-content`.
   - Placed the primary hero header inside `<main id="main-content">`.
   - Labeled primary navigation with `aria-label="Primary"`.
   - Promoted stage nodes to `<h3>` tags for a clean `h1 -> h2 -> h3` hierarchy.
3. **Focus States & Keyboard Reachability**:
   - Enforced visible, high-contrast `:focus-visible` outlines (`2px solid var(--mint)`) across all interactive buttons, links, and code blocks.
4. **Contrast & ARIA Hygiene**:
   - Adjusted color tokens (`--slate`, `--burn`, `--attest`, `--mint`) to exceed 4.5:1 contrast against light background tokens.
   - Marked purely decorative numbers, arrows, and glyphs with `aria-hidden="true"`.
   - Added `.sr-only` "(opens in a new tab)" announcements for external CTAs.
5. **Hermetic Test Suite**:
   - Verified in `tests/website-a11y.test.ts`.

**Payout Wallet Address**: `0xC345C07229307d4f1c7935aD2cAe48e390215808`
