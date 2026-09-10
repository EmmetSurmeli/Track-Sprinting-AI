# GitHub and application submission

The application needs the code as well as a demo. This repository is designed to run locally after cloning; hosting the app is not required.

## Before pushing

- Run `python -m pytest -q` and review `docs/VALIDATION.md` for pending checks.
- Complete one real API generation and inspect its citations, frame references and language.
- Keep `.env`, `.venv/`, `models/`, `artifacts/`, original athlete videos and generated media out of Git. `.gitignore` already excludes these. Never use `git add -f` for them.
- Keep README status accurate. Do not call the app clinically validated or claim a model was trained for this project.
- Record the demonstration and verify playback/audio. Provide the requested link or upload separately from the code.

## Push an initial repository

Create an empty GitHub repository in your own account, with visibility appropriate for the application reviewers. Then run these commands from the project folder, replacing the example remote with your actual repository URL:

```bash
git status --short
git add README.md THIRD_PARTY.md pyproject.toml requirements.lock.txt .gitignore .env.example .streamlit/config.toml app.py src scripts tests docs .github
git diff --cached --stat
git diff --cached --check
git commit -m "Build local sprint video analysis MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

If a remote named `origin` already exists, inspect it with `git remote -v` before changing anything. Do not overwrite an unrelated repository. If you choose private visibility, ensure the reviewers can access it using the application's specified process.

No footage is bundled in the public code. Reviewers can upload their own compatible clip; your recording demonstrates the actual private test video. Add a demo link to README when you have a shareable recording. Review any exported screenshots or metadata for information you do not want to publish.

## Finish by the deadline

Submission target: Saturday September 12, 2026, 11:59 p.m., assuming Eastern time. Leave time to check both links from the reviewer's perspective. The app is an MVP: a truthful working core with clear limitations is stronger than an unsupported feature list.
