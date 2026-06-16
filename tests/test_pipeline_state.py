import unittest

from tools_library.pipeline_state import PipelineState, PENDING, IN_PROGRESS, DONE, ERROR


class TestPipelineState(unittest.TestCase):
    def test_head_starts_at_first_step(self):
        state = PipelineState(["a", "b", "c"])
        self.assertEqual(state.head().name, "a")

    def test_mark_done_advances_without_auto_continue(self):
        state = PipelineState(["a", "b"])
        a = state.head()
        state.start(a)
        nxt = state.mark_done(a)
        self.assertIsNone(nxt)
        self.assertEqual(a.status, DONE)
        self.assertEqual(state.head().name, "b")

    def test_auto_continue_chains_through_multiple_steps(self):
        state = PipelineState(["a", "b", "c", "d"])
        state.get("b").auto_continue = True
        state.get("c").auto_continue = True

        a = state.head()
        state.start(a)
        nxt = state.mark_done(a)
        self.assertEqual(nxt.name, "b")

        state.start(nxt)
        nxt2 = state.mark_done(nxt)
        self.assertEqual(nxt2.name, "c")

        state.start(nxt2)
        nxt3 = state.mark_done(nxt2)
        self.assertIsNone(nxt3)
        self.assertEqual(state.head().name, "d")

    def test_cancel_reverts_to_pending_and_becomes_head(self):
        state = PipelineState(["a", "b"])
        a = state.head()
        state.start(a)
        self.assertEqual(a.status, IN_PROGRESS)
        state.mark_cancelled(a)
        self.assertEqual(a.status, PENDING)
        self.assertIs(state.head(), a)

    def test_cancel_does_not_auto_resume_even_if_checked(self):
        state = PipelineState(["a", "b"])
        state.get("a").auto_continue = True
        a = state.head()
        state.start(a)
        state.mark_cancelled(a)
        self.assertEqual(state.head().name, "a")
        self.assertEqual(a.status, PENDING)

    def test_is_finished(self):
        state = PipelineState(["a"])
        a = state.head()
        self.assertFalse(state.is_finished())
        state.start(a)
        state.mark_done(a)
        self.assertTrue(state.is_finished())
        self.assertIsNone(state.head())

    def test_set_auto_continue(self):
        state = PipelineState(["a", "b"])
        b = state.get("b")
        state.set_auto_continue(b, True)
        self.assertTrue(b.auto_continue)

    def test_get_unknown_name_returns_none(self):
        state = PipelineState(["a"])
        self.assertIsNone(state.get("nonexistent"))

    def test_mark_error_halts_and_stays_head(self):
        state = PipelineState(["a", "b"])
        a = state.head()
        state.start(a)
        state.mark_error(a)
        self.assertEqual(a.status, ERROR)
        self.assertIs(state.head(), a)

    def test_error_does_not_auto_continue_even_if_next_checked(self):
        state = PipelineState(["a", "b"])
        state.get("b").auto_continue = True
        a = state.head()
        state.start(a)
        state.mark_error(a)
        # mark_error returns nothing to start automatically — caller must not
        # advance past an errored step regardless of the next step's checkbox.
        self.assertEqual(state.head().name, "a")

    def test_retry_error_resets_to_pending(self):
        state = PipelineState(["a", "b"])
        a = state.head()
        state.start(a)
        state.mark_error(a)
        state.retry_error(a)
        self.assertEqual(a.status, PENDING)
        self.assertIs(state.head(), a)

    def test_retry_error_noop_when_not_errored(self):
        state = PipelineState(["a"])
        a = state.head()
        state.retry_error(a)
        self.assertEqual(a.status, PENDING)


if __name__ == "__main__":
    unittest.main()
