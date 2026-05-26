# Diagrams

Native drawio (`.drawio`) XML files. Upload directly at <https://app.diagrams.net/> via **File → Open from → Device**, or drag the file into the canvas.

| File | What it shows |
|---|---|
| `01-ecosystem.drawio` | C4-style ecosystem map — cenote-core as the shared library, downstream products (knowtis-ai, cfdi-agent), end users, external integrations (Voyage / Cohere / pgvector today; Anthropic / Langfuse / DeepEval planned M1.1+). |
| `02-architecture.drawio` | Internal architecture — 5 layers (models, chunkers, embedders, stores, retrievers) plus M1.0 future-API stubs. Color-coded: blue = Protocol, green = impl, orange = data model, pink dashed = future stub. |
| `03-runtime-flow.drawio` | Sequence diagram of indexing path (green) and query path (blue), with batching, rate limiting, transactional upsert, and HNSW tuning visible. |

## How to render or edit

1. **drawio.com (recommended)**: <https://app.diagrams.net/> → File → Open from → Device → pick the `.drawio` file. Edit visually, export to PNG/SVG/PDF as needed.
2. **VS Code**: install the *Draw.io Integration* extension by Henning Dieterichs. Open the `.drawio` file in the editor — renders inline.
3. **Desktop app**: <https://github.com/jgraph/drawio-desktop/releases> — open the file directly.

## Updating

Each file is plain XML; you can edit in drawio's GUI and re-save as `.drawio` (not `.xml` — drawio uses `.drawio` for its native files even though the content is XML). Keep diagrams in sync with the codebase: if you add a new module under `src/cenote/`, update `02-architecture.drawio`.
