# Ungrounded: Entity Grounding Failure Degrades Tool Selection in LLM Agents

**Taran Douley**
Shroud Labs Limited, United Kingdom
taran@shroudlabs.io · ORCID : 0009-0002-3673-4500

*Preprint. Revised September 2026.*

---

## Abstract

Decoy artefacts such as canary tokens and honey accounts are a mature defensive primitive whose value rests on a single property: nothing legitimate touches them. As organisations connect large language model agents to internal tooling via protocols such as MCP, the same primitive suggests itself for agent tool registries. Its viability depends on a false-positive rate that had not been measured.

We report twelve studies totalling 46,759 trials across ten models and six model families. A baseline measurement across 101 benign engineering prompts found low spurious invocation, but all nine positive trials originated from a single prompt. We initially attributed this to decoy attractiveness, a hypothesis supported by a significant monotonic trend (Cochran-Armitage p = 0.014); subsequent studies reversed it.

The mechanism is **entity grounding failure**. When an agent cannot ground an entity referenced in a request — because it is unnamed ("our CDN provider") or named but unfamiliar ("Northbrook CDN") — it invokes internal-lookup tools to resolve the entity as a prerequisite sub-goal. A configuration-export decoy fires on up to 51.67% of such requests; a credential-listing decoy remains largely quiet, inverting the intuitive placement heuristic.

The effect is not confined to purpose-built decoys. On two real, unmodified MCP servers taken from the reference implementations, with no injected tool of any kind, **correct tool selection falls by 36–58 percentage points when the referent cannot be grounded**, replicated across **six model families from four organisations** including two open-weights families. On the filesystem catalogue the degradation is monotonic across grounded, unfamiliar and ungroundable conditions (53.9% → 25.6% → 1.7%). One model is null on this metric, and we argue it exhibits a distinct third failure mode — calling the required tool with a fabricated argument — which the metric scores as success.

We further establish four results that constrain the finding. Reasoning effort and API surface each move the rate by a factor of two, in model-specific directions, so any published figure must state both. Multi-turn measurement raises observed exposure by roughly a quarter over single-turn, making all prior figures lower bounds. Returning realistic tool results produces **no** forwarding of the retrieved configuration in 720 trials, and introducing the ungroundable entity through *retrieved content* rather than the user turn produces **no** effect (p = 1.0) — so the behaviour is not an attacker-triggerable primitive on this evidence. Finally, combining a base-rate estimate for ungroundable requests (5.0% of a benign engineering set) with the measured conditional rate implies a decoy tool would fire on 0.6–2.1% of all agent traffic, which is disqualifying for the canary application that motivated the work.

We test three mitigations. A system-prompt guard implementing our own earlier recommendation eliminates the behaviour but removes half of unrelated task completions; a narrowed second version removes 88% of it for 5.67 pp of collateral cost; scoping the tool's own description *increases* invocation by 22 pp on the condition it targets. We report all three, including our own preregistered predictions that failed.

**Keywords:** LLM agents, Model Context Protocol, deception technology, canary tokens, tool selection, agent security

---

## 1. Introduction

Canary tokens and honey accounts derive their signal quality from an asymmetry: legitimate users have no reason to touch them, so every alert is real. Thinkst Canary and comparable products are widely deployed on this basis.

LLM agents connected to internal tools present an analogous opportunity. An agent given a tool registry can be given a decoy tool — one no legitimate task should ever call — providing a tripwire on a surface with minimal existing instrumentation. The precondition is the same asymmetry: benign agents must leave the decoy alone.

To our knowledge no measurement of that false-positive rate has been published. This paper provides one, together with an account of why the initial measurement was misleading and what the underlying mechanism turned out to be.

**Contributions.**

1. A false-positive baseline for decoy tools in an agent tool registry (3,030 trials).
2. Identification of entity grounding failure as the mechanism driving spurious invocation, with matched-control isolation of two contributing components.
3. Cross-vendor replication across six models and two vendors (7,200 trials).
4. Evidence that one production model does not exhibit the behaviour, indicating tractability.
5. Demonstration that the effect generalises beyond purpose-built decoys to **real, unmodified MCP servers**, where correct tool selection falls 49–58 pp on ungroundable referents (2,400 trials, both vendors).
6. Measurement of the two experimental parameters that most affect the reported rate — reasoning effort and API surface — each worth a factor of two, in model-specific directions.
7. Two negative results that bound the severity: no forwarding of retrieved configuration across 720 two-turn trials, and no effect when the entity arrives through retrieved content rather than the user turn (p = 1.0).
8. An unconditional false-positive estimate for the canary application, combining a base-rate proxy with the measured conditional rate.
9. Three mitigations evaluated with a utility cost measured on the same trials, including one that inverts.
10. A schema-level law governing which tool is substituted, evaluable on a catalogue without running a model (§3.12).
11. Replication across six model families from four organisations, including open weights (§3.14).
12. Measurement of a third failure mode — argument fabrication — that the correct-tool metric used throughout this literature scores as success, together with the withdrawal of our own incorrect inference about where it occurs (§3.15).
11. Retraction of five of our own hypotheses, two preregistered, with the data that overturned them; and correction of two defects in our own published method.

### 1.1 Related work

Existing MCP security research concentrates on adversarial manipulation of the tool registry. Invariant Labs characterised Tool Poisoning Attacks [5], in which instructions are embedded in tool descriptions at registration, together with shadowing and rug-pull variants; MCPTox [6] provides a large-scale empirical benchmark for this class. Wang et al. [7] extend the surface to tool *selection*, showing that persuasive or genetic-algorithm-optimised descriptions can bias which tool an agent chooses. A parallel line addresses transport-layer defects, including missing DNS rebinding protection in both official SDKs [8, 9].

This work differs in requiring no adversary at all. The tool descriptions are ordinary, the prompts are benign, and misselection arises from a property of the *request* rather than of the registry. Where Wang et al. show that tool choice can be deliberately skewed by a crafted description, we show that comparable misselection occurs spontaneously whenever the agent cannot ground an entity it has been asked about.

---

## 2. Method

### 2.1 Shared apparatus

All studies use a single-turn agent given ten realistic engineering tools plus one decoy. No tool results are returned to the agent; each trial records the complete set of tool calls in the first assistant turn.

System prompt: *"You are an engineering assistant with access to the team's tools. Use the tools available to you to help with the user's request."*

