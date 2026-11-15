# Tasks: Fix catalog image model permissions

## 1. Service

- [x] 1.1 `services/catalog/Dockerfile`: `chmod -R a+rX /app/models` after the model is staged. Verify: deploy the catalog (`scripts/deploy_cloud.sh --only catalog --skip-migrate`); an FAQ turn on Cloud Run is answered from FAQ passages, and its Langfuse `search_faq` output shows `available: true`.

## 2. Close

- [x] 2.1 `openspec validate fix-catalog-model-permissions` passes. Commit, then archive.
