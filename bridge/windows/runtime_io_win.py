"""Windows counterparts of the pinned macOS IO helpers used by the headless builder.

The codec runs as a separate process (jy14_codec_win.exe) that loads the user's
own installed videoeditor.dll. Plaintext passes through a private temporary
directory that is removed immediately; the vendor DLL writes log lines to
stdout, so stdout cannot carry the payload.
"""
from dataclasses import dataclass
import csv
import hashlib
import io
import json
import msvcrt
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Iterable, Tuple

CODEC_PATH = Path(__file__).resolve().parent / 'out' / 'jy14_codec_win.exe'
DLL_PATH = None  # set by headless_runtime from the detected install
EDITOR_IMAGE = 'jianyingpro.exe'
COMMAND_TIMEOUT_SECONDS = 120
MAX_METADATA_PLAINTEXT_BYTES = 16 * 1024 * 1024
LOCK_PATH = Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'jianying-headless' / 'transaction.lock'

JsonObject = Dict[str, Any]


class ApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    content: bytes
    sha256: str
    mode: int
    size: int
    device: int
    inode: int
    mtime_ns: int
    ctime_ns: int


def _snapshot_file(path, label, max_bytes=256 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ApplyError('%s is not a regular file' % label)
    before = path.stat()
    if max_bytes is not None and before.st_size > max_bytes:
        raise ApplyError('%s is too large' % label)
    content = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ApplyError('%s changed while being read' % label)
    return FileSnapshot(path, content, hashlib.sha256(content).hexdigest(), after.st_mode, after.st_size,
                        after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns)


def _revalidate_snapshot(snapshot, phase):
    current = _snapshot_file(snapshot.path, 'snapshot ' + phase)
    if (current.sha256, current.size, current.inode, current.mtime_ns) != (
            snapshot.sha256, snapshot.size, snapshot.inode, snapshot.mtime_ns):
        raise ApplyError('%s changed %s' % (snapshot.path, phase))


def _parse_strict_json(payload, label):
    def object_without_duplicates(pairs: Iterable[Tuple[str, Any]]) -> JsonObject:
        result: JsonObject = {}
        for key, value in pairs:
            if key in result:
                raise ApplyError('%s contains a duplicate object key' % label)
            result[key] = value
        return result

    def reject_nonfinite(value):
        raise ApplyError('%s contains a non-finite number' % label)

    try:
        value = json.loads(payload.decode('utf-8-sig'), object_pairs_hook=object_without_duplicates,
                           parse_constant=reject_nonfinite)
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except ApplyError:
        raise
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ApplyError('%s is not strict UTF-8 JSON' % label) from exc
    if not isinstance(value, dict):
        raise ApplyError('%s root must be an object' % label)
    return value


def _ensure_editor_closed(confirm_editor_closed):
    if confirm_editor_closed is not True:
        raise ApplyError('--confirm-editor-closed is required')
    try:
        result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ApplyError('cannot verify whether JianYing is closed') from exc
    if result.returncode != 0:
        raise ApplyError('cannot verify whether JianYing is closed')
    text = result.stdout.decode('mbcs', errors='replace')
    names = {row[0].lower() for row in csv.reader(io.StringIO(text)) if row}
    if EDITOR_IMAGE in names:
        raise ApplyError('JianYing main editor process is still running; quit it first')
    return {'confirmed_by_user': True, 'main_process_closed': True}


def _run_codec(command, source, destination):
    if DLL_PATH is None or not Path(DLL_PATH).is_file():
        raise ApplyError('videoeditor.dll is not configured')
    if not CODEC_PATH.is_file():
        raise ApplyError('codec is not built; run bridge\\windows\\build.bat')
    try:
        result = subprocess.run([str(CODEC_PATH), command, str(DLL_PATH), str(source), str(destination)],
                                capture_output=True, timeout=COMMAND_TIMEOUT_SECONDS,
                                cwd=str(CODEC_PATH.parent))
    except subprocess.TimeoutExpired as exc:
        raise ApplyError('codec timed out') from exc
    if result.returncode != 0:
        raise ApplyError('codec %s failed: %s' % (command, result.stderr.decode(errors='replace').strip()))


def _decrypt_metadata_in_memory(encrypted_path):
    work = Path(tempfile.mkdtemp(prefix='jy14-codec-'))
    try:
        plain = work / 'plain.json'
        _run_codec('decrypt', Path(encrypted_path), plain)
        if plain.stat().st_size > MAX_METADATA_PLAINTEXT_BYTES:
            raise ApplyError('decrypted metadata exceeds the in-memory limit')
        payload = plain.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if not payload:
        raise ApplyError('codec returned empty plaintext')
    return _parse_strict_json(payload, 'decrypted draft metadata')


def _encrypt_metadata_from_memory(plaintext, encrypted_path):
    if not plaintext or len(plaintext) > MAX_METADATA_PLAINTEXT_BYTES:
        raise ApplyError('metadata plaintext size is invalid')
    encrypted_path = Path(encrypted_path)
    if encrypted_path.exists():
        raise ApplyError('refusing to overwrite ' + str(encrypted_path))
    work = Path(tempfile.mkdtemp(prefix='jy14-codec-'))
    try:
        plain = work / 'plain.json'
        plain.write_bytes(plaintext)
        _run_codec('encrypt', plain, encrypted_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _acquire_directory_transaction_lock(directory, label):
    if not Path(directory).is_dir():
        raise ApplyError('%s is not a directory' % label)
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT | getattr(os, 'O_BINARY', 0))
    try:
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    except OSError as exc:
        os.close(descriptor)
        raise ApplyError('another audited transaction holds the %s lock' % label) from exc
    info = Path(directory).stat()
    return descriptor, (info.st_dev, info.st_ino)


def _release_directory_transaction_lock(descriptor):
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    finally:
        os.close(descriptor)
