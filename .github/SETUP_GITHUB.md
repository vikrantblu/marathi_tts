# Push to GitHub & Enable Copilot Features

## Prerequisites

1. **Install Git for Windows**  
   Download from https://git-scm.com/download/win  
   After install, restart PowerShell.

2. **Install GitHub CLI** (for Copilot terminal suggestions)
   ```powershell
   winget install --id GitHub.cli
   ```

3. **Create a GitHub account** at https://github.com (if not already done)

---

## Step 1 — Initialise git and push

```powershell
cd marathi_tts

# One-time setup
git init
git add .
git commit -m "initial: Marathi TTS — all three platforms"

# Create a GitHub repo (gh CLI does this without a browser)
gh auth login          # follow prompts: GitHub.com → HTTPS → browser
gh repo create marathi-tts --private --source=. --remote=origin --push
```

---

## Step 2 — Verify CI runs

1. Go to https://github.com/YOUR_USERNAME/marathi-tts/actions  
2. You should see **"TTS Engine Tests"** workflow running automatically.  
3. It runs `test_all_platforms.py` on Ubuntu — should show ✅ ALL PASS.

---

## Step 3 — Enable Copilot Coding Agent

1. Go to your repo **Settings → Copilot** and enable the coding agent.  
2. Create a GitHub Issue for any feature / bug, e.g.:  
   > *"FEAT-14: Add pre-recorded stotra audio playback on mobile"*  
3. On the issue page, assign it to **Copilot**.  
4. Copilot reads `copilot-instructions.md`, writes code, and opens a PR.  
5. Review the PR — CI runs automatically and Copilot self-corrects on failures.

---

## Step 4 — Use `gh copilot` in your terminal

```powershell
gh copilot suggest "how do I sign an APK with a keystore in Gradle"
gh copilot explain "git rebase -i HEAD~3"
```

---

## Step 5 — Future workflow

```powershell
# Before any code change
git pull

# After a feature
git add -A
git commit -m "feat: FEAT-14 pre-recorded stotra audio mobile"
git push
# → CI runs automatically, blocking the PR merge if tests fail
```
