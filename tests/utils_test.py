"""This contains the unit tests for treadmill.utils.
"""

import os
import shutil
import signal
import stat
import tempfile
import time
import unittest

# Disable W0402: string deprecated
# pylint: disable=W0402
import string

import mock
import yaml

from treadmill import utils


class UtilsTest(unittest.TestCase):
    """This contains the treadmill.utils tests."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        if self.root and os.path.isdir(self.root):
            shutil.rmtree(self.root)

    @mock.patch('treadmill.subproc.get_aliases', mock.Mock(return_value={}))
    def test_create_script(self):
        """this tests the create_script function.

        the function creates executable scripts from templates that exist
        in the template directory.
        """
        script_file = os.path.join(self.root, 'script')
        # Function we are testing
        utils.create_script(script_file,
                            'supervisor.run',
                            service='testservice',
                            user='testproid',
                            home='home',
                            shell='shell',
                            cmd='run',
                            as_root=True)

        # Read the output from the mock filesystem
        with open(script_file) as script:
            data = script.read()

        # Validate that data is what it should be
        self.assertTrue(data.index(
            '${TREADMILL_S6}/bin/s6-setuidgid testproid') > 0)

        # Validate that the file is +x
        self.assertEqual(utils.os.stat(script_file).st_mode, 33261)

    @mock.patch('treadmill.subproc.get_aliases', mock.Mock(return_value={}))
    def test_create_script_perms(self):
        """this tests the create_script function (permissions).
        """
        script_file = os.path.join(self.root, 'script')
        # Test non-default mode (+x)
        mode = (stat.S_IRUSR |
                stat.S_IRGRP |
                stat.S_IROTH)

        utils.create_script(script_file,
                            'supervisor.run',
                            mode,
                            service='testservice',
                            user='testproid',
                            cmd='run')

        self.assertEqual(utils.os.stat(script_file).st_mode, 33060)

    def test_base_n(self):
        """Test to/from_base_n conversions."""
        alphabet = (string.digits +
                    string.ascii_lowercase +
                    string.ascii_uppercase)

        for base in [2, 10, 16, 36, 62]:
            for num in [0, 10, 2313, 23134223879243284]:
                n_num = utils.to_base_n(num, base=base, alphabet=alphabet)
                _num = utils.from_base_n(n_num, base=base, alphabet=alphabet)
                self.assertTrue(num == _num)

        self.assertEqual(utils.to_base_n(15, base=16), 'f')
        self.assertEqual(utils.to_base_n(10, base=2), '1010')

        self.assertEqual(
            utils.from_base_n('101', base=2),
            int('101', base=2),
        )
        self.assertEqual(
            utils.from_base_n('deadbeef', base=16),
            int('deadbeef', base=16)
        )

    def test_ip2int(self):
        """Tests IP string to int representation conversion."""
        self.assertEqual(0x40E9BB63, utils.ip2int('64.233.187.99'))

        ip = utils.ip2int('192.168.100.1')
        self.assertEqual('192.168.100.2', utils.int2ip(ip + 1))
        self.assertEqual('192.168.100.0', utils.int2ip(ip - 1))

        ip = utils.ip2int('192.168.100.255')
        self.assertEqual('192.168.101.0', utils.int2ip(ip + 1))

        ip = utils.ip2int('192.168.100.0')
        self.assertEqual('192.168.99.255', utils.int2ip(ip - 1))

    def test_to_obj(self):
        """Tests dict to namedtuple conversion."""
        obj = utils.to_obj({'a': 1, 'b': 2, 'c': 3}, 'foo')
        self.assertEqual(1, obj.a)
        self.assertEqual(2, obj.b)
        self.assertEqual(3, obj.c)

        obj = utils.to_obj({'a': 1, 'b': [1, 2, 3], 'c': 3}, 'foo')
        self.assertEqual(1, obj.a)
        self.assertEqual([1, 2, 3], obj.b)
        self.assertEqual(3, obj.c)

        obj = utils.to_obj({'a': 1, 'b': {'d': 5}, 'c': 3}, 'foo')
        self.assertEqual(1, obj.a)
        self.assertEqual(5, obj.b.d)
        self.assertEqual(3, obj.c)

        obj = utils.to_obj({'a': [1, {'d': 5}, 3], 'b': 33}, 'foo')
        self.assertEqual(1, obj.a[0])
        self.assertEqual(5, obj.a[1].d)
        self.assertEqual(3, obj.a[2])
        self.assertEqual(33, obj.b)

    def test_kilobytes(self):
        """Test memory/disk size string conversion."""
        self.assertEqual(10, utils.kilobytes('10K'))
        self.assertEqual(10, utils.kilobytes('10k'))
        self.assertRaises(Exception, utils.kilobytes, '10')

        self.assertEqual(10 * 1024, utils.kilobytes('10M'))
        self.assertEqual(10 * 1024, utils.kilobytes('10m'))

        self.assertEqual(10 * 1024 * 1024, utils.kilobytes('10G'))
        self.assertEqual(10 * 1024 * 1024, utils.kilobytes('10g'))

    def test_size_to_bytes(self):
        """Test conversion of units to bytes."""
        self.assertEqual(10, utils.size_to_bytes(10))
        self.assertEqual(-10, utils.size_to_bytes(-10))
        self.assertEqual(10, utils.size_to_bytes('10'))
        self.assertEqual(-10, utils.size_to_bytes('-10'))
        self.assertEqual(10 * 1024, utils.size_to_bytes('10K'))
        self.assertEqual(-10 * 1024, utils.size_to_bytes('-10K'))
        self.assertEqual(-10 * 1024 * 1024, utils.size_to_bytes('-10M'))

    def test_cpuunits(self):
        """Test conversion of cpu string to bmips."""
        self.assertEqual(10, utils.cpu_units('10%'))
        self.assertEqual(10, utils.cpu_units('10'))

    def test_validate(self):
        """Tests dictionary validation."""
        schema = [
            ('required', True, str),
            ('optional', False, str),
        ]

        struct = {'required': 'foo'}
        utils.validate(struct, schema)
        self.assertIn('optional', struct)

        struct = {'required': 'foo', 'optional': 'xxx'}
        utils.validate(struct, schema)

        struct = {'required': 'foo', 'optional': 1234}
        self.assertRaises(Exception, utils.validate,
                          struct, schema)

        schema = [
            ('required', True, list),
            ('optional', False, list),
        ]

        struct = {'required': ['foo']}
        utils.validate(struct, schema)

        struct = {'required': 'foo'}
        self.assertRaises(Exception, utils.validate,
                          struct, schema)

    def test_to_seconds(self):
        """Tests time interval to seconds conversion."""
        self.assertEqual(0, utils.to_seconds('0s'))
        self.assertEqual(3, utils.to_seconds('3s'))
        self.assertEqual(180, utils.to_seconds('3m'))
        self.assertEqual(7200, utils.to_seconds('2h'))
        self.assertEqual(259200, utils.to_seconds('3d'))

    def test_find_in_path(self):
        """Tests finding program in system path."""
        temp_dir = self.root
        saved_path = os.environ['PATH']
        # xxxx is not in path
        self.assertEqual('xxxx', utils.find_in_path('xxxx'))

        os.environ['PATH'] = os.environ['PATH'] + ':' + temp_dir

        open(os.path.join(temp_dir, 'xxxx'), 'w+').close()
        # xxxx is in path, but not executable.
        self.assertEqual('xxxx', utils.find_in_path('xxxx'))

        os.chmod(os.path.join(temp_dir, 'xxxx'), int(utils.EXEC_MODE))
        self.assertEqual(
            os.path.join(temp_dir, 'xxxx'),
            utils.find_in_path('xxxx')
        )

        os.environ['PATH'] = saved_path

    def test_humanreadable(self):
        """Tests conversion of values into human readable format."""
        self.assertEqual('1.0M', utils.bytes_to_readable(1024, 'K'))
        self.assertEqual('1.0G', utils.bytes_to_readable(1024, 'M'))
        self.assertEqual(
            '2.5T',
            utils.bytes_to_readable(1024 * 1024 * 2.5, 'M')
        )
        self.assertEqual('1.0K', utils.bytes_to_readable(1024, 'B'))
        self.assertEqual('2,310', utils.cpu_to_readable(2310))
        self.assertEqual('23.10', utils.cpu_to_cores_readable(2310))

    def test_tail(self):
        """Tests utils.tail."""
        filed, filepath = tempfile.mkstemp()
        with os.fdopen(filed, 'w') as f:
            for i in range(0, 5):
                f.write('%d\n' % i)

        with open(filepath) as f:
            lines = utils.tail_stream(f)
            self.assertEqual(['0\n', '1\n', '2\n', '3\n', '4\n'], lines)
        os.unlink(filepath)

        filed, filepath = tempfile.mkstemp()
        with os.fdopen(filed, 'w') as f:
            for i in range(0, 10000):
                f.write('%d\n' % i)
        with open(filepath) as f:
            lines = utils.tail_stream(f, 5)
            self.assertEqual(
                ['9995\n', '9996\n', '9997\n', '9998\n', '9999\n'],
                lines
            )

        # Test utils.tail given the file name.
        lines = utils.tail(filepath, 5)
        self.assertEqual(
            ['9995\n', '9996\n', '9997\n', '9998\n', '9999\n'],
            lines
        )
        os.unlink(filepath)

        self.assertEqual([], utils.tail('/no/such/thing'))

    @mock.patch('os.write', mock.Mock())
    @mock.patch('os.close', mock.Mock())
    def test_report_ready(self):
        """Tests reporting service readyness."""

        cwd = os.getcwd()
        tmpdir = self.root
        os.chdir(tmpdir)

        utils.report_ready()
        self.assertFalse(os.write.called)
        self.assertFalse(os.close.called)

        with open('notification-fd', 'w+') as f:
            f.write('300')
        utils.report_ready()
        os.write.assert_called_with(300, mock.ANY)
        os.close.assert_called_with(300)

        os.write.reset()
        os.close.reset()
        with open('notification-fd', 'w+') as f:
            f.write('300\n')
        utils.report_ready()
        os.write.assert_called_with(300, mock.ANY)
        os.close.assert_called_with(300)

        os.chdir(cwd)

    def test_signal_flag(self):
        """Tests signal flag."""
        signalled = utils.make_signal_flag(signal.SIGHUP, signal.SIGTERM)
        self.assertFalse(signalled)

        os.kill(os.getpid(), signal.SIGHUP)
        time.sleep(0.1)
        self.assertTrue(signalled)

        signalled.clear()
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(0.1)
        self.assertTrue(signalled)

    def test_to_yaml(self):
        """Tests conversion of dict to yaml representation."""

        obj = {
            'xxx': chr(40960) + 'abcd' + chr(1972)
        }

        self.assertEqual(yaml.dump(obj), '{xxx: abcd}\n')


if __name__ == '__main__':
    unittest.main()
