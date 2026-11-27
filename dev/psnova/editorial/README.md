# Offline localization editing toolkit

A dependency-free Python CLI for provenance-aware bilingual concordance, candidate terminology conflicts, editing batches and optimistic-concurrency merges. Python 3.10+ with SQLite FTS5 trigram support. No network, model API, executable spreadsheet content, or macros are used. All examples are synthetic. Reference data, source game text, and query outputs must be kept outside the public source tree unless authorized for redistribution.

## Reference search

```
python l10n.py --db /path/to/reference.sqlite stats
python l10n.py --db /path/to/reference.sqlite search "example" --locale en-US --limit 5
python l10n.py --db /path/to/reference.sqlite search "example" --exact
python l10n.py --db /path/to/reference.sqlite conflicts --limit 100
```

Search is literal substring in source or target; strings shorter than three characters use ordinary SQLite matching. `--exact` matches the complete source string. Results carry corpus, locale, source locator, status and notes; a confirmed review segment is not necessarily a released translation. Conflict candidates are not decisions: inflection, context, punctuation and different locales may explain differences.

Use `pair_text.py` below to populate a database from authorized bilingual text exports. Keep each game build or localization revision in a separately named corpus.

## Editable corpus and worker workflow

One JSON object per line, UTF-8. String IDs are mandatory, and leading zeroes are retained. Required for editing: `id`, `source` (or `jp`), `translation`; recommended `scene`, `category`, `speaker`, `context`, `provenance`, `constraints`. Keep original source locally immutable. Keep `translation` distinct from any reference target.

```
python l10n.py batch corpus.jsonl work/batches --size 60
python l10n.py merge corpus.jsonl revised.jsonl work/worker1.jsonl work/worker2.jsonl --assignments work/batches/assignments.json
```

Each batch owns only its items, with adjacent items as read-only context. Entries with unresolved glyphs are excluded from editing and kept as read-only context. Ordering follows input order; supply scene-ordered input. Grouping uses scene, category, then group, falling back to unclassified. Each item carries a `base_sha256` fingerprint. Each batch has an `assignment_id`; the coordinator keeps `assignments.json` (do not hand this manifest to workers). Workers emit only proposed edits, e.g.:

```json
{"id":"001","assignment_id":"batch_0000","base_sha256":"<copy from assigned batch>","translation":"A star.","reason":"Clarify the context."}
```

Merge requires the coordinator manifest for the exact corpus snapshot and rejects edits outside assigned ownership, mixed assignments per proposal file, duplicate IDs, stale fingerprints, unknown IDs, blocked source glyphs, missing reasons, lost protected brace tags, unbalanced color codes and Japanese text in English revisions. It writes a separate output atomically after every edit passes. Merge is a proposed-edit integration step, not editorial approval. Do not merge two alternative revisions blindly. Review all proposed changes before export. Existing reference text is never automatically copied into translations.

Structural lint currently follows a specific brace-tag dialect; it is a starting point, not a substitute for the game's production encoder, token grammar, or rendered layout validation. Add language-specific policy before enabling other targets. No actual RMD build integration or character voice inference in this version.

## Test

```
python -m unittest -v
```

## Structured bilingual game-text import

`pair_text.py` accepts lossless JSONL exports with `archive`, `member`, `category`, `group` (integer), `key`, `text`, and optional `locator`. The exporter must supply a consistent structural archive identity across languages. Select verified language groups explicitly; do not infer language by string position. Duplicate structural keys, missing counterparts, blank values and fully redacted strings are reported separately. Identical source and target is counted but not treated as a failure (proper nouns and numbers can match). Review partially redacted strings and language contamination separately.

```sh
python pair_text.py raw.jsonl raw.jsonl --jp-group 0 --en-group 1 --out pairs --db reference.sqlite --corpus game-build-id
python l10n.py --db reference.sqlite search "example" --corpus game-build-id
```

Group 0/1 in this example is illustrative; confirm actual language groups before import. Use different inputs for separately installed locales. A new versioned corpus ID is required for every import. Records are tagged `released-file-paired` to indicate structural pairing, not semantic validation. The database search prioritizes that status above draft confirmations; explicit `--corpus` filtering is also available. The tool does not extract game archives, determine current game version, decide which variant is displayed by the game, or automatically select a glossary term.

## Nova local corpus preparation

`python nova_prepare.py DATASET OUT [--reference-db LOCAL_DB]` adapts the original extracted dataset to the editing schema, attaches event/NPC context, suggests uncertain glyph readings using conservative text alignment, and produces structural/terminology review queues. No original text is modified. ID-bank grouping, NPC continuation, and scene references are provisional and should be checked against the game. Reference query results and all output are local-only. A reference match is not approval to adopt wording. Use the generic `batch` command to generate review assignments. No binary encoding or public release is performed. The source extraction and all generated outputs must remain outside Git. Unit tests cover core tools including event multiline parsing and alignment.

