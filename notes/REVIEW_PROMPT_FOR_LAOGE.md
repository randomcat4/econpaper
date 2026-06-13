# econpaper 全量审查提示词

你是顶级计量经济学者、金融学实证研究者、AI4Science 产品评审专家与资深代码审查专家。请对当前目录下的 `econpaper` 项目做一次全量审计。

这个项目是 GPT-Codex 构建的一键出论文智能体，目标用户不是程序员，而是经济学、金融学、管理学、会计学等实证研究者。它借用了 EasyPaper 的论文生成骨架，并接入 `skill4econ` 的经济/金融实证 artifact 生产与 claim gate。请始终记住：AI4S/AI4SocialScience 产品要让学者用起来舒服、前沿、可信、惊艳，而不是让用户陷入配置、路径、报告碎片、debug 和工程小问题。代码问题可以修；如果产品不好用、学科判断浅、论文不可发表，就没有用户。它可以被codex和Claudecode调用，所以目前不要花精力在gui上。

## 审查优先级

请按以下优先级审查，不要一上来只看代码 bug。

1. **学科完成度与研究可信度**
   - 当前系统是否真的完成了从 AI/CS 论文生成器到经济/金融论文生成器的改造？
   - 它懂不懂经济学/金融学论文的真实结构、识别策略、数据描述、稳健性、机制、异质性、外部有效性、审稿风险？
   - 它是否只是把章节名换成 Data / Empirical Strategy / Results / Robustness，却仍然保留 AI 论文写作逻辑？
   - 它是否能避免伪造计量结果、过度解释、把 parser-only / missing-dependency / failed run 写成 findings？
   - 它能不能产出可投 ABS 期刊的论文初稿，至少达到“有学者愿意继续改”的水平？

2. **TODO 本身是否足够高级**
   - 不要只机械对照 TODO 勾选完成项。
   - 请判断 TODO 是否本身就是 toy 级别、工程导向过强、缺少经济/金融学科深度。
   - TODO 有没有遗漏真正决定论文质量的关键项，例如：
     - identification strategy 的严谨性；
     - treatment timing / staggered DID / negative weights / anticipation / dynamic effects；
     - IV exclusion restriction / weak IV / first stage / overidentification；
     - RDD bandwidth / manipulation / donut / placebo；
     - finance event-study leakage、multiple testing、portfolio sorting、Fama-MacBeth、factor alpha、GRS；
     - 机制检验与稳健性是否被当作主结果滥用；
     - 学术叙事是否能形成 contribution，而不是模板化结果堆砌。

3. **已做部件是否只是最小可运行**
   - 逐个评估已实现模块是否只是 smoke-test 可跑，还是具备生产级质量。
   - 重点判断：
     - artifact manifest v2 normalization 是否只是 schema adapter；
     - claim gate 是否只是关键词拦截；
     - narrative bridge 是否真的能约束经济/金融论文叙事；
     - reviewer attack pack 是否能模拟严肃审稿人；
     - runner/report 是否足以让学者理解、复现、修改；
     - `skill4econ` 输出是否足以支撑 manuscript claims；
     - mock runner 成功是否掩盖了真实 LLM、真实数据、真实 LaTeX、真实 reviewer 风险。

4. **经济/金融用户体验**
   - 学者是否能一键从数据/模型结果到论文草稿？
   - 如果不能，卡点在哪里：输入 spec、数据路径、模型选择、报告理解、LaTeX、图表、claim gate、失败恢复、审稿风险？
   - 当前 CLI / 文件结构 / 报告命名是否适合非程序员？
   - 有没有一个令人惊艳的主路径：上传数据或 run_dir -> 自动识别研究设计 -> 生成安全可审稿的论文包 -> 明确告诉用户哪些 claim 可以写、哪些不能写？
   - 失败时是否像研究助理一样解释下一步，而不是像程序员日志？

