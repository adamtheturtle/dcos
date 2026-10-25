"""Key a local builder image by its inputs, independently of checkout location."""
import hashlib
import json
import sys
from pathlib import Path


def builder_key(context, salt, names):
    inputs = [(name, hashlib.sha256((Path(context) / name).read_bytes()).hexdigest()) for name in sorted(names)]
    return hashlib.sha256(json.dumps([salt, inputs], sort_keys=True).encode()).hexdigest()


if __name__ == '__main__':
    print(builder_key(sys.argv[1], sys.argv[2], sys.argv[3:]))
