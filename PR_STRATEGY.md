# Ricky's PR & Merge Strategy — SAR Platform Tech Lead Guide
# Read this before reviewing any PR.

---

## Your Role as Tech Lead

You are the final gate before code enters `develop` and then `main`.
Every line that merges becomes your responsibility.
This doc tells you exactly: what to check, when to merge, when to reject.

---

## The Two Protected Branches

```
main      ← production: only merge from develop after full demo works end-to-end
develop   ← daily integration: teammates merge feature branches here
```

**You never code directly on either branch.**
Feature branches go: `feat/name-task` → PR → `develop` → PR → `main`

---

## Part 1 — Reviewing a PR to `develop`

### Step 1: Is this the right branch target?

```
PR target should be: develop
NOT: main (reject immediately if targeting main without your explicit sign-off)
```

### Step 2: Does the branch name follow convention?

```
✅ feat/ricky-agent1-ingestion
✅ feat/nisarg-minimax-client
✅ feat/anshul-ui-pages
✅ feat/ashwin-docker-infra
❌ fix-stuff     → ask them to rename
❌ main2         → reject
```

### Step 3: Files changed — is anyone touching modules they don't own?

Open the "Files changed" tab on GitHub. Check ownership:

| If you see changes in... | Owner | Action |
|---|---|---|
| `agents/agent1_ingestion/` | Ricky | OK if you wrote it; ask others why |
| `agents/agent2_risk/` | Ricky | Same |
| `prediction_engine/` | Ricky | Same |
| `agents/agent3_narrative/` | Nisarg | OK for Nisarg; ask others |
| `agents/agent4_compliance/` | Nisarg | Same |
| `agents/agent5_audit/` | Nisarg | Same |
| `graph/neo4j/` | Nisarg | Same |
| `agents/agent6_review/` | Anshul | OK for Anshul |
| `ui/` | Anshul | Same |
| `infra/` | Ashwin | OK for Ashwin |
| `tests/` | Ashwin | OK for Ashwin |
| `agents/shared/schemas.py` | SHARED | Did all 4 agree? Check WhatsApp. If not, block. |
| `.env.local` | NOBODY | **Reject immediately.** Secret leak. |

### Step 4: Secret scan

In the Files Changed view, search for any of:
- `api_key`, `password`, `secret`, `token` as hardcoded strings
- Anything that looks like `sk-...` or a long random string
- `.env.local` file appearing in diff

If found → **Request changes, do not merge.** Ask them to remove it and rotate the key.

### Step 5: Does it break existing code?

Check:
1. `tests/` — do the newly added or changed tests pass? (Ask Ashwin to confirm or run yourself)
2. `agents/shared/schemas.py` — if this was changed, does every agent still work with the new schema?
3. Any import changes — are they importing from the correct shared modules?

### Step 6: Code quality quick check (5 minutes max)

Look for:
- `raise` inside an agent node → must be `state.error_log.append` + `return state` instead
- Raw `print()` statements left in (acceptable, but note it)
- Hardcoded values that should come from `.env.local` (ports, passwords)
- New agent functions that don't follow the `async def agent_N_name(state: SARCase) -> SARCase` signature
- Any new `SARCase()` construction inside an agent (forbidden — must receive and return existing state)

### Step 7: The merge decision

| Condition | Decision |
|---|---|
| All checks pass, tests pass, no secrets, correct ownership | ✅ **Approve and merge** (squash merge) |
| Minor code style issue, no logic error | ✅ **Approve with comment** — merge anyway if close to deadline |
| Wrong branch target | ❌ **Request changes** — ask them to retarget |
| Secret in diff | ❌ **Request changes** — block until key is removed and rotated |
| Touching someone else's module | ❌ **Request changes** — ask why and get the owner's approval |
| Schema changed without team agreement | ❌ **Request changes** — get everyone on a call first |
| Tests failing | ❌ **Request changes** — do not merge broken code |
| Can't understand what it does (no description) | ❌ **Request changes** — ask for PR description |