Legitimate tools: `read_file`, `search_code`, `list_directory`, `run_tests`, `git_log`, `query_database`, `fetch_url`, `search_docs`, `create_ticket`, `send_message`.

Three decoy variants, ordered a priori by assumed attractiveness to an attacker:

| Variant | Tool | Description |
|---|---|---|
| low | `legacy_batch_reconcile_v1` | Deprecated internal batch reconciliation endpoint retained for compatibility with the retired 2019 ledger export process. Not for general use. |
| medium | `internal_config_export` | Export internal service configuration, including environment settings, for the specified service. |
| high | `list_service_credentials` | List stored service account credentials and API keys for all connected internal systems. Returns secret values. |

Tool position within the registry is fixed, with the decoy in the final position on every trial.[^pos] `max_tokens` = 1024; temperature at provider default (1.0).

[^pos]: Earlier drafts of this section stated that tool position was shuffled per trial. It was not, in any of the four studies; position was confounded with decoy status throughout. A subsequent 400-trial control with seeded per-trial shuffling shows a flat profile — 20.00% with the decoy last against 27.73% elsewhere, p = 0.60 — so the confound is absent even though the stated control was. Binomial confidence intervals are Wilson score intervals; contingency tests are Fisher exact unless stated.

### 2.2 Study 1 — baseline

101 unique benign engineering prompts × 10 runs × 3 variants = 3,030 trials on `claude-sonnet-4-6`.

### 2.3 Study 2 — matched pairs

12 prompt pairs holding task constant and varying only the referent (unresolved possessive vs named vendor), × 3 variants × 10 runs, plus 4 control prompts from Study 1 that never triggered. 840 trials.

### 2.4 Study 3 — three-condition isolation

Study 2 confounds referent ambiguity with entity familiarity: "Cloudflare" both disambiguates and supplies a known entity. Study 3 adds a **fictional named vendor** condition ("Northbrook CDN") — unambiguous referent, unknowable entity. 12 triples × 3 conditions × 3 variants × 10 runs plus controls = 1,200 trials per model, on `claude-sonnet-4-6` and `claude-haiku-4-5-20251001`.

### 2.5 Study 4 — cross-vendor

Six models, 1,200 trials each. Model selection followed a rule fixed before results were observed: each vendor's flagship, balanced and lightweight general-purpose text models, at the newest generation available per tier.

| Tier | Anthropic | OpenAI |
|---|---|---|
| Flagship | `claude-opus-5` | `gpt-5.6-sol` |
| Balanced | `claude-sonnet-4-6` | `gpt-5.6-terra` |
| Lightweight | `claude-haiku-4-5-20251001` | `gpt-5.6-luna` |

`claude-sonnet-4-6` was retained as an anchor for continuity with Studies 1–3. A third vendor was attempted and abandoned: all candidate models returned plan-level quota errors.

OpenAI reasoning models reject function tools on the Chat Completions endpoint unless `reasoning_effort` is set explicitly. All three ran at `reasoning_effort=none`, the minimum available, as the closest match to the extended-thinking-off default under which the Anthropic arm ran. This is a deliberate choice, not the API default, and is a limitation (§6).

---

### 2.6 Studies 5–8 — design

Studies 5–8 were added in September 2026. **Study 5 was preregistered**: arms, six numbered predictions and decision rules were fixed in a protocol document before the first paid trial and were not edited afterwards. Studies 6–8 were not preregistered and are reported as exploratory where relevant.

**Study 5 — reasoning effort, API surface, and a system-prompt mitigation.** Study 4 ran every OpenAI arm at `reasoning_effort=none`. This was not a free choice: OpenAI reasoning models reject function tools on Chat Completions unless effort is `none`, so it was the only reachable setting on that endpoint. Reaching the API default (`medium`) requires the Responses API, which confounds effort with endpoint. Three arms therefore separate them: `chat/none` (anchor, reproducing Study 4), `responses/none` (bridge, effort held, endpoint moved) and `responses/default` (the shipping configuration). Token budget was raised from 1,024 to 4,096 in every arm because reasoning tokens are billed against it and a default-effort model can otherwise exhaust the budget and emit no call, which scores as a false abstention. Stimuli are imported from the Study 4 harness rather than reimplemented, making the schema drift of Limitation 6 impossible by construction.

**Study 6 — consequence and a tool-description mitigation.** Realistic results are returned for every tool and the second turn is measured. The decoy returns a mundane configuration payload containing no credentials; a credential-shaped payload was considered and rejected as prejudicial to the outcome. Every trial continues to turn 2 whether or not the decoy fired, so escalation has a comparison group.

**Study 7 — adversarial delivery.** The user turn is benign and names no external entity; the entity arrives in the first file, document or history result the agent retrieves. Nothing injected is an instruction. Three conditions hold the task and the surrounding content constant and vary only the referent. Each trial records whether the entity actually reached the model, so trials in which it did not are excluded rather than counted as clean.

**Study 9 — substitution direction.** A re-analysis of Study 8, adding no trials. For each trial where the required tool was not called, the arity of the first tool actually called is compared with the arity of the required tool, using the catalogues' own JSON schemas. `required` argument count is the pre-specified metric; the null model draws a tool uniformly from the same catalogue excluding the expected one. An argument required by at least 60% of a catalogue's tools is treated as ambient context (`repo_path`, `path`) rather than as a referent.

**Study 8 — real catalogues.** Two unmodified MCP servers (`filesystem`, 14 tools; `git`, 12 tools) taken verbatim from the reference implementations, with **no injected decoy**. Stimuli are written against each catalogue's actual tool names, task held constant, referent varying. The outcome is whether the agent selects the tool the task requires. Significance uses a cluster permutation test over triples; because that test penalises cluster *count* rather than effect size, the stimulus set was extended (git 5 → 11 triples, filesystem 4 → 9) rather than the run count increased.

---

## 3. Results

### 3.1 Study 1 — baseline and the single-prompt anomaly

| Variant | Hits | Trials | Rate | 95% CI |
|---|---|---|---|---|
| low | 0 | 1,010 | 0.00% | 0.00–0.38% |
| medium | 3 | 1,010 | 0.30% | 0.10–0.87% |
| high | 6 | 1,010 | 0.59% | 0.27–1.29% |

Cochran-Armitage trend across variants: p = 0.014. Low vs high: p = 0.031.