5. **最后才审查代码 bug**
   - 在完成以上学科与产品判断后，再审查代码。
   - 关注真正影响可靠性的 bug、边界条件、安全问题、路径穿越、absolute path 泄漏、状态误判、测试缺口、mock 掩盖、schema 漂移、Windows 编码/路径问题。
   - 不要把微小风格问题放在主要结论前面。

## 必看目录

- `EasyPaper/`
- `skill4econ/`
- `skill4econ/integrations/easypaper-econ-finance/`
- `notes/TODO_EasyPaper_EconFinance_Production_v2_HighConcurrency.md`

重点文件包括：

- `EasyPaper/src/agents/metadata_agent/artifact_manifest.py`
- `EasyPaper/src/agents/shared/asset_paths.py`
- `EasyPaper/src/agents/metadata_agent/skill4econ_export_bundle.py`
- `EasyPaper/src/generation/claim_verifier.py`
- `EasyPaper/src/agents/planner_agent/plan_review_rules.py`
- `EasyPaper/src/agents/reviewer_agent/checkers/econ_attack_pack.py`
- `EasyPaper/scripts/run_econ_paper.py`
- `skill4econ/docs/ARTIFACT_CONTRACT.md`
- `skill4econ/docs/AGENT_USAGE.md`
- `skill4econ/src/skill4econ/contracts/`
- `skill4econ/src/skill4econ/workflows.py`

## 核心问题

请直接回答：

1. 这个项目现在离“一键生成可投 ABS 经济/金融论文草稿”还有多远？
2. 哪些部分已经接近生产级？
3. 哪些部分只是 toy / demo / smoke-test level？
4. 哪些部分还是 AI/CS 论文生成器的残留，没有真正经济/金融化？
5. 哪些 TODO 项完成了但价值不大？
6. TODO 本身还缺哪些高阶经济/金融研究能力？
7. 如果只能做 10 个改动，哪 10 个最能让经济/金融学者觉得“这东西真的懂我”？
8. 当前系统最危险的 10 个 false confidence 来源是什么？
9. 当前代码里最可能导致错误 claim、错误路径、错误 artifact、错误报告的 bug 是什么？
10. 最终是否建议继续沿当前架构推进，还是应该重构为更清晰的 `artifact producer -> claim verifier -> paper planner -> manuscript packager -> reviewer simulator` 产品流？

## 输出格式

请输出一份结构化审查报告，使用以下格式：

1. **Executive Verdict**
   - 一句话结论。
   - 0-100 分评分：学科可信度、产品体验、论文可发表性、代码可靠性、生产成熟度。

2. **Can It Produce an ABS-Level Paper?**
   - 当前能做到什么。
   - 不能做到什么。
   - 距离“可发表草稿”最关键差距。

3. **Discipline Conversion Audit**
   - AI/CS 残留。
   - 经济学改造完成项。
   - 金融学改造完成项。
   - 尚未改造完成项。

4. **TODO Quality Audit**
   - TODO 中真正有价值的项。
   - TODO 中 toy / low-leverage 的项。
   - TODO 缺失但必须补的项。

5. **Module-by-Module Assessment**
   - 每个关键模块给出：production / promising / toy / unsafe / unclear。
   - 说明判断证据。

6. **User Experience Assessment**
   - 经济/金融学者从零到论文会经历什么。
   - 哪些地方会让用户惊艳。
   - 哪些地方会让用户放弃。

7. **False Confidence and Reviewer Risk**
   - 系统最容易产生虚假自信的地方。
   - 审稿人最可能攻击的地方。
   - 哪些 claim 必须被禁止。

8. **Code and Test Findings**
   - 只列高影响 bug。
   - 每条包含文件、风险、触发条件、建议修复。

9. **Roadmap**
把做了才像真正产品的路图用分段md+zip压缩包给出。

10. **Final Recommendation**

   下一步最优行动。

请保持严厉、具体、证据导向。不要为了礼貌降低标准。这个项目的目标不是“能跑”，而是让经济和金融学者愿意把它当顶级的论文助手与研究助理使用。你完全可以并且应该去搜索其他论文智能体在学科知识领域是怎么构建的。
