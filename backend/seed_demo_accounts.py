#!/usr/bin/env python3
"""
Convenience entrypoint for BrandShield Demo-Account Seeder.
Can be executed directly:
    python seed_demo_accounts.py
or with options:
    python seed_demo_accounts.py --help
"""
import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.seed_demo_accounts import main

if __name__ == "__main__":
    main()
