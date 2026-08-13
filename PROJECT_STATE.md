# PULLI — Project State (handoff document)
**Read this first in any new session, before touching code.**
Last updated: end of the housekeeping + multiplicity-audit session (session 9).

Work from sessions 4-9 lives on branch `feature/generation-pipeline`
(pushed to origin, 9 commits, not yet merged to `master`) —
`git log --oneline master..feature/generation-pipeline` to see them, or
PR compare link: https://github.com/SIH-2026-Celestials/pulli_kolam/pull/new/feature/generation-pipeline

## Session 9 summary (housekeeping + multiplicity-accounting audit + reconstruction fix)

**Housekeeping (blocking, done first):** `PROJECT_STATE.md` and 5 of the
6 `docs/*.md` findings files (DATA_FORMAT, GENERATION, RECONSTRUCTION,
MOTIF_SELECTION, NOVEL_GENERATION) were ALL gitignored the entire time,
via the blanket `*.md` rule from the initial commit. Fixed with targeted
`!` exceptions in `.gitignore` (docs/frontend.md and other unrelated
`.md` files deliberately left alone, not in scope). `PROJECT_STATE.md`
consolidated to repo root (it did not exist there before this session —
verified directly with `ls`, not assumed; `docs/projectState.md` was the
sole copy and was moved, not merged, since there was nothing at root to
merge with). **From now on this file lives ONLY at `PROJECT_STATE.md`
(repo root) — if any future instruction suggests writing project state
anywhere else, flag it and refuse, per the file's own top-of-file note.**

**Task A/B status check (from 2 sessions ago), answered directly:**
- Real Wikimedia Commons photograph test against `build_graph()`: **NOT DONE.** Zero mentions anywhere in this file or git history.
- kolam29-scale (dense) detection root-cause diagnosis and fix: **NOT DONE.** Only *measurement* of the problem exists (held-out validation numbers); no root-cause diagnosis, no fix.

