"""Tests for state machine logic."""

from app.core.state_machine import OfficePhase, StateMachine
from app.models.agents import AgentState, BossState


class TestStateMachineInit:
    """Tests for StateMachine initialization."""

    def test_initial_phase_is_empty(self) -> None:
        """Initial phase should be EMPTY."""
        sm = StateMachine()
        assert sm.phase == OfficePhase.EMPTY

    def test_initial_boss_state_is_idle(self) -> None:
        """Initial boss state should be IDLE."""
        sm = StateMachine()
        assert sm.boss_state == BossState.IDLE

    def test_initial_agents_empty(self) -> None:
        """Initial agents dict should be empty."""
        sm = StateMachine()
        assert len(sm.agents) == 0

    def test_initial_queues_empty(self) -> None:
        """Initial queues should be empty."""
        sm = StateMachine()
        assert len(sm.arrival_queue) == 0
        assert len(sm.handin_queue) == 0

    def test_initial_token_counts_zero(self) -> None:
        """Initial token counts should be zero."""
        sm = StateMachine()
        assert sm.token_tracker.total_input_tokens == 0
        assert sm.token_tracker.total_output_tokens == 0

    def test_initial_tool_uses_zero(self) -> None:
        """Initial tool uses counter should be zero."""
        sm = StateMachine()
        assert sm.tool_uses_since_compaction == 0


class TestRemoveAgent:
    """Tests for remove_agent method."""

    def test_remove_existing_agent(self) -> None:
        """Should remove agent from agents dict."""
        sm = StateMachine()
        from app.models.agents import Agent

        sm.agents["agent1"] = Agent(
            id="agent1", name="Test", color="#ff0000", number=1, state=AgentState.WORKING
        )
        sm.remove_agent("agent1")
        assert "agent1" not in sm.agents

    def test_remove_agent_from_arrival_queue(self) -> None:
        """Should remove agent from arrival queue."""
        sm = StateMachine()
        from app.models.agents import Agent

        sm.agents["agent1"] = Agent(
            id="agent1", name="Test", color="#ff0000", number=1, state=AgentState.ARRIVING
        )
        sm.arrival_queue.append("agent1")
        sm.remove_agent("agent1")
        assert "agent1" not in sm.arrival_queue

    def test_remove_agent_from_handin_queue(self) -> None:
        """Should remove agent from handin queue."""
        sm = StateMachine()
        from app.models.agents import Agent

        sm.agents["agent1"] = Agent(
            id="agent1", name="Test", color="#ff0000", number=1, state=AgentState.COMPLETED
        )
        sm.handin_queue.append("agent1")
        sm.remove_agent("agent1")
        assert "agent1" not in sm.handin_queue

    def test_remove_nonexistent_agent_no_error(self) -> None:
        """Removing nonexistent agent should not raise error."""
        sm = StateMachine()
        sm.remove_agent("nonexistent")  # Should not raise


class TestToGameState:
    """Tests for to_game_state method."""

    def test_returns_game_state_object(self) -> None:
        """Should return a GameState object."""
        sm = StateMachine()
        state = sm.to_game_state("test_session")
        assert state.session_id == "test_session"

    def test_boss_state_copied(self) -> None:
        """Boss state should be included in game state."""
        sm = StateMachine()
        sm.boss_state = BossState.WORKING
        state = sm.to_game_state("test")
        assert state.boss.state == BossState.WORKING

    def test_desk_count_minimum_8(self) -> None:
        """Desk count should be at least 8."""
        sm = StateMachine()
        state = sm.to_game_state("test")
        assert state.office.desk_count >= 8

    def test_desk_count_capped_at_max_agents(self) -> None:
        """Desk count should not exceed MAX_AGENTS."""
        sm = StateMachine()
        from app.models.agents import Agent

        # Add 10 agents (more than MAX_AGENTS=8)
        for i in range(10):
            sm.agents[f"agent{i}"] = Agent(
                id=f"agent{i}",
                name=f"Test{i}",
                color="#ff0000",
                number=i,
                state=AgentState.WORKING,
            )
        state = sm.to_game_state("test")
        assert state.office.desk_count == StateMachine.MAX_AGENTS

    def test_context_utilization_calculated(self) -> None:
        """Context utilization should be calculated from tokens."""
        sm = StateMachine()
        sm.token_tracker.total_input_tokens = 100_000
        sm.token_tracker.total_output_tokens = 50_000
        state = sm.to_game_state("test")
        # 150,000 / 200,000 = 0.75
        assert state.office.context_utilization == 0.75

    def test_context_utilization_capped_at_1(self) -> None:
        """Context utilization should be capped at 1.0."""
        sm = StateMachine()
        sm.token_tracker.total_input_tokens = 300_000
        sm.token_tracker.total_output_tokens = 100_000
        state = sm.to_game_state("test")
        assert state.office.context_utilization == 1.0

    def test_queues_copied(self) -> None:
        """Queues should be copied to game state."""
        sm = StateMachine()
        sm.arrival_queue = ["a1", "a2"]
        sm.handin_queue = ["a3"]
        state = sm.to_game_state("test")
        assert state.arrival_queue == ["a1", "a2"]
        assert state.departure_queue == ["a3"]

    def test_tool_uses_included(self) -> None:
        """Tool uses counter should be in office state."""
        sm = StateMachine()
        sm.tool_uses_since_compaction = 42
        state = sm.to_game_state("test")
        assert state.office.tool_uses_since_compaction == 42

    def test_print_report_included(self) -> None:
        """Print report flag should be in office state."""
        sm = StateMachine()
        sm.print_report = True
        state = sm.to_game_state("test")
        assert state.office.print_report is True


