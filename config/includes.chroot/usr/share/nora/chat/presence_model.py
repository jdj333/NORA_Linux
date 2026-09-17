"""Small, deterministic activity envelope for NORA's emerald."""
import math

LABELS = {'ready': 'Ready', 'loading': 'Model starting', 'thinking': 'Thinking…',
          'replying': 'Replying…', 'reading': 'Reading a website…',
          'command': 'Running a command…', 'stopping': 'Stopping…',
          'listening': 'Listening · microphone on', 'speaking': 'Speaking · microphone off'}
ACTIVE = frozenset({'thinking', 'replying', 'reading', 'command', 'stopping', 'listening', 'speaking'})


def intensity(state, elapsed, since_chunk=None, animate=True):
    """0..1 glow strength; response accents follow received text, not fake audio."""
    if not animate:
        return 0.40 if state in ACTIVE else 0.18
    if state == 'replying':
        accent = 0 if since_chunk is None else math.exp(-max(0, since_chunk) / 0.38)
        return min(0.82, 0.28 + 0.46 * accent + 0.06 * math.sin(elapsed * 3.1))
    if state in ACTIVE:
        period = 3.6 if state == 'thinking' else 4.4
        return 0.24 + 0.24 * (0.5 - 0.5 * math.cos(elapsed * math.tau / period))
    return 0.10 if state == 'loading' else 0.18
