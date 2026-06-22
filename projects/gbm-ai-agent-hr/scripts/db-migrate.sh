#!/bin/bash
# ============================================
# GBM AI Agent HR - Database Migration Script
# Uses Alembic for migration management
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Load environment
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Default database URL
DB_URL="${DATABASE_URL:-mysql+pymysql://hr_admin:hr_admin_password@localhost:3306/hr_user}"

case "${1:-}" in
    init)
        echo "Initializing Alembic..."
        alembic init alembic
        echo "Alembic initialized. Edit alembic.ini to configure your database URL."
        ;;
    revision)
        echo "Creating new migration revision..."
        MESSAGE="${2:-auto migration}"
        alembic revision -m "$MESSAGE"
        echo "Revision created: $MESSAGE"
        ;;
    upgrade)
        echo "Upgrading database to latest revision..."
        TARGET="${2:-head}"
        alembic upgrade "$TARGET"
        echo "Database upgraded to: $TARGET"
        ;;
    downgrade)
        echo "Downgrading database..."
        TARGET="${2:--1}"
        alembic downgrade "$TARGET"
        echo "Database downgraded to: $TARGET"
        ;;
    current)
        echo "Current database revision:"
        alembic current
        ;;
    history)
        echo "Migration history:"
        alembic history --verbose
        ;;
    stamp)
        echo "Stamping current revision without running migrations..."
        REVISION="${2:-head}"
        alembic stamp "$REVISION"
        echo "Stamped with revision: $REVISION"
        ;;
    *)
        echo "Usage: $0 {init|revision|upgrade|downgrade|current|history|stamp} [args...]"
        echo ""
        echo "Commands:"
        echo "  init                  Initialize Alembic"
        echo "  revision [message]    Create new migration"
        echo "  upgrade [target]      Upgrade to target revision (default: head)"
        echo "  downgrade [target]    Downgrade to target revision (default: -1)"
        echo "  current               Show current revision"
        echo "  history               Show migration history"
        echo "  stamp [revision]      Stamp current revision"
        exit 1
        ;;
esac
