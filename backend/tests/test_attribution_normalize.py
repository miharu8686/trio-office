"""Tests for hook-side subagent attribution normalization on event intake."""

# pyright: reportPrivateUsage=false

from datetime import UTC, datetime
from typing import Literal

from app.core.event_processor import EventProcessor
from app.core.state_machine import StateMachine
from app.models.agents import Agent, AgentState
from app.models.events import EventType, ToolEvent, ToolEventData

SESSION_ID = "session-norm-001"

ToolEventType = Literal[
    EventType.PRE_TOOL_USE,
    EventType.POST_TOOL_USE,
    EventType.PERMISSION_REQUEST,
]


def create_test_agent(
    agent_id: str,
    native_id: str | None = None,
    state: AgentState = AgentState.WORKING,
) -> Agent:
    """Create a test agent with minimal required fields."""
    return Agent(
        id=agent_id,
        native_id=native_id,
        name=f"Agent-{agent_id[-4:]}",
        color="#3B82F6",
        number=1,
        state=state,
    )


def make_tool_event(
    agent_id: str | None,
    event_type: ToolEventType = EventType.PRE_TOOL_USE,
) -> ToolEvent:
    """Build a minimal tool event attributed to *agent_id*."""
    return ToolEvent(
        event_type=event_type,
        session_id=SESSION_ID,
        timestamp=datetime.now(UTC),
        data=ToolEventData(agent_id=agent_id, tool_name="Read"),
    )


def make_processor_with_agents(agents: dict[str, Agent]) -> EventProcessor:
    """Create an EventProcessor with a seeded StateMachine for SESSION_ID."""
    processor = EventProcessor()
    sm = StateMachine()
    sm.agents = agents
    sm.arrival_queue = list(agents.keys())
    processor.sessions[SESSION_ID] = sm
    return processor


class TestNormalizeToolEventAttribution:
    """Tests for EventProcessor._normalize_tool_event_attribution."""

    def test_native_id_rewritten_to_display_key(self) -> None:
        """subagent_<native_id> should become the registered display key."""
        processor = make_processor_with_agents(
            {"subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id="abc123")}
        )
        event = make_tool_event("subagent_abc123")

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "subagent_toolu_AAA"

    def test_post_tool_use_also_normalized(self) -> None:
        processor = make_processor_with_agents(
            {"subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id="abc123")}
        )
        event = make_tool_event("subagent_abc123", EventType.POST_TOOL_USE)

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "subagent_toolu_AAA"

    def test_main_left_unchanged(self) -> None:
        processor = make_processor_with_agents(
            {"subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id="abc123")}
        )
        event = make_tool_event("main")

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "main"

    def test_registered_display_key_left_unchanged(self) -> None:
        """An agent_id that already matches a registered agent is not touched."""
        processor = make_processor_with_agents(
            {"subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id="abc123")}
        )
        event = make_tool_event("subagent_toolu_AAA")

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "subagent_toolu_AAA"

    def test_unregistered_toolu_key_left_unchanged(self) -> None:
        """A display key whose agent was already removed must not be re-linked."""
        processor = make_processor_with_agents(
            {"subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id=None)}
        )
        event = make_tool_event("subagent_toolu_GONE")

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "subagent_toolu_GONE"
        # The unlinked agent must not have been FIFO-linked to a bogus native ID.
        assert processor.sessions[SESSION_ID].agents["subagent_toolu_AAA"].native_id is None

    def test_unknown_session_left_unchanged(self) -> None:
        processor = EventProcessor()
        event = make_tool_event("subagent_abc123")

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "subagent_abc123"

    def test_unlinked_agent_is_fifo_late_linked(self) -> None:
        """An event arriving before SUBAGENT_INFO links via the FIFO fallback."""
        processor = make_processor_with_agents(
            {"subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id=None)}
        )
        event = make_tool_event("subagent_abc123")

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "subagent_toolu_AAA"
        assert processor.sessions[SESSION_ID].agents["subagent_toolu_AAA"].native_id == "abc123"

    def test_two_unlinked_agents_fifo_linked_in_arrival_order(self) -> None:
        """With multiple unlinked agents, events link them in arrival order."""
        processor = make_processor_with_agents(
            {
                "subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id=None),
                "subagent_toolu_BBB": create_test_agent("subagent_toolu_BBB", native_id=None),
            }
        )
        first = make_tool_event("subagent_native_A")
        second = make_tool_event("subagent_native_B")

        processor._normalize_tool_event_attribution(first)
        processor._normalize_tool_event_attribution(second)

        agents = processor.sessions[SESSION_ID].agents
        assert first.data.agent_id == "subagent_toolu_AAA"
        assert agents["subagent_toolu_AAA"].native_id == "native_A"
        assert second.data.agent_id == "subagent_toolu_BBB"
        assert agents["subagent_toolu_BBB"].native_id == "native_B"

    def test_non_tool_event_types_ignored(self) -> None:
        processor = make_processor_with_agents(
            {"subagent_toolu_AAA": create_test_agent("subagent_toolu_AAA", native_id="abc123")}
        )
        event = make_tool_event("subagent_abc123", EventType.PERMISSION_REQUEST)

        processor._normalize_tool_event_attribution(event)

        assert event.data.agent_id == "subagent_abc123"
