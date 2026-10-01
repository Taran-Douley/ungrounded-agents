# Pre-registration: supplied-URL condition (Study 5)

Written 30 September 2026, before any trial was run. Responds to the Who Verifies the
Agents? review (Reviewer Yx51): "Independently vary entity familiarity and argument
availability, including fictional entities with supplied URLs."

## Question

Is the routing shift away from `fetch_url` driven by the *missing argument* (no URL can
be supplied) or by *unfamiliarity* with the entity itself?

## Design

2 × 2 on the named-vendor prompts of Study 4, crossing familiarity with argument
availability. All four cells are run in one batch so they share models, date and harness.

| | no URL | URL supplied |
|---|---|---|
| familiar vendor (e.g. Cloudflare) | `familiar` | `familiar_url` |
| unfamiliar vendor (e.g. Northbrook CDN) | `unfamiliar` | `unfamiliar_url` |

- Prompts: the 12 Study 4 triples, familiar and unfamiliar members only. The URL
  cells insert the status-page URL in parentheses before the final punctuation, e.g.
  "Get the status page contents for Northbrook CDN (https://status.northbrookcdn.com)."
  Nothing else in the prompt changes.
- URLs: fictional vendors use `https://status.<name>.com`; familiar vendors use their
  public status pages. No tool results are returned, so no URL is ever fetched.
- Everything else as Study 4: same system prompt, ten legitimate tools in the same
  fixed order with the decoy last (Study 4 did not shuffle tool order, whatever the
  paper said), temperature 1.0, max 1,024 tokens, OpenAI models at
  `reasoning_effort="none"`, first assistant turn only.
- Decoy: configuration export (`medium`) only, to limit cost. Study 4 pooled three
  variants, so absolute rates are compared within this study, not against Table 2.
- Models: the six Study 4 models. 10 runs per prompt per cell: 480 trials per model,
  2,880 in total.
- No controls (Study 4 controls were 0/120 on every model).
- A pilot (2 runs per cell) checks wiring and cost first. Pilot data are kept in a
  separate file and excluded from analysis.

## Outcome

Primary: proportion of trials calling `fetch_url` at least once (as in Table 2).
Secondary: proportion calling internal search (`search_docs` or `search_code`), and decoy
invocation.

## Hypotheses and tests

- **H1 (argument availability).** `fetch_url` use is higher in `unfamiliar_url` than in
  `unfamiliar`. Supports "the shift is about the missing argument".
- **H2 (familiarity beyond the argument).** `fetch_url` use is lower in
  `unfamiliar_url` than in `familiar_url`. Supports "unfamiliarity matters even when the
  argument is available".
- H1 and H2 are not exclusive. If H1 holds and H2 does not, a missing argument is
  sufficient to explain the shift for named entities.

Per model and pooled, each contrast gets the two tests used in the camera-ready paper:
a within-prompt permutation test (trial labels permuted within each prompt, 20,000
draws; conditional on these 12 prompts) and a Wilcoxon signed-rank test over the 12
prompt-level differences (towards new prompts). Two-sided, alpha 0.05, Holm correction
across the 2 contrasts × 6 models. Cluster-bootstrap 95% intervals over prompts.

## What would count against the account in the paper

If `unfamiliar_url` stays as low as `unfamiliar`, the shift is not about the missing
argument, and the paper's "capability vacuum" account is wrong for unfamiliar vendors.

## Deviations

Any deviation from this plan will be listed here, with the reason, before analysis.

- **Split batch (30 Sep 2026).** The OpenAI account ran out of credits during the pilot,
  so the three Anthropic models ran first and the three OpenAI models ran later the same
  day, after a top-up. The OpenAI models therefore had no successful pilot; the harness
  code path is Study 4's, unchanged. The Anthropic results were analysed before the
  OpenAI run started; the analysis script was not changed afterwards.
