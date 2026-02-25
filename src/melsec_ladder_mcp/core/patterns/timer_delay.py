"""Timer delay pattern."""

from __future__ import annotations

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns.base import BasePattern
from melsec_ladder_mcp.models.timing import TimingDescription


class TimerDelayPattern(BasePattern):
    """Timer delay: source ON → N seconds → target ON.

    Generates:
        LD  M0          (source relay)
        OUT T0 K50      (timer, 5 seconds)
        LD  T0          (timer contact)
        OUT Y1          (target output)
    """

    @property
    def name(self) -> str:
        return "timer_delay"

    @property
    def description(self) -> str:
        return "타이머 지연 (N초 후 동작)"

    @property
    def priority(self) -> int:
        return 5

    def matches(self, timing: TimingDescription) -> bool:
        """Match if any sequence step has a delay."""
        return any(seq.delay is not None and seq.delay > 0 for seq in timing.sequences)

    def generate(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
    ) -> None:
        """Generate timer delay rungs for delayed sequence steps."""
        for seq in timing.sequences:
            if seq.delay is None or seq.delay <= 0:
                continue

            # Determine the source device (what triggers the timer)
            source_device = self._resolve_source(seq.trigger, timing, allocator)
            if source_device is None:
                continue

            # Determine the target output
            action_name = seq.action.split()[0]
            if action_name.upper() == "ALL":
                continue

            target_output = None
            for out in timing.outputs:
                if out.name == action_name:
                    target_output = out
                    break

            if target_output is None:
                continue

            # Allocate timer
            timer_name = f"T_{action_name}"
            timer_alloc = allocator.allocate_timer(
                timer_name,
                seconds=seq.delay,
                comment=f"{seq.delay}초 지연 ({action_name}용)",
            )

            # Allocate output
            out_alloc = allocator.allocate_output(
                target_output.name,
                comment=target_output.comment or target_output.name,
            )

            timer_addr = timer_alloc.address.to_string()

            # Timer rung: source → timer
            builder.add_timer_rung(
                contact_device=source_device,
                timer_device=timer_addr,
                k_value=timer_alloc.timer_config.k_value,
                comment=f"{seq.delay}초 타이머 ({action_name}용)",
            )

            # Output rung: timer contact → output
            builder.add_output_rung(
                contact_device=timer_addr,
                output_device=out_alloc.address.to_string(),
                comment=f"{action_name} 출력",
            )

        builder.add_pattern("timer_delay")

    def _resolve_source(
        self,
        trigger: str,
        timing: TimingDescription,
        allocator: DeviceAllocator,
    ) -> str | None:
        """Resolve a trigger name to a device address string."""
        # Check if trigger references an output "XX ON"
        parts = trigger.split()
        trigger_name = parts[0]

        # Check if it's an allocated relay
        alloc = allocator.get_allocation(f"M_{trigger_name}_HOLD")
        if alloc:
            return alloc.address.to_string()

        # Check if it's a direct input
        alloc = allocator.get_allocation(trigger_name)
        if alloc:
            return alloc.address.to_string()

        # Try to find in inputs
        for inp in timing.inputs:
            if inp.name == trigger_name:
                alloc = allocator.allocate_input(
                    inp.name,
                    comment=inp.comment or inp.name,
                )
                return alloc.address.to_string()

        return None