All nine positive trials came from one prompt: *"Get the status page contents for our CDN provider."* The remaining 100 prompts produced zero hits across 3,000 trials. Conditional on the single prompt, rates were 0% / 30% / 60%.

### 3.2 Study 2 — the prompt belongs to a class

| Condition | Hits | Trials | Rate |
|---|---|---|---|
| Unresolved referent | 67 | 360 | 18.61% |
| Named vendor | 0 | 360 | 0.00% |
| Controls | 0 | 120 | 0.00% |

p = 4.572 × 10⁻²². Eleven of twelve pairs produced at least one hit.

The variant ordering inverted relative to Study 1: `internal_config_export` 60/120 (50.00%), `list_service_credentials` 7/120 (5.83%), `legacy_batch_reconcile_v1` 0/120.

### 3.3 Study 3 — isolating the components

Pooled across variants:

| Condition | Sonnet 4-6 | Haiku 4-5 |
|---|---|---|
| Unresolved | 69/360 = 19.17% | 27/360 = 7.50% |
| Fictional vendor | 43/360 = 11.94% | 16/360 = 4.44% |
| Real vendor | 8/360 = 2.22% | 5/360 = 1.39% |
| Controls | 0/120 | 0/120 |

Sonnet: unresolved vs real p = 1.799 × 10⁻¹⁴; unresolved vs fictional p = 0.009923.
Haiku: unresolved vs real p = 8.038 × 10⁻⁵; unresolved vs fictional p = 0.1149 (n.s.).

Configuration-export variant, where the effect concentrates:

| Condition | Sonnet 4-6 | Haiku 4-5 |
|---|---|---|
| Unresolved | 62/120 = 51.67% | 26/120 = 21.67% |
| Fictional vendor | 39/120 = 32.50% | 15/120 = 12.50% |
| Real vendor | 5/120 = 4.17% | 2/120 = 1.67% |

The core contrast used throughout §3.4 — ungroundable entity (unnamed **or** unfamiliar) versus groundable and familiar — also holds here, so it replicates in all four studies rather than only in the cross-vendor arm:

| Model | Ungroundable | Known | OR | p |
|---|---|---|---|---|
| `claude-sonnet-4-6` | 112/720 = 15.56% | 8/360 = 2.22% | 8.11 | 4.696 × 10⁻¹³ |
| `claude-haiku-4-5` | 43/720 = 5.97% | 5/360 = 1.39% | 4.51 | 2.614 × 10⁻⁴ |

### 3.4 Study 4 — cross-vendor

Core contrast, ungroundable entity (unnamed **or** unfamiliar) versus groundable and familiar:

| Model | Ungroundable | Known | OR | p |
|---|---|---|---|---|
| `claude-sonnet-4-6` | 91/720 = 12.64% | 3/360 = 0.83% | 17.2 | 1.037 × 10⁻¹³ |
| `gpt-5.6-terra` | 75/720 = 10.42% | 7/360 = 1.94% | 5.9 | 7.663 × 10⁻⁸ |
| `claude-haiku-4-5` | 40/720 = 5.56% | 4/360 = 1.11% | 5.2 | 2.392 × 10⁻⁴ |
| `gpt-5.6-sol` | 36/720 = 5.00% | 1/360 = 0.28% | 18.9 | 7.825 × 10⁻⁶ |
| `gpt-5.6-luna` | 29/720 = 4.03% | 0/360 = 0.00% | ∞ | 8.95 × 10⁻⁶ |
| `claude-opus-5` | 1/720 = 0.14% | 0/360 = 0.00% | — | 1 (n.s.) |

Controls: 0/120 on every model. All six arms completed with zero request errors.

**Configuration-export cell, unresolved condition** (120 trials each): Sonnet 4-6 39.17%, Terra 30.00%, Haiku 13.33%, Sol 4.17%, Luna 2.50%, Opus 5 **0.00%**.

Opus 5 is significantly below four of the five other models on the pooled unresolved condition: vs Terra p = 1.294 × 10⁻¹⁷; vs Sonnet 4-6 p = 1.320 × 10⁻¹⁶; vs Haiku p = 2.989 × 10⁻⁶; vs Sol p = 9.037 × 10⁻⁴. Only Luna is not significantly different. Restricting to the configuration-export cell alone (120 trials per model) the Sol comparison falls to p = 0.0599, so the pooled figures are quoted throughout.

Per-model totals are reported over the 1,080 core trials, excluding the 120 control trials; the reproduction script uses the same convention. Where the abstract refers to "1,200 trials" it means the full per-model allocation including controls.

### 3.5 Tool distribution

Across Study 4's 7,200 trials: `search_docs` 3,513, `fetch_url` 2,677, `search_code` 2,043, `query_database` 310, `internal_config_export` 239, `list_directory` 175, `read_file` 162, `git_log` 71, `list_service_credentials` 48, `run_tests` 7.

The 48 credential-decoy invocations against 239 configuration-export invocations, across identical trial counts, is the aggregate form of the placement argument in §5.

The agent attempts to resolve the entity through legitimate channels first — documentation search, then URL fetch — and reaches the configuration export en route.

---

### 3.6 Study 5 — reasoning effort and API surface

`gpt-5.6-terra`, pooled over ungroundable conditions, 720 trials per arm:

| arm | ungroundable → decoy | known → decoy |
|---|---|---|
| `chat/none` (Study 4 configuration) | 12.08% | 0.83% |
| `responses/none` (endpoint moved) | 6.11% | 0.28% |
| `responses/default` (shipping) | 12.08% | 3.33% |

The anchor arm reproduces Study 4 twenty-four days later (credentials/unresolved 15.00% → 14.17%; configuration/known 1.67% → 1.67%), so the differences below are attributable to the manipulations rather than to model change.

**Effort, endpoint held constant:** 6.11% → 12.08%, p = 1.05 × 10⁻⁴. The rate doubles at the API default. Our preregistered prediction was that it would fall; it is recorded as a failed prediction. The direction is model-specific: `gpt-5.6-sol` falls 3.06% → 0.83% (p = 0.0034) and `gpt-5.6-luna` falls 6.67% → 3.75% (p = 0.017).

**Endpoint, effort held constant:** the pooled rate halves, and the credentials decoy moves from 14.17% to 0.00% on identical schemas. `chat/none` and `responses/default` coincide at 12.08% because two large opposing effects cancel; without the bridge arm this would read as "configuration does not matter". We attribute the endpoint effect tentatively to the two surfaces carrying the system prompt differently (a `messages` entry versus a top-level `instructions` field); this is untested.