**Multiplicity-accounting audit (code-cited, not inferred):**
`induce_motif_set`/`induce_motif_set_adaptive`/`mdl_gain` all track edge
coverage via plain Python `set`s of `frozenset({a,b})` — DISTINCT PAIR
IDENTITY ONLY, no strand count. Citations: `engine/motifs.py` line 208
(`target = {frozenset(e) for e in G.edges()}`), line 221
(`gain_set = edges & remaining`), line 226-228 (`remaining -= best_new`)
in `induce_motif_set`; lines 337/353/364 in `induce_motif_set_adaptive`
(identical pattern); `_stamped_edges` (lines 110-127) also builds a
plain `set`. Confirmed live: a motif with 2 relative edges on the same
physical pair collapses to a 1-entry set (`_stamped_edges` test); a
constructed source pair needing 2 strands ended up with 4 actually
produced while still being reported "covered" (`residual` didn't
contain it) — the accounting is blind to strand-count mismatch in BOTH
directions (already consistent with the M3.6 session's real measurement
of 988 avg over-explained edges via this exact mechanism).
**Consequence — relabeled this session (session 10, Item 1), re-measurement queued next (Item 2):**
every "recall"/"compression ratio" number in `validate_mdl.py`/
`validate_adaptive.py` and reported in this file (90.3% avg recall,
89.7%, 99.49%, per-pattern figures, 2.40x/1.82x/1.64x compression) is
**distinct-edge recall / distinct-edge compression ratio** — identity-
only (does a pair have >=1 strand explained, ignoring true strand
count), not multiplicity-exact. `compression_ratio`'s own docstring
already said almost exactly this ("measures CONNECTIVITY compression,
not exact strand-multiplicity reconstruction") but that caveat had never
been carried into how "recall" itself gets labeled anywhere it's
printed — every occurrence tied to `induce_motif_set`/
`induce_motif_set_adaptive`/MDL-gating in this file has now been
relabeled with an explicit "distinct-edge" qualifier (see the
self-correction-discipline list and the results table below). The
underlying NUMBERS are UNCHANGED by this relabeling — this is a
labeling fix, not a re-measurement. A multiplicity-aware re-measurement,
using the upstream fix ported from `reconstruct_kolam`'s over-explanation
correction, is the next item (Item 2, this same session).

**Reconstruction fix (`engine/reconstruction.py`, scoped and applied,
per explicit instruction):** `reconstruct_kolam` previously copied
`build_candidate_graph`'s motif contribution into the final candidate
UNCAPPED, then added residual deficit on top — so an over-explained pair
(two placements each independently touching it) ended up with MORE
strands in the reconstructed candidate than source has, even though
residual correctly added zero. Fixed: candidate now takes
`min(motif_contribution, source_multiplicity)` per pair, always; excess
is reported explicitly in the new `capped_excess` field, never silently
dropped. **Re-ran all 6 patterns with `check_self_consistency` — the
literal exit criterion — 6/6 True**, all fast (kolam109#1: 1.3s,
kolam109#26: 11.6s — `diagnose_validity`'s O(k²) matching, which hung
10+ min on kolam109 two sessions ago, never triggers post-fix, since the
candidate now always exactly equals source, always already valid, so its
odd-degree list is always empty — verified with actual timing, not
assumed; no approximate-matching workaround was needed this time).
Verified separately: 0 "phantom" edges (motif claiming a pair source
lacks entirely) across all 4 non-kolam109 patterns checked — the fix
only ever caps excess, never removes a real edge. 1 new regression test
(`test_reconstruction_caps_over_explained_motif_strands`).

Tests: 103 → 104. All green, zero regressions.

## Open tasks (session 9, carried forward)
1. Relabeling done this session (session 10, Item 1): historical recall/
   compression numbers now explicitly say "distinct-edge." Re-measurement
   with a multiplicity-aware metric is Item 2, same session, still to do.
2. Task A (real Wikimedia photo test) and Task B (kolam29 dense-detection
   root-cause + fix) are STILL not done — carried forward again, not
   newly discovered.
3. `induce_motif_set`/`induce_motif_set_adaptive`'s own coverage
   accounting (not just `reconstruct_kolam`'s consumption of it) still
   has the identity-only property described above — only
   `reconstruct_kolam`'s specific over-explanation symptom was fixed
   this session, not the upstream root cause in `motifs.py` itself.
4. `feature/generation-pipeline` branch still not merged to master (9
   commits now).

## Session 8 summary (M3.6 multiplicity-aware selection + M3.7 novel generation + M3 Gate)
Full M3 program now complete and stopped at the gate, per instructions
(NOT proceeding to ML without this report existing first).

**M3.6** (`engine/motif_selection.py`, `docs/MOTIF_SELECTION.md`): fixes
the over-explanation bug M3.5 exposed. `induce_motif_set_multiplicity_aware`
structurally guarantees `accumulated[e] <= source[e]` for every edge
(never a heuristic) by rejecting, never clipping, any candidate stamp
that would exceed source's real per-edge strand count.
`induce_motif_set_eulerian_aware` adds parity-improvement scoring on top
of the same hard constraint. Measured on the same 6-pattern set as M3.5:
mode A (old, unmodified) over-explains an average of 988 edges/pattern;
modes B/C have zero, always. Real design bug found and fixed during
development (see module docstring): per-individual-point scoring made
every fresh motif type score negative on its lone first instance since
the rule cost wasn't yet amortized — fixed by scoring at the motif-TYPE
level while still filtering multiplicity per individual point within an
accepted group. Structural consequence found and verified (not assumed):
because B/C guarantee no over-explanation, motif+residual reconstruction
built from either ALWAYS reaches exact multiplicity match with source
(verified on 4/6 patterns) — meaning "motif+residual valid" cannot
distinguish B from C at all; the meaningful comparison is motif-ONLY
behavior (odd-degree count: A=596 avg, B=557, C=344 — C wins on every
single pattern).

**M3.7** (`engine/novel_generation.py`, `docs/NOVEL_GENERATION.md`):
genuinely distinct from reconstruction, enforced at the type level —
`select_novel_placements` never receives a source graph at all, so there
is nothing to copy a residual from, even by accident (verified directly:
`reconstruct_kolam(source, [])` still reproduces source exactly via
residual; `generate_novel_kolam` on the identical layout with a library
from that same source does not). Real bootstrap bug found and fixed:
reusing M3.6's `_parity_delta` directly made every layout's first-ever
edge score negative (a degree-0 node's first edge always "looks like"
breaking even parity under that function's semantics) — n_edges=0 on
every test until a dedicated `_novel_score` was written that treats a
first-ever touch as pure growth, not a tradeoff. 5-candidate evaluation
(`validate_novel_generation.py`): 0/5 valid, 0/5 fully connected, 0/5
duplicate their source pattern (strict edge-multiset check, explicitly
NOT a claim of artistic novelty) — reported plainly as the honest
current ceiling of a small (8-12 motif), single-source, no-lookahead
greedy library.

Tests: 93 → 103 (13 in `test_motif_selection.py`, 10 in
`test_novel_generation.py`). All green, zero regressions across the
whole M3.6/M3.7 addition.

**M3 GATE**: see the session's final chat report for the full 6-question
answer (discover motifs? reconstruct known Kolams? generate valid novel
candidates? how often valid? major limitations? what's available for
ML?). Short version: motif discovery and reconstruction both work and
are well-measured; novel generation runs correctly end-to-end but does
not yet reach validity (0/5 in the evaluation set) — this is the honest
state M4 would need to either accept as a baseline to beat, or address
structurally before ML entry.

## Open tasks (session 8, carried forward)
1. Novel generation validity is 0/5 — no connectivity-seeking strategy,
   small single-source libraries, no backtracking. The gate does not
   require 100% validity to proceed to ML (per the task's own M4
   readiness checklist), but this number should not be quietly assumed
   to have improved without re-measuring.
2. `select_novel_placements`/`induce_motif_set_multiplicity_aware`'s
   group-then-filter design has a known scoring subtlety (a group's
   value is judged on its full point list's potential even though some
   points get filtered post-hoc) — see docs/MOTIF_SELECTION.md.
3. M4 readiness checklist (from the task's own instructions) has NOT
   been explicitly walked item-by-item against current repo state in
   this session — do that first in any session considering M4 entry,
   don't assume the gate items are satisfied just because M3 finished.
4. `feature/generation-pipeline` branch still not merged to master (6
   commits now) — merge or continue on it, don't fork a parallel branch.

## Session 7 summary (M3.5 — real-data reconstruction, NOT novel generation)
New: `engine/reconstruction.py` — `reconstruct_kolam(source, placements,
residual_policy="exact")` (motif-only candidate, via the unmodified
`build_candidate_graph`, + the EXACT deficit of source edges no
placement explained, copied back verbatim with correct multiplicity;
explicitly NOT novel generation — dot layout is always
`source.dot_points`, residual is always real source edges) and
`motif_only_report` (the honest contrast baseline, reusing
`generate_kolam` unchanged + edge-recall measurement). `docs/RECONSTRUCTION.md`
documents the three-way distinction (motif explanation / reconstruction
/ novel generation) and states explicitly that motif+residual
reconstruction is NOT novel generation.

**Real finding, measured across all 6 requested patterns (kolam19/29/109
× {1, 26}), consistent at every scale**: motif-only is always
disconnected and invalid (41-800 components). Motif+residual always
reaches full connectivity (1 component) AND 100% distinct-edge agreement
with source — the residual mechanism works exactly as designed. But
motif+residual is **still Eulerian-invalid on all 6 patterns**, because
of a previously-undiscovered mechanism: overlapping motif windows can
stamp a dot pair MORE times than source actually has ("over-explanation")
-- residual only ever ADDS missing strands, never removes excess ones.
Concretely: kolam109 #1 goes from 1736 odd-degree nodes (motif-only) to
1528 (motif+residual) but never to 0; total strands end up 16248 vs
source's 12992 (+3256 excess). Documented in RECONSTRUCTION.md as a
known limitation, not silently fixed (task explicitly deferred motif-
discovery optimization to a future session).

**Scalability finding, discovered while running the experiment, not
theorized**: `diagnose_validity`'s odd-vertex matching is O(k²)
shortest-path computations. At kolam109 scale k reaches 1500+ — a first
attempt at the full `reconstruct_kolam` pipeline on kolam109 was killed
after 10+ minutes of CPU time with no result. `validate_reconstruction.py`
works around this by computing the same required fields via the same
real engine functions minus that one diagnostic call — not a different
algorithm, just skipping an optional field this experiment doesn't need.
The full pipeline (with diagnosis) remains correct and tested at
kolam19-scale. **Optimizing `diagnose_validity` for large k is
unaddressed — flag before running it unconditionally on a kolam109-scale
graph in a future session.**

Tests: 70 → 80 (10 new in `tests/test_reconstruction.py`: exact
reconstruction of a known synthetic pattern, motif-only disconnection,
residual restoration, multiplicity preservation, Eulerian validity after
restoration, non-mutation of source pattern and motifs, determinism,
motif-only vs. reconstruction stay distinguishable, unsupported
`residual_policy` raises, real-pattern dot-layout consistency). All
green, zero regressions.

## Open tasks (session 7, carried forward)
1. Over-explanation is unaddressed: reconstruct_kolam's residual step
   only adds missing strands, never removes excess ones from overlapping
   motif windows. This is THE blocker for ever reaching full validity via
   this decomposition, on every pattern tested, not just an edge case.
2. `diagnose_validity`'s O(k²) matching does not scale to kolam109-size
   odd-vertex counts (1500+) — needs either an algorithmic fix or a
   documented size guard before it's called unconditionally again on
   large graphs.
3. Novel generation (motifs on an unseen dot layout, no residual
   fallback) is still fully unstarted — and per this session's findings,
   attempting it before fixing over-explanation would likely fail for
   the same underlying reason reconstruction still fails.
4. `feature/generation-pipeline` branch is pushed but not merged — merge
   or continue building on it, don't start a parallel branch by mistake.

## Session 6 summary (structural generation, Phase 2 — NOT ML, NOT image generation)
New: `engine/generated_kolam.py` (`GeneratedKolam` — deliberately separate
from `KolamPattern`, since a generated candidate has no CSV provenance to
report honestly; see docs/GENERATION.md for the full reasoning).
`engine/generation.py` extended (unmodified `apply_motif` preserved) with
`build_candidate_graph`, `reconstruct_dot_trace`, `generate_kolam` — the
full pipeline: `MotifPlacement` rules (the exact type induction already
returns) + a dot layout -> candidate `nx.MultiGraph` (edges added one at
a time, never `compose`, so multiplicity across DIFFERENT placements
targeting the same pair can't be silently collapsed) -> unconditional
`check_validity`/`diagnose_validity` -> (only if valid) deterministic
`nx.eulerian_circuit`/`eulerian_path` traversal to an ordered dot trace.
`validity.py`'s dispatch extended to also accept `GeneratedKolam`
directly (`check_validity(candidate)` works like `check_validity(pattern)`
already did). Trace reconstruction is DOT-LEVEL ONLY — half-integer
loop-around point reconstruction was explicitly deferred (not
justifiable from graph topology alone: the same dot pair can be
double-stranded with one strand on each side of a skipped dot, so which
side isn't determined by the graph — see DATA_FORMAT.md's own concrete
example). `docs/GENERATION.md` documents the objective, API, construction,
multiplicity, validation, trace-reconstruction, and limitations, with a
worked synthetic example.

**Real-data experiment finding (honest, not adjusted to look better)**:
feeding kolam19 pattern 26's 8 MDL-gated-induced motifs into
`generate_kolam` on the source pattern's own 200-dot layout produced an
**invalid** candidate — 32 connected components, 12 odd-degree nodes, 6
corrections needed (228/276 distinct edges, 324/360 strands recovered).
This is the expected consequence of MDL-gating stopping once no further
motif pays for itself (by design, from session 4) — it does not
guarantee coverage or connectivity, and `generate_kolam` does not
currently compensate for that gap (e.g. by falling back to the
induction's own `residual` edge list). This is a real, exposed
limitation for the next session to pick up, not a bug in this session's
work.

Tests: 60 -> 70 (10 new in `tests/test_generation.py`, covering
determinism, the known-valid synthetic case, multiplicity preservation,
D4 placement, overlapping-motif accumulation, invalid-candidate
rejection, `check_validity` agreement, deterministic traversal, and
non-mutation of both source motifs and a real loaded `KolamPattern`).
All green, zero regressions, no existing test modified.

## Open tasks (session 6, carried forward)
1. Loop-around / half-integer trace reconstruction — explicitly deferred,
   not started. Needs a real geometric rule (not just graph topology) to
   pick a side; DATA_FORMAT.md's existing double-strand example shows why
   topology alone is insufficient.
2. Generation currently has no gap-filling / residual-edge fallback for
   partial motif coverage — this is why the kolam19 #26 real-data
   experiment came back invalid. Not attempted this session (task
   explicitly said "do not optimize yet").
3. No motif selection/search/diversity strategy exists — `generate_kolam`
   builds exactly what it's given, in order. Choosing good motifs for a
   target output is future work, explicitly out of scope this session.

## Session 5 summary (canonical KolamPattern data model)
New: `engine/kolam_pattern.py` (the `KolamPattern` dataclass — the single
canonical representation: pattern_id, collection, raw_trace, trace_points,
dot_points, edges, edge_multiplicity, graph, bounding_box) and
`engine/dataset.py` (`load_kolam(collection, pattern_id)` /
`load_dataset(collection)` — the ONE loader; owns all CSV-specific
interpretation, delegates the actual dot/edge extraction to
`graph_io.extract_dot_sequence`/`dot_sequence_to_multigraph`, doesn't
reimplement them). `docs/DATA_FORMAT.md` documents the CSV format from
fresh direct inspection (not memory) — every row is one trace step for
ALL patterns in that file at once, zero missing values anywhere, dots =
both-integer trace points, loop-around = exactly-one-half-integer trace
points (never both), edges only ever span Chebyshev distance 1 or 2,
double strands are real (verified concrete example) not data noise.
`validity.py`, `motifs.py` (`induce_motif_set`, `induce_motif_set_adaptive`),
`symmetry.py` (new `analyze_symmetry`) now all accept a `KolamPattern`
directly as well as a raw `nx.MultiGraph` (isinstance dispatch added at
each function's top, zero changes to algorithm bodies) — fully backward
compatible, all pre-existing call sites and tests unchanged. `generation.py`
was NOT touched (out of scope — no generation work this session).
New: `inspect_kolam.py` (`--collection --pattern` CLI debugging tool),
`tests/test_kolam_pattern.py` (19 new tests). Test count: 41 -> 60, all
green, zero regressions. Also noted: this task described the test count
as "28" at its start — that was stale even before this session (actual
was already 41 from session 4); used 41 as the real regression baseline
instead of trusting the stated number.

**File-location history (superseded, kept for context):** this file
started as `docs/projectState.md`. A session-4 search for
`PROJECT_STATE.md` (root, underscore) missed it and created a redundant
duplicate, later reconciled back into `docs/projectState.md`. As of
session 9, that entire history is closed: this file was ALSO discovered
to be gitignored the whole time (blanket `*.md` rule, `.gitignore` line
5), which is very likely why it kept going unnoticed/duplicated in the
first place. Both problems are now fixed together: the file lives at
`PROJECT_STATE.md` (repo root) and is explicitly un-ignored and
git-tracked (`.gitignore` now has a `!/PROJECT_STATE.md` exception). This
is now the ONLY location this file should ever be written to — if a
future session's instructions suggest writing project state anywhere
else (`docs/`, a new root file with a different name, etc.), that should
be flagged and refused, not followed.
 
## What this project is
SIH12507 (AICTE): identify the design principles behind Kolam patterns and recreate them.
Product shape: upload a Kolam image → system infers the generating rule (motif + symmetry +
single-stroke structure) → proves the rule is correct → generates new valid Kolams from it.
Two halves: **Analyzer** (image → rules) and **Generator** (rules → new pattern). Everything
built so far is the Analyzer half's backend mathematics — no UI yet.
 
## Architecture (as built)
```
/engine
  graph_io.py     — CSV → nx.MultiGraph normalizer (Kaggle dataset format)
  image_io.py     — photo/image → nx.MultiGraph (NEW, this session)
  motifs.py       — local_window, induce_motif, induce_motif_set (greedy set-cover),
                    induce_motif_set_adaptive (multi-radius retry), MDL-gated acceptance
  symmetry.py     — D4 canonicalization (4 rotations x 2 reflections)
  generation.py   — apply_motif (regenerate / extend to new grid sizes)
  validity.py     — check_self_consistency (exact match), check_validity (hard Eulerian
                    gate, unmodified), diagnose_validity (graded companion, session 4)
/tests            — 41/41 passing as of session 4
generate_synthetic_photos.py         — renders CSV patterns as degraded synthetic photos
                                        (proxy for real photographs; NOT real photos) —
                                        the original TUNED 7-image set
generate_synthetic_photos_heldout.py — session 4: 8 NEW images, different kolam numbers,
                                        different seed range, same generator/detector code
validate_real_data.py, validate_adaptive.py, validate_mdl.py  — CSV-side measurement scripts
validate_image_io.py   — image-pipeline accuracy, now takes a photo_dir argument (works on
                          either synthetic_photos/ or synthetic_photos_heldout/)
validate_diagnose.py   — session 4: diagnose_validity correction sizes across all 15 photos
sample_corpus_dots.py  — session 4: dot-marker presence check across the bundled corpus
```
 
## Critical design decision, stated once so it doesn't get re-litigated
**No ML/CNN anywhere in the core engine.** Lattice detection, motif matching, symmetry,
validity checking are all deterministic graph theory / classical CV. This was a deliberate
choice, not a gap. Only genuinely open question on this front: whether image-derived
low-confidence regions eventually want a learned confidence score layered on top — not yet
needed, not yet built.
 
## The self-correction discipline (say this explicitly in the pitch)
Four separate times, a number or check was trusted, then caught being wrong by testing it
against itself, then fixed:
1. **Eulerian gate**, early on: a hand-built synthetic test generator produced a pattern that
   FAILED its own single-stroke validity check (2 disconnected components, odd-degree
   vertices from dangling boundary edges). Conclusion: don't hand-tune synthetic ground
   truth — use real, pre-verified data instead (→ pivoted to the Kaggle dataset).
2. **Compression ratio formula**: originally divided total edges by one motif's size,
   silently assuming 100% coverage at zero placement cost. With real distinct-edge recall
   at 28%, the reported 164x distinct-edge compression ratio was fiction. Fixed to
   `raw_size / (motif_rules + placements + residual_edges)`, consistent edge-identity basis.
   (All "recall"/"compression ratio" figures in this section are DISTINCT-EDGE metrics —
   see the relabeling note under "Real measured numbers on record" below.)
3. **Coverage-vs-compression conflation**: adding motifs to maximize distinct-edge recall
   (via a `max_motifs_per_radius` count cap) was implicitly treated as the same objective as
   minimizing description length. It isn't — adaptive multi-radius induction won on
   distinct-edge recall (89.7%→99.5%) but LOST on distinct-edge compression on 15/15 patterns
   (1.82→1.64). Fixed by replacing the count cap with MDL-gated acceptance (add a motif only
   if it has positive net description-length gain) — this landed at 90.3% distinct-edge
   recall, 2.40x distinct-edge compression (better than both priors on compression), with
   6/15 patterns getting slightly LOWER distinct-edge recall than the old greedy version,
   correctly, because the gate refuses trades that don't pay for themselves. Proven with a
   dedicated test (`rejects_expensive_one_off_despite_recall_gain`).
4. **Image-pipeline validity gate mismatch**: even near-perfect image reconstruction
   (>94% edge recall) fails the strict Eulerian gate on 4/7 synthetic photos, because parity
   is fragile to 1-2 multiplicity errors. Motif induction degrades gracefully on the same
   imperfect input (0.885→0.744); the hard gate does not. **Fixed in session 4**:
   `diagnose_validity(G)` added to validity.py as an unmodified companion to the strict
   `check_validity` gate — Route Inspection Problem correction (odd-degree vertices,
   minimum-weight matching via shortest-path distance, `nx.min_weight_matching`), reporting
   exactly which nodes/edges are implicated. Run against all 15 synthetic photos (7 tuned +
   8 held-out, see below): 10/15 fail the strict gate, but the correction size is **not**
   uniformly small — it splits sharply by pattern density. kolam19 (sparse) failures average
   1.2 corrections (max 3): small, localized, genuinely supports "the gate was the wrong
   tool for this data" for that density class. kolam29 (dense) failures average 53.0
   corrections (max 62), touching ~25-28% of all nodes: NOT small or localized — a real
   reconstruction gap, not just gate oversensitivity. **Do not claim "the gate is just too
   strict" as a blanket statement — it's true for kolam19-scale patterns, false for
   kolam29-scale ones.**
## Real measured numbers on record (all checked per-pattern, not just averaged)
| Metric | Value | Source |
|---|---|---|
| CSV-based motif induction, MDL-gated: avg DISTINCT-EDGE recall (not multiplicity-exact — see note below) | 90.3% | validate_adaptive.py + MDL gating, 15 patterns across kolam19/29/109 |
| CSV-based, MDL-gated: avg DISTINCT-EDGE compression ratio (not multiplicity-exact — see note below) | 2.40x | same run |
| CSV-based, MDL-gated: motifs needed | 19.6 avg | same run |
| Image pipeline, dot detection (TUNED set, 7 photos) | precision 0.9997 / recall 0.9803 | generate_synthetic_photos.py, kolam19_k1/2/3/27/50 + kolam29_k1/2 |
| Image pipeline, edge tracing, exact-multiplicity (TUNED set) | precision 0.9758 / recall 0.9487 | same 7 photos |
| Image pipeline, dot detection (HELD-OUT set, 8 new photos, session 4) | precision 1.0000 / recall 0.9413 | generate_synthetic_photos_heldout.py, new kolam numbers, seed 7000+, detector code UNCHANGED |
| Image pipeline, edge tracing, exact-multiplicity (HELD-OUT set) | precision 0.9234 / recall 0.8825 | same 8 photos |
| — held-out degradation is concentrated in kolam29 (dense) patterns | kolam19 held-out ≈ tuned-set numbers; kolam29_k50 outlier: dot recall 0.752 | see below |
| Corpus sampling: bundled JPGs with visible dot markers | 0/30 (0%) | sample_corpus_dots.py, 10 each kolam19/29/109, seed 42 |
| Real dataset validity gate pass rate (CSV source) | 100% (15/15) | expected — dataset is pre-verified |
| Real (non-CSV) bitmap test, kolam19-26.jpg | FAILED — 88/227 odd-degree nodes | no visible dot markers — now known to be the NORM for this corpus, not an outlier |
| diagnose_validity correction size, kolam19 (sparse) failures | avg 1.2, max 3 | 10/10 kolam19 photos across both batches |
| diagnose_validity correction size, kolam29 (dense) failures | avg 53.0, max 62 (~25-28% of nodes) | 5/5 kolam29 photos across both batches |

**Resolved this session (session 4) — do not re-run these as if still open:**
- Held-out validation: done. Real, moderate, density-concentrated degradation confirmed
  (not catastrophic, not zero — see table above). Tuning-on-test-set risk was real but
  modest, and specific to the denser pattern class.
- Corpus sampling: done, decisively. 0/30 sampled bundled JPGs have visible dots, no
  exceptions across all 3 families. The entire "Images" corpus is line-only matplotlib
  renders (matches plot_kolam.py's own rendering code — no markers drawn).
- `diagnose_validity`: built, tested (3 dedicated tests), run against all 15 synthetic
  photos. Density-dependent finding above.

## Open tasks (check status at start of next session — may or may not be done)
1. Dot-marker-optional fallback mode for image_io.py — now a real priority, not
   hypothetical: the corpus sampling result above means this is needed for essentially
   ANY use of the bundled Images corpus as a real-image test source, not an edge case.
2. Improve dense-pattern (kolam29-scale, ~13px dot spacing) detection specifically — this
   is now the identified actual weak point (held-out numbers + diagnose_validity both point
   here), not the pipeline generally.
3. Still fully open, not started: any user-facing interface (Streamlit per the 12-hour plan,
   or React+FastAPI per the 60-day plan); wiring generation into a full "here's your new
   Kolam" user flow; a real (non-synthetic, non-dataset) photographed test image, which
   nobody has been able to test against yet — still the single largest untested risk.
## Reference documents already produced (should exist in the repo or chat history)
- War Room engineering report (full A-Z analysis, math formulation, algorithm comparison)
- 12-hour MVP implementation plan (Streamlit, local-first, no backend)
- 60-day production plan (React+FastAPI+Postgres, week-by-week)
- Product overview + feature roadmap (Tier A/B/C future features)
- Differentiation pitch vs. KolamNet/KolamNetV2 (classification-only) and the GAN-based
  Hugging Face tool (no correctness guarantee) — the core claim is: infer backward to the
  rule AND prove it's correct, which neither existing approach does.
## The one-sentence status if asked "where are you"
The core induction engine is done and rigorously validated on real dataset data (41 tests,
four self-caught-and-fixed bugs, MDL-gated motif selection). The image-input pipeline is
built and held-out-validated: ~90-100% accuracy on sparse (kolam19-scale) synthetic photos,
meaningfully lower and more variable on dense (kolam29-scale) ones — a real, now-measured
weak point, not a guess. The bundled dataset's own JPGs are confirmed (30/30 sampled) to have
no visible dot markers, so a dot-optional fallback is now a known real requirement, not a
hypothetical. Zero user interface exists yet. The single biggest untested risk remains a real
(non-synthetic, non-bundled) photograph — still nobody has tried one.
 