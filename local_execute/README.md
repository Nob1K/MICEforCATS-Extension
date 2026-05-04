# local_execute

adapts the notebooks originally designed to run on Google Colab. Uses a Python venv + [papermill](https://papermill.readthedocs.io/) to run notebooks from the shell.

---

## Pipeline at a glance

```
 build_env.sh                   (one-time)
      |
      v  creates .venv, installs deps, registers `mice-venv` Jupyter kernel
      |
      |
 run_feat_extract.sh            (heavy — will take many hours on GPU)
      |
      v  papermill MICE-Replica_feat_extract.ipynb -> output_feat_extract.ipynb
         writes:
           ../original_nb_data/MICE_Output/results_summary.csv
           ../original_nb_data/MICE_Output/results_layers.csv
         output notebook contains the layer-wise BERTScore plot inline
      |
      v  cell 14 of the output notebook prints batched LLM-judge prompts
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
```

---

## Prerequisites

- Linux
- Python 3.10+
- A GPU with enough VRAM to load `meta-llama/Meta-Llama-3-8B-Instruct` in fp16 (~16 GB). CPU works in theory but a full run is very slow.
- A Hugging Face account that has accepted the Meta Llama 3 license, and an HF access token.
- The dataset CSV at `../original_nb_data/Data/dataset_Brandon.csv`.

### `.env`

Create `local_execute/.env`:

```
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The notebook reads this via `python-dotenv` when its working directory is `local_execute/` — which is what the run scripts arrange.

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

Verify registration:

```bash
ls ~/.local/share/jupyter/kernels/mice-venv/
```

You should see a `kernel.json` whose `argv[0]` ends in `local_execute/.venv/bin/python`.

Re-running `build_env.sh` is safe — venv creation is skipped if it exists, and `ipykernel install` is idempotent.

---

## Running the pipeline

**It is recomended that you use our already extracted features, as running feature extraction is very compute heavy and will take a lot of time. You can find our extracted feature in ../original_nb_data/MICE_Output/eval-1k. Use the data in that folder to train logistic regression and random forest, which will be in step 4 (skip 1-3).**

### 1. Feature extraction

```bash
./run_feat_extract.sh
```

Activates the venv, runs the main notebook through papermill, writes the executed copy to `output_feat_extract.ipynb`. Outputs land in `../original_nb_data/MICE_Output/`:

- `results_summary.csv` — one row per question (final text, log-confidence, etc.)
- `results_layers.csv` — one row per (question, layer) with BERTScore P/R/F1
- `Brandon_featextract_lite_checkpoint.pkl` — periodic checkpoint, used to resume after interruption

The plot from cell 13 is embedded in `output_feat_extract.ipynb` — open it in any notebook viewer to see the layer-wise F1 curves.

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


### 4. Train Logistic Regression and Random Forest with extracted features, then run the evaluation pipeline

---

## Test runs (subset of samples)

Don't hand-edit the notebook to slice the dataset. Use papermill parameters instead — the main notebook has a tagged `parameters` cell with `LIMIT = None` that you override at the command line:

```bash
cd local_execute
source .venv/bin/activate
papermill MICE-Replica_feat_extract.ipynb output_test.ipynb \
    -k mice-venv \
    -p LIMIT 5
```

This runs the full pipeline on the first 5 rows of `dataset_Brandon.csv`. The default (`LIMIT = None`) means no slicing, so `run_feat_extract.sh` continues to do a full run unchanged.

**Important:** if a previous full or partial run has written `Brandon_featextract_lite_checkpoint.pkl` into the output directory, the test run will resume from that checkpoint instead of starting fresh. Delete it first for a clean test:

```bash
rm -f ../original_nb_data/MICE_Output/Brandon_featextract_lite_checkpoint.pkl
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
| `output_feat_extract.ipynb` | Generated by papermill. Contains executed cells, printed batch prompts (cell 14), and the embedded layer-F1 plot. |
| `output_judge.ipynb` | Generated by papermill. Contains coverage + accuracy printout. |

Outputs that land **outside** this folder (in `../original_nb_data/MICE_Output/`):

| File | Producer | Purpose |
|---|---|---|
| `results_summary.csv` | feat-extract cell 12 | One row per question. |
| `results_layers.csv` | feat-extract cell 12 | One row per (question, layer). |
| `Brandon_featextract_lite_checkpoint.pkl` | feat-extract cell 10 | Resume state. Delete to force a clean run. |
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
You're outside the venv. Either `source .venv/bin/activate` first, or just inspect `~/.local/share/jupyter/kernels/mice-venv/kernel.json` directly — no `jupyter` CLI required.

**`KeyError: 'HF_TOKEN'` or 401 on model download.**
`.env` not being found. The run scripts `cd "$(dirname "$0")"` first, so `load_dotenv()` looks for `local_execute/.env`. Confirm the file exists there and has no quotes around the token value.

**`401 Unauthorized` on `meta-llama/Meta-Llama-3-8B-Instruct`.**
Your HF account hasn't accepted the Llama 3 license yet. Visit the model page on huggingface.co and click "Agree and access repository", then retry.

**CUDA OOM during generation.**
Either lower `MAX_NEW_TOKENS` in cell 3, or lower the `CHUNK_SIZE = 256` for BERTScore in cell 10, or run with a smaller model.

**Test run starts at sample N instead of 0.**
Stale `Brandon_featextract_lite_checkpoint.pkl`. Remove it (see Test runs section above).

**Notebook hangs forever during the judge step.**
Make sure you're running `run_judge.sh` and not the old interactive cell. The current pipeline reads from `judge_responses.json`, never from stdin.

---

## What changed from the original Colab notebook

- `from google.colab import userdata` removed; HF token now comes from `.env` via `python-dotenv`.
- `from google.colab import drive` / `drive.mount(...)` removed; paths are local filesystem paths anchored at `Path.cwd().parent`.
- `__file__`-based path resolution replaced with `Path.cwd().parent` (papermill cwd is `local_execute/`).
- Inline `!pip install` cells removed in favor of `requirements.txt`.
- Interactive `input()`-based judge cell extracted into a separate notebook (`run_judge.ipynb`) that reads from a JSON file.
- A `parameters`-tagged cell with `LIMIT = None` was added so test runs are a CLI override rather than a code edit.
