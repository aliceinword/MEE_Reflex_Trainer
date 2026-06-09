## Summary

- Imports 25 AdaptiBar past questions into the MBE deck
- Fixes MEE call-of-the-question display: questions with multiple calls (e.g. Torts Feb 2025 Q3) now show every call
  - Parser keeps context-first calls ("In a negligence action..."), splits multiple "? Explain." calls mashed on one line, no longer breaks "v." in case names (Son v. Driver), and folds numbered-call preambles into Question 1
  - Restores the corrupted July 2015 Civil Procedure Q2 call stem via scripts/fix_question_calls.py
- Adds scripts/call_parsing_check.py (DB audit + regression fixtures, 0 offenders across 272 questions) and wires it into scripts/architecture_check.py
- Includes earlier branch work: MBE drill layout/scrolling fixes, practice stats sync, PDF import cleanup, and question bank repairs

## Test plan

- [ ] `python scripts/call_parsing_check.py` passes (5/5 fixtures, 0 offenders)
- [ ] `python scripts/architecture_check.py` passes
- [ ] Open Torts Feb 2025 Q3 and confirm Call 1/2/3 all display
- [ ] Spot-check MBE Drills load and record answers