Run from the repository root, with inputs and outputs under the existing ignored `dump/` directory:

```sh
python dev/psnova/editorial/nova_prepare.py dump/editorial-dataset dump/editorial-prepared
python dev/psnova/editorial/l10n.py batch dump/editorial-prepared/corpus.jsonl dump/editorial-batches --size 60
python -m unittest discover -s dev/psnova/editorial -v
```

The adapter expects `messages.jsonl` (string `id`, `japanese`, `english`, `source_archive`, `source_path`, optional `english_layout_context`/`message_context`), `names.json` (JP name to object containing `english`), `glyph_readings.json` (full hash to object containing optional `candidate`), and `scan/{b,p}_csv/`. Generate these locally with the existing extraction tools under `dev/psnova/rmdtext/`. No extracted data is shipped. Reconcile the English baseline against the current release recipe before editing. Review candidate readings and context assignments before use; the adapter intentionally does not apply them to the source. Keep approved translations and attribution separate from the existing release recipe until provenance and redistribution permissions have been resolved. Do not publish inherited or modified third-party translations without permission. This tooling does not alter the game or the existing localization builder.

## Production RMD validation and glyph preview

From the repository root, with original Japanese 1.00 and 1.05 archives and the normal release Python dependencies installed:

```sh
python dev/psnova/editorial/nova_validate.py dump/revised.jsonl --changed-from dump/corpus.jsonl --base /path/to/NOVA_FileList_Vita.cpk --update /path/to/NOVA_FileList_Vita_patch.cpk --out dump/review-validation --preview
```

Select specific entries with repeated `--id`, changes with `--changed-from`, or all nonempty targets with `--all`. The original archives are SHA-256 checked, read only, and the production encoder and release font settings are used directly. No CPK is rebuilt. `--font` and `--fallback-font` allow explicit font paths; use the release defaults for comparable results. The output directory must be new. `report.json` lists failures, encoded glyph counts, line widths, layout context and atlas dimensions; failures return a nonzero exit code. `--preview` writes local PNGs reconstructed from the actual encoded glyph atlases. Button and variable placeholders are schematic, and this is not a full game UI render (no game shaders, layout transforms, control colors or dynamic values). Unknown layout contexts are explicitly unverified, not counted as fully checked. For IDs missing from release recipes the corpus context is provisional. Review these cases separately. Synthetic tests cover the adapter, not the actual game archives; run the command locally before accepting any edits.

Assignment manifests are snapshot-bound; regenerate batches when the baseline changes. Submit a single assignment per proposal file, retaining its ID. This enforces declared ownership, not authentication; the coordinator must verify the submitter and keep the manifest immutable. Older batches must be regenerated for the new merge command.

## Terminology and character review

`editorial_review.py` provides a local editorial reference layer. Run from the repository root:

```sh
python dev/psnova/editorial/editorial_review.py seed dump/editorial-prepared/corpus.jsonl dump/glossary.json
python dev/psnova/editorial/editorial_review.py profiles dump/editorial-prepared/corpus.jsonl dump/character-evidence.json
python dev/psnova/editorial/editorial_review.py enrich dump/editorial-batches --glossary dump/glossary.json --profiles dump/character-evidence.json
python dev/psnova/editorial/editorial_review.py lint dump/revised.jsonl dump/terminology-warnings.json --glossary dump/glossary.json
```

`seed` discovers alternative translations for identical short source strings. It does not select a preferred translation or automatically import reference wording. `profiles` groups by Japanese speaker name, excludes unresolved glyphs and mismatched event text, and counts possible pronoun forms and sentence endings with evidence message IDs. These are provisional surface observations, not linguistic parsing or confirmed character traits. Character variants remain distinct; inspect quotations, speaker IDs, addressees and context before writing voice guidance. `enrich` adds only terms and compact character profiles relevant to editable batch items; it preserves baseline fingerprints and the coordinator manifest. Regenerate the corpus and assignments after changing source extraction or speaker context.

Glossary format: an object with `version: 1` and a `terms` array. Each term has a unique string `id`, Japanese `source`, and `status` (`candidate`, `verified`, `canonical`, `exception`, `deprecated`, `disputed`). `match` defaults to `exact`; use `substring` only after checking compounds and ambiguity. Optional `categories` and `message_ids` restrict the scope. Canonical and exception entries require an `allowed` list of accepted target forms; deprecated entries require a `deprecated` list. Active entries require `reason` and nonempty `evidence`. For example, using invented terminology:

```json
{"version":1,"terms":[{"id":"fixture-star","source":"青星","status":"canonical","allowed":["Blue Star","Blue Stars"],"reason":"Reviewed example","evidence":["synthetic fixture"]}]}
```