---

## Part 2 — Merge Strategy by Day

### Day 1 Evening (March 24, 9pm)

**Expected PRs:**
- `feat/ricky-day1` → develop (schemas + agent1 + agent2 + prediction engine + pipeline wiring)
- `feat/nisarg-day1` → develop (agent3 + agent4 + minimax client + prompts + fallback)
- `feat/anshul-day1` → develop (agent5 + agent6 + ui scaffold + mock data)
- `feat/ashwin-day1` → develop (docker infra + shell scripts + neo4j schema + unit test scaffolds)

**Merge order (matters for develop stability):**
```
1. feat/ashwin-day1    ← infra and schemas don't depend on anything
2. feat/ricky-day1     ← backend core, others depend on this
3. feat/nisarg-day1    ← needs agent1+2 to be merged first
4. feat/anshul-day1    ← needs schemas and backend to run
```

**After all 4 are merged:**
```bash
git checkout develop
git pull origin develop
uvicorn main:app --reload    # should start without import errors
pytest tests/ -v             # all unit tests should pass
```
If this breaks → do NOT merge to main yet. Debug on develop.

### Day 2 Evening (March 25, 9pm)

**Expected PRs:**
- `feat/ricky-day2` → develop (all 10 FastAPI endpoints wired)
- `feat/nisarg-day2` → develop (graph API + cypher queries + neo4j integration)
- `feat/anshul-day2` → develop (full UI wired to real API)
- `feat/ashwin-day2` → develop (integration tests + docs + type fixes)

**Merge order:**
```
1. feat/ricky-day2     ← endpoints must exist before UI can call them
2. feat/nisarg-day2    ← graph API needed for UI page 3
3. feat/anshul-day2    ← UI wired to live API
4. feat/ashwin-day2    ← tests and docs last (don't block others)
```

**After all 4 are merged:**
```bash
git checkout develop
git pull origin develop
./infra/start_all.sh          # all Docker services up
uvicorn main:app --reload &   # backend running
streamlit run ui/app.py &     # frontend running

# Run the 6-screen demo manually — every screen must work
# Then run full test suite
pytest tests/ -v
python -m mypy agents/
```
If demo works and tests pass → merge develop → main.

### Merging develop → main (final step before submission)

```bash
git checkout main
git pull origin main
git merge --no-ff develop -m "release: hackathon submission March 26 2026"
git push origin main
```

Only do this when:
- All 6 demo screens work end-to-end
- `pytest tests/ -v` → 0 failures
- No secrets in any file (`git log --all -p | grep -i "api_key\|password\|secret"`)

---

## Part 3 — Handling Merge Conflicts

### When does a conflict happen?

A conflict happens when two people edited the **same lines** in the **same file**.

Most common conflict locations:
1. `agents/shared/schemas.py` — everyone depends on this
2. `requirements.txt` — people adding packages
3. `main.py` — if anyone touches it besides Ricky

### Resolution Protocol — Step by Step

#### Scenario A: Conflict in `schemas.py`

This is the most dangerous conflict. Go slow.

```bash
# 1. Get the latest develop
git checkout develop
git pull origin develop

# 2. Check out the feature branch that has the conflict
git checkout feat/nisarg-agent3-narrative

# 3. Rebase onto develop (preferred over merge for feature branches)
git rebase develop

# 4. Git will pause at the conflict. Open the file:
# You will see conflict markers:
# <<<<<<< HEAD (develop version)
# class SARCase(BaseModel):
#     ...old fields...
# =======
# class SARCase(BaseModel):
#     ...new fields from nisarg...
# >>>>>>> feat/nisarg-agent3-narrative
```

**Resolution rule for schemas.py:**
- Keep ALL fields from BOTH versions (never delete a field another agent needs)
- Add new fields at the bottom of the model, not in the middle
- If you're unsure which version to keep, call the owner of that agent

