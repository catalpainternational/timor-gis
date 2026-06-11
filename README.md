# Timor GIS

Timor Leste GIS data as Django models
This initial release uses administrative boundariew from Estrada, tweaked to include Atauro as a separate entity, with pcode which are intended to match existing data from PNDS.

Data inputs are stored as `gpkg` files in Git LFS.

## Syncing a new provider boundary drop

Provider datasets (Estrada, INTL/PNDS, ...) arrive in different CRS, field
schemas, code schemes, spellings and coverage. `sync_provider_geo` folds a drop
into the canonical importer data **without moving stable pcodes** (which exist to
match PNDS downstream). Suco identity is decided by *polygon overlap*, not names,
so respellings, re-parentings and duplicate names can't shift a code; anything
the provider introduces gets a freshly minted canonical code.

```sh
# 1. propose: reconcile against the current sukus.csv/gpkg, write the crosswalk + report
manage.py sync_provider_geo intl2024 --source /path/to/shapefiles --propose

# review timor_locations/data/crosswalk/sync_report.md; record any corrections
# in suco_overrides.csv (durable -- honoured verbatim on every re-run)

# 2. apply: regenerate sukus.gpkg + sukus.csv from the reviewed crosswalk
manage.py sync_provider_geo intl2024 --source /path/to/shapefiles --apply
```

`--apply` runs a hard **geographic guard** first: every suco must sit inside its
coded admin-post polygon, or the sync aborts. Provider configuration lives in
`timor_locations/sync/adapters.py`; the durable crosswalk + overrides + report
live under `timor_locations/data/crosswalk/`.

## Environment

This is intended to be compatible with:

- Django 4.1+
- Python 3.10+

```sh
gh repo clone catalpainternational/timor_locations
cd timor_locations
poetry install
```

### Development

 - When developing please install prerequisites with `poetry install --with dev --no-root`

### Pre Commit

If `pre-commit` is installed your code will be checked before commit.
This includes

- black
- flake8
- isort
- mypy

The same checks are run on push. See `pytest.yaml` for details on the checks being run.

### New Release

For a new release, change the `version` property in pyproject.toml and push a git tag with the version number

See `build.yaml` for details on release tagging

## Changelog

### 0.3.0

- Renamed aldeia importer and data file from 2022 → 2024 naming (see CHANGELOG).
- **Composable imports:** run `import_timor_geo_data` then
  `import_timor_geo_data_aldeias` on the same DB.
- **Suco pcode authority:** `sukus.gpkg` (`Suco.shp`) is canonical for suco pcodes
  and names. Aldeia `NewSucoCod` in `aldeias_2024.gpkg` is **not authoritative**
  when it disagrees — the upstream INTL aldeia layer is census-EA prep data and
  explicitly not official. There is no public MAE/INETL shapefile release with
  consistent `New*Cod` across suco and aldeia layers; legal admin boundaries live
  in ministerial diplomas (text annexes). Census geography used 452 sucos / 2231
  aldeias; this bundle has 466 / 2238.
- **Remapping:** 15 attribute-level pcode mismatches are audited in
  `timor_locations/data/crosswalk/aldeia_suco_pcode_remap.csv`. At import time the
  hybrid resolver (trust matching `NewSucoCod` when the aldeia `SUCO` name agrees,
  else spatial containment) may remap ~72 aldeia rows off stale aldeia-layer codes.
- When sucos are already loaded from `sukus.gpkg`, the aldeia importer **skips
  suco/admin-post/municipality geometry rollup** so suko polygons are not replaced
  by unions of aldeia polygons.

### 0.2.0

**Re-keyed onto the INTL ("New*Cod") code scheme.** `pcode` is now a `CharField`
(was integer) holding the official INTL code — `NewSucoCod` / `NewPostAdC` /
`NewMunCode` / `NewAldCode`, zero-padded strings (e.g. suco `010106`). This:

- gives **every** entity a real code from the source (no minted/NULL codes); the
  data is **466 sucos / 70 posts / 14 municipalities / 2238 aldeias**, all current
  INTL 2024 boundaries, with re-parenting baked in as INTL's own structure;
- re-keys onto INTL string pcodes (fixes a latent leading-zero bug — codes like
  `08050104` no longer truncated by an `IntegerField`); **0.3.0** makes the suco
  and aldeia importers composable on those codes;
- replaces the idea of a single `legacy_pcode` column with a `ProviderCode` table:
  every scheme an area has been coded in (Estrada, INTL 2024, future vintages) is a
  row, so adding a scheme is INSERTs not a schema migration, and splits/merges/
  renames are representable. Seed it from the committed `suco_crosswalk.csv` with
  `manage.py load_provider_codes`; look codes up with `code_for(area, scheme)`.
  The crosswalk currently bridges **sucos only** — posts/municipalities/aldeias are
  not yet mapped.
- **Migration note:** the model PK type changes int→str, and migration `0008`
  **flushes the four area tables** before the type change so no stringified-integer
  code can survive the re-key. Run order on an existing DB: `migrate` →
  `import_timor_geo_data` → `load_provider_codes`. Downstream consumers that store
  or compare the pcode value must migrate (see the partisipa-import coordination).
  The importer is idempotent (upsert by INTL code) and re-runnable.

Also includes the Django-4.2 importer fix (see 0.0.9) and the reusable
`sync_provider_geo` pipeline. Known gap: suco **Beduku** (Liquiçá/Bazartete) is
absent from the INTL 2024 source and is not yet included.

### 0.0.9

- Fixed `import_timor_geo_data` / `import_timor_geo_data_aldeias` for **Django 4.2+**:
  the upserts now use the plain base manager instead of the annotated
  `GeoDataManager`, avoiding `FOR UPDATE cannot be applied to the nullable side of
  an outer join` (the manager annotates a nullable FK join that the
  `update_or_create` / `get_or_create` locking SELECT can't lock). Data unchanged.

...


## Manually Uploading a new version to PyPi

Bump `pyproject.toml`
Then run `poetry build` and `poetry publish`

```bash
poetry build
poetry publish
```

See the file `build.yml` for the workflow
