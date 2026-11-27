# Editorial worker protocol

- Work only on assigned message IDs; surrounding scene context is read-only. Read the original language first. Preserve correct existing writing; change only for an identifiable issue. For an independent translation task, do not consult inherited translated wording.
- Prioritize meaning, mechanics, quantities, conditions, speaker identity, narrative continuity, then fluency and concision. Do not add facts or resolve deliberate ambiguity. Use the approved terminology and voice profiles; escalate disagreements instead of silently introducing variants.
- Preserve variable, icon, formatting and control tokens; do not invent button mappings. Respect source-specific rendering and timing constraints. Do not translate a placeholder just to increase coverage.
- Use authorized local references sparingly. Search a term and consult relevant context rather than pasting an entire corpus into a prompt. Keep reference snippets, source locators and internal editorial notes private; do not put them into public commits or release notes.
- Output JSONL proposals with ID, assignment_id, original fingerprint, replacement translation and concrete reason. One assignment per proposal file. Do not edit source assets or output recipes directly. A separate reviewer checks Japanese accuracy, terminology and layout. No change is required if the original is good.