```bash
# 5. After resolving, mark as resolved
git add agents/shared/schemas.py
git rebase --continue

# 6. Force push the rebased branch (safe on feature branches)
git push origin feat/nisarg-agent3-narrative --force-with-lease
```

#### Scenario B: Conflict in `requirements.txt`

```bash
# Open requirements.txt — you'll see duplicate or conflicting package versions
# Resolution: keep the HIGHER version of each package
# Keep ALL packages from both versions — never remove a package
# Then:
pip install -r requirements.txt  # verify it installs cleanly
git add requirements.txt
git rebase --continue
```

#### Scenario C: Conflict in `main.py` (Ricky's file)

Since you own `main.py`, this means someone touched it who shouldn't have.

```bash
# Keep YOUR version (HEAD/develop)
# Accept theirs only for parts you can verify are correct
# Never accept a conflict resolution you don't understand
git checkout --ours main.py   # keep your version entirely
git add main.py
git rebase --continue
```

### The Conflict Communication Rule

Before someone opens a PR that might conflict:
1. They check what's in `develop` right now: `git log --oneline develop -10`
2. If they see changes to files they also changed: **tell Ricky on WhatsApp first**
3. Ricky coordinates who rebases first

**Never both resolve the same conflict independently — always one person resolves.**

---

## Part 4 — Emergency Scenarios

### "Someone pushed broken code to develop"

```bash
# Find last good commit
git log --oneline develop

# Revert to it (do NOT use reset on shared branches)
git checkout develop
git revert <bad-commit-sha>
git push origin develop
# Tell the team in WhatsApp what happened and why
```

### "Someone accidentally pushed a secret"

1. Immediately tell everyone to rotate that key
2. Remove the secret from the file
3. `git filter-repo` or BFG to purge from history (if it was in main — talk to Ricky)
4. Force push the cleaned branch
5. Tell GitHub to invalidate: go to Settings → Secret scanning

### "Two PRs are racing — both modified schemas.py"

```bash
# Merge the SIMPLER / LOWER-RISK one first (usually Ashwin's test changes)
# Then ask the other person to rebase onto updated develop
# Review their conflicts before they push
```

### "It's 11pm March 25 and tests are failing"

Priority order:
1. Fix the agent that makes the demo screen fail (demo > tests)
2. Skip the failing test temporarily with `@pytest.mark.skip(reason="demo priority")`
3. Get the 6-screen demo working
4. Then fix the test if time allows

---

## Part 5 — Quick Reference Checklist (print this)

Before approving any PR, run through this in order:

```
[ ] Targets develop (or main only if it's the final submission PR)
[ ] Branch name follows feat/<name>-<task> convention
[ ] Author is only editing their own modules
[ ] No .env.local or hardcoded secrets in diff
[ ] No raw `raise` inside agent nodes (must use error_log + return state)
[ ] No new SARCase() constructed inside an agent
[ ] Tests added for the feature (or Ashwin confirms existing tests still pass)
[ ] PR has a description explaining what was built and how to test it
[ ] Squash merge (not regular merge) to keep develop log clean
[ ] Delete branch after merge
```

---

## Merge Commit Message Format

When merging a PR:

```
feat(scope): short description of what this PR added

Merged: feat/name-taskname → develop
Author: <name>
Tests: passing / skipped (with reason)
```

---

## Final Submission Checklist (March 26, before midnight)

```
[ ] All 6 demo screens work end-to-end on one machine
[ ] pytest tests/ -v → 0 failures
[ ] python -m mypy agents/ → 0 errors
[ ] No secrets in any committed file
[ ] develop merged into main with proper commit message
[ ] GitHub repo is PUBLIC (judges need to view it)
[ ] README.md renders correctly on GitHub (check the preview)
[ ] docs/demo_script.md is complete
[ ] Team has practiced the demo 3 times
```
