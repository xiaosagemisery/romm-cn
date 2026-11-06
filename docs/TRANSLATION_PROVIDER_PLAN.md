# Translation provider plan

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
| Microsoft Edge translate endpoint (`edge.microsoft.com/translate/auth` for a token, `api-edge.cognitive.microsofttranslator.com/translate`) | No | No published limit | Normally reachable | Not documented or supported by Microsoft. It is the service the Edge browser's built-in translator uses, and many open-source clients call it. It can change or be throttled without notice. |
| Azure Translator, official (F0 tier) | Yes (Azure account, key and region) | About 2 million characters per month | Global endpoint unverified; Azure China has its own endpoint (`api.translator.azure.cn`) | Same wire format as the Edge endpoint, so supporting it costs little. Sign-up reportedly needs an international card. |
| Tencent Cloud TMT | Yes (real-name account) | Reported 5 million characters per month | Yes | Official, but every user needs their own keys. |
| Baidu Fanyi | Yes (real-name account) | Reports disagree (50 thousand to 1 million per month) | Yes | Official, quota unclear. |
| Alibaba Cloud machine translation | Yes | Reported 1 million characters per month | Yes | Official, quota unverified. |
| Google (current) | No | None published | Blocked or slow | Kept only as an opt-in fallback. |
| MyMemory, public LibreTranslate instances | No | Small daily caps, rate limits | Unverified | Quality and quotas are too weak for scanning a library. |

Quotas above come from secondary sources and must be checked on each vendor's pricing page before anyone depends on them. None of these hosts could be reached from the development sandbox, so reachability from China is based on how the services are generally used, not on a test run.

## Decision

1. **Default: the Edge translate endpoint.** It is the only candidate that is free, keyless and normally reachable from mainland China, which is what the Google endpoint offered.
2. **Official Azure Translator as the supported option.** Users who want a stable, documented service set a key. It reuses the same request code with a different endpoint and header, including the Azure China endpoint.
3. **Google stays, off by default.** Users outside China can add it to the provider list.
4. Keyed Tencent, Baidu and Alibaba providers are not built now. The provider interface leaves room for them if the Edge endpoint proves unreliable.

## Design

### Provider chain

`TRANSLATION_PROVIDERS` is an ordered, comma-separated list. The default is `edge`. Valid names are `edge`, `microsoft` and `google`. `translate_text` tries them in order and returns the first successful result; if all fail it returns the original text, as today.

### Failure handling

A provider that fails (timeout, HTTP error, malformed response) is skipped for five minutes. Without this, an unreachable provider would add its timeout to every game in a scan. After the pause it is tried again. If no provider is available the original text is returned immediately.

### Microsoft wire format (edge and microsoft)

- Request: `POST {endpoint}/translate?api-version=3.0&to=<code>` with a JSON body `[{"Text": "..."}]`. `from` is omitted so the service detects the language.
- Response: `[{"translations": [{"text": "...", "to": "zh-Hans"}]}]`.
- Language codes map from the app's codes: `zh-CN` to `zh-Hans`, `zh-TW` to `zh-Hant`, `en` stays `en`.
- `edge`: the bearer token comes from `GET https://edge.microsoft.com/translate/auth`, is cached in memory until shortly before it expires, and is fetched again after a 401.
- `microsoft`: the `Ocp-Apim-Subscription-Key` and `Ocp-Apim-Subscription-Region` headers carry the user's key and region.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TRANSLATION_PROVIDERS` | `edge` | Ordered provider list. |
| `MICROSOFT_TRANSLATOR_KEY` | empty | Key for the official Azure Translator. Required when `microsoft` is listed. |
| `MICROSOFT_TRANSLATOR_REGION` | empty | Azure resource region. Required for multi-service and regional resources. |
| `MICROSOFT_TRANSLATOR_ENDPOINT` | `https://api.cognitive.microsofttranslator.com` | Set to `https://api.translator.azure.cn` for Azure China. |

`microsoft` without a key is skipped with a warning.

### Unchanged

The title placeholder (`ZQX0ZQX`), the in-memory cache, the Wikidata title lookup and the search-term translation keep working through `translate_text`. Call sites do not change.

## Testing

- Unit tests per provider with a mocked HTTP client: success, HTTP error, malformed body, token reuse and refresh, language code mapping.
- Chain tests: first provider fails and the second answers, all fail and the original text comes back, a failed provider is skipped for five minutes and retried after.
- The autouse test fixture keeps patching `translate_text`, so no test reaches the network.
- A live check against the real endpoints, once the hosts are reachable from the sandbox: translate a sentence containing the placeholder and confirm the placeholder survives.

## Risks

- The Edge endpoint is undocumented. It may change, require different headers or be throttled. Mitigation: the five-minute pause keeps scans fast, the `microsoft` provider is the supported path, and the chain can fall back to another provider.
- Reachability from mainland China is not tested here. Mitigation: the chain and pause behavior, plus the `microsoft` option with the Azure China endpoint.
- The placeholder may not survive on a new provider. Mitigation: the existing fallback translates the summary without it.

## Documentation and rollout

Update `README.md`, `ChangeFromUpstream.md`, `project.md`, `env.template` and `examples/docker-compose.romm-cn.yml` in the same change, replacing the "needs Google" notes. Existing deployments get Edge by default with no action. Anyone who wants Google back sets `TRANSLATION_PROVIDERS=google`.

## Open questions

- Whether the Edge endpoint works from the user's mainland network (needs a check there).
- Whether to add a keyed Tencent or Baidu provider if the Edge endpoint turns out to be unreliable.
