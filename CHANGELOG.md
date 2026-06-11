# 0.3.0

 - **Breaking:** renamed the aldeia importer `import_timor_geo_data_2022` →
   `import_timor_geo_data_aldeias`. The old name implied 2022 data; the command
   has loaded the INTL 2024 boundaries since 0.2.0. Update any deploy scripts.
 - Renamed the data file `aldeias_2022.gpkg` → `aldeias_2024.gpkg` (and its
   internal layer) to reflect that it holds the INTL 2024 aldeia boundaries, not
   2022 — the geometries and codes come straight from the INTL 2024 source.
 - Removed the stale, unused `Admin_Aldeia2022.csv` (superseded 2022 data,
   referenced nowhere).
 - **Fix:** `import_timor_geo_data` and `import_timor_geo_data_aldeias` now compose
   when run in sequence. Suco pcodes come from `sukus.gpkg`; aldeias link via
   `SucoIndex` (trust matching `NewSucoCod` when names agree, else spatial
   containment). Hierarchy upserts key on `pcode` only. When sucos are already
   loaded, the aldeia importer skips re-creating the hierarchy. Audit:
   `timor_locations/data/crosswalk/aldeia_suco_pcode_remap.csv`.

# 0.2.0

 - Re-keyed onto the INTL ("New*Cod") scheme: `pcode` is now a `CharField` PK
 - Migration 0008 flushes the area tables before the type change (re-import after)
 - Added the `sync_provider_geo` reconciliation pipeline (INTL 2024 boundaries)
 - Added a `ProviderCode` table (per-scheme code bridge) + `load_provider_codes`;
   replaces the single-column legacy code. See the README 0.2.0 notes for details.

# 0.0.5

 - Bugfix for municipality name

# 0.0.4

 - Added municipality and admin post names to 'Suco' to avoid lookups

# 0.0.3

- Requirements made with poetry 1.5.0
- Added "pcode"
- Installed "geojson" from github main for Py 3.12 support
- Fixed a typing bug which broke the API page


# 0.0.2

 - Topology added

# 0.0.1

 - Initial release