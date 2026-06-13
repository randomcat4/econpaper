# Search Tier Boundary Probe Summary / 搜索分层边界探针总报告

Date: 2026-06-13

Scope: only external Codex child runs performed paper-access probing. This instance prepared prompts/schema, observed outputs, and wrote the report. It did not perform the paper-access probing itself.

范围：真实访问与论文可达性尝试均由外部 Codex 子进程执行；本实例只准备 prompt/schema、观察输出并写报告。

## Implementation Verdict

结论：另一个 code 叉不是纯 toy，但边界处理在这轮之前有 toy 味。L1 检索处方、ingest 解析、Paper Store 合约已经有可用骨架；L2 过窄，且可能把未完成/降格结果包装成成功；L3 主要还是围绕 L2 的编排壳，没有真正给出无登录态下的访问边界审计。

本轮已把 search stack 改成 fail closed：

- L2 official API search now includes OpenAlex and arXiv Atom. Crossref remains for citation verification and DOI truth.
- Offline mode, source outage, API budget exhaustion, and L3 internal failure are hard boundaries, not downgraded successes.
- Partial candidates/evidence may be retained, but the result is marked blocked when required sources were not actually queried.
- A new auth-gated boundary probe runs a separate Codex child process, records raw/final JSON, and classifies what can be reached without publisher login.

## Probe Runs

| Run | Conditions | Selected | Metadata | PDF handle/readiness | Text extracted/readiness | Login | Paywall/forbidden | Captcha/bot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `mixed_arxiv_local_30` | 15 arXiv + 15 local PDFs | 30 | 30 | 30 | 0 | 0 | 0 | 0 |
| `no_login_access_boundary` | 10 arXiv + 10 DOI/publisher + 10 local PDFs | 30 | 30 | 20 | 20 | 0 | 0 | 8 |
| `paper_store_contract_boundary` | 15 arXiv + 15 local PDFs | 30 | 30 | 30 | 30 | 0 | 0 | 0 |

Detailed outputs:

- `reports/boundary_probe_formal/mixed_arxiv_local_30/final.json`
- `reports/boundary_probe_no_login/no_login_access_boundary/final.json`
- `reports/boundary_probe_paper_store_contract/paper_store_contract_boundary/final.json`

## Observed Capability Boundary / 观察到的能力边界

arXiv:

- Public arXiv API, abstract pages, and PDF byte-range/header probes work without login.
- The child runs could verify canonical PDF handles with HTTP `206` and `application/pdf`.
- For arXiv, `full_text-ready` means a legal open PDF candidate is ready for the normal ingestion/extraction pipeline. Some runs intentionally stopped after range probes instead of full download.
- 中文解释：arXiv 在无登录态下可拿到元数据、摘要页，并确认 PDF 句柄；部分运行只做 range/header 探测，没有全量下载。

Local `D:\论文库中文1pdf`:

- Existing local PDFs can be selected, opened, and classified without web access.
- One run found the child environment lacked PyPDF2, so local text extraction was blocked by `text_extractor_unavailable`.
- A later run used PyMuPDF and extracted first-two-page text from all 15 selected local PDFs, with at least 518 extracted characters per file. No selected local PDF hit `pdf_no_text_layer` in that run.
- 中文解释：本地白名单 PDF 能打开、能分类；环境里有 PyMuPDF 时可抽取文本，没有 extractor 时必须显式标边界，不能伪装成全文成功。

DOI/publisher pages without login:

- DOI content negotiation/CSL metadata often succeeds even when the publisher page is blocked.
- AEA, SAGE, OUP/QJE, Chicago, and PNAS examples returned public `403` Cloudflare/captcha-like pages in this no-login environment.
- Cambridge Core and Elsevier examples exposed public landing/metadata pages but no simple public PDF entitlement in the capped probe.
- No institutional proxy, publisher account, credentialed session, Sci-Hub, shadow library, captcha bypass, or login bypass was used.
- 中文解释：没有各论文网站登录态时，多数 DOI/publisher 只能做到 metadata/landing page；遇到 403、bot-check、无公开 PDF 链接即停。

## Practical Contract

- `bibrecord_only`: metadata/page evidence exists, but no usable PDF handle was found or legally reachable.
- `pdf_no_text_layer`: a PDF handle exists, but first-pass extraction is too thin and should go to OCR.
- `full_text-ready`: a PDF handle is available and either text was extracted locally or, for arXiv, the open PDF is ready for normal ingestion extraction.

## Next Engineering Edges

- Add MinerU/Marker/PyMuPDF extraction as explicit Paper Store stages with provenance, not hidden secondary success.
- Persist final URL, HTTP status, content type, byte count, and boundary label per paper.
- Keep DOI-only publisher results as metadata-only until a legal open-access copy, author manuscript, or subscription entitlement is available.
