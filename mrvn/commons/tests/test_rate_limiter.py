from unittest import TestCase

from commons.rate_limiter import RateLimiter, RateLimiterRegistry


class RateLimiterTestCase(TestCase):
    def test_unlimited_rate_limiter(self) -> None:
        """Rate limiter with rpm=0 should not limit requests."""
        limiter = RateLimiter(rpm=0)

        for _ in range(100):
            wait_time = limiter.get_wait_time()
            self.assertEqual(wait_time, 0.0)

    def test_rate_limiter_allows_requests_under_limit(self) -> None:
        """Requests under the limit should proceed immediately."""
        limiter = RateLimiter(rpm=10)

        for _ in range(10):
            wait_time = limiter.acquire()
            self.assertEqual(wait_time, 0.0)

    def test_rate_limiter_calculates_wait_time(self) -> None:
        """When limit is reached, wait time should be calculated."""
        limiter = RateLimiter(rpm=5)

        # Fill up the limit
        for _ in range(5):
            limiter.acquire()

        # Next request should require waiting
        wait_time = limiter.get_wait_time()
        self.assertGreater(wait_time, 0.0)
        self.assertLessEqual(wait_time, 60.0)

    def test_rate_limiter_current_count(self) -> None:
        """Current count should track requests in window."""
        limiter = RateLimiter(rpm=10)

        self.assertEqual(limiter.current_count, 0)

        limiter.acquire()
        self.assertEqual(limiter.current_count, 1)

        limiter.acquire()
        self.assertEqual(limiter.current_count, 2)

    def test_rate_limiter_reset(self) -> None:
        """Reset should clear all tracked timestamps."""
        limiter = RateLimiter(rpm=10)

        for _ in range(5):
            limiter.acquire()

        self.assertEqual(limiter.current_count, 5)

        limiter.reset()
        self.assertEqual(limiter.current_count, 0)


class RateLimiterRegistryTestCase(TestCase):
    def setUp(self) -> None:
        self.registry = RateLimiterRegistry()

    def test_get_or_create_creates_new_limiter(self) -> None:
        """Should create a new limiter for unknown agent."""
        limiter = self.registry.get_or_create(agent_id=1, rpm=60)

        self.assertIsInstance(limiter, RateLimiter)
        self.assertEqual(limiter.rpm, 60)

    def test_get_or_create_returns_existing_limiter(self) -> None:
        """Should return same limiter for same agent."""
        limiter1 = self.registry.get_or_create(agent_id=1, rpm=60)
        limiter2 = self.registry.get_or_create(agent_id=1, rpm=60)

        self.assertIs(limiter1, limiter2)

    def test_get_or_create_recreates_on_rpm_change(self) -> None:
        """Should create new limiter if RPM changes."""
        limiter1 = self.registry.get_or_create(agent_id=1, rpm=60)
        limiter2 = self.registry.get_or_create(agent_id=1, rpm=30)

        self.assertIsNot(limiter1, limiter2)
        self.assertEqual(limiter2.rpm, 30)

    def test_remove_limiter(self) -> None:
        """Should remove limiter for agent."""
        self.registry.get_or_create(agent_id=1, rpm=60)
        self.registry.remove(agent_id=1)

        # Next call should create a new limiter
        limiter = self.registry.get_or_create(agent_id=1, rpm=60)
        self.assertEqual(limiter.current_count, 0)

    def test_clear_all_limiters(self) -> None:
        """Should remove all limiters."""
        self.registry.get_or_create(agent_id=1, rpm=60)
        self.registry.get_or_create(agent_id=2, rpm=30)

        self.registry.clear()

        # All limiters should be new
        limiter1 = self.registry.get_or_create(agent_id=1, rpm=60)
        limiter2 = self.registry.get_or_create(agent_id=2, rpm=30)

        self.assertEqual(limiter1.current_count, 0)
        self.assertEqual(limiter2.current_count, 0)

    def test_separate_limiters_per_agent(self) -> None:
        """Different agents should have separate limiters."""
        limiter1 = self.registry.get_or_create(agent_id=1, rpm=60)
        limiter2 = self.registry.get_or_create(agent_id=2, rpm=30)

        self.assertIsNot(limiter1, limiter2)
        self.assertEqual(limiter1.rpm, 60)
        self.assertEqual(limiter2.rpm, 30)

        # Acquiring on one shouldn't affect the other
        limiter1.acquire()
        self.assertEqual(limiter1.current_count, 1)
        self.assertEqual(limiter2.current_count, 0)
