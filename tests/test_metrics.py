from my_crew.utils.metrics import MetricsCollector, extract_token_usage


class FakeUsage:
    prompt_tokens = 120
    completion_tokens = 80
    total_tokens = 200


class FakeResult:
    token_usage = FakeUsage()

    def __str__(self):
        return "workflow output text"


class TestExtractTokenUsage:
    def test_extracts_all_fields(self):
        usage = extract_token_usage(FakeResult())
        assert usage == {
            "prompt_tokens": 120,
            "completion_tokens": 80,
            "total_tokens": 200,
        }

    def test_plain_string_has_no_usage(self):
        assert extract_token_usage("just text") == {}


class TestMetricsCollector:
    def test_records_phase_with_tokens(self):
        collector = MetricsCollector()
        started = collector.start_timer()
        metric = collector.record_phase("research", started, FakeResult())

        assert metric.phase == "research"
        assert metric.attempt == 1
        assert metric.duration_s >= 0
        assert metric.output_chars == len("workflow output text")
        assert metric.total_tokens == 200

    def test_attempts_increment_per_phase(self):
        collector = MetricsCollector()
        collector.record_phase("research", collector.start_timer(), "one")
        collector.record_phase("research", collector.start_timer(), "two")
        collector.record_phase("planning", collector.start_timer(), "plan")

        attempts = [(m.phase, m.attempt) for m in collector.records]
        assert attempts == [("research", 1), ("research", 2), ("planning", 1)]

    def test_totals_aggregate(self):
        collector = MetricsCollector()
        collector.record_phase("research", collector.start_timer(), FakeResult())
        collector.record_phase("planning", collector.start_timer(), "no tokens here")

        totals = collector.totals()
        assert totals["phase_attempts"] == 2
        assert totals["total_tokens"] == 200
        assert totals["total_output_chars"] > 0

    def test_totals_tokens_none_when_unknown(self):
        collector = MetricsCollector()
        collector.record_phase("research", collector.start_timer(), "text only")
        assert collector.totals()["total_tokens"] is None

    def test_snapshot_is_serializable(self):
        collector = MetricsCollector()
        collector.record_phase("research", collector.start_timer(), FakeResult())
        snapshot = collector.snapshot()
        assert snapshot[0]["phase"] == "research"
        assert snapshot[0]["total_tokens"] == 200
