# Agent Guidelines

## 📝 Change Tracking & Releases
- **MANDATORY**: All functional changes, features, bug fixes, and significant UI updates MUST be recorded in [CHANGELOG.md](file:///home/acroarch/Documents/Projects/git-clones/Carla/CHANGELOG.md) BEFORE or alongside each commit. NEVER skip updating CHANGELOG.md.
- **MANDATORY**: When cutting a release, creating tags, or modifying release structures, [releases.json](file:///home/acroarch/Documents/Projects/git-clones/Carla/releases.json) MUST be updated with the new version, urgency rating (`minor`, `suggested`, `critical`), release notes, and basic installation guide.
- Keep entries structured under the latest date / version with datetime timestamps, commit hashes, and clear, concise bullet points following [Keep a Changelog](https://keepachangelog.com/) standards.

## 🚀 Commits
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, etc.).

## ⚡ Direct Execution (Anti-Exploration Loop)
- Limit codebase reading to targeted single lookups.
- NEVER chain more than 2-3 exploratory reads without immediately modifying files or producing the implementation. Move straight to writing the code.

## 🎨 Theming
- All frontend colors come from the theme engine (`source/frontend/styles/`) or Qt palette roles. No hardcoded hex/rgb colors in widget code: use `theme_manager.engine.get_token(...)`, `get_active_skin_palette()`, or `palette(...)` roles in QSS.
- `source/tests/test_theme.py` guards the global QSS; keep it green when adding widgets.
