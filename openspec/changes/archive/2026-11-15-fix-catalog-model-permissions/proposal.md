# Proposal: Fix catalog image model permissions

## Why

On Cloud Run, the catalog's knowledge and FAQ searches return `available: false`. The error is `embedding model '/app/models/all-MiniLM-L6-v2' could not be loaded: No such file or directory: .../model.safetensors`. As a result, the FAQ agent can only answer "let me check with our specialist team". Found through the Langfuse trace of a GCP FAQ turn (2026-11-15). The image saves the model as root at build time. Current sentence-transformers/safetensors writes `model.safetensors` with mode 0600, and the container runs as user `app`, so at runtime the weights cannot be read. The index itself builds correctly (136 product chunks, 31 FAQ chunks).

## What Changes

- `services/catalog/Dockerfile`: after staging the model and building the index, make `/app/models` readable by everyone (`chmod -R a+rX`), next to the existing `chown` of `/app/data`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `product-catalog-service`: knowledge search works in the container image as a non-root user (a new scenario under "FAQ knowledge search").

## BASELINE.md sections affected

None.

## Non-goals

- Changing the embedding model, the index build or the degraded-mode behavior.

## Impact

- **Services:** catalog image only. **Agents:** the FAQ and product agents get their RAG results on Cloud Run and in compose. **APIs, data, scripts, docs:** none.
