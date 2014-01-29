from unittest import TestCase
from mock import MagicMock, call

from loader import Counter



class Test_Counter(TestCase):
    def test_success(self):
        c = Counter(5)
        c._print = MagicMock()

        c.success()
        c._print.assert_called_with('done')
        c.success('xxx')
        c._print.assert_called_with('done (xxx)')


    def test_skipped(self):
        c = Counter(5)
        c._print = MagicMock()

        c.skipped()
        c._print.assert_called_with('skipped')
        c.skipped('xxx')
        c._print.assert_called_with('skipped (xxx)')


    def test_not_found(self):
        c = Counter(5)
        c._print = MagicMock()

        c.not_found()
        c._print.assert_called_with('file not found')
        c.not_found('xxx')
        c._print.assert_called_with('file not found (xxx)')


    def test_error(self):
        c = Counter(10)
        c._print = MagicMock()

        try:
            1/0
        except Exception:
            c.error()
            calls = c._print.call_args_list
            self.assertEqual('error', calls[0][0][0])
            self.assertTrue(calls[1][0][0].startswith('Traceback'))

            c._print.reset_mock()
            c.error('xxx')
            calls = c._print.call_args_list
            self.assertEqual('error (xxx)', calls[0][0][0])


    def test_counter(self):
        c = Counter(7)
        c._print = MagicMock()
        c.print_current('xxx')
        c._print.assert_called_with('Processing (1/7) xxx... ', True)

        c.error()
        c.print_current('yyy')
        c._print.assert_called_with('Processing (2/7) yyy... ', True)

        c.skipped()
        c.not_found()
        c.success()
        c.success()
        c.success()

        c._print.reset_mock()
        c.print_result()
        calls = [
            call('Warning: 7 should have been processed but only 6 were counted'),
            call('3 processed, 1 skipped, 1 not found, 1 errors'),
        ]
        c._print.assert_has_calls(calls)

        c.success()

        c._print.reset_mock()
        c.print_result()
        calls = [
            call('4 processed, 1 skipped, 1 not found, 1 errors')
        ]
        c._print.assert_has_calls(calls)

