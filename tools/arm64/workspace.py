"""Transfer sources and completed artifacts between a checkout and a Linux volume."""
import json
import os
import shutil
import tempfile
import sys
import tarfile
from pathlib import Path, PurePosixPath

MANIFEST = '.dcos-arm64-source-files.json'
EXCLUDED = ('packages/cache', '.build-logs', '.pytest_cache', MANIFEST)


def pack_sources(root, stream):
    def include(member):
        # Stream readers cannot seek back to materialize tar hard links.
        archive.inodes.clear()
        name = member.name[2:] if member.name.startswith('./') else member.name
        if any(name == prefix or name.startswith(prefix + '/') for prefix in EXCLUDED):
            return None
        return member
    with tarfile.open(fileobj=stream, mode='w|') as archive:
        archive.add(str(root), arcname='.', filter=include)


def extract(root, stream):
    names = set()
    with tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe archive path: ' + member.name)
            name = str(path)
            destination = root / name
            if destination.is_symlink() or (member.issym() and destination.is_file()):
                destination.unlink()
            if member.isfile():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=str(destination.parent), delete=False) as output:
                    temporary = output.name
                    try:
                        shutil.copyfileobj(archive.extractfile(member), output)
                        output.flush()
                        os.chmod(temporary, member.mode)
                        os.utime(temporary, (member.mtime, member.mtime))
                        os.replace(temporary, str(destination))
                    finally:
                        if os.path.exists(temporary):
                            os.unlink(temporary)
            else:
                archive.extract(member, str(root))
            names.add(name)
    return names


def sync_sources(root, stream):
    manifest = root / MANIFEST
    previous = set(json.loads(manifest.read_text())) if manifest.exists() else set()
    current = extract(root, stream)
    for name in sorted(previous - current, key=lambda name: name.count('/'), reverse=True):
        path = root / name
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass  # Keep build caches and other files that were never copied as sources.
    manifest.write_text(json.dumps(sorted(current)))


def artifact_files(root):
    cache = root / 'packages/cache'
    paths = set()
    for archive in (cache / 'packages').glob('*/*--*.tar.xz'):
        if archive.name.endswith('-tmp.tar.xz'):
            continue
        paths.add(archive)
        for latest in archive.parent.glob('*latest'):
            if latest.read_text().strip() + '.tar.xz' == archive.name:
                paths.add(latest)
    for directory in ('bootstrap', 'complete'):
        for path in (cache / directory).glob('*'):
            if path.is_file() and '-tmp' not in path.name:
                paths.add(path)
    installer = cache / 'dcos_generate_config.sh'
    if installer.is_file():
        paths.add(installer)
    return sorted(paths)


def pack_artifacts(root, stream):
    with tarfile.open(fileobj=stream, mode='w|') as archive:
        for path in artifact_files(root):
            archive.add(str(path), arcname=str(path.relative_to(root)), recursive=False)


def main():
    operation, folder = sys.argv[1:]
    root = Path(folder)
    if operation == 'pack-sources':
        pack_sources(root, sys.stdout.buffer)
    elif operation == 'sync-sources':
        sync_sources(root, sys.stdin.buffer)
    elif operation == 'pack-artifacts':
        pack_artifacts(root, sys.stdout.buffer)
    elif operation == 'unpack-artifacts':
        extract(root, sys.stdin.buffer)
    else:
        raise ValueError('Unknown workspace operation: ' + operation)


if __name__ == '__main__':
    main()
