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

### 0.1.0

**Re-keyed onto the INTL ("New*Cod") code scheme.** `pcode` is now a `CharField`
(was integer) holding the official INTL code — `NewSucoCod` / `NewPostAdC` /
`NewMunCode` / `NewAldCode`, zero-padded strings (e.g. suco `010106`). This:

- gives **every** entity a real code from the source (no minted/NULL codes); the
  data is **466 sucos / 70 posts / 14 municipalities / 2238 aldeias**, all current
  INTL 2024 boundaries, with re-parenting baked in as INTL's own structure;
- **unifies the two import tracks** — `import_timor_geo_data` (sucos) and
  `import_timor_geo_data_2022` (aldeias) now produce the *same* INTL-keyed sucos —
  and fixes a latent leading-zero bug (codes like `08050104` no longer truncated by
  an `IntegerField`);
- adds a nullable `legacy_pcode` for traceability; the committed
  `suco_crosswalk.csv` is the legacy→INTL bridge for downstream migration.
- **Migration note:** the model PK type changes int→str — downstream consumers
  that store/compare the pcode value must migrate (see the partisipa-import
  coordination). The importer is idempotent (upsert by INTL code) and re-runnable.

Also includes the Django-4.2 importer fix (see 0.0.9) and the reusable
`sync_provider_geo` pipeline. Known gap: suco **Beduku** (Liquiçá/Bazartete) is
absent from the INTL 2024 source and is not yet included.

### 0.0.9

- Fixed `import_timor_geo_data` / `import_timor_geo_data_2022` for **Django 4.2+**:
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