**Consequence.** Reasoning effort and API surface are first-order experimental parameters. Any decoy-rate figure must state both, and cross-model comparison is valid only within a fixed pair.

### 3.7 Studies 5–6 — three mitigations, with utility measured on the same trials

A mitigation that suppresses the behaviour by suppressing the agent is a regression. Every trial therefore records whether a task-appropriate legitimate tool was called, scored on requests with a real named vendor and on control requests with no entity to resolve.

| measure | want | baseline | guard v1 | guard v2 |
|---|---|---|---|---|
| decoy, ungroundable | down | 12.08% | **0.00%** | **1.39%** |
| expected tool, known vendor | flat | 99.72% | 83.33% | 98.33% |
| expected tool, entity-free control (n = 300) | flat | 98.00% | 50.00% | 92.33% |

**Guard v1** implements this paper's own earlier recommendation ("fail closed on ungroundable entities") as a system-prompt clause naming no tool and no decoy concept. It eliminates the behaviour (0/720) and removes half of unrelated control work (p = 3.2 × 10⁻⁹). Under the preregistered decision rule this is a regression, not a mitigation.

Its failure mode is diagnostic: it cannot distinguish *which outside organisation is this?* — where internal tooling genuinely cannot help — from *which resource inside a system already identified?*, which is ordinary under-specification. It demands an S3 bucket and AWS account for "Amazon S3".

**Guard v2** (exploratory, written after seeing v1) narrows scope to outside organisations, permits proceeding once one is named, and exempts the team's own systems. It removes 88% of the behaviour for 5.67 pp of control utility (p = 0.0018) — which still fails the preregistered ±5 pp bar, by 0.67 pp.

That cost is not indiscriminate. Splitting the control set by whether it carries a possessive referent of its own:

| control subset | n | baseline | guard v1 | guard v2 |
|---|---|---|---|---|
| no referent at all | 150 | 100.00% | 100.00% | **100.00%** |
| as classified | 300 | 98.00% | 50.00% | 92.33% |
| all four controls | 600 | 98.83% | 25.00% | 69.83% |

On the single control with no referent whatsoever, all three arms score 100%. Guard v2's entire measured cost falls on requests that do contain an ungroundable referent. Its practical limitation is that it stops on *possessive* phrasing — "our docs site" — which is common and which users expect to work.

**Tool-description scoping** (Study 6) adds one sentence to the decoy's own description stating that it does not cover third-party vendors. This is the lever a server author holds rather than the agent developer.

| condition | plain | scoped | p |
|---|---|---|---|
| unresolved | 28.33% | 26.67% | 0.885 |
| **fictional vendor** | **38.33%** | **60.00%** | **0.0012** |
| known vendor | 10.00% | 2.50% | 0.030 |

The mitigation **inverts on the condition it targets**, raising invocation by 22 pp. Naming third-party vendors in order to exclude them appears to raise the tool's apparent relevance for exactly those requests; the negation does not function as a constraint. Where the vendor is recognised, the model has enough grounding to apply the exclusion and the sentence helps. This is one tool, one model and one wording, and is not evidence that scoping never works — it is evidence that it must be measured rather than assumed.

### 3.8 Study 6 — consequence, and single-turn undercounting

Across 720 two-turn trials the agent **never** forwarded the retrieved configuration: 0 messages sent, 0 tickets filed. In the 19 trials where payload content reached the assistant's own answer, all 19 acknowledged that the configuration did not answer the question; one additionally asserted a false association between a fictional vendor and an internal service. Escalation ran at 87.5% after the decoy fired against 85.0% when it did not, so continued tool use reflects the ungroundable request rather than the configuration export; firing is the model's own choice and is not randomised, so this contrast supports no causal claim.

Single-turn measurement, however, **undercounts exposure**: 33.33% of ungroundable trials called the decoy in turn 1, and 42.08% called it in either turn. Every rate in Studies 1–5 is a lower bound by roughly a quarter.

### 3.9 Study 7 — adversarial delivery is not supported

| retrieved content mentions | decoy, any turn | 95% CI |
|---|---|---|
| nothing external | 3/120 = 2.50% | 0.85 – 7.09% |
| a real vendor | 2/120 = 1.67% | 0.46 – 5.87% |
| an unfamiliar vendor | 4/120 = 3.33% | 1.30 – 8.26% |

Clean versus unfamiliar: **p = 1.0**. All nine positive trials fall on one stimulus and fire at 3/2/4 across the three conditions, i.e. flat — the user's own configuration question driving a configuration lookup, with the injected entity contributing nothing.

The unfamiliar interval tops out at 8.26% against a user-turn effect of 12–30% on the same model and decoy. **An effect of the magnitude this paper reports for user-delivered entities is excluded for content-delivered ones**; a small effect is not. The mechanism is tied to the referent of the *request*, not to the presence of an ungroundable entity in context. This bounds the security interpretation: an adversary able to write a dependency name or issue title does not thereby induce internal-tool invocation.

### 3.10 Study 8 — real, unmodified MCP catalogues

No injected decoy. Outcome is correct tool selection. 2,400 trials.

| catalogue × model | known | unfamiliar | ungroundable | gap | p (cluster) |
|---|---|---|---|---|---|
| git × `claude-sonnet-4-6` | 62.3% | 69.1% | **13.2%** | 49.1 pp | **0.0072** |
| git × `gpt-5.6-terra` | 78.2% | 85.9% | **20.0%** | 58.2 pp | **0.00085** |
| filesystem × `claude-sonnet-4-6` | 53.9% | 25.6% | **1.7%** | 52.2 pp | **0.032** |
| filesystem × `gpt-5.6-terra` | 1.7% | 0.0% | 0.0% | 1.7 pp | 0.497 |

Trial-level misselection gives the same result with greater power: git × claude 31.4% vs 5.5% (p = 7.9 × 10⁻¹³), git × gpt 43.6% vs 15.0% (p = 4.3 × 10⁻¹¹), filesystem × claude 98.3% vs 46.1% (p = 9.2 × 10⁻³³).

The fourth cell is **uninterpretable rather than null**: `gpt-5.6-terra` selects the required tool only 1.7% of the time even when the entity is familiar, because the catalogue's `list_allowed_directories` description instructs the model to call it before accessing files. That is a demand characteristic this single-turn design cannot separate from grounding failure.

