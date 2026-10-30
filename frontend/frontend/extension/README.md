# TraceGuard AI – Chrome Extension (Manifest V3)

## Build and load (Windows)

```powershell
cd D:\frontend\extension
npm install
npm run build
```

Then in Chrome: `chrome://extensions` → turn on **Developer mode** → **Load unpacked** → choose `D:\frontend\extension\dist`.
After code changes, run `npm run build` again and click the reload icon on the extension card.

## Permissions (why each is needed)

| Permission | Why |
|---|---|
| `webNavigation` | Detect top-level navigations, errors and redirects to build a hostname-only event. |
| `storage` | Event queue, settings, recent alerts and per-tab status (`chrome.storage.local/session`). |
| `notifications` | HIGH RISK / configured-severity alerts with a "View evidence" button. |
| `alarms` | MV3 workers sleep; an alarm retries the queue with backoff and prunes old alerts. |
| `tabs` | Read the active tab's host for the popup and set the per-tab badge. |
| `scripting` | Inject the optional warning banner into a flagged tab only. |
| host `http://localhost:8000/*` | The default dev backend. Other backends are requested at runtime from Options. |
| optional host `<all_urls>` | Only if you click "Allow in-page warning banner" in Options. |

## Privacy

Only the normalised hostname, event type, timestamp, random event id and (when observed) the previous host are sent.
Never URLs with path/query/fragment, page content, form values, cookies, tokens or keystrokes. Incognito,
`chrome://`, `file://`, extension pages and excluded domains are skipped. Nothing is collected until consent is given.

## Backend contract (assumed)

`POST {backend}/api/v1/extension/events` with `Authorization: Bearer <token>` and the event JSON. The extension expects
`{ "assessment": { "severity": "HIGH_RISK|SUSPICIOUS|NEEDS_REVIEW|LOW_OBSERVED_RISK|UNKNOWN", "reason": "...", "finding_id": "...", "redirects": [] } }`.
Any other response is treated as "not assessed", never as safe. Adjust `parseAssessment` in `src/background/pipeline.ts` if your API differs.

## Demo

Demo mode (default) uses synthetic fixtures only (`.invalid` / `.test` domains), no backend. The popup's demo buttons apply a
scenario to the active tab, fire the notification, and show the in-page banner if site access was granted.
