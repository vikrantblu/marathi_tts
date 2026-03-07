---
mode: 'agent'
description: 'Add a new test assertion to test_all_platforms.py'
---

Add a new test case to the cross-platform test suite.

**What to test:** ${input:testDescription:Describe the assertion (e.g., "anusvara before प should become म्प")}

**Steps:**
1. Read `test_all_platforms.py` to identify the correct section (A–K) for this test.
2. Write the assertion following the existing pattern:
   - Import the relevant module
   - Call the function under test
   - Assert the expected output
   - Print `✓ <description>` on pass or `✗ <description>` on fail
3. Run `python test_all_platforms.py` to verify the new test passes on all 3 platforms.
4. If the test is for a phonetic rule, ensure it tests all 3 platforms (web, desktop, mobile).
5. Update `copilot-instructions.md` test coverage table with the new check.

**Sections:**
- A: SandhiEngine — B: Sanskrit phonetics — C: MetreEngine — D: ProsodyEngine
- E: Old Marathi — F: Modern Marathi — G: G2P lexicon — H: (reserved)
- I: TextNormalizer — J: GrammarEngine — K: number_to_words
