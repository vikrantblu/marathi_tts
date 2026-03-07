---
mode: 'agent'
description: 'Audit a mobile screen for Android accessibility (TalkBack, content descriptions, touch targets)'
---

Perform an accessibility audit on a mobile screen.

**Target screen:** ${input:screenName:Fragment name (e.g., OutputFragment, InputFragment)}

**Audit checklist:**
1. Read the fragment layout XML and Kotlin source.
2. Check every interactive element (Button, ImageButton, Chip, Slider, EditText) for:
   - `android:contentDescription` — must be present and meaningful (not just "button")
   - Touch target size — minimum 48dp × 48dp per Material guidelines
   - `android:importantForAccessibility` — set appropriately for decorative elements
3. Check `ImageView` elements: decorative ones need `importantForAccessibility="no"`.
4. Check dynamic content (RecyclerView items, TextViews updated programmatically):
   - `ViewCompat.setAccessibilityDelegate` or custom `AccessibilityNodeInfo` where needed
   - `announceForAccessibility()` for important state changes (e.g., TTS generation complete)
5. Check focus order: `android:nextFocusDown/Up/Left/Right` if non-linear navigation needed.
6. Check color contrast: text on background meets WCAG AA (4.5:1 for normal, 3:1 for large text).

**Output:** List each finding with severity (critical/warning/info) and the fix.
Apply fixes directly. Run `python test_all_platforms.py` after changes.
