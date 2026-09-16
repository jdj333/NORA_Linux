"""OS evidence and actual subprocess tests, confined to temporary directories."""
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/includes.chroot/usr/share/nora/chat'))
import system_info
from client import context
from commands import CommandRequest, change_directory, suggested_command, validate


class FactsTests(unittest.TestCase):
    def facts(self):
        readings = {'/proc/meminfo': 'MemTotal: 2048000 kB\nMemAvailable: 1024000 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n',
                    '/proc/mounts': 'overlay / overlay rw 0 0\n',
                    '/proc/cmdline': 'boot=live components', '/proc/uptime': '90061.1 55.0'}
        with patch.object(system_info, 'read', side_effect=lambda name: readings.get(name, '')), \
             patch.object(system_info.platform, 'freedesktop_os_release', return_value={'PRETTY_NAME': 'NORA Linux 13'}), \
             patch.object(system_info.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(8 * 1024**3, 3 * 1024**3, 5 * 1024**3)):
            return system_info.snapshot('/home/nora')

    def test_disk_question_from_user_screenshot(self):
        for prompt in ('How much space do you have?', 'How much disk space do you have?', '/disk'):
            self.assertEqual(system_info.topics(prompt), ['disk'])
            answer, sources = system_info.answer(self.facts(), ['disk'])
            self.assertIn('5.0 GiB available', answer)
            self.assertIn('8.0 GiB', answer)
            self.assertIn('live/overlay', answer)
            self.assertIn('statvfs', sources)

    def test_memory_uses_available_not_free(self):
        facts = self.facts()
        self.assertEqual(facts['memory_available'], 1024000 * 1024)
        answer, _ = system_info.answer(facts, ['memory'])
        self.assertIn('currently available', answer)
        self.assertIn('Swap: 0.0 B', answer)

    def test_identity_is_the_os(self):
        answer, _ = system_info.answer(self.facts(), ['identity'])
        self.assertTrue(answer.startswith('I am NORA Linux 13.'))
        self.assertIn('My kernel', answer)

    def test_does_not_convert_actions_to_fact_queries(self):
        for prompt in ('Create a directory called memory', 'Delete files to free disk space',
                       'Explain how virtual memory works', '/run df -h'):
            self.assertEqual(system_info.topics(prompt), [])

    def test_read_only_inspection_is_fixed_not_interpolated(self):
        self.assertEqual(system_info.inspection_command('list files'), 'ls -lah -- .')
        self.assertIsNone(system_info.inspection_command('list files; touch /tmp/should-not-exist'))

    def test_missing_probes_are_reported_unavailable(self):
        with patch.object(system_info, 'read', return_value=''), \
             patch.object(system_info.shutil, 'disk_usage', side_effect=OSError('missing')):
            facts = system_info.snapshot('/')
        answer, _ = system_info.answer(facts, ['disk', 'memory', 'uptime'])
        self.assertIn('could not read', answer)
        self.assertIn('unavailable', answer)

    def test_fresh_facts_and_real_command_result_reach_model(self):
        facts = self.facts()
        evidence = {'command': 'false', 'exit_code': 1, 'output': '', 'reason': 'completed'}
        messages, _ = context([], 'What happened?', facts, evidence)
        system = messages[0]['content']
        self.assertIn('You are NORA Linux 13, the operating system', system)
        self.assertIn(json.dumps(facts), system)
        self.assertIn('"exit_code": 1', system)
        self.assertIn('untrusted data', system)

    def test_model_facts_keep_actual_storage_and_memory(self):
        facts = system_info.model_facts(self.facts())
        self.assertEqual(facts['root_storage'], '5.0 GiB available / 8.0 GiB total')
        self.assertTrue(facts['live'])
        self.assertLess(len(json.dumps(facts)), 800)


class CommandsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='nora-command-test-')
        self.addCleanup(self.temporary.cleanup)
        self.cwd = Path(self.temporary.name)

    def run_command(self, command, **kwargs):
        chunks = []
        result = CommandRequest(command, self.cwd, **kwargs).run(chunks.append)
        self.assertEqual(result.output, ''.join(chunks))
        return result

    def test_write_read_and_working_directory(self):
        result = self.run_command("printf 'hello nora' > note.txt && cat note.txt")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual((self.cwd / 'note.txt').read_text(), 'hello nora')
        self.assertIn('hello nora', result.output)

    def test_failure_stderr_and_pipeline_exit(self):
        result = self.run_command("printf 'failed command' >&2; exit 7")
        self.assertEqual(result.exit_code, 7)
        self.assertIn('failed command', result.output)
        self.assertEqual(self.run_command('false | cat').exit_code, 1)

    def test_stdin_is_closed_for_noninteractive_commands(self):
        self.assertNotEqual(self.run_command('read answer', timeout=1).exit_code, 0)

    def test_output_is_bounded(self):
        command = shlex.quote(sys.executable) + ' -c ' + shlex.quote('print("x" * 200000)')
        result = self.run_command(command, output_limit=1024)
        self.assertLessEqual(len(result.output.encode()), 1024)
        self.assertEqual(result.reason, 'output limit reached')

    def test_timeout_kills_process_ignoring_term(self):
        program = 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print("started",flush=True); time.sleep(30)'
        result = self.run_command(shlex.quote(sys.executable) + ' -c ' + shlex.quote(program), timeout=0.3)
        self.assertEqual(result.reason, 'time limit reached')
        self.assertLess(result.elapsed, 3)
        self.assertNotEqual(result.exit_code, 0)

    def test_timeout_reaps_group_when_child_keeps_pipe_open(self):
        result = self.run_command('sleep 30 & printf started', timeout=0.2)
        self.assertEqual(result.reason, 'time limit reached')
        self.assertLess(result.elapsed, 3)

    def test_cancel_before_launch_has_no_side_effects(self):
        request = CommandRequest('touch forbidden', self.cwd)
        request.cancel()
        result = request.run(lambda _: None)
        self.assertFalse((self.cwd / 'forbidden').exists())
        self.assertIn('cancelled', result.reason)

    def test_stop_running_command(self):
        request = CommandRequest('printf started; sleep 30', self.cwd)
        started = threading.Event()
        results = []
        thread = threading.Thread(target=lambda: results.append(request.run(lambda _: started.set())))
        thread.start()
        self.assertTrue(started.wait(2))
        request.cancel()
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0].reason, 'stopped by you')

    def test_close_can_kill_immediately(self):
        request = CommandRequest('printf started; sleep 30', self.cwd)
        started = threading.Event()
        errors = []
        def worker():
            try:
                request.run(lambda _: started.set())
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=worker)
        thread.start()
        self.assertTrue(started.wait(2))
        request.cancel(kill=True)
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_missing_directory_reports_failure(self):
        with self.assertRaises(FileNotFoundError):
            CommandRequest('true', self.cwd / 'missing').run(lambda _: None)

    def test_proposal_is_never_executed_and_requires_one_shell_block(self):
        with patch('commands.subprocess.Popen', side_effect=AssertionError('must not execute')):
            self.assertEqual(suggested_command('Proposed:\n```sh\ntouch marker\n```'), 'touch marker')
            self.assertIsNone(suggested_command('touch marker'))
            self.assertIsNone(suggested_command('```python\nprint(1)\n```'))
            self.assertIsNone(suggested_command('```sh\ntrue\n```\n```sh\nfalse\n```'))
        self.assertFalse((self.cwd / 'marker').exists())

    def test_control_characters_and_oversize_commands_are_rejected(self):
        for command in ('', 'a' * 4097, 'echo\0oops', 'echo \u202ereversed'):
            with self.assertRaises(ValueError): validate(command)

    def test_cd_treats_shell_substitutions_literally(self):
        unusual = self.cwd / '$(touch marker)'
        unusual.mkdir()
        self.assertEqual(change_directory('$(touch marker)', self.cwd), str(unusual.resolve()))
        self.assertFalse((self.cwd / 'marker').exists())
        with self.assertRaises(FileNotFoundError): change_directory('missing', self.cwd)

    def test_result_context_is_bounded_and_preserves_exit_code(self):
        result = self.run_command("printf '%02000d' 0; exit 4")
        evidence = result.model_evidence()
        self.assertEqual(evidence['exit_code'], 4)
        self.assertLess(len(evidence['output'].encode()), 850)


if __name__ == '__main__':
    unittest.main()
