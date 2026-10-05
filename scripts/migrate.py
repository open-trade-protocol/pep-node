"""Migration scripts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.listing import get_engine, init_db


def migrate_up():
    """Run database migrations."""
    print("Running migrations...")
    
    engine = get_engine(settings.database_url)
    init_db(engine)
    
    print("Migrations completed successfully.")


def migrate_down():
    """Rollback migrations."""
    print("Rolling back migrations...")
    print("Not implemented yet. Use alembic for production migrations.")


def main():
    """Main entry point for migrations."""
    parser = argparse.ArgumentParser(description="Database migrations")
    parser.add_argument("action", choices=["up", "down"], help="Migration action")
    args = parser.parse_args()
    
    if args.action == "up":
        migrate_up()
    elif args.action == "down":
        migrate_down()


if __name__ == "__main__":
    main()
