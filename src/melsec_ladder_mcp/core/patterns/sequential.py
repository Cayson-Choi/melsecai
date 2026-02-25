"""Sequential control pattern (combines self-hold + timer delays)."""

from __future__ import annotations

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns.base import BasePattern
from melsec_ladder_mcp.models.timing import TimingDescription


class SequentialPattern(BasePattern):
    """Sequential control: combines self-hold + timer delays.

    Typical pattern: PB1 → RL ON → 5s → GL ON → 10s → BZ ON, PB2 → ALL OFF

    Generates:
        LD  X0          (start)
        OR  M0          (self-hold)
        ANI X1          (stop)
        OUT M0          (relay)
        LD  M0          → OUT Y0  (RL)
        LD  M0          → OUT T0 K50  (5s timer)
        LD  T0          → OUT Y1  (GL)
        LD  M0          → OUT T1 K100  (10s timer)
        LD  T1          → OUT Y2  (BZ)
    """

    @property
    def name(self) -> str:
        return "sequential"

    @property
    def description(self) -> str:
        return "순차 제어 (자기유지 + 타이머 복합)"

    @property
    def priority(self) -> int:
        return 20

    def matches(self, timing: TimingDescription) -> bool:
        has_self_hold = False
        has_timer = False

        for seq in timing.sequences:
            action_upper = seq.action.upper()
            if seq.delay is None and "ON" in action_upper and "ALL" not in action_upper:
                has_self_hold = True
            if seq.delay is not None and seq.delay > 0:
                has_timer = True

        return has_self_hold and has_timer and len(timing.inputs) >= 2

    def generate(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
    ) -> None:
        """Generate sequential control rungs."""
        start_input = timing.inputs[0]
        stop_input = timing.inputs[-1]

        # Allocate inputs
        start_alloc = allocator.allocate_input(
            start_input.name,
            comment=start_input.comment or f"{start_input.name} (시작)",
        )
        stop_alloc = allocator.allocate_input(
            stop_input.name,
            comment=stop_input.comment or f"{stop_input.name} (정지)",
        )

        # Allocate self-hold relay
        relay_alloc = allocator.allocate_relay(
            "M_HOLD",
            comment="운전 자기유지",
        )

        start_addr = start_alloc.address.to_string()
        stop_addr = stop_alloc.address.to_string()
        relay_addr = relay_alloc.address.to_string()

        # Rung 0: Self-hold circuit
        builder.add_self_hold_rung(
            start_device=start_addr,
            stop_device=stop_addr,
            relay_device=relay_addr,
            comment=f"{start_input.name} 자기유지 회로",
        )

        # Direct outputs (no delay) — driven by the relay
        for seq in timing.sequences:
            if seq.trigger == start_input.name and seq.delay is None:
                action_name = seq.action.split()[0]
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

        # Timer delayed outputs — all timers driven by the relay
        for seq in timing.sequences:
            if seq.delay is None or seq.delay <= 0:
                continue

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
            timer_alloc = allocator.allocate_timer(
                f"T_{action_name}",
                seconds=seq.delay,
                comment=f"{seq.delay}초 지연 ({action_name}용)",
            )

            # Allocate output
            out_alloc = allocator.allocate_output(
                target_output.name,
                comment=target_output.comment or target_output.name,
            )

            timer_addr = timer_alloc.address.to_string()

            # Timer rung: relay → timer
            builder.add_timer_rung(
                contact_device=relay_addr,
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

        builder.add_pattern("self_hold")
        builder.add_pattern("timer_delay")
        builder.add_pattern("sequential")
