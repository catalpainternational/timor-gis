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

### 0.0.9

- Fixed `import_timor_geo_data` / `import_timor_geo_data_2022` for **Django 4.2+**:
  the upserts now use the plain base manager instead of the annotated
  `GeoDataManager`, avoiding `FOR UPDATE cannot be applied to the nullable side of
  an outer join` (the manager annotates a nullable FK join that the
  `update_or_create` / `get_or_create` locking SELECT can't lock). Data unchanged.
- Reconciled the suco dataset against the **INTL 2024** boundary set (via PNDS):
  442 -> **466 sucos** (15 JDR 2025/26 sub-divisions + 12 previously-missing
  sucos), all boundaries refreshed, **6 new admin posts** (Matebian, Quelicai
  Antigo, Hatulia B, Loes, Lore, Barique), and ~87 sucos re-pointed to their
  correct current admin post. Stable pcodes preserved throughout.
- Refreshed `aldeias_2022.gpkg` from the INTL 2024 aldeia layer (2230 -> **2238
  aldeias**: 214 added, 206 superseded, 46 re-parented), incl. the aldeias under
  the new sucos. The aldeia track is already on the INTL `NewAldCode` scheme, so
  this is an authoritative refresh keyed on `NewAldCode` (see
  `manage.py sync_provider_geo intl2024 --level aldeia`).
- Added the `sync_provider_geo` pipeline + versioned crosswalk (see above).
- Known gap: suco **Beduku** (Liquiçá/Bazartete) is absent from the INTL 2024
  source and is not yet included.

...


## Manually Uploading a new version to PyPi

Bump `pyproject.toml`
Then run `poetry build` and `poetry publish`

```bash
poetry build
poetry publish
```

See the file `build.yml` for the workflow
