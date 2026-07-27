# Agent Instructions

This file gives MiMo Code CLI (and any other compatible coding agent)
project-specific guidance. Edit it freely.

## Project overview

Haimei DevFlow — AI-driven software development workflow system.
Steps 3-14: each step produces a doc, passes hourong QA, saves output path to DB.

## Build, test, lint

<!-- Common commands the agent should know about. -->

## Conventions

- Steps 6-14 save artifacts with `doc_path` (file path on disk) and call `complete_step(N)`.
- `complete_step` now calls `_generate_step_handover` for ALL steps (incl QA_REQUIRED).
- `_generate_step_handover` extracts `handover_doc_path` from `doc_path` / `doc_paths` / `docs_dir` / logical keys.
- `complete_step` checks for `qa_passed` in artifacts: if True, sets `completed` status even for QA_REQUIRED steps (since steps 6-14 have internal hourong QA loop).
- Frontend `loadStatus()` has a safety net: `qa_review` status + `qa_passed` artifact → treat as `completed`.
- Steps 4-14 auto-redirect on frontend via `useWorkflowStep.ts` composable (WS `done` event and polling `completed` status).
- Step4 has 4 serial sub-steps (houwang1-4 → hourong1-4 verification).
- Frontend `handleExecute()` for steps 6-14 retries status check up to 3×1s to handle `haimei_auto_advance` race on freshly started steps.

## Hard Rules — never violate

- **NEVER change usernames, passwords, or user credentials** unless the user EXPLICITLY asks for it. This includes creating, updating, resetting, or modifying any user account.
- **NEVER modify user data** (users table) without explicit, unambiguous permission.

## Out of scope

<!-- Areas the agent should not modify without explicit permission. -->
