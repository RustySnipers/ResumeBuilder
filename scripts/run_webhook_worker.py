#!/usr/bin/env python3
"""
Webhook Worker Startup Script

Starts the webhook background worker for processing webhook events.

Usage:
    python scripts/run_webhook_worker.py

Environment Variables:
    DATABASE_URL                  - PostgreSQL connection URL (required)
    WEBHOOK_PENDING_BATCH_SIZE    - Batch size for pending events (default: 100)
    WEBHOOK_RETRY_BATCH_SIZE      - Batch size for retry events (default: 100)
    WEBHOOK_SLEEP_SECONDS         - Sleep interval between cycles (default: 10)

Example:
    export DATABASE_URL="postgresql://user:pass@localhost/resumebuilder"
    python scripts/run_webhook_worker.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.webhooks.worker import main

if __name__ == "__main__":
    print("=" * 60)
    print("ResumeBuilder Webhook Worker")
    print("=" * 60)
    print()

    # Check for required environment variables
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable is required")
        print()
        print("Example:")
        print('  export DATABASE_URL="postgresql://user:pass@localhost/resumebuilder"')
        print('  python scripts/run_webhook_worker.py')
        sys.exit(1)

    print(f"Database URL: {os.getenv('DATABASE_URL').split('@')[1] if '@' in os.getenv('DATABASE_URL') else '(hidden)'}")
    print(f"Pending batch size: {os.getenv('WEBHOOK_PENDING_BATCH_SIZE', '100')}")
    print(f"Retry batch size: {os.getenv('WEBHOOK_RETRY_BATCH_SIZE', '100')}")
    print(f"Sleep interval: {os.getenv('WEBHOOK_SLEEP_SECONDS', '10')}s")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWebhook worker stopped by user")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)
