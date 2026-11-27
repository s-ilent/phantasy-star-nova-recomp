"""Coordinator-owned assignment manifests; hashes detect stale inputs, not malicious workers."""
import json
from pathlib import Path


def snapshot(records, digest):
    return digest({mid: digest(row) for mid, row in records.items()})


def load_manifest(path, records, digest, blocked):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('unsupported assignment manifest')
    if data.get('corpus_sha256') != snapshot(records, digest):
        raise ValueError('assignment manifest belongs to a different corpus snapshot')
    batches = data.get('assignments')
    if not isinstance(batches, dict):
        raise ValueError('missing manifest assignments')
    owners = {}
    for assignment_id, entries in batches.items():
        if not assignment_id or not isinstance(entries, dict) or not entries:
            raise ValueError('invalid assignment')
        for mid, fingerprint in entries.items():
            if mid in owners:
                raise ValueError(f'{mid}: duplicate assignment ownership')
            if mid not in records or fingerprint != digest(records[mid]) or blocked(records[mid]):
                raise ValueError(f'{mid}: stale or blocked assignment')
            owners[mid] = assignment_id
    return owners
