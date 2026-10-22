# ENME408 Microneedle Design Studio

Public analytical edition of the existing Streamlit studio. Interactive geometry,
structural estimates, A/B comparisons and design-space sweeps use the original
calculation engine. No recorded engineering results are bundled.

## Run locally

Use Python **3.12**. From this folder:

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in PowerShell or
`source .venv/bin/activate` on Linux/macOS, then run:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Run the included regression checks with:

```sh
python -B -m unittest discover -s tests -v
```

## Upload and deploy when ready

Upload the **contents** of this folder to the root of the existing
`nnamviet-ai/microneedle-design-studio` repository, preserving `src/`, `tests/`
and `.streamlit/`. Include `.gitignore` and `.streamlit/config.toml`; some file
pickers hide dotfiles. `UPLOAD_FILES.txt` lists every prepared file.

In Streamlit Community Cloud, create an app using that repository, the branch
containing the uploaded files (usually `main`), and **`app.py`** as the main file.
Select **Python 3.12** in Advanced settings. No secrets, workbook, Abaqus
installation or additional operating-system packages are required.

If you instead upload the whole folder as a repository subfolder, set the main
file to `MICRONEEDLE_UI_DEPLOY/app.py`. Prefer the root layout above.

See the official [deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
and [dependency instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).
Nothing has been uploaded or deployed as part of preparing this folder.

## Included features and boundaries

- Circular/rectangular finite-tip geometry; single needle and illustrative 4 by 4
  array; wireframe, dark view, interactive camera and standalone HTML export.
- Axial and bending estimates, nominal stress, ideal elastic buckling indicators,
  explicit loading/material assumptions and calculation report download.
- A/B geometry and response comparison with shared conditions and HTML/CSV/JSON
  exports; switching modes preserves design state.
- One- and two-parameter sweeps, response plots, rejected-input gaps, candidate
  selection/transfer and CSV/HTML/JSON exports.

Defaults are illustrative design assumptions. Results are unvalidated analytical
estimates, not measured FEA/MTS results or certified capacities. The original
model's applicability messages remain visible.

Recorded FEA/MTS views, registered project geometries, workbook literature
presets and registered provenance are unavailable. The private results workbook
has been excluded, including any derived or sanitised copy. No substitute
engineering results have been generated. Restoring those features requires a
separately reviewed and explicitly approved safe dataset and a read-only adapter.

The app does not read neighbouring workspace folders or accept private datasets.
All source-file references resolve from the deployment directory. User exports
contain only analytical inputs and computed estimates.

See `DEPLOYMENT_REPORT.md` for test results and remaining limitations. Do not
upload the original project, local validation environment, caches or private data.
