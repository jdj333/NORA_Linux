"""Fresh, read-only Linux facts and deterministic answers to system questions."""
from datetime import datetime, timezone
import getpass
import os
from pathlib import Path
import platform
import re
import shutil


def read(path):
    try:
        return Path(path).read_text(errors='replace')
    except OSError:
        return ''


def human_bytes(value):
    if value is None:
        return 'unavailable'
    size = float(value)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if size < 1024 or unit == 'TiB':
            return f'{size:.1f} {unit}'
        size /= 1024


def snapshot(cwd):
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        release = {}
    memory = {}
    for line in read('/proc/meminfo').splitlines():
        match = re.fullmatch(r'(\w+):\s+(\d+) kB', line)
        if match:
            memory[match[1]] = int(match[2]) * 1024
    filesystems = []
    for label, path in [('root', '/'), ('home', str(Path.home()))]:
        try:
            usage = shutil.disk_usage(path)
            filesystems.append({'label': label, 'path': path, 'total': usage.total,
                                'used': usage.used, 'available': usage.free})
        except OSError:
            filesystems.append({'label': label, 'path': path, 'error': 'unavailable'})
    mounts = [line.split() for line in read('/proc/mounts').splitlines()]
    root_type = next((row[2] for row in mounts if len(row) >= 3 and row[1] == '/'), 'unknown')
    try:
        uptime = int(float(read('/proc/uptime').split()[0]))
    except (ValueError, IndexError):
        uptime = None
    return {
        'observed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'os': release.get('PRETTY_NAME', platform.system()),
        'kernel': platform.release(), 'architecture': platform.machine(),
        'hostname': platform.node(), 'user': getpass.getuser(), 'uid': os.getuid(),
        'cpu_count': os.cpu_count(), 'memory_total': memory.get('MemTotal'),
        'memory_available': memory.get('MemAvailable'),
        'swap_total': memory.get('SwapTotal'), 'swap_free': memory.get('SwapFree'),
        'uptime_seconds': uptime, 'root_filesystem': root_type,
        'live_session': 'boot=live' in read('/proc/cmdline').split(),
        'filesystems': filesystems, 'cwd': str(cwd),
    }


def topics(prompt):
    text = prompt.lower().strip()
    shortcuts = {'/system': ['identity', 'cpu', 'memory', 'disk', 'uptime'],
                 '/disk': ['disk'], '/memory': ['memory'], '/cpu': ['cpu'],
                 '/uptime': ['uptime']}
    if text in shortcuts:
        return shortcuts[text]
    # General explanations and action requests should go to the model, not be
    # mistaken for a request to measure the current machine.
    if re.search(r'\b(create|delete|remove|install|format|change|explain|compare)\b', text):
        return []
    if not re.match(r'^(how|what|which|who|show|tell|check|do you|are you|can you (show|tell|check))\b', text):
        return []
    found = []
    if re.search(r'\b(disk|storage|space|filesystem)\b', text): found.append('disk')
    if re.search(r'\b(memory|ram|swap)\b', text): found.append('memory')
    if re.search(r'\b(cpu|processor|cores|architecture)\b', text): found.append('cpu')
    if re.search(r'\b(uptime)\b|how long.*(running|up)', text): found.append('uptime')
    if re.search(r'\b(kernel|operating system|os|hostname)\b|who are you|what are you|about yourself', text):
        found.insert(0, 'identity')
    return found


def model_facts(facts):
    """Compact measurements keep first-token latency practical on small CPUs."""
    root = facts['filesystems'][0]
    storage = 'unavailable' if 'error' in root else (
        f"{human_bytes(root['available'])} available / {human_bytes(root['total'])} total")
    return {'os': facts['os'], 'kernel': facts['kernel'], 'arch': facts['architecture'],
            'cpus': facts['cpu_count'], 'user': f"{facts['user']} (UID {facts['uid']})",
            'cwd': facts['cwd'], 'RAM': f"{human_bytes(facts['memory_available'])} available / {human_bytes(facts['memory_total'])} total",
            'root_storage': storage, 'root_type': facts['root_filesystem'],
            'live': facts['live_session'], 'uptime_s': facts['uptime_seconds'],
            'observed_utc': facts['observed_utc']}


def answer(facts, selected):
    lines = []
    sources = []
    for topic in selected:
        if topic == 'identity':
            lines.append(f"I am {facts['os']}. My kernel is {facts['kernel']} on {facts['architecture']}. "
                         f"My hostname is {facts['hostname']}; this session runs as {facts['user']} (UID {facts['uid']}).")
            sources.append('/etc/os-release, uname, session identity')
        elif topic == 'disk':
            for filesystem in facts['filesystems']:
                if 'error' in filesystem:
                    lines.append(f"I could not read usage for {filesystem['path']}.")
                    continue
                lines.append(f"My {filesystem['label']} filesystem ({filesystem['path']}) has "
                             f"{human_bytes(filesystem['available'])} available out of "
                             f"{human_bytes(filesystem['total'])}; {human_bytes(filesystem['used'])} is used.")
            if facts['live_session'] or facts['root_filesystem'] == 'overlay':
                lines.append('I am using a live/overlay root filesystem. Its writable space is temporary; '
                             'these figures are not the capacity of an installed physical disk.')
            lines.append('Root and home figures may describe the same filesystem; do not add them together.')
            sources.append('statvfs / and home, /proc/mounts, /proc/cmdline')
        elif topic == 'memory':
            lines.append(f"I have {human_bytes(facts['memory_total'])} of RAM, with "
                         f"{human_bytes(facts['memory_available'])} currently available. "
                         f"Swap: {human_bytes(facts['swap_free'])} free of {human_bytes(facts['swap_total'])}.")
            sources.append('/proc/meminfo (MemAvailable includes reclaimable memory)')
        elif topic == 'cpu':
            lines.append(f"I see {facts['cpu_count']} logical CPUs and the {facts['architecture']} architecture.")
            sources.append('CPU count, uname')
        elif topic == 'uptime':
            seconds = facts['uptime_seconds']
            if seconds is None:
                lines.append('I could not read my uptime.')
            else:
                days, rest = divmod(seconds, 86400)
                hours, rest = divmod(rest, 3600)
                lines.append(f'I have been running for {days} days, {hours} hours, {rest // 60} minutes.')
            sources.append('/proc/uptime')
    return '\n'.join(lines), f"Observed {facts['observed_utc']} · Sources: " + '; '.join(sources)


def inspection_command(prompt):
    """Only fixed, read-only commands selected by explicit inspection requests."""
    text = prompt.lower().strip().rstrip('?.')
    choices = {
        '/processes': 'ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 16',
        '/network': 'ip -brief address && ip route',
        '/files': 'ls -lah -- .',
        'show running processes': 'ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 16',
        'what processes are running': 'ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 16',
        'what is your ip address': 'ip -brief address && ip route',
        'show network interfaces': 'ip -brief address && ip route',
        'list files': 'ls -lah -- .', 'show files': 'ls -lah -- .',
        'what files are here': 'ls -lah -- .',
    }
    return choices.get(text)