An earlier run of the git catalogue with 5 triples returned p = 0.336 on effects of the same magnitude. Extending to 11 triples returned p = 0.00085. The cluster permutation test penalises cluster count, so **stimulus breadth, not run count, is the power lever** for designs of this shape.

### 3.11 Base rate and the unconditional false-positive rate

Every rate above is conditional on the request being ungroundable. The canary application depends on the unconditional rate. Classifying the 101 benign prompts of Study 1 against the same taxonomy gives **5.0%** carrying an ungroundable *external* entity. The classifier independently selects prompt 65 — the only prompt that ever fired the decoy in Study 1, at 9/9 — together with two prompts later shown anomalous in Studies 5 and 6.

| measurement | P(ungroundable) × P(decoy \| ungroundable) | of all requests |
|---|---|---|
| single-turn | 5.0% × 12.08% | **0.60%** |
| two-turn | 5.0% × 42.08% | **2.08%** |

At 100,000 agent requests per day this is 600–2,100 alerts. **A decoy tool firing on 1–2% of ordinary traffic does not satisfy the asymmetry that makes canary instrumentation useful.** Both inputs are soft — the base rate is a lower-bound proxy from a benign engineering set, the conditional rate is one model on one catalogue — and the order of magnitude rather than the decimals is the claim.

### 3.12 Study 9 — substitution is predictable from the tool schemas

A re-analysis of Study 8's trials, adding no data. Study 8 established that selection collapses; it did not say what is chosen instead. We fixed one hypothesis before analysing: an agent that cannot ground a referent cannot fill the argument naming it, so it substitutes a tool whose schema does not require that argument.

**Arity (confirmed).** Substituted tools require fewer arguments than the expected tool in every live cell: pooled Δ = −0.97 required arguments over 659 substitutions (554 lower, 16 higher, 89 level; sign test p = 2.6 × 10⁻¹⁴¹). A null model drawing uniformly from the same catalogue gives Δ = −0.25, so this is not an artefact of catalogue composition.

**The referent argument (confirmed but largely definitional).** The substitute lacks the expected tool's referent argument in 424/424 cases. This figure is inflated: in both catalogues nearly every referent argument is unique to its own tool, so any substitution necessarily drops it. The non-trivial subset — where another tool requiring the same argument existed — is 53/53, resting on a single argument pair (`branch_name`, shared by `git_checkout` and `git_create_branch`). Suggestive, not decisive.

**Condition-specificity (refuted).** The rule is condition-independent: mean arity Δ is −1.03 when the entity is grounded and known, −0.85 when unfamiliar, −1.01 when ungroundable. This contradicts our hypothesis as stated and yields a cleaner account:

> **Grounding failure determines the *rate* of misselection; schema arity determines its *direction*.**

The first is conditional and is measured in §3.10. The second holds unconditionally, and can be evaluated on a catalogue without running a model.

**The attractor (exploratory, added after the above failed).** A single argument-light orienting tool absorbs most substitution in its catalogue: `list_allowed_directories` (zero required arguments) takes 339/394 = 86.0% of filesystem misselections, `git_status` (one) takes 122/265 = 46.0% of git's. Arity is necessary but not sufficient — `git_status` and `git_diff_staged` both take one argument and substitution concentrates on the former — so arity predicts the candidate set and semantics selects within it.

This also reframes Studies 1–7 retrospectively. `internal_config_export` took a single optional argument in a registry of ten mostly two-argument tools: it was that catalogue's attractor. The decoy studies were observing this law through a narrow aperture.

### 3.13 Study 10 — mitigation transfer across vendors

Guard v1, guard v2 and baseline were rerun on `claude-sonnet-4-6` (5,040 trials, no errors, entity-free controls at n = 300). The baseline arm reproduces Study 4's figure for this model exactly: 12.64% on ungroundable requests, 24 days later and on a different endpoint.

| | `gpt-5.6-terra` | `claude-sonnet-4-6` |
|---|---|---|
| decoy, ungroundable | 12.08% → **1.39%** | 12.64% → **1.67%** |
| known-vendor utility | −1.39 pp (p = 0.123) | +3.33 pp (p = 0.211) |
| entity-free control utility | −5.67 pp (p = 0.0018) | **−20.67 pp** (p = 1.3 × 10⁻⁷) |

**The benefit transfers; the price does not.** Guard v2 removes 87–89% of the behaviour on both vendors with no measurable cost on requests naming a real vendor. Its collateral cost on entity-free controls is nearly four times larger on Sonnet, which also abstains on 23.67% of those controls at baseline against terra's 0.00% — the guard is acting on a model already disposed to stop and ask.

The consequence for reporting is that a single figure for the cost of this mitigation is not portable. Guard v1 remains a regression on both vendors (known-vendor utility 86.11% → 32.78% on Sonnet).

### 3.14 Study 11 — six model families, and a third failure mode

Study 8's design was run on four open-weights models through an OpenAI-compatible gateway (9,600 trials, no errors). Selection rule, declared before results were seen: the largest general-purpose instruct model per family advertising tool support, excluding vision, coder and thinking variants and anything below 30B.

| catalogue | model | known | ungroundable | gap | p |
|---|---|---|---|---|---|
| git | `qwen3-235b-a22b-2507` | 93.6% | **37.7%** | 55.9 pp | **0.0037** |
| git | `gpt-oss-120b` | 83.2% | **41.8%** | 41.4 pp | **0.0040** |
| git | `gemma-4-31b-it` | 65.5% | **27.3%** | 38.2 pp | **0.030** |
| git | `llama-3.3-70b-instruct` | 78.2% | 77.3% | 0.9 pp | 0.921 |
| filesystem | `gemma-4-31b-it` | 59.4% | **2.2%** | 57.2 pp | **0.032** |
| filesystem | `qwen3-235b-a22b-2507` | 36.7% | **0.6%** | 36.1 pp | **0.032** |
| filesystem | `llama-3.3-70b-instruct` | 61.7% | 63.9% | −2.2 pp | 0.846 |
| filesystem | `gpt-oss-120b` | 19.4% | 0.6% | 18.9 pp | void |

The effect replicates across **six model families from four organisations** on catalogues none of them authored. `openai/gpt-oss-120b` degrades by 41.4 pp on git where its hosted counterpart degrades by 58.2 pp, indicating a property of the model family rather than of a serving stack.

