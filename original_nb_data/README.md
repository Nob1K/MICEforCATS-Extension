# Original Notebooks and Data

The original Colab notebooks and source datasets for the MICE-for-CATS extension project. Notebooks here import `google.colab` and read from Google Drive paths - **they are not directly runnable locally**. For the Colab-stripped, locally-executable versions of the core pipeline, see [`../local_execute/`](../local_execute/README.md).

This folder is the source of truth for the experimental work and the data it operates on.

---

## Notebooks

### Pipeline notebooks (Colab originals)

| Notebook | Purpose |
|---|---|
| `MICE-Replica.ipynb` | MICE-for-CATS replication for feature extraction part. Loads Llama-3-8B-Instruct, generates a response per question, extracts intermediate-layer hidden states using logit lens, computes per-layer BERTScore F1 against the final-layer text, and saves `results_summary.csv` + `results_layers.csv`. Local equivalent: `MICE-Replica_feat_extract.ipynb`. |
| `MICE-Replica-Brandon_sRun.ipynb` | Brandon's sample run of `MICE-Replica.ipynb` against `Data/dataset_Brandon.csv`. Outputs were combined with Trek's run to produce the precomputed `MICE_Output/eval-1k/` bundle. |
| `MICE-Replica-Trek_sRun.ipynb` | Trek's sample run, against `Data/dataset_Trek.csv`. Companion to Brandon's run. |
| `MICE-Evals.ipynb` | Trains MICE Logistic Regression and Random Forest classifiers on the featurized eval bundle, then evaluates with smECE, ROC/PR-AUC, expected utility under three risk profiles, and per-type accuracy with empirical-MBR thresholds. Local equivalent: `local_execute/MICE-Evals.ipynb`. |
| `MICE-Classifiers.ipynb` | Earlier classifier exploration - bridges raw feature-extraction output into classifier-ready form. Largely superseded by `MICE-Evals.ipynb`. |
| `LogitLens.ipynb` | Standalone logit-lens implementation used to develop and validate the layer-extraction technique before it was integrated into `MICE-Replica.ipynb`. Useful as a reference for how the per-layer hidden-state decoding works. |
| `BaselineModel-TS.ipynb` | Baseline accuracy experiments - runs Llama 3 on the question set without any MICE machinery (no logit lens, no calibration), to establish the floor that the MICE classifiers need to beat. Outputs land in `TS_Baseline_Output/`. |
| `SubsetQuestionsToCSV.ipynb` | Utility: loads one of the Hugging Face dataset directories under `Data/` and dumps it to CSV. Used during dataset construction. |
| `MICE_Output/results_finalizer.ipynb` | Concatenates per-runner CSVs (Brandon + Trek), pivots layer-wise BERTScores into wide form, builds a stratified train/val/test split, and saves the `data_bundle.joblib` consumed by `MICE-Evals.ipynb`. Local equivalent: `local_execute/finalize_results.ipynb`. |
| `Data/download_data.ipynb` | Downloads the three source datasets (AmbigQA, AbstentionBench, TriviaQA), takes 1k from each, and writes them as Hugging Face Dataset directories under `Data/`. Run this once before anything else if rebuilding the dataset from scratch. |
| `Data/misc/de-duplicater.ipynb` | Utility: Deduplicates our training data |

### Folder layout

| Path | Contents |
|---|---|
| `Data/` | Source datasets and the curated CSVs used by the pipeline notebooks. See section below. |
| `MICE_Output/` | Outputs of pipeline runs. `lite_results_*_trek.csv` and `results_*_brandon.csv` are raw per-runner outputs; `eval-1k/` is the finalized bundle (train/val/test split + featurized `data_bundle.joblib`) used by evaluation. `results_finalizer.ipynb` lives here because it's the notebook that produces the bundle. |
| `TS_Baseline_Output/` | Outputs of `BaselineModel-TS.ipynb` - Llama-3 raw responses for the baseline comparison. |
| `sync/` | Google Drive sync utilities (`pull.py`, `pull_all.py`, `update.sh`) for us to sync with this repo more conveniently. |

---

## Data

`Data/` holds three source datasets (downloaded from Hugging Face) and the curated CSVs derived from them.

### Source datasets

Each is stored as a Hugging Face `Dataset` directory (`data-*.arrow` + `dataset_info.json` + `state.json`), 1k samples each. Loadable with `datasets.load_from_disk(<path>)`.

| Directory | Source | Question type emphasis |
|---|---|---|
| `ambigQA_hf_1k/` | [AmbigQA](https://huggingface.co/datasets/sewon/ambig_qa) | Ambiguous questions - should prompt the model to **clarify**. |
| `abstentionBench_hf_1k/` | [AbstentionBench](https://huggingface.co/datasets/facebook/AbstentionBench) | Unanswerable questions - should prompt the model to **abstain**. |
| `triviaQA_hf_1k/` | [TriviaQA](https://huggingface.co/datasets/mandarjoshi/trivia_qa) | Well-formed factual questions - model should **answer**. |
| `combined_datasets_hf/` | Union of the three above | All three response types in one dataset. |
| `combined_datasets_lite_hf/` | Smaller curated subset of `combined_datasets_hf/` | Contains smaller questions for faster feature extraction. |

The three response targets (`abstain` / `clarify` / `answer`) form the three-way classification problem that we have formulated.

### CSVs used

| File | Purpose |
|---|---|
| `dataset_Brandon.csv` | Brandon's split of the combined dataset (~500 rows). Input to `MICE-Replica-Brandon_sRun.ipynb` and to `local_execute/MICE-Replica_feat_extract.ipynb`. |
| `dataset_Trek.csv` | Trek's split (~500 rows). Input to `MICE-Replica-Trek_sRun.ipynb`. |

Both CSVs share the schema: `question_id`, `question`, `answer`, `type` (one of `abstain` / `clarify` / `answer`).

### Subdirectories

| Path | Contents |
|---|---|
| `Data/TestTrain/` | Reserved for train/test exports, currently empty. |
| `Data/misc/` | miscellaneous CSVs from earlier experiments (`dataset_lite_*`, `dataset_Brandon.xlsx`) and the `de-duplicater.ipynb` notebook. |

---

## This folder is read-only mostly

Anything that needs to *run* locally has been ported to `../local_execute/` with the Colab dependencies stripped. Treat `original_nb_data/` as the historical record:

- The Colab notebooks here are what was actually executed during the project, with their saved outputs intact.
- The CSVs and HF datasets are the inputs those runs consumed.
- The `MICE_Output/` artifacts are what those runs produced, and what `local_execute/run_eval.sh` reads from by default.

If you want to reproduce results, work from `local_execute/`. If you want to read what was done, work from here.
