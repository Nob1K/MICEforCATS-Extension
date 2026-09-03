# MICE for CATs — Extension to Answer / Clarify / Abstain

Can a language model's internal activations tell you when it should answer a question, ask for clarification, or abstain from answering?

This project extends [MICE for CATs: Model-Internal Confidence Estimation for Calibrating Agents with Tools](https://arxiv.org/abs/2504.20168) from its original binary tool-calling setting to a three-way decision over question answering. We reproduce the MICE feature-extraction pipeline on Llama-3-8B-Instruct, build a 2,500-question benchmark with a ground-truth action for each question, and test whether MICE-style confidence estimates support a three-way decision policy.

## Headline results

**Calibration transfers. The decision policy does not.**

MICE features produce well-calibrated confidence estimates in the QA setting, which is a large improvement over the model's own token-level confidence:

| Confidence source | smECE ↓ |
|---|---|
| Llama-3 raw log-confidence | 0.384 |
| MICE logistic regression | 0.034 |
| **MICE random forest** | **0.021** |

That is an **18x reduction** in smooth expected calibration error over the raw baseline, on the 500-question held-out test split of the 2,500-question set.

But well-calibrated confidence turned out not to be *sufficient*. MICE for CATs assumes the optimal action can be read off a threshold on a one-dimensional confidence axis. In the three-way setting that assumption breaks - the confidence distributions for `clarify` and `abstain` overlap almost completely:

| Decision method | Test accuracy |
|---|---|
| Llama-3 baseline (no decision layer, all 2,500 questions) | 36.4% |
| Theoretical MBR utility thresholds (avg. over risk profiles) | 47.5% |
| Theoretical MBR utility thresholds (best profile) | 52.2% |
| Empirical thresholds tuned on validation | 52.6% |
| **Random forest predicting the action directly** | **61.0%** |

The takeaway: the confidence *estimate* survives the move from tool-calling to question-answering, but the *thresholding scheme* built on top of it does not. Treating action selection as direct multi-class classification over the same model-internal features works better than any threshold on the calibrated score.

## Method

1. **Benchmark.** 2,500 questions drawn from three datasets, where the source dataset defines the correct action:

   | Source | Correct action | Why |
   |---|---|---|
   | [AmbigQA](https://huggingface.co/datasets/sewon/ambig_qa) | `clarify` | Question is ambiguous |
   | [AbstentionBench](https://huggingface.co/datasets/facebook/AbstentionBench) | `abstain` | Question is unanswerable |
   | [TriviaQA](https://huggingface.co/datasets/mandarjoshi/trivia_qa) | `answer` | Well-formed factual recall |

   Baseline Llama-3-8B-Instruct picks the right action 36.4% of the time (912/2,500), and is badly skewed: it answers 97.4% of TriviaQA questions, abstains on only 11.3% of AbstentionBench, and clarifies on 0.8% of AmbigQA.

2. **Feature extraction.** For each question, generate a response with Llama-3-8B-Instruct, then apply **logit lens** - the model's unembedding matrix applied to intermediate-layer hidden states - to decode a text prediction at every layer. Compute **BERTScore** between each intermediate layer's text and the final-layer text. The trajectory of that similarity across depth, plus the normalized log-confidence of the generated response, gives **32 features** per question.

3. **Confidence estimation.** Train logistic regression and random forest on those 32 features against LLM-judge-labeled correctness, using a 60/20/20 stratified split (1,500 / 500 / 500, `random_state=42`).

4. **Decision policy.** Three approaches, evaluated on the held-out test split:
   - *Theoretical:* Minimum Bayes Risk thresholds derived from a hand-specified utility function over six (action x correctness) pairs, under low/medium/high risk profiles.
   - *Empirical:* the same decision rule, but with the two thresholds grid-searched on the validation split under 0/1 loss.
   - *Direct:* a random forest trained on the same features with the action label as the target, skipping the confidence layer entirely.

5. **Scoring.** An LLM judge (following the AbstentionBench protocol) classifies each Llama response as an answer, a clarification request, or an abstention.

## Running it

**`local_execute/` is the main execution path.** It runs the pipeline from a shell via a Python venv and [papermill](https://papermill.readthedocs.io/), with no Colab dependency. Start here: **[`local_execute/README.md`](local_execute/README.md)**.

The fastest path: evaluation only on our prebuilt dataset, CPU-only, seconds to run, no GPU and no HuggingFace token:

```bash
cd local_execute
./build_env.sh      # one-time: venv + `mice-venv` Jupyter kernel
./run_eval.sh       # trains LR + RF on the precomputed eval-2.5k bundle,
                    # reproduces the smECE / AUC / utility / MBR results
```

Results and every plot land in `output_eval.ipynb`.

To regenerate features from scratch instead of using the precomputed bundle, you need a CUDA GPU with ~16 GB VRAM, a Hugging Face token with the Meta Llama 3 license accepted, and several hours. The full four-step pipeline (feature extraction → manual LLM judge → apply judge → finalize bundle) is documented in `local_execute/README.md`.

**Colab is the backup path.** [`original_nb_data/`](original_nb_data/README.md) holds the original Colab notebooks with their saved outputs, the source datasets, the precomputed output bundles, and the [written report](original_nb_data/report.pdf). These notebooks import `google.colab` and read Drive paths, so they are not directly runnable locally - you are welcome to copy them to your own Drive and adapt. This folder was what we actually developed with and executed first.

## Limitations

- **One model.** Everything is Llama-3-8B-Instruct. Whether MICE features calibrate this well on other architectures, other sizes, or instruction-tuned-vs-base variants is untested.
- **The judge step is manual.** In `local_execute`, prompts are printed for you to paste into an external LLM and the responses are pasted back as JSON. It is not an API call, so it is not reproducible end-to-end without human involvement.
- **Hand-chosen utility values.** The theoretical MBR thresholds depend on utility numbers we picked, not on anything estimated from data.
- **The LLM judge is unvalidated.** Response classification is done by an external LLM rather than human annotation, and we did not measure judge–human agreement. Judge error could propagate into both the correctness labels used to train the confidence models and the accuracy numbers reported above.
- **500-question test set.** Confidence intervals on the accuracy figures are wide: the 52.6% vs. 61.0% gap is meaningful, the 52.2% vs. 52.6% gap probably is not.

## Contributions

A three-person project by **Brandon Cheng**, **Justin Mehes**, **Trek Stenger**.

**Brandon Cheng**
- Implemented the confidence-feature extraction method: logit-lens decoding of Llama-3-8B-Instruct's intermediate layers, and layer-wise BERTScore against the final-layer text. This produces the 32-feature representation every downstream model in the project trains on.
- Implemented part of the feature-extraction execution script.
- Set up the repository, the `local_execute/` pipeline (venv bootstrap, papermill-driven run scripts, parameterized notebooks), and the Google Drive sync tooling in `original_nb_data/sync/`.
- Wrote the project report and the repository documentation.

**Justin Mehes**
- Obtained and preprocessed all the datasets.
- Compiled our pipeline including batching of feature extraction, LR and RF classifiers, theoretical, empirical, and alternative decision making approaches. Created evaluations (smECE, utility, confidence graphs, all figures).
- Co-wrote the project report.

**Trek Stenger**
- Proposed benchmark of AmbigQA / AbstentionBench / TriviaQA, and the LLM-judge scoring protocol.
- Implemented baseline model, question subsetting.


Feature extraction was split by dataset shard across all three of us and combined into the `eval-2.5k` bundle.

## Repository layout

| Path | Contents |
|---|---|
| [`local_execute/`](local_execute/README.md) | Locally-runnable pipeline: shell scripts + papermill-driven notebooks. **Start here.** |
| [`original_nb_data/`](original_nb_data/README.md) | Colab originals, source datasets, precomputed output bundles, written report |
| `original_nb_data/report.pdf` | Full write-up with figures |
| `original_nb_data/MICE_Output/eval-2.5k/` | Precomputed 2,500-question feature bundle used by `run_eval.sh` |
| `original_nb_data/MICE_Output/eval-1k/` | Earlier 1,000-question bundle, retained for reference |

## Citation

Extends:

> Subramani, N., Eisner, J., Svegliato, J., Van Durme, B., Su, Y., & Thomson, S. (2025).
> *MICE for CATs: Model-Internal Confidence Estimation for Calibrating Agents with Tools.* [arXiv:2504.20168](https://arxiv.org/abs/2504.20168)

## License

MIT - see [LICENSE](LICENSE).



