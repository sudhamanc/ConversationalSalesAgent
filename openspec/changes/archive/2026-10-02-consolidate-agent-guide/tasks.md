# Tasks: Remove BootStrapAgent and Move the Agent Service Guide into README

- [x] 1.1 Guide content moved into README ("Agent Service Guide", sections 1-10); `agent.py` template updated to `agent_model()`, env table adds `MODEL_REQUEST_TIMEOUT_MS` and MCP URLs; docs/agent-service-guide.md deleted
- [x] 1.2 BootStrapAgent/ deleted (not in services.conf, compose, setup or deploy)
- [x] 1.3 34 files repointed; `git grep` finds no live references (archived OpenSpec changes and the historical CustomerCommunicationAgent/IMPLEMENTATION_SUMMARY.md excluded)
- [x] 1.4 tests/test_baseline_doc.py, evals offline and SuperAgent tests pass (112 passed)
