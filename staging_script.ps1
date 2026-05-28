Push-Location E:\code\DevFlow
$env:CI='true'
$env:GIT_TERMINAL_PROMPT='0'
$env:GCM_INTERACTIVE='never'

# Stage modified files that are core source
$modified = git diff --name-only
$core_modified = $modified | Where-Object {
    $_ -match '^\.(gitignore)' -or
    $_ -match '^Dockerfile' -or
    $_ -match '^Makefile' -or
    $_ -match '^requirements\.txt' -or
    $_ -match '^pyproject\.toml' -or
    $_ -match '^docker\-compose(yaml|\.min|\.dev|\.prod|\.e2e|\.deploy)\.yaml' -or
    $_ -match '^docker/.*\.(yaml|conf|sh)$' -or
    $_ -match '^SRS_' -or
    $_ -match '^uv\.lock$' -or
    $_ -match '^frontend/(src/|components\.d\.ts|package\.json|package-lock\.json|vite|tsconfig)' -or
    $_ -match '^frontend/((public|static)/.*)' -or
    $_ -match '^backend/(app/|test_devflow\.db$)' -or
    $_ -match '^\.env(\.production)?(\.example)?$' -or
    $_ -match '^scripts/\w+\.sh$' -or
    $_ -match '^docker/entrypoint\.sh$' -or
    $_ -match 'backend/tests/conftest\.py' -or
    $_ -match 'backend/app/\w+\.(py)$' -or
    $_ -notmatch 'test_perf_devflow\.db' -and $_ -notmatch '-journal$' -and $_ -ne 'backend/devflow.db' -and $_ -ne 'backend/devflow_test.db' -and $_ -ne 'backend/test_devflow.db'
}

foreach ($f in $core_modified | Sort-Object) {
    try {
        git add -f $f
    } catch {}
}

# Stage untracked core files
$untracked = git ls-files --others --exclude-standard
$core_untracked = $untracked | Where-Object {
    # Exclude noise directories
    $_ -notmatch '^\.trae/' -and
    $_ -notmatch '^backups/' -and
    $_ -notmatch '^.codeartsdoer/' -and
    $_ -notmatch 'htmlcov/' -and
    $_ -notmatch '^\.pytest_cache/' -and
    $_ -notmatch '^__pycache__$' -and
    $_ -notmatch '^tests/screenshots/' -and
    $_ -notmatch 'node_modules/' -and
    $_ -notmatch '/results/$' -and
    $_ -notmatch '/cli/results/$' -and
    $_ -notmatch '\.db(-|$)' -and
    $_ -notmatch 'nul$' and
    # Keep backend/data/ subdir, docs subdir, scripts/dir
    $_ -match '^backend/app/' -or
    $_ -match '^docs/\S+' -or
    $_ -match '^\.github/' -or
    $_ -match '^\.trae/workspace/' -or
    $_ -eq 'run_chat_index.ts' -or
    $_ -eq 'hermes_bridge.py' -or
    $_ -eq 'hermes_tree.json' -or
    $_ -eq 'bridge_client.ts' -or
    $_ -eq 'STARTUP_GUIDE.md'
    
}

foreach ($f in $core_untracked | Sort-Object) {
    try {
        git add -f $f
    } catch {}
}

git status --short
Pop-Location
