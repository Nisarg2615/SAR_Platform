# SAR Platform — Team Navigation Guide

## Read this before starting any OpenCode session

Start every session from the project root:
  cd ~/Sar-platform
  opencode

## Module ownership
- agents/agent1_ingestion   → shared
- agents/agent2_risk        → shared
- agents/agent3_narrative   → shared
- agents/agent4_compliance  → shared
- agents/agent5_audit       → shared
- agents/agent6_review      → shared
- prediction_engine/        → shared
- graph/neo4j/              → shared
- infra/                    → shared
- tests/                    → shared
- ui/                       → shared

## Before writing any code
1. Pull latest develop:   git pull origin develop
2. Create feature branch: git checkout -b feat/your-feature
3. Open OpenCode:         opencode
4. Work only in your owned module

## Before opening a PR
1. Run: pytest tests/ -v
2. Run: python -m mypy agents/
3. Check no secrets in your diff
4. Get one teammate to review
