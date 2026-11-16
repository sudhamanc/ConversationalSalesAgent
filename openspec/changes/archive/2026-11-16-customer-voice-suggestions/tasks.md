# Tasks: Customer-Voice Suggested Next Steps

## 1. Gateway (`SuperAgent/server`)

- [x] 1.1 Add `api/suggestion_playbook.py` (`journey_stage`, `PLAYBOOK`, `reply_template`, `asks_customer`, `validate`, `finalize`). Verify: `pytest SuperAgent/tests/test_suggestions.py -q` covers every stage, each reply topic, and the validator's reject and keep cases.
- [x] 1.2 Rewrite `api/suggestions.py`: customer-voice prompt with the contract, stage, known and missing facts, and the head and tail of the reply; the parsed output is passed through `finalize`; the playbook is used on failure. Verify: tests assert that the prompt contains the reply's closing question and the stage, that rep-voice model output is replaced, and that an exception still yields 3 chips; `tests/test_tracing.py` still passes.
- [x] 1.3 `api/chat.py`: read the session state after the turn, pass it to `generate_suggestions`, and use the provisioning playbook instead of `_ACTIVATION_SUGGESTIONS`. Verify: `pytest SuperAgent/tests -q`.

## 2. UI (`SuperAgent/client`)

- [x] 2.1 Add `src/utils/placeholders.js` (`findPlaceholder`, `hasPlaceholder`). Verify: a node script asserts next, wrap-around and none.
- [x] 2.2 `ChatInput.jsx`: select the placeholder on pre-fill, Tab or Enter moves to the next, send is blocked while placeholders remain, with a hint. Verify: `npm run build` ✓; manual browser check on the GCP deploy.
- [x] 2.3 `SuggestionCard.jsx`: pencil marker on template chips (Tailwind only). Verify: `npm run build`.
- [x] 2.4 Rewrite `src/utils/suggestions.js` fallbacks in customer voice (no "…to customer", no filler). Verify: grep finds no `customer"`/`Continue` chips; `npm run build`.

## 3. Docs

- [x] 3.1 Update the `suggestions` description in `openspec/BASELINE.md` §5, `SuperAgent/README.md` and `SuperAgent/client/AGENTS.md`. Verify: `pytest tests/test_baseline_doc.py -q`.

## 4. Evals

- [x] 4.1 ~~Run `scripts/eval.sh`~~ Skipped by user decision (no billed Gemini requests). Suggestions are not scored by any eval tier, and no agent or router prompt changed; mocked suites cover the behavior (`pytest SuperAgent/tests -q`: 81 passed).
