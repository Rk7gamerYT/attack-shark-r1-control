"""Bounded subprocess entrypoint so HID requests cannot block the Qt UI."""
import json
import sys
from mouse import discover
from settings import apply_settings, read_settings


def run(request):
    receivers = [r for r in discover() if str(r.node) == request['node']]
    if len(receivers) != 1:
        raise ValueError('Receptor não encontrado. Reconecte e tente novamente.')
    receiver = receivers[0]
    if request['action'] == 'read':
        return read_settings(receiver)
    return {'message': apply_settings(receiver, request['section'], request['values'])}


if __name__ == '__main__':
    try:
        print(json.dumps(run(json.load(sys.stdin))))
    except Exception as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(1)
