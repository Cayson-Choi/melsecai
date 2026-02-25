"""Self-hold (자기유지) circuit pattern."""

from __future__ import annotations

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns.base import BasePattern
from melsec_ladder_mcp.models.timing import TimingDescription


class SelfHoldPattern(BasePattern):
    """Self-hold circuit: PB ON → Relay holds → PB2 OFF.

    Generates:
        LD  X0      (start button)
        OR  M0      (self-hold)
        ANI X1      (stop button)
        OUT M0      (relay)
    """

    @property
    def name(self) -> str:
        return "self_hold"

    @property
    def description(self) -> str:
        return "자기유지 회로 (PB ON → 유지 → PB OFF)"

    @property
    def priority(self) -> int:
        return 10

    def matches(self, timing: TimingDescription) -> bool:
        """Match if there's a start action and a stop/reset action."""
        has_start = False
        has_stop = False

        for seq in timing.sequences:
            action_upper = seq.action.upper()
            if "ON" in action_upper and "ALL" not in action_upper:
                has_start = True
            if "OFF" in action_upper or "정지" in seq.action or "STOP" in action_upper:
                has_stop = True

        return has_start and has_stop and len(timing.inputs) >= 2

    def generate(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
    ) -> None:
        """Generate self-hold circuit rungs."""
        if len(timing.inputs) < 2:
            return

        # Allocate devices
        start_input = timing.inputs[0]
        stop_input = timing.inputs[-1]  # Last input is typically stop

        start_alloc = allocator.allocate_input(
            start_input.name,
            comment=start_input.comment or f"{start_input.name} (시작)",
        )
        stop_alloc = allocator.allocate_input(
            stop_input.name,
            comment=stop_input.comment or f"{stop_input.name} (정지)",
        )

        # Allocate relay for self-hold
        relay_name = f"M_{start_input.name}_HOLD"
        relay_alloc = allocator.allocate_relay(
            relay_name,
            comment=f"{start_input.name} 자기유지",
        )

        start_addr = start_alloc.address.to_string()
        stop_addr = stop_alloc.address.to_string()
        relay_addr = relay_alloc.address.to_string()

        builder.add_self_hold_rung(
            start_device=start_addr,
            stop_device=stop_addr,
            relay_device=relay_addr,
            comment=f"{start_input.name} 자기유지 회로",
        )

        # Output first action if there's a direct output
        for seq in timing.sequences:
            if seq.trigger == start_input.name and seq.delay is None:
                action_name = seq.action.split()[0]  # e.g., "RL" from "RL ON"
                # Find matching output device
                for out in timing.outputs:
                    if out.name == action_name:
                        out_alloc = allocator.allocate_output(
                            out.name,
                            comment=out.comment or out.name,
                        )
                        builder.add_output_rung(
                            contact_device=relay_addr,
                            output_device=out_alloc.address.to_string(),
                            comment=f"{out.name} 출력",
                        )
                        break

        builder.add_pattern("self_hold")
