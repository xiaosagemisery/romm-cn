# Translation provider plan

Status: the provider chain, the failure pause, the `microsoft` provider and the `google` provider are implemented in `backend/utils/translator.py`. The `microsoft` provider has only been tested against a mocked HTTP client, because no key was available. The keyless Edge route and any keyed Tencent, Baidu or Alibaba provider are not built.

Replace the Google Translate step with a free provider that works from mainland China, without making every user create an account first.

## Problem

`backend/utils/translator.py` calls `translate.googleapis.com`, an unofficial keyless endpoint. From mainland China it is blocked or very slow, so every scanned game waits for the timeout and keeps its English summary. The project is meant for mainland users, so the default provider has to be reachable there.

## Requirements

- Free, and usable out of the box without an account, like the Google endpoint was.
- Reachable from mainland China without a proxy.
- A failing provider must not slow a scan down: no repeated timeouts.
- Existing behavior stays: failures return the original text, results are cached in memory, the game title is still protected with a placeholder, and tests never reach the network.

## Candidates

| Provider | Key needed | Free allowance | Mainland access | Notes |
| --- | --- | --- | --- | --- |
| Microsoft Edge translate endpoint (`edge.microsoft.com/translate/auth` for a token, `api-edge.cognitive.microsofttranslator.com/translate`) | No | No published limit | Normally reachable | Not documented or supported by Microsoft. The token endpoint answers 404 now (see the live check), so it is not usable. |
| Azure Translator, official (F0 tier) | Yes (Azure account, key and region) | About 2 million characters per month | Global endpoint unverified; Azure China has its own endpoint (`api.translator.azure.cn`) | Same wire format as the Edge endpoint, so supporting it costs little. Sign-up reportedly needs an international card. |
| Tencent Cloud TMT | Yes (real-name account) | Reported 5 million characters per month | Yes | Official, but every user needs their own keys. |
| Baidu Fanyi | Yes (real-name account) | Reports disagree (50 thousand to 1 million per month) | Yes | Official, quota unclear. |
| Alibaba Cloud machine translation | Yes | Reported 1 million characters per month | Yes | Official, quota unverified. |
| Google (current) | No | None published | Blocked or slow | Kept only as an opt-in fallback. |
| MyMemory, public LibreTranslate instances | No | Small daily caps, rate limits | Unverified | Quality and quotas are too weak for scanning a library. |

Quotas above come from secondary sources and must be checked on each vendor's pricing page before anyone depends on them. None of these hosts could be reached from the development sandbox, so reachability from China is based on how the services are generally used, not on a test run.

## Findings from the live check

Run on 2026-11-06 after the hosts were allowed in the development sandbox:

- `api-edge.cognitive.microsofttranslator.com/translate` is reachable and answers 401 without a token, as expected.
- `edge.microsoft.com/translate/auth`, the token endpoint the keyless route depends on, answers 404 with an empty body, with a plain client identifier and with a browser-style one. The keyless Edge route therefore cannot be used as planned, and no working keyless token source was found.
- Faking an Edge browser identity to get past this was not pursued: the endpoint is internal to Edge and undocumented.

## Decision

1. **Provider chain with a failure pause.** Whatever provider is chosen, a failing one must not slow a scan down, and users must be able to swap providers by configuration.
2. **Official Azure Translator (`microsoft`) is the first provider.** It is documented, free up to the F0 allowance, and has an Azure China endpoint (`api.translator.azure.cn`). It needs a key, so it is skipped when none is set.
3. **Google stays as the next provider in the default chain,** so installs without a key behave as before. Users in mainland China set a key, or list only the providers they can reach.
4. **The keyless Edge route is not built** because its token endpoint is gone (see the findings). A keyless, stable and mainland-reachable provider does not currently exist among the candidates, so the remaining choice is which keyed provider to support next. That is an open question for the project owner.

## Design

### Provider chain

`TRANSLATION_PROVIDERS` is an ordered, comma-separated list. The default is `microsoft,google`. Valid names are `microsoft` and `google`. `translate_text` tries them in order and returns the first successful result; if all fail it returns the original text, as today.

### Failure handling

A provider that fails (timeout, HTTP error, malformed response) is skipped for five minutes. Without this, an unreachable provider would add its timeout to every game in a scan. After the pause it is tried again. If no provider is available the original text is returned immediately.

### Microsoft wire format

- Request: `POST {endpoint}/translate?api-version=3.0&to=<code>` with a JSON body `[{"Text": "..."}]`. `from` is omitted when the source is detected automatically.
- Response: `[{"translations": [{"text": "...", "to": "zh-Hans"}]}]`.
- Language codes map from the app's codes: `zh-CN` to `zh-Hans`, `zh-TW` to `zh-Hant`, `en` stays `en`.
- Headers: `Ocp-Apim-Subscription-Key` carries the key and `Ocp-Apim-Subscription-Region` the region when one is set.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TRANSLATION_PROVIDERS` | `microsoft,google` | Ordered provider list. |
| `MICROSOFT_TRANSLATOR_KEY` | empty | Key for the official Azure Translator. Required when `microsoft` is listed. |
| `MICROSOFT_TRANSLATOR_REGION` | empty | Azure resource region. Required for multi-service and regional resources. |
| `MICROSOFT_TRANSLATOR_ENDPOINT` | `https://api.cognitive.microsofttranslator.com` | Set to `https://api.translator.azure.cn` for Azure China. |

`microsoft` without a key is skipped with a warning and does not start the failure pause.

### Unchanged

The title placeholder (`ZQX0ZQX`), the in-memory cache, the Wikidata title lookup and the search-term translation keep working through `translate_text`. Call sites do not change.

## Testing

- Unit tests per provider with a mocked HTTP client: success, HTTP error, malformed body, token reuse and refresh, language code mapping.
- Chain tests: first provider fails and the second answers, all fail and the original text comes back, a failed provider is skipped for five minutes and retried after.
- The autouse test fixture keeps patching `translate_text`, so no test reaches the network.
- A live check of the official endpoint needs a key and has not been run; the placeholder check stays open until one is available.

## Risks

- Without a key, users in mainland China still hit Google, which is blocked or slow there. Mitigation: the failure pause limits the cost to one timeout every five minutes, and the README says to set a key.
- Azure sign-up may need an international card, and the quota figures come from secondary sources. Mitigation: they are listed as unverified, and the provider interface leaves room for Tencent, Baidu or Alibaba.
- The placeholder may not survive on a new provider. Mitigation: the existing fallback translates the summary without it.

## Documentation and rollout

Update `README.md`, `ChangeFromUpstream.md`, `project.md`, `env.template` and `examples/docker-compose.romm-cn.yml` in the same change, replacing the "needs Google" notes. Existing deployments keep working with no action, because the default chain ends in Google. Anyone in mainland China sets `MICROSOFT_TRANSLATOR_KEY` (and the Azure China endpoint if needed), or sets `TRANSLATION_PROVIDERS` to the providers they can reach.

## Open questions

- Which keyed provider to add next for mainland users who have no Azure account (Tencent Cloud TMT, Baidu Fanyi or Alibaba Cloud), since no keyless route works.
- Whether to run a keyless route that depends on a Bing web page token. It is fragile and not allowed to be tested from the sandbox, so it is not planned.