An exception must be scoped. Message-specific approved terms override category-specific terms, which override unscoped terms for the same source; equal-priority applicable approved terms are rejected. The linter reports advisory review warnings for missing approved forms or deprecated wording. English matching is case-insensitive, literal and boundary-aware; inflections must be enumerated. It does not prove semantic correctness, enforce capitalization or automatically replace any text. Candidate, verified and disputed entries are informational until an editor explicitly approves them. Run the linter separately before accepting revisions; merge's structural checks remain unchanged. Keep generated terminology, profiles, evidence and enriched batches local.

## Independent editorial review ledger

Use `review_ledger.py` for the reviewed workflow. `l10n.py merge` remains a proposal-only integration command; it does not confer approval. Editors must record a decision for every assigned ID (including unchanged messages). Keep the manifest, full baseline and returned decisions with the coordinator. Use one actor identifier per actual worker; the coordinator must verify identity and role externally.

Editor JSONL example (synthetic):

```json
{"id":"001","assignment_id":"batch_0000","base_sha256":"<assigned fingerprint>","actor":"editor-A","decision":"revise","severity":"minor","translation":"A star.","reason":"Clarifies the referent."}
```

Decisions are `keep`, `revise`, `query`; severity is `none`, `minor`, `major`, `blocker`, or `query`. Only `revise` carries replacement text. A query cannot be silently approved. Run the ledger after editor submissions to obtain each `editor_sha256`. Independent reviewers should read the source and baseline before consulting the proposal. Their JSONL records contain `id`, `actor`, `reason`, `editor_sha256`, and `verdict` (`agree` or `disagree`). A disagreement or query needs a third distinct actor's resolution with `id`, `actor`, `reason`, `reviewer_sha256`, `decision` (`keep` or `revise`), and `translation` for revisions. Fingerprints are generated by the tool, not guessed by workers.

```sh
python dev/psnova/editorial/review_ledger.py dump/corpus.jsonl --assignments dump/batches/assignments.json --edits dump/editor.jsonl --out dump/review-round1
python dev/psnova/editorial/review_ledger.py dump/corpus.jsonl --assignments dump/batches/assignments.json --edits dump/editor.jsonl --reviews dump/reviewer.jsonl --out dump/review-round2
```

Add `--resolutions dump/lead.jsonl` as needed, and `--finalize` with a new output directory once every assigned ID has a terminal approval. The ledger reports coverage and disagreements, and refuses to emit `revised.jsonl` until all assigned IDs are approved. Unassigned rows and approved unchanged rows are preserved; approved revisions retain the ledger-entry hash. Keep the ledger itself for provenance. This is editorial approval only: run glossary lint and production RMD validation separately, and resolve permission/provenance issues before release. The manifest can cover a pilot subset; completion is relative to that subset, not the whole game. Keep benchmark labels separate from editor and reviewer inputs. Do not publish local review outputs.

## Conversation context browser

`nova_context.py` creates a separate, snapshot-bound index from the locally extracted dataset and prepared editorial corpus. It preserves every parsed event-table and NPC-table occurrence (including repeated IDs and base/update copies). Generic crew groups and invalid NPC continuations remain distinct. Rows without matching RMD messages are displayed as missing, not dropped. Unreferenced messages use explicitly inferred ID/bank groups, not confirmed conversations. The index does not alter the corpus or invalidate existing assignment fingerprints.

From the repository root:

```sh
python dev/psnova/editorial/nova_context.py dump/corpus.jsonl --index dump/context.json build dump/editorial-dataset
python dev/psnova/editorial/nova_context.py dump/corpus.jsonl --index dump/context.json message MESSAGE_ID
python dev/psnova/editorial/nova_context.py dump/corpus.jsonl --index dump/context.json message MESSAGE_ID --occurrences
python dev/psnova/editorial/nova_context.py dump/corpus.jsonl --index dump/context.json scene 'TABLE::GROUP'
python dev/psnova/editorial/nova_context.py dump/corpus.jsonl --index dump/context.json search --speaker SpeakerA --speaker SpeakerB
python dev/psnova/editorial/nova_context.py dump/corpus.jsonl --index dump/context.json browse --out dump/context.html
```

`message` returns the complete group for each occurrence; `--occurrences` returns only the matching occurrence records. `search` returns group IDs and occurrence counts; repeated `--speaker` arguments require all named speakers to occur in a group, not necessarily to talk directly to each other. Supply `--revised dump/revised.jsonl` before the subcommand to compare existing and revised translations; IDs and original source must match the baseline. The self-contained HTML is read-only and runs locally without a server. It embeds all source and target text, so keep it and the index outside Git and do not publish them. Speaker names remain provisional. Event-table order and NPC continuation order are not proof of runtime execution order, branching or conversation choice logic. UI/quest/skill relationships and Lua control flow are not yet reconstructed. Inspect context at whole-group scope during independent review, but do not edit unassigned IDs.