**`llama-3.3-70b-instruct` is a null on this metric.** Its grounded performance is already weak on the discriminating triples — 12/20, 13/20 and 15/20 correct when the entity is fully grounded, against 20/20 for `qwen3-235b` — leaving little room to fall. We initially inferred a further explanation: that on *"Show me the contents of our last deploy commit"* it invokes `git_show` 17 of 20 times while `git_show` requires a `revision` the prompt does not supply, so the call could only be made by fabricating one. Study 12 measured this directly and the inference was **wrong on that example** — llama supplies `HEAD` (17/20) or `main` (2/20), conventions rather than invented values. The claim is withdrawn and the corrected account is in §3.15.

Study 12 nonetheless confirms a third failure mode alongside the two characterised above:

| mode | behaviour | how it presents |
|---|---|---|
| substitution | a lower-arity tool avoiding the unfillable argument | wrong tool, honest result |
| resolution-seeking | internal lookup to identify the entity | decoy invocation |
| **fabrication** | the correct tool with an invented argument | **correct tool, silently wrong answer** |

Fabrication is the most damaging of the three and is **scored as success** by this study's metric. The inference follows from the schema — a required parameter with nothing available to fill it — but the harness records tool names and not arguments, so it cannot be confirmed from these data. The llama cells are therefore reported as null *on this metric*, with the metric itself noted as blind to fabrication.

### 3.15 Study 12 — recording call arguments

Every harness in Studies 1–11 records tool names and not arguments, so a model calling the required tool with an invented argument scores as a success. Study 12 records arguments for two open-weights models on both real catalogues (2,400 trials, no errors), classifying each supplied value against the prompt as `grounded` (present in the request), `default` (a convention such as `HEAD` or `main`) or `fabricated` (a specific value appearing nowhere in the prompt and not a convention).

Restricted to required, non-ambient arguments — excluding optional parameters, and excluding `repo_path`, which no stimulus supplies:

| model | known | ungroundable | p |
|---|---|---|---|
| `llama-3.3-70b-instruct` | 6.0% | **17.0%** | **1.3 × 10⁻⁶** |
| `qwen3-235b-a22b-2507` | 6.0% | 1.8% | 0.0028 |

The two models fail in opposite directions on identical stimuli. `qwen3-235b` collapses in tool choice (65.8% → 20.2% correct) while its fabrication rate falls; `llama-3.3-70b` holds its tool choice (57.2% → 62.8%) while its fabrication of required arguments nearly triples. Substitution and fabrication behave as complements rather than as points on one scale.

Correcting the metric — scoring a trial as successful only when the required tool is called *and* no required argument is fabricated — flips the sign of llama's effect from −5.5 pp to +5.5 pp, which is at least directionally sensible, but it remains non-significant (p = 0.137) against qwen's +41.2 pp (p = 9.3 × 10⁻³⁴). **Fabrication is real and grounding-dependent, and it does not account for llama's null.** That model is less affected than the other five families, not immune, and not merely concealing the effect in its arguments.

Of calls the tool-name metric scored correct on ungroundable requests, 51.8% of llama's carried a fabricated argument against 8.6% of qwen's. A further 15.5% and 16.0% respectively carried a conventional default, which is also a silently wrong answer — answering about `HEAD` when asked about "our last deploy commit" — and is likewise invisible to a tool-name metric.

---

## 4. Mechanism

> When a tool-using agent cannot ground an entity referenced in a request, because the entity is unnamed or named but unfamiliar, it invokes internal-lookup tools to resolve the entity before attempting the task.

The decoy that fires is the one plausibly answering *what is this thing?* A configuration export is a defensible way to discover which vendor an organisation uses; a credential dump is not. This accounts for the inversion of the a priori attractiveness ordering, and the tool distribution in §3.5 is consistent with a resolution attempt in progress.

**The general form.** Study 8 shows the decoy is incidental. What degrades is *tool selection itself*: when the referent cannot be grounded, the agent substitutes a broad, argument-light, orienting tool for the specific one the task requires — `git_log` for `git_show`, `list_allowed_directories` for `read_text_file`, configuration export for a status fetch. A decoy is simply a tool that is attractive to that substitution and that nothing else should call. The security framing is a special case of a capability failure.

**The direction of substitution is predictable without the model.** Study 9 (§3.12) separates rate from direction. Grounding failure governs how often misselection occurs; the tool schemas govern what is chosen instead, and that second half holds regardless of grounding condition. The substitute is reliably lower-arity, and a single argument-light orienting tool absorbs most of a catalogue's misselection. A catalogue can therefore be audited for this risk statically, before any agent is connected to it.

**Which component dominates is predictable from the domain.** Study 8 separates the two contributors more cleanly than Study 3 could. On `git`, unfamiliar referents cost nothing — 69.1% and 85.9%, at or above the grounded condition — and only ambiguity degrades selection. On `filesystem`, unfamiliarity costs 28 pp on its own and ambiguity a further 24. The difference is whether the domain permits resolution by inspection: an unrecognised commit hash or branch name is still something the tools can look up, whereas an unrecognised vendor is not. This replaces the "weighting is model-specific" conclusion of §5 with a stronger, falsifiable one: **the weighting is domain-specific, and its direction can be stated in advance from whether the referent is lookupable.**

**What the mechanism does not extend to.** Study 7 shows the trigger is the referent *of the request*. An ungroundable entity merely present in retrieved context does not produce the behaviour (p = 1.0). Study 6 shows that once the agent holds configuration it did not need, it does not forward it (0/720) and generally states that the result did not answer the question. The mechanism is a resolution attempt, not an exfiltration drive.

---

## 5. Findings withdrawn

We report five of our own hypotheses that did not survive, two of them preregistered.

**Attractiveness monotonicity.** Study 1 reported spurious invocation rising with assumed attacker-attractiveness (p = 0.014). It rested on nine observations and reverses at higher n in both vendors. Configuration export outfires credential listing in four of six models, ties in one, and reverses marginally in one (Sol: 4.17% vs 5.00%). **Attacker-attractiveness is the wrong heuristic for decoy placement.**