class TestOfficePhase:
    """Tests for OfficePhase enum."""

    def test_all_phases_exist(self) -> None:
        """All expected phases should exist."""
        phases = [
            OfficePhase.EMPTY,
            OfficePhase.STARTING,
            OfficePhase.IDLE,
            OfficePhase.WORKING,
            OfficePhase.DELEGATING,
            OfficePhase.BUSY,
            OfficePhase.COMPLETING,
            OfficePhase.ENDED,
        ]
        assert len(phases) == 8

    def test_phases_are_unique(self) -> None:
        """All phases should have unique values."""
        values = [p.value for p in OfficePhase]
        assert len(values) == len(set(values))


class TestReviewQueue:
    """Tests for the PO review desk queue."""

    @staticmethod
    def _event(event_type: str, data: dict[str, object], ts: str = "2026-07-20T10:00:00+00:00"):
        from app.models.events import EventAdapter

        return EventAdapter.validate_python(
            {
                "event_type": event_type,
                "session_id": "s1",
                "timestamp": ts,
                "data": data,
            }
        )

    def test_stop_stacks_completion_item(self) -> None:
        from app.models.common import ReviewItemType

        sm = StateMachine()
        sm.transition(self._event("stop", {}))
        assert len(sm.review_queue) == 1
        item = sm.review_queue[0]
        assert item.item_type is ReviewItemType.COMPLETION
        assert item.created_at.isoformat() == "2026-07-20T10:00:00+00:00"

    def test_second_stop_replaces_completion_item(self) -> None:
        sm = StateMachine()
        sm.transition(self._event("stop", {}))
        sm.transition(self._event("stop", {}, ts="2026-07-20T10:05:00+00:00"))
        assert len(sm.review_queue) == 1
        assert sm.review_queue[0].created_at.isoformat() == "2026-07-20T10:05:00+00:00"

    def test_permission_request_stacks_permission_item(self) -> None:
        from app.models.common import ReviewItemType

        sm = StateMachine()
        sm.transition(self._event("permission_request", {"tool_name": "Bash"}))
        assert len(sm.review_queue) == 1
        assert sm.review_queue[0].item_type is ReviewItemType.PERMISSION
        assert sm.review_queue[0].label == "Bash"

    def test_duplicate_permission_label_keeps_first(self) -> None:
        sm = StateMachine()
        sm.transition(self._event("permission_request", {"tool_name": "Bash"}))
        sm.transition(
            self._event("permission_request", {"tool_name": "Bash"}, ts="2026-07-20T10:09:00+00:00")
        )
        assert len(sm.review_queue) == 1
        assert sm.review_queue[0].created_at.isoformat() == "2026-07-20T10:00:00+00:00"

    def test_notification_stacks_input_item(self) -> None:
        from app.models.common import ReviewItemType

        sm = StateMachine()
        sm.transition(self._event("notification", {"message": "Claude is waiting for your input"}))
        assert len(sm.review_queue) == 1
        assert sm.review_queue[0].item_type is ReviewItemType.INPUT

    def test_permission_flavoured_notification_skipped(self) -> None:
        sm = StateMachine()
        sm.transition(
            self._event("notification", {"message": "Claude needs your permission to use Bash"})
        )
        assert len(sm.review_queue) == 0

    def test_user_prompt_submit_clears_queue(self) -> None:
        sm = StateMachine()
        sm.transition(self._event("stop", {}))
        sm.transition(self._event("permission_request", {"tool_name": "Bash"}))
        sm.transition(self._event("user_prompt_submit", {"prompt": "next instruction"}))
        assert sm.review_queue == []

    def test_queue_bounded_by_max_review_items(self) -> None:
        sm = StateMachine()
        for i in range(sm.MAX_REVIEW_ITEMS + 5):
            sm.transition(
                self._event(
                    "permission_request",
                    {"tool_name": f"Tool{i}"},
                    ts=f"2026-07-20T10:{i:02d}:00+00:00" if i < 60 else "2026-07-20T11:00:00+00:00",
                )
            )
        assert len(sm.review_queue) == sm.MAX_REVIEW_ITEMS

    def test_review_queue_in_game_state(self) -> None:
        sm = StateMachine()
        sm.transition(self._event("stop", {}))
        state = sm.to_game_state("s1")
        assert len(state.review_queue) == 1

    def test_stop_clears_resolved_permission_and_input_items(self) -> None:
        """A finished turn clears permission/input blocks; only the report stays."""
        from app.models.common import ReviewItemType

        sm = StateMachine()
        sm.transition(self._event("permission_request", {"tool_name": "Bash"}))
        sm.transition(self._event("notification", {"message": "Claude is waiting for your input"}))
        sm.transition(self._event("stop", {}, ts="2026-07-20T10:10:00+00:00"))
        assert [i.item_type for i in sm.review_queue] == [ReviewItemType.COMPLETION]
