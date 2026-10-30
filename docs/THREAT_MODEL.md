# Threat model - what TraceGuard AI can and cannot do

TraceGuard AI is an investigation aid, **not antivirus**. A status of LOW OBSERVED RISK means "no significant
issue in the signals checked", never "safe".

## Can detect (when configured)
- Hostnames matching a threat-intelligence provider's list (Safe Browsing or the local mock fixture).
- Heuristic indicators on the hostname (lookalike/spoofing patterns) and observed redirect hops between hostnames.
- Relationships between visited sites, observed redirect sources, and external domains the extension reports.

## Cannot detect
- Malicious page *content*, drive-by exploits, malicious downloads, or anything inside encrypted traffic.
- Threats on pages never navigated to, or in excluded domains, incognito windows, `chrome://` and file URLs.
- Brand-new malicious domains absent from provider lists. **No match is not proof of safety.**
- Request-level behaviour: Manifest V3 `webNavigation` gives hostnames and outcomes, not full traffic inspection.

## Evidence classes
| Class | Meaning | Example |
|---|---|---|
| Confirmed | Provider reputation match | Safe Browsing hit |
| Heuristic | Rule-derived, labelled `is_inferred` | Lookalike of a popular brand |
| Unknown | Provider timeout / rate limit / no data | Never mapped to safe |

## Data handling
Collected: normalized hostname, timestamp, outcome, observed redirect source host, observed external hostnames.
Never collected: URLs with path/query/fragment, page content, form values, cookies, tokens, keystrokes, raw audio.
Reputation providers receive **domains only**. LLM providers receive only the evidence the agent retrieved for the
current question, and only when an LLM is enabled in configuration.

## Known limitations of this build
See docs/STATUS.md: graph vertices are not yet per-user isolated, and several privacy endpoints are pending.
Do not host this for multiple users until those items are closed.
