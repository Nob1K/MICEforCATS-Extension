# Local Execution pipeline

Implementation in this folder adapts the notebooks originally designed to run on Google Colab (see more in original_nb_data). Uses a Python venv + [papermill](https://papermill.readthedocs.io/) to run notebooks from the shell.

---

## Pipeline at a glance

```
 build_env.sh                   (one-time)
      |
      v  creates .venv, installs deps, registers `mice-venv` Jupyter kernel
      |
      |
 run_feat_extract.sh            (heavy - will take hours on GPU)
      |
      v  papermill MICE-Replica_feat_extract.ipynb -> output_feat_extract.ipynb
         writes:
           ../original_nb_data/MICE_Output/results_summary.csv
           ../original_nb_data/MICE_Output/results_layers.csv
         output notebook contains the layer-wise BERTScore plot inline
      |
      v  the cell under "Judge Sample Questions" prints batched LLM-judge prompts
      |
 (manual)  copy printed prompts into an external LLM (Claude, GPT, etc.),
           collect the JSON arrays it returns, save concatenated as
           local_execute/judge_responses.json
      |
      v
 run_judge.sh                   (seconds)
      |
      v  papermill run_judge.ipynb -> output_judge.ipynb
         reads results_summary.csv + judge_responses.json
         writes ../original_nb_data/MICE_Output/results_summary_judged.csv
         prints coverage + accuracy

 finalize_results.sh            (CPU; seconds)
      |
      v  papermill finalize_results.ipynb -> output_finalize.ipynb
         reads results_summary_judged.csv + results_layers.csv
         writes ../original_nb_data/MICE_Output/<BUNDLE_DIR>/
                  summary_full.csv, layers_full.csv, data_bundle.joblib
         (default BUNDLE_DIR = "my-eval"; eval-2.5k is reserved for the
          precomputed bundle and is never overwritten)

  -----  the steps above are OPTIONAL - skip it if you're
         using our precomputed eval-2.5k bundle (the default for run_eval).  -----

 run_eval.sh                    (CPU-only; seconds)
      |
      v  papermill MICE-Evals.ipynb -> output_eval.ipynb
         reads ../original_nb_data/MICE_Output/<BUNDLE_DIR>/
                 layers_full.csv, summary_full.csv, data_bundle.joblib
         (default BUNDLE_DIR = "eval-2.5k" - our precomputed bundle.
          override with -p BUNDLE_DIR my-eval to use your own.)
         trains LR + RF, runs smECE / AUC / utility / MBR analyses
         renders all plots inline in output_eval.ipynb
```

---

## Prerequisites

- Linux for steps 1–3 (CUDA GPU required for Llama 3 inference). Step 4 (eval) runs on CPU and works fine on macOS or any laptop.
- Python 3.10+
- A GPU with enough VRAM to load `meta-llama/Meta-Llama-3-8B-Instruct` in fp16 (~16 GB). CPU works in theory but a full run is very slow. (for steps 1 - 3)
- A Hugging Face account that has accepted the Meta Llama 3 license, and an HF access token.
- The dataset CSVs at `../original_nb_data/Data`.

### `.env`

Create `local_execute/.env`:

```
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The notebook reads this via `python-dotenv` when its working directory is `local_execute/` - which is what the run scripts arrange.

---

## First-time setup

```bash
cd local_execute
./build_env.sh
```

What it does:

1. Creates `.venv/` if missing.
2. Installs everything in `requirements.txt`.
3. Registers a Jupyter kernel called `mice-venv` pointing at `.venv/bin/python`. The run scripts pass `-k mice-venv` to papermill, which is what makes notebook cells execute against this venv (and not your system Python).

Verify registration (Linux):

```bash
ls ~/.local/share/jupyter/kernels/mice-venv/
```

For MacOS:
```bash
ls ~/Library/Jupyter/kernels/mice-venv/
```

You should see a `kernel.json` whose `argv[0]` ends in `local_execute/.venv/bin/python`.

Re-running `build_env.sh` is safe - venv creation is skipped if it exists, and `ipykernel install` is idempotent.

---

## Running the pipeline

**It is recommended that you use our already extracted features, as running feature extraction is very compute heavy and will take a lot of time. You can find our extracted feature in ../original_nb_data/MICE_Output/eval-2.5k. Use the data in that folder to train logistic regression and random forest, which will be in step 4 (skip 1-3).**

**Run this command if your scripts are not executing due to permission issues**
```bash 
chmod +x *.sh
```

### 1. Feature extraction

```bash
./run_feat_extract.sh
```

Activates the venv, runs the main notebook through papermill, writes the executed copy to `output_feat_extract.ipynb`. Outputs land in `../original_nb_data/MICE_Output/`:

- `results_summary.csv` - one row per question (final text, log-confidence, etc.)
- `results_layers.csv` - one row per (question, layer) with BERTScore P/R/F1
- `featextract_checkpoint.pkl` - periodic checkpoint, used to resume after interruption

The plot from cell 13 is embedded in `output_feat_extract.ipynb` - open it in any notebook viewer to see the layer-wise F1 curves.

This notebook uses `../original_nb_data/Data/dataset_Brandon.csv` as an input, this can be changed in the notebook.

### 2. Manual LLM-judge step

Open the executed `output_feat_extract.ipynb` and find cell 14 (under "Judge Sample Questions"). It will have printed a series of batched prompts to its output. Each batch tells the LLM to classify model replies as `abstain`, `clarify`, or `answer`, and to return a JSON array.

For each batch:

1. Copy the printed prompt.
2. Paste into your LLM of choice (Claude, ChatGPT, etc.).
3. Capture the JSON array it returns.

Concatenate all the JSON arrays into one file at `local_execute/judge_responses.json`. Two formats are accepted:

```json
[
  {"id": 1, "predicted_type": "answer"},
  {"id": 2, "predicted_type": "abstain"}
]
```

or, if you'd rather not hand-flatten:

```json
[
  [{"id": 1, "predicted_type": "answer"}, {"id": 2, "predicted_type": "abstain"}],
  [{"id": 3, "predicted_type": "clarify"}]
]
```

`run_judge.ipynb` flattens the second form automatically.

### 3. Apply judge results

```bash
./run_judge.sh
```

Reads `results_summary.csv` and `judge_responses.json`, joins them on `question_id`, computes a `judge_decision` column (1 if the LLM's predicted type matches the ground-truth `type` column, else 0), and writes:

- `../original_nb_data/MICE_Output/results_summary_judged.csv`

Coverage and accuracy print to the executed notebook (`output_judge.ipynb`).

#### Running eval on your own data

If you ran steps 1–3 yourself and want to evaluate on those outputs instead of the precomputed bundle, first turn your `results_summary_judged.csv` + `results_layers.csv` into a bundle:

```bash
./finalize_results.sh
```

This writes `summary_full.csv`, `layers_full.csv`, and `data_bundle.joblib` into `../original_nb_data/MICE_Output/my-eval/` (60/20/20 stratified split, `random_state=42` - same recipe as `eval-2.5k`). It does **not** touch `eval-2.5k/`.

Then point `run_eval` at your bundle by overriding the `BUNDLE_DIR` parameter:

```bash
source .venv/bin/activate
papermill MICE-Evals.ipynb output_eval.ipynb -k mice-venv -p BUNDLE_DIR my-eval
```

`run_eval.sh` continues to default to `eval-2.5k`, so anyone using the precomputed path is unaffected.

### 4. Train Logistic Regression and Random Forest with extracted features, then run the evaluation pipeline (start at this step if you just want to see results and not extract your own features as training data)

```bash
./run_eval.sh
```

By default this reads our precomputed bundle in `../original_nb_data/MICE_Output/eval-2.5k/` (`layers_full.csv`, `summary_full.csv`, `data_bundle.joblib`). Trains the logistic regression model and the random forest model on the bundle's train split, then runs the evaluation pipeline (smECE, AUC, utility, MBR analyses), focusing on RF because it was found to be the most calibrated.

Graphs and outputs can be viewed at the output notebook saved to `output_eval.ipynb`.


---

## Test runs for feature extraction (subset of samples)

Don't hand-edit the notebook to slice the dataset. Use papermill parameters instead - the main notebook has a tagged `parameters` cell with `LIMIT = None` that you override at the command line:

```bash
cd local_execute
source .venv/bin/activate
papermill MICE-Replica_feat_extract.ipynb output_test.ipynb \
    -k mice-venv \
    -p LIMIT 5
```

This runs the full pipeline on the first 5 rows of `dataset_Brandon.csv`. The default (`LIMIT = None`) means no slicing, so `run_feat_extract.sh` continues to do a full run unchanged.

**Important:** if a previous full or partial run has written `featextract_checkpoint.pkl` into the output directory, the test run will resume from that checkpoint instead of starting fresh. Delete it first for a clean test:

```bash
rm -f ../original_nb_data/MICE_Output/featextract_checkpoint.pkl
```

---

## File reference

| File | Purpose |
|---|---|
| `build_env.sh` | One-time venv setup + kernel registration. Idempotent. |
| `requirements.txt` | Pinned Python dependencies for the venv. |
| `.env` | Holds `HF_TOKEN`. **Do not commit.** |
| `MICE-Replica_feat_extract.ipynb` | Main notebook: load Llama 3, generate, extract per-layer logit-lens texts, BERTScore them, save CSVs. Has a `parameters`-tagged cell exposing `LIMIT` for test runs. |
| `run_feat_extract.sh` | Runs the main notebook via papermill against the `mice-venv` kernel. Output: `output_feat_extract.ipynb`. |
| `run_judge.ipynb` | Applies LLM-judge predictions to the summary CSV. Reads `judge_responses.json`. |
| `run_judge.sh` | Runs `run_judge.ipynb` via papermill. Output: `output_judge.ipynb`. |
| `judge_responses.json` | (You create this.) Concatenated JSON output from the external LLM judge. Flat array or list-of-batches both work. |
| `MICE-Evals.ipynb` | Trains LR + RF on a featurized bundle, runs smECE / AUC / utility / MBR evaluation, plots results. CPU-only; no GPU or LLM required. Has a `parameters`-tagged cell exposing `BUNDLE_DIR` (default `"eval-2.5k"`). |
| `run_eval.sh` | Runs `MICE-Evals.ipynb` via papermill against the default `BUNDLE_DIR=eval-2.5k`. Output: `output_eval.ipynb`. |
| `finalize_results.ipynb` | Optional bridge: turns `results_summary_judged.csv` + `results_layers.csv` (from your local feat-extract + judge run) into the eval-canonical bundle (`summary_full.csv`, `layers_full.csv`, `data_bundle.joblib`). Has a `parameters`-tagged cell exposing `BUNDLE_DIR` (default `"my-eval"`). |
| `finalize_results.sh` | Runs `finalize_results.ipynb` via papermill. Output: `output_finalize.ipynb`. |
| `output_feat_extract.ipynb` | Generated by papermill. Contains executed cells, printed batch prompts, and the embedded layer-F1 plot. |
| `output_judge.ipynb` | Generated by papermill. Contains coverage + accuracy printout. |
| `output_eval.ipynb` | Generated by papermill. Contains LR/RF classification reports, smECE/AUC tables, and all evaluation plots. |

Outputs that land **outside** this folder (in `../original_nb_data/MICE_Output/`):

| File | Producer | Purpose |
|---|---|---|
| `results_summary.csv` | feat-extract cell 12 | One row per question. |
| `results_layers.csv` | feat-extract cell 12 | One row per (question, layer). |
| `featextract_checkpoint.pkl` | feat-extract cell 10 | Resume state. Delete to force a clean run. |
| `results_summary_judged.csv` | run_judge | Summary + `predicted_type` + `judge_decision`. |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'transformers'` (or any other dep) when running a notebook.**
Papermill is using the wrong kernel. Confirm:
```bash
jupyter kernelspec list   # must be run with the venv activated
```
You should see `mice-venv`. If not, re-run `./build_env.sh`. Make sure both run scripts pass `-k mice-venv`.

**`Command 'jupyter' not found`.**
You're outside the venv. Either `source .venv/bin/activate` first, or inspect the kernelspec on disk directly - no `jupyter` CLI required. The path differs by platform:
- Linux: `~/.local/share/jupyter/kernels/mice-venv/kernel.json`
- macOS: `~/Library/Jupyter/kernels/mice-venv/kernel.json`

