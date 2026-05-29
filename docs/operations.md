# Operations Runbook

This runbook captures the one-time migration from the current GitHub Actions
`mkdocs gh-deploy` flow to a versioned docs pipeline driven by
[`mike`](https://github.com/jimporter/mike). It is intended for the maintainer
to execute manually when v0.4.0 is ready to ship. ADR-0004 and ADR-0005 record
the rationale.

## Pre-flip checklist

- `mike` is installed as a dev dependency (added in Phase 5; verify with `uv run mike --version`).
- v0.4.0 release is staged: tag-triggered deploys pair best with a real version cut.
- ADR-0004 (docs hosting) and ADR-0005 (release process) reference this migration.
- Working tree is clean and `main` is up to date with `origin/main`.

## Switch GitHub Pages source

Flip Pages from "GitHub Actions" to "Deploy from a branch" (`gh-pages`, `/`).

Using the `gh` CLI:

```bash
gh api repos/jovandyaz/cenote/pages -X DELETE 2>/dev/null || true
gh api repos/jovandyaz/cenote/pages -X POST -f source[branch]=gh-pages -f source[path]=/
```

UI alternative: **Settings > Pages > Source > Deploy from a branch**, select
`gh-pages` and `/` (root), then **Save**.

## Rewrite `.github/workflows/docs.yml`

Replace the current `mkdocs gh-deploy` job with a `mike`-driven workflow:

- On push to `main`: deploy the rolling `dev` alias.
- On tag push matching `v*`: deploy the concrete version and update `latest`.

```bash
# On push to main
uv run mike deploy --push --update-aliases dev

# On tag push (v*)
uv run mike deploy --push --update-aliases "${version}" latest
```

The `mike` plugin block in `mkdocs.yml` is intentionally **not** added yet; add
it in the same PR that rewrites the workflow so previews stay coherent.

## Bootstrap the `gh-pages` branch

After the Pages source has been switched, seed `gh-pages` once so the alias and
default version exist before the first tag-triggered run:

```bash
uv run mike deploy --push 0.3.0 latest
uv run mike set-default --push latest
```

Subsequent deploys (manual or via CI) will publish into the same branch.

## Rollback procedure

If the new pipeline misbehaves, restore the previous GitHub Actions-based flow:

```bash
gh api repos/jovandyaz/cenote/pages -X DELETE
gh api repos/jovandyaz/cenote/pages -X POST -f build_type=workflow
git restore .github/workflows/docs.yml
```

Then revert the `mkdocs.yml` `mike` plugin block (if it was added) and push to
`main`. Pages will rebuild from the workflow artifact on the next run.