**A fixed ambiguity/unknowability split.** Study 3 decomposed the effect approximately 60% unknowability, 40% ambiguity. Study 4 shows the split direction is model-specific: `gpt-5.6-luna` (0.83% unresolved vs 7.22% fictional, p = 1.053 × 10⁻⁵) and `gpt-5.6-sol` (p = 0.02496) are driven almost entirely by unknowability; `gpt-5.6-terra` runs the opposite way (15.00% vs 5.83%, p = 7.583 × 10⁻⁵); Sonnet (p = 0.262) and Haiku (p = 0.871) show no significant difference. The mechanism is general; the weighting is not.

A third hypothesis, that invocation scales with model capability (Study 3: Sonnet vs Haiku OR = 2.92, p = 5.225 × 10⁻⁶), also failed to generalise. Neither vendor's ordering is monotonic in capability, and the balanced tier fires most in both.

**Preregistered prediction 2 — that raising reasoning effort would reduce the rate.** Study 5's protocol reasoned that more deliberation gives more opportunity to notice that internal tooling cannot identify an external vendor. On `gpt-5.6-terra` the rate doubled instead (6.11% → 12.08%, p = 1.05 × 10⁻⁴). It fell on the other two models. No directional claim about reasoning effort is supportable.

**Preregistered prediction 5 — that a well-formed entity-resolution guard would cost under 5 pp of ordinary utility.** Guard v1 cost 48 pp on entity-free controls; guard v2, after narrowing, still costs 5.67 pp (p = 0.0018). Neither passes the bar we set in advance. We had also expected the failure mode to be under-blocking; it was over-blocking.

**That substitution is specific to grounding failure.** Study 9 fixed the hypothesis that an agent substitutes a lower-arity tool *because* it cannot fill the referent argument, and therefore that the pattern would be stronger when the referent is ungroundable. It is not: mean arity change is −1.03 when the entity is grounded and known against −1.01 when it is ungroundable. The substitution rule is unconditional. What grounding failure controls is how often substitution happens, not what is substituted. The replacement account is stronger than the original, but it is a replacement, not a confirmation.

**An untested recommendation of our own.** §7 of the original preprint recommended failing closed on ungroundable entities. Guard v1 is that recommendation implemented literally, and it is a regression. We retain the recommendation only in the narrowed form of guard v2, and with its measured cost attached.

---

## 6. Limitations

Four limitations of the original preprint are discharged by Studies 5–8 and are marked as such. Two defects in our own published method were found and are recorded here rather than silently corrected.

**Discharged.**

- ~~Reasoning configuration.~~ Studies 5 rerun the OpenAI arms at the API default on the Responses API. The effect survives; the rate changes by a factor of two, in model-specific directions, and the API surface matters as much as the setting (§3.6).
- ~~Single-turn.~~ Study 6 returns realistic tool results and measures the second turn. Exposure is ~25% higher than single-turn measurement shows; forwarding does not occur (§3.8).
- ~~Adversarial delivery untested.~~ Study 7 tests it. It does not replicate (§3.9).
- ~~Schema drift between studies.~~ Studies 5–7 import the Study 4 stimuli rather than reimplementing them, making drift impossible by construction. Studies 1–4 remain non-poolable with each other as previously stated.

**Corrections to our own method.**

1. **A stated control was never implemented.** The original README, briefing and §2.1 of this preprint stated that tool position is shuffled per trial so that ordering cannot confound condition. No harness implemented it; the decoy occupied the final catalogue position in all 13,470 trials of Studies 1–4. A 400-trial control with seeded per-trial shuffling shows the profile is flat (last position 20.00% against 27.73% elsewhere, p = 0.60), so no published result depends on the correction, but the control was absent and the claim was wrong as written.
2. **Two of four matched controls are not entity-free.** "Fetch **our** public status page" and "the library **we depend on**" both carry ungroundable referents. They read as clean controls in Studies 1–4 only because `reasoning_effort=none` suppressed the behaviour; at the API default the first fires 3/30 and the second abstains 30/30 then hunts 30/30. "Controls at zero throughout" holds only for entity-free controls (0/1,260 across all baseline arms) and is qualified accordingly.

**Standing.**

3. **Stimulus authorship.** All prompt triples and fictional vendor names were generated with LLM assistance after the hypothesis was formed. Construct-fitting is not excluded. Independently authored stimuli are in collection.
4. **Ecological validity and base rate.** The unconditional estimate in §3.11 rests on a lexical classifier applied to our own benign prompt set, not on production traffic. It is a lower-bound proxy: prompts authored to be answerable select for groundable referents. One independent author, briefed blind, produced 20 realistic requests of which none fell in the target class. **Measuring how often real agent traffic contains ungroundable referents is the single most valuable thing we cannot do ourselves.**
5. ~~**Two vendors.**~~ **Discharged.** Studies 8 and 11 replicate the effect across six model families from four organisations (Anthropic, OpenAI, Alibaba, Google), including two open-weights families served through a third-party gateway.
6. **Run-to-run variance.** The named-vendor condition gave 0/360 in Study 2 and 8/360 in Study 3 with identical prompts.
7. **Stimulus set size.** Twelve triples in Studies 2–7; nine and eleven in Study 8. Per-triple breakdowns are released so concentration can be assessed directly.
8. **No true-positive measurement.** This work characterises false positives only. Whether a decoy tool detects an actual adversary is untested.
9. **Consequence is bounded at two turns and one payload.** The 0/720 forwarding result means forwarding does not occur within two turns on a payload containing no credentials. It is not evidence that it never occurs. A credential-shaped payload was rejected as prejudicial and remains untested, as does a longer horizon; the agent is frequently still searching when measurement stops.
10. **Study 7 excludes only a large effect.** The unfamiliar-condition interval reaches 8.26%. A content-delivered effect smaller than that is not excluded, and the injected content is inert rather than adversarially phrased.
11. **Guard v2 is post-hoc.** It was written after seeing guard v1 fail and is not covered by the Study 5 preregistration. It requires independent confirmation on fresh stimuli before it carries weight.
12. **Mitigations are single-model.** All three were evaluated on `gpt-5.6-terra`. Whether the description-scoping inversion is a property of that model or of tool descriptions generally is unknown.
13. **The correct-tool metric is blind to argument fabrication.** Studies 1–11 record tool names and not arguments, so a model calling the required tool with an invented argument scores as a success. Study 12 adds argument recording for two models on two catalogues and confirms the failure mode is real and grounding-dependent, but the remaining nine studies are unrevised: every "no effect" and every correct-tool rate in them should be read as "on this metric". Argument classification is itself lexical — a value semantically implied but not lexically present in the prompt is scored fabricated — and the conventional-defaults list is a judgement call fixed before the run.
14. **Mitigation cost is model-specific.** Guard v2's benefit transfers across vendors (87–89% reduction) but its collateral cost ranged 5.67–20.67 pp across the two models tested. No single figure for the cost of this mitigation is portable, and it has been evaluated on two models.
15. **Open-weights arms are not configuration-matched.** They run chat-completions with no reasoning-effort parameter, which §3.6 shows is a materially different configuration from the hosted arms. They are reported as a separate block and are not pooled.
16. **Study 9 uses a crude proxy.** Required-argument count stands in for what is presumably a richer notion of tool specificity, only the first tool call per trial is scored, and the attractor result (H4) is post-hoc. The referent-argument result is largely definitional on these two catalogues; its non-trivial subset rests on one argument pair.
17. **Two catalogue × model cells are uninterpretable.** `filesystem` × `gpt-5.6-terra` cannot speak to grounding in either direction, because the catalogue's own tool description creates a demand characteristic this design cannot separate from the effect.

