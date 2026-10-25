import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from workspace import artifact_files, artifact_inventory, extract, pack_artifacts, pack_sources, sync_sources


class WorkspaceTest(unittest.TestCase):
    def test_sync_preserves_cache_and_removes_deleted_sources(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as destination:
            source, destination = Path(source), Path(destination)
            (source / 'old.py').write_text('old')
            (source / 'link').symlink_to('old.py')
            stream = io.BytesIO()
            pack_sources(source, stream)
            stream.seek(0)
            sync_sources(destination, stream)
            cache = destination / 'packages/cache/keep'
            cache.parent.mkdir(parents=True)
            cache.write_text('cached build')
            (source / 'old.py').unlink()
            (source / 'new.py').write_text('new')
            stream = io.BytesIO()
            pack_sources(source, stream)
            stream.seek(0)
            sync_sources(destination, stream)
            self.assertFalse((destination / 'old.py').exists())
            self.assertEqual((destination / 'new.py').read_text(), 'new')
            self.assertEqual(cache.read_text(), 'cached build')

    def test_source_copy_excludes_build_outputs(self):
        with tempfile.TemporaryDirectory() as source:
            source = Path(source)
            cache = source / 'packages/cache/output'
            cache.parent.mkdir(parents=True)
            cache.write_text('not a source')
            (source / 'build.py').write_text('source')
            stream = io.BytesIO()
            pack_sources(source, stream)
            stream.seek(0)
            with tarfile.open(fileobj=stream) as archive:
                names = archive.getnames()
                self.assertEqual(archive.getmember('.').uid, 0)
                self.assertEqual(archive.getmember('.').gid, 0)
            self.assertIn('./build.py', names)
            self.assertNotIn('./packages/cache/output', names)

    def test_export_ignores_unfinished_archives_and_pointers(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            package = root / 'packages/cache/packages/example'
            package.mkdir(parents=True)
            archive = package / 'example--complete.tar.xz'
            archive.write_bytes(b'complete')
            (package / 'example--unfinished.tar.xz-tmp.tar.xz').write_bytes(b'partial')
            latest = package / 'latest'
            latest.write_text('example--unfinished')
            self.assertEqual(artifact_files(root), [archive])
            latest.write_text('example--complete')
            self.assertEqual(artifact_files(root), sorted([archive, latest]))

    def test_delta_export_skips_identical_files_and_keeps_changed_pointer(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            package = root / 'packages/cache/packages/example'
            package.mkdir(parents=True)
            (package / 'example--one.tar.xz').write_bytes(b'first archive')
            latest = package / 'latest'
            latest.write_text('example--one')
            existing = artifact_inventory(root)
            (package / 'example--two.tar.xz').write_bytes(b'second archive')
            latest.write_text('example--two')
            stream = io.BytesIO()
            pack_artifacts(root, stream, existing)
            stream.seek(0)
            with tarfile.open(fileobj=stream) as archive:
                self.assertEqual(archive.getnames(), [
                    'packages/cache/packages/example/example--two.tar.xz',
                    'packages/cache/packages/example/latest'])

    def test_reject_parent_traversal(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            member = tarfile.TarInfo('../outside')
            member.size = 1
            archive.addfile(member, io.BytesIO(b'x'))
        stream.seek(0)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                extract(Path(root), stream)


if __name__ == '__main__':
    unittest.main()
