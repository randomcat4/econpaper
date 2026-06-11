"""
Prompt contracts for PlannerAgent.
"""
from ...prompts import PromptLoader as _PromptLoader

_prompt_loader = _PromptLoader()

_STEP1_STRUCTURE_SYSTEM_DEFAULT = """You are an expert academic paper planner.
Given a paper's metadata and target venue, decide the high-level structure.
Output ONLY a JSON object. No markdown, no explanation."""
STEP1_STRUCTURE_SYSTEM = _prompt_loader.load(
    "planner", "step1_structure", default=_STEP1_STRUCTURE_SYSTEM_DEFAULT
)

STEP1_STRUCTURE_USER = """Decide the structure for this paper:

**Title**: {title}
**Idea/Hypothesis**: {idea_hypothesis}
**Method summary**: {method}
**Data**: {data}
**Experiments summary**: {experiments}
**Target venue/style**: {style_guide}
**Target pages**: {target_pages}
**Research Context**: {research_context_summary}
**Code Assets**: {code_writing_assets_summary}

{venue_required_sections_block}

{content_brief_block}

Output JSON:
{{
  "paper_type": "empirical|theoretical|survey|position|system|benchmark",
  "contributions": ["Contribution 1", "Contribution 2", ...],
  "narrative_style": "technical|tutorial|concise|comprehensive",
  "sections": [
    {{
      "section_type": "abstract",
      "section_title": "Abstract",
      "mission": "What this section must accomplish in 1-2 sentences",
      "key_content": ["Content point 1", "Content point 2"]
    }},
    {{
      "section_type": "introduction",
      "section_title": "Introduction",
      "mission": "Motivate the problem and present contributions",
      "key_content": ["Problem background", "Research gap", "Proposed approach", "Contributions summary"]
    }},
    ...
  ],
  "structure_rationale": "Why this structure suits the venue and content",
  "abstract_focus": "What the abstract should emphasize"
}}

IMPORTANT:
- "abstract" is always required.
- Choose sections appropriate for {style_guide}. Use your knowledge of venue norms.
- Each section needs section_type (lowercase, e.g. "method", "result") and section_title.
- Each section MUST include "mission" (1-2 sentence goal) and "key_content" (list of content points to cover).
- The mission should capture what the section must accomplish, not just describe its topic.
- key_content should list concrete content points that the section needs to address.
- For empirical studies, consider whether a dedicated Method section is needed.
- Include a dedicated "conclusion" section for full-paper outputs.
- Do NOT merge the conclusion into Discussion or create a "Discussion and Conclusion" section.
Output valid JSON only."""

_STEP2_CITATION_SYSTEM_DEFAULT = """You are an expert academic citation strategist.
Given a paper's structure and venue, decide the total citation count and
per-section allocation. Output ONLY a JSON object."""
STEP2_CITATION_SYSTEM = _prompt_loader.load(
    "planner", "step2_citation", default=_STEP2_CITATION_SYSTEM_DEFAULT
)

_ELEMENT_ASSIGNMENT_SYSTEM_DEFAULT = """You assign figures and tables to the single best section for semantic fit.
Output ONLY a JSON object mapping each element id to one section_type string from the plan.
No markdown, no code fences, no explanation."""
ELEMENT_ASSIGNMENT_SYSTEM = _prompt_loader.load(
    "planner", "element_assignment", default=_ELEMENT_ASSIGNMENT_SYSTEM_DEFAULT
)

STEP2_CITATION_USER = """Decide the citation strategy for this paper:

**Title**: {title}
**Venue**: {style_guide}
**Target pages**: {target_pages}
**Sections**: {section_list}
**Available reference keys**: {reference_keys}

Output JSON:
{{
  "total_target": <int>,
  "rationale": "Why this total is appropriate for the venue and paper scope",
  "section_allocation": {{
    "<section_type>": {{
      "target_refs": <int>,
      "rationale": "Why this section needs this many"
    }},
    ...
  }}
}}

Use your knowledge of academic publishing norms to decide appropriate totals.
Sections that carry literature-review duties need more citations.
Abstract and conclusion typically need 0 citations.
Output valid JSON only."""

_STEP6_PLAN_CRITIC_SYSTEM_DEFAULT = """You are a paper-plan critic.
Review the paper plan for structure quality, section coverage, coherence, and venue fit.
Return JSON only."""
STEP6_PLAN_CRITIC_SYSTEM = _prompt_loader.load(
    "planner", "step6_plan_critic", default=_STEP6_PLAN_CRITIC_SYSTEM_DEFAULT
)

STEP6_PLAN_CRITIC_USER = """Review this paper plan and report issues.

Rules:
- Return JSON only.
- Severity values: blocker, major, minor, soft.
- Use soft for style preferences (for example, preferred introduction contribution summary style).
- Do not promote style-only observations to blocker.

Paper Plan JSON:
{paper_plan_json}

Output:
{{
  "summary": "High-level assessment",
  "issues": [
    {{
      "severity": "blocker|major|minor|soft",
      "section_type": "optional section type or null",
      "location": "short location hint",
      "problem": "What is wrong",
      "recommendation": "How to fix it"
    }}
  ]
}}
"""

_STEP7_PLAN_OPTIMIZER_SYSTEM_DEFAULT = """You are a paper-plan optimizer.
Revise the supplied paper plan to resolve review issues while preserving valid parts.
Return JSON only."""
STEP7_PLAN_OPTIMIZER_SYSTEM = _prompt_loader.load(
    "planner", "step7_plan_optimizer", default=_STEP7_PLAN_OPTIMIZER_SYSTEM_DEFAULT
)

STEP7_PLAN_OPTIMIZER_USER = """Revise the paper plan according to review issues.

Current plan JSON:
{paper_plan_json}

Review issues JSON:
{review_issues_json}

Return the fully revised paper plan as JSON only. Preserve fields that are still valid.
"""
