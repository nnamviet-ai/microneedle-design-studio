# Deployment preparation report

Prepared 22 October 2026 (Pacific/Auckland).

**Ready for upload as the public analytical edition.** No upload or cloud
deployment has been performed. The original project was left unchanged.

## Source and entry point

The existing project's entry point is `MICRONEEDLE_UI/app.py`. This independent
deployment's entry point is `app.py`. Upload this folder's contents to the
repository root and select Python 3.12 in Streamlit Community Cloud.

Files were selected explicitly; no recursive project/data copy was used.
The numerical engine, geometry generator, prediction figures, A/B modules and
design-space modules are byte-for-byte copies of the original. Changes are
limited to the app shell and predictor presentation, portable path resolution,
deployment configuration, dependencies, documentation and data-independent tests.

The public presentation removes workbook imports, recorded-data controls and
workbook-only presets. The source hash included in analytical JSON reports
resolves relative to this deployment rather than a machine-specific location.
No analytical equations, constants or numerical algorithms were changed.

## Local verification

- Fresh Python 3.12 virtual environment outside the upload folder: installation
  from `requirements.txt` succeeded; `pip check` found no broken dependencies.
- **25 tests passed** using `python -B -m unittest discover -s tests -v`.
  These include closed-form axial/bending/Euler limits, taper compliance,
  material and load-sharing scaling, geometry topology/dimensions, array pitch,
  A/B comparisons and state preservation, invalid inputs, one/two-axis sweeps,
  rejected combinations, export contents and candidate transfer.
- A copy of the app was run from an independent temporary directory, with no
  source project or data copied alongside it. The local server returned HTTP 200.
- Headless Chrome rendered the single-needle WebGL geometry, the 17-mesh array
  (16 needles plus illustrative base), A/B comparison and completed sweep.
  Geometry HTML downloaded successfully (4,835,419 bytes). No browser page errors
  or final Streamlit exception panels were observed.
- Screenshots were inspected for the functioning single-design page. Browser
  captures and raw test logs remain outside the upload folder because local
  diagnostic output can contain machine paths.
- Compatible Linux x86-64 / CPython 3.12 wheels were downloaded successfully for
  all five pinned direct dependencies. This checks package availability; the
  application has not been executed on Linux or Streamlit Community Cloud.

Pinned direct dependencies: Streamlit 1.65.0, Plotly 7.1.0, pandas 3.0.6,
NumPy 2.5.4 and SciPy 1.18.1. Workbook dependencies are unnecessary in this edition.

## Feature status

| Feature | Result |
| --- | --- |
| Single circular/rectangular geometry, array, wireframe/dark controls | Passed |
| Analytical predictor and invalid-input handling | Passed |
| A/B comparison, state preservation and export generation | Passed |
| 1D/2D design-space sweeps and rejected designs | Passed |
| Candidate selection and transfer to the studio | Passed |
| Standalone geometry HTML browser download | Passed |
| Calculation/comparison/sweep report and figure generation | Passed in UI/unit tests |
| Recorded FEA/MTS evidence and registered geometries | Excluded; approved safe data missing |
| Workbook literature presets and registered provenance | Excluded with the private workbook |

Browser rotation/zoom, linked-camera behaviour, every download click and PNG
camera export have not each been separately automated. Existing camera/export
code and embedded Plotly assets are retained; HTML export generation is tested.

## Exclusions and remaining items

No `.venv`, caches, backups, project reports, Abaqus databases/input decks,
raw MTS files, workbooks, confidential result files, secret files or personal
records are bundled. `MASTER_RESULTS.xlsx` and all derived workbook copies
are absent. Only general analytical/visualisation source modules and reviewed
data-independent tests were selected. `.gitignore` blocks common private-data,
simulation, workbook, environment, log and secret paths from accidental commits.

Static scanning checks machine-specific paths, email addresses and common secret
signatures; it cannot establish every possible confidentiality classification.
The manifest provides the exact small source-only upload set for review.

Nothing else is needed to run this analytical edition. Recorded evidence features
require explicit approval of a safe dataset plus integration work; they are not
represented as functioning or independently validated. Actual GitHub upload and
Community Cloud execution remain unperformed as requested.

## Integrity check

81 original source/document/workbook files were hash-checked before and after
preparation; none changed. Seven retained engine/geometry/comparison/sweep modules
match the originals byte-for-byte.

Analytical engine SHA-256:

`0294ae25040d08a6b82aafd25abf6ab2f5c6af373b371346e128e477bb61f567`
