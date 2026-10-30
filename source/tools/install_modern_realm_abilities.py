"""Install the audited shared RA conversion and free level-one Tireless."""
import argparse
import json
from pathlib import Path
from install_modern_tireless import install
from modern_realm_abilities import apply

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--rollback', type=Path)
    parser.add_argument('--build-dir', type=Path)
    args = parser.parse_args()
    if args.apply and args.rollback:
        parser.error('Choose apply or rollback')
    print(json.dumps(install(args.game, args.apply, args.rollback, args.build_dir,
                             migration=apply, backup_prefix='modern-shared-ras'), indent=2))
