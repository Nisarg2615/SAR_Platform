# Contributing to SAR Platform

This document defines the exact process every team member must follow. No exceptions.

---

## Branch Structure

```
main          ← production-ready code only. NEVER touch directly.
develop       ← integration branch. Merge into this at end of each day.
feat/ricky-*  ← Ricky's feature branches
feat/nisarg-* ← Nisarg's feature branches
feat/anshul-* ← Anshul's feature branches
feat/ashwin-* ← Ashwin's feature branches
```

---

## Daily Git Workflow

### Morning (start of work)
```bash
git checkout develop
git pull origin develop
git checkout -b feat/yourname-task-description
# e.g. feat/ricky-agent1-ingestion
```

### During work
- Commit every time a task is complete (not every 5 minutes)
- Commit message format: `feat(scope): short description`
  - Examples:
    - `feat(agent1): add ingestion node with pydantic gate`
    - `fix(agent3): handle minimax timeout with fallback`
    - `test(agent2): add risk scoring unit tests`
    - `infra: add health check to start_all.sh`
- **Never commit broken code** — if it doesn't run, stash it: `git stash`

### Evening sync (9pm every night)
```bash
git add .
git commit -m "feat(day1-ricky): agent1 ingestion complete with pydantic gate"
git push origin feat/your-branch

# Open PR on GitHub to develop
# Fill in PR template
# Tag at least 1 other person to review
# Merge only after 1 approval
```

---

## Commit Message Format

```
<type>(<scope>): <short description>

Types: feat | fix | test | docs | infra | refactor | chore
Scope: agent1 | agent2 | agent3 | agent4 | agent5 | agent6 | pipeline | ui | neo4j | infra | prediction
```

**Good examples:**
- `feat(agent2): add xgboost risk scoring with shap explanation`
- `fix(agent3): fallback activates on minimax timeout`
- `test(integration): add full pipeline e2e test for structuring scenario`
- `docs: update README with fresh setup instructions`

**Bad examples:**
- `update stuff`
- `fix bug`
- `wip`

---

## Pull Request Rules

1. **Title**: Use the same format as commit messages
2. **Description**: List what you built + how to test it
3. **Reviewer**: Tag at least 1 team member
4. **Checks**: All must pass before merge
   - `pytest tests/ -v` — no failures
   - `python -m mypy agents/` — no type errors
5. **Merge**: Squash merge preferred. Delete branch after merge.

### PR Template

```markdown
## What this PR does
Brief description of what was built.

## How to test
1. Step to reproduce or test
2. Expected output

## Checklist
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Type checks pass (`python -m mypy agents/`)
- [ ] No secrets in diff
- [ ] MASTER_CONTEXT.md still accurate
```

---

## GitHub Branch Protection Rules

Set these up in: **GitHub → Settings → Branches → Add rule**

### Rule 1: `main`
```
Branch name pattern: main
✅ Require a pull request before merging
   ✅ Require approvals: 2
   ✅ Dismiss stale PR approvals when new commits are pushed
✅ Require status checks to pass before merging
   ✅ Require branches to be up to date before merging
✅ Do not allow bypassing the above settings
✅ Restrict who can push to matching branches: (only Ricky)
```

### Rule 2: `develop`
```
Branch name pattern: develop
✅ Require a pull request before merging
   ✅ Require approvals: 1
   ✅ Dismiss stale PR approvals when new commits are pushed
✅ Do not allow force pushes
✅ Do not allow deletions
```

---

## Code Ownership Rules

| Module | Owner | Can other members edit? |
|---|---|---|
| `agents/agent1_ingestion/` | Ricky | No — ask Ricky |
| `agents/agent2_risk/` | Ricky | No — ask Ricky |
| `prediction_engine/` | Ricky | No — ask Ricky |
| `agents/agent3_narrative/` | Nisarg | No — ask Nisarg |
| `agents/agent4_compliance/` | Nisarg | No — ask Nisarg |
| `graph/neo4j/` | Nisarg | No — ask Nisarg |
| `agents/agent5_audit/` | Anshul | No — ask Anshul |
| `agents/agent6_review/` | Anshul | No — ask Anshul |
| `ui/` | Anshul | No — ask Anshul |
| `infra/` | Ashwin | No — ask Ashwin |
| `tests/` | Ashwin | No — ask Ashwin |
| `agents/shared/schemas.py` | **SHARED** | All 4 must agree first |
| `requirements.txt` | **SHARED** | Coordinate before editing |
| `MASTER_CONTEXT.md` | **SHARED** | Team discussion required |

---

## What to Do When Stuck

1. Try to solve it independently — max **30 minutes**
2. Post in team WhatsApp with:
   - What you're trying to do
   - What error you got (paste the traceback)
   - What you already tried
3. Tag the person who owns the relevant module
4. If it's a schema conflict: all 4 people must agree before anyone changes `schemas.py`

---

## Secrets Policy

- **Never** commit `.env.local` (it's in `.gitignore`)
- **Never** hardcode API keys or passwords in any `.py` file
- Use `os.getenv("KEY_NAME")` always
- If you accidentally commit a secret: tell Ricky immediately, we rotate the key

---

## File You Must Read Before Every Session

```
MASTER_CONTEXT.md  ← single source of truth, read it every morning
```
