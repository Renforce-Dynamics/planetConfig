"""Resolve, validate and compare composed configuration files."""
import argparse
import json
import yaml
from . import load_config

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("resolve", "validate", "diff"))
    parser.add_argument("path")
    parser.add_argument("other", nargs="?")
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.path, overrides=args.set)
        if args.output:
            config.freeze(args.output)
        if args.action == "diff":
            if args.other is None:
                parser.error("diff requires a second config path")
            print(json.dumps({"same": config.digest == load_config(args.other).digest}))
        elif args.action == "resolve":
            print(yaml.safe_dump(config.data, sort_keys=False), end="")
        else:
            print(json.dumps({"configuration_valid": True, "sha256": config.digest}))
        return 0
    except (ValueError, OSError) as error:
        parser.error(str(error))

if __name__ == "__main__":
    raise SystemExit(main())
