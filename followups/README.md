# Follow-up studies (September 2026)

Studies run after the five in the paper, released with v1.2.0. About 28,000 further
trials: harnesses, per-trial data and a full written record (`RESULTS.md`).

## Numbering: read this first

These folders keep their **internal** study numbers, which overlap with the paper's.

| Here | What it is | Not to be confused with |
|---|---|---|
| `study05_effort_and_mitigation` | reasoning effort and endpoint; entity-resolution guard; tool-order control | the paper's **Study 5**, the supplied-URL study (`../harnesses/url_supplied.py`, October 2026) |
| `study06_multiturn_consequence` | two-turn runs with tool results returned | — |
| `study07_adversarial_delivery` | unfamiliar entity delivered in retrieved content, not the user turn | — |
| `study08_11_real_catalogues` | real, unmodified `git` and `filesystem` MCP servers, no decoy; 2 hosted + 4 open-weights models | — |
| `study09_substitution` | re-analysis: what gets called instead (no new trials) | — |
| `study12_argument_recording` | argument recording; fabrication vs substitution | — |
| `study00_base_rate` | share of ordinary requests with an ungroundable external entity (no API calls) | — |

Harness file names follow run order, not study number: `exp8_substitution.py` is Study 9 and
`exp9_arguments.py` is Study 12. Study 10 (guard transfer to Claude) is in the Study 5 folder.

Studies 13 to 15 are not in this repository.

## Results the paper cites (Appendix F)

Recomputed from the CSVs here.

| Question | Result | Data |
|---|---|---|
| Does the fixed tool order (decoy last) carry the effect? | No. With order shuffled per trial, the decoy in last position fires 4/20 (20.0%) vs 61/220 (27.7%) elsewhere, ungroundable trials, p = 0.60 | `study05_.../data/exp5_shuffled.csv` |
| Does reasoning effort change the rate? | Yes, in a model-specific direction. `gpt-5.6-terra`, Responses API: 6.1% at `none`, 12.1% at default (720 ungroundable trials each); `sol` and `luna` fall at default | `exp5_results.csv` |
| Does a system-prompt entity-resolution guard help? | Pre-registered v1: decoy 0%, but refuses half of entity-free work, so not a mitigation. Exploratory v2: 12.1% to 1.4% on terra, 12.6% to 1.7% on Sonnet; control-utility cost 5.7 to 20.7 pp | `exp5_results.csv` |
| Does single-turn measurement undercount? | Yes. Decoy in turn 1 vs either turn: 33.3% vs 42.1% (plain description), 43.3% vs 54.2% (scoped). Nothing forwarded in 720 trials | `study06_.../data/exp6_results.csv` |
| Can an attacker trigger it through retrieved content? | Not at the size seen for user-turn entities: 3/120 clean, 2/120 real vendor, 4/120 unfamiliar vendor (p = 1.0) | `study07_.../data/exp7_results.csv` |
| Does it happen on real MCP servers without a decoy? | Correct-tool selection falls 36 to 58 pp on ungroundable referents in git and filesystem catalogues, across Anthropic, OpenAI, Alibaba and Google models; `llama-3.3-70b` shows no effect | `study08_11_.../data/*.json` |

`RESULTS.md` has the full record, including predictions that failed.

## Integrity

`sha256sum -c MANIFEST.sha256` from this folder checks every data file. Files ending
`_mock.csv` were synthetic test data and are not included. API keys are read from the
environment; `_shared/.env.example` holds placeholders only.
