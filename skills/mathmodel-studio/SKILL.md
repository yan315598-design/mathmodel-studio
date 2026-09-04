---
name: mathmodel-studio
description: Plugin shim for mathmodel-studio. Use when Codex invokes the math modeling plugin for CUMCM 国赛, 中国研究生数学建模竞赛（华为杯）, 华数杯, MCM/ICM, Diangong Cup, APMCM, 建模, 相似题或子问检索, Stage 知识包, 论文证据链, model selection, robustness analysis, paper writing, or final review.
---

# mathmodel-studio plugin shim

This wrapper exists so Codex plugins can discover the skill from the official `./skills/` plugin layout.

Before doing any work, read `../../SKILL.md` and treat it as the primary workflow. Resolve `references/`, `competitions/`, `templates/`, `scripts/`, and `config/` relative to `../..`.

Do not duplicate workflow rules here; the root `SKILL.md` is the source of truth.