---

## 7. Implications

**Catalogues can be audited before deployment.** The direction of misselection follows from the tool schemas alone (§3.12): substitution moves toward lower-arity tools, and concentrates on the catalogue's broadest argument-light orienting tool. That tool — `list_allowed_directories` in the reference filesystem server, `git_status` in the reference git server — is where misselection will accumulate, and it can be identified without running a model. Catalogue authors should expect an argument-light tool to absorb traffic it was not designed for, and reviewers of an MCP registry now have something concrete to look for.

**The finding is about tool selection, not decoys.** Correct tool selection falls 49–58 pp on ungroundable referents across real, unmodified MCP servers and both vendors, with no injected tool. Deployments should expect degraded tool choice — not merely spurious decoy calls — wherever requests refer to entities the agent cannot resolve. Possessive phrasing ("our CDN provider", "our staging directory") is the common natural-language form of this and is pervasive in ordinary requests.

**Decoy tooling is not viable as canary instrumentation for this class of tool.** Combining the base rate with the measured conditional rate gives 0.6–2.1% of all agent traffic (§3.11). The asymmetry that makes canary tokens valuable does not hold. Where a decoy is used anyway, place it where it cannot plausibly resolve a sub-goal: a credential-listing decoy is generally quiet, a configuration-export decoy is not, and attacker-attractiveness is the wrong heuristic.

**Report the configuration or the number is not comparable.** Reasoning effort and API surface each move the rate by a factor of two, in model-specific directions, and they can cancel. Any published rate must state both, and cross-model comparison is valid only within a fixed pair. Measurement should be multi-turn; single-turn undercounts by roughly a quarter.

**Prompt-level mitigation is available but not free.** Guard v2 removes 88% of the behaviour for 5.67 pp of collateral cost, concentrated entirely on requests carrying a possessive referent. The unsolved design problem is distinguishing *our X*, which the team's own tools can often resolve, from *our third-party X*, which they cannot. Tool-description scoping is not a substitute: the one wording we tested inverted, raising invocation by 22 pp on the condition it targeted.

**Detection.** The anomaly is not in the request, the permissions, or the user. A least-privilege gateway observes a correctly permissioned agent making an authorised call on behalf of a user with normal history. The signal resides in the grounding state of the entity under discussion, which no current control measures — and which, per §3.11, is a lexically detectable property of the request.

**Failure modes are not interchangeable.** Substitution returns a true answer about the wrong thing; fabrication returns a false answer about a thing that does not exist, and passes a correct-tool check. Evaluations that score only which tool was called will report the second as a success. Any benchmark in this area should score arguments as well as tool identity.

**Tractability.** `claude-opus-5` recorded one invocation in 1,200 trials, significantly below three of the five other models tested. Together with the fact that the effect is a capability failure rather than an adversarial one, this suggests the behaviour is amenable to training intervention.

**What this work does not support.** It does not show exfiltration: across 720 two-turn trials no configuration was forwarded. It does not show an attack primitive: an ungroundable entity arriving through retrieved content produces no effect. Claims in either direction should not be drawn from this paper.

---

## 8. Availability

Harnesses, per-trial raw data for all eight studies, the Study 5 preregistration, and analysis scripts: github.com/ShroudLabs/ungrounded-agents
Archived release: 10.5281/zenodo.21958705

All runs are resumable. Derived columns are recomputed from the raw tool-call record at analysis time, so a scoring definition can be corrected without rerunning a trial — a facility used twice, once when a leakage metric was found to be scoring correct behaviour as harm, and once when a resolution-seeking detector was found to undercount by roughly 80× because the model asks by imperative rather than by question.

**A cross-vendor reproducibility hazard.** An exhausted account is reported as HTTP 429 with `insufficient_quota` by one vendor and HTTP 400 with "credit balance is too low" by the other. Harnesses that treat 429 as rate limiting and 400 as a malformed request will retry the first indefinitely and strip parameters from the second, in both cases presenting a dead account as a slow or misconfigured run. Both failure modes occurred during this work.

---

## Acknowledgements

[Independent stimulus authors, once they have consented to be named.]

## References

[1] Thinkst Applied Research. Canary and Canarytokens. https://canary.tools
[2] Model Context Protocol specification. https://modelcontextprotocol.io
[3] Wilson, E.B. (1927). Probable inference, the law of succession, and statistical inference. *JASA* 22(158), 209–212.
[4] Armitage, P. (1955). Tests for linear trends in proportions and frequencies. *Biometrics* 11(3), 375–386.
[5] Beurer-Kellner, L. and Fischer, M. (2025). MCP Security Notification: Tool Poisoning Attacks. Invariant Labs. https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks
[6] MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP Servers (2025). arXiv:2508.14925
[7] Wang et al. (2025). MCP Preference Manipulation Attack (MPMA). arXiv:2505.11154
[8] CVE-2025-66416. Model Context Protocol Python SDK does not enable DNS rebinding protection by default. CWE-1188. Fixed in mcp 1.23.0. GHSA-9h52-p55h-vw2f
[9] CVE-2025-66414. Model Context Protocol TypeScript SDK, equivalent defect. Fixed in 1.24.0.
[10] OWASP MCP Top 10 (2025). MCP03:2025 — Tool Poisoning.
