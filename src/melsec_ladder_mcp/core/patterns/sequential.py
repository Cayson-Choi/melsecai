"""Sequential control pattern (combines self-hold + timer delays).

Supports two modes:
- Cumulative: all timers driven by the same relay (Practice 11 style)
- Chained: each timer driven by the previous timer (car wash style)
"""

from __future__ import annotations

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns.base import BasePattern
from melsec_ladder_mcp.models.ladder import (
    CoilElement,
    ContactElement,
    ContactMode,
    Rung,
    SeriesConnection,
    TimerElement,
)
from melsec_ladder_mcp.models.timing import TimingDescription


class SequentialPattern(BasePattern):
    """Sequential control: combines self-hold + timer delays.

    Cumulative mode (all timers from relay):
        LD  X0 / OR M0 / ANI X1 / OUT M0
        LD  M0 → OUT Y0  (RL)
        LD  M0 → OUT T0 K50  (5s timer)
        LD  T0 → OUT Y1  (GL)
        LD  M0 → OUT T1 K100  (10s timer)
        LD  T1 → OUT Y2  (BZ)

    Chained mode (each timer from previous):
        LD  X0 / OR M0 / ANI X1 / OUT M0
        LD  M0 → OUT Y0  (RL)
        LD  M0 → OUT T0 K50  (stage 1 timer)
        LD  M0 / ANI T0 → OUT Y1  (stage 1 gated output)
        LD  T0 → OUT T1 K30  (stage 2 timer)
        LD  T0 / ANI T1 → OUT Y2  (stage 2 gated output)
        ...
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

    @staticmethod
    def _is_chained(timing: TimingDescription) -> bool:
        """Detect if sequences form a chain (vs cumulative/parallel timers).

        Cumulative: all delayed sequences share the same trigger.
        Chained: delayed sequences have different triggers forming a chain.
        """
        delayed = [s for s in timing.sequences if s.delay is not None and s.delay > 0]
        if len(delayed) < 2:
            return False
        triggers = {s.trigger for s in delayed}
        return len(triggers) > 1

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

        if self._is_chained(timing):
            self._generate_chained(timing, allocator, builder, relay_addr, start_input)
        else:
            self._generate_cumulative(timing, allocator, builder, relay_addr, start_input)

        builder.add_pattern("self_hold")
        builder.add_pattern("timer_delay")
        builder.add_pattern("sequential")

    def _generate_cumulative(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
        relay_addr: str,
        start_input,
    ) -> None:
        """Generate cumulative mode: all timers driven by the relay."""
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

    def _generate_chained(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
        relay_addr: str,
        start_input,
    ) -> None:
        """Generate chained mode: each timer driven by the previous timer."""
        # Build trigger → delayed sequences map
        trigger_map: dict[str, list[tuple[float, str, str]]] = {}
        for seq in timing.sequences:
            if seq.delay is None or seq.delay <= 0:
                continue
            action_upper = seq.action.upper()
            if "ALL" in action_upper:
                continue
            parts = seq.action.split()
            action_name = parts[0]
            action_kw = parts[1].upper() if len(parts) > 1 else "ON"
            trigger_map.setdefault(seq.trigger, []).append(
                (seq.delay, action_name, action_kw)
            )

        # Find chain starter among immediate outputs
        chain_starter = None
        direct_immediates = []
        for seq in timing.sequences:
            if seq.delay is not None:
                continue
            if seq.trigger != start_input.name:
                continue
            action_name = seq.action.split()[0]
            if action_name.upper() == "ALL":
                continue
            if f"{action_name} ON" in trigger_map:
                chain_starter = action_name
            else:
                direct_immediates.append(seq)

        # Generate direct immediate outputs (e.g., RL)
        for seq in direct_immediates:
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

        if chain_starter is None:
            return

        # Walk the chain
        current_name = chain_starter
        current_enable = relay_addr
        last_timer_addr = None
        flicker_entries: list[tuple[float, str]] = []
        completion_entries: list[tuple[float, str]] = []

        while True:
            trigger_key = f"{current_name} ON"
            if trigger_key not in trigger_map:
                break

            entries = trigger_map[trigger_key]
            duration = entries[0][0]

            # Classify entries: chain continuation vs flicker vs completion
            chain_next = None
            for _delay, action_name, action_kw in entries:
                if action_kw in ("FLICKER", "점멸"):
                    flicker_entries.append((_delay, action_name))
                elif f"{action_name} ON" in trigger_map:
                    chain_next = (_delay, action_name)
                else:
                    completion_entries.append((_delay, action_name))

            # Allocate timer for current stage
            timer_alloc = allocator.allocate_timer(
                f"T_{current_name}",
                seconds=duration,
                comment=f"{current_name} 타이머 ({duration}초)",
            )
            timer_addr = timer_alloc.address.to_string()
            k_value = timer_alloc.timer_config.k_value

            # Timer rung: enable → timer
            builder.add_timer_rung(
                contact_device=current_enable,
                timer_device=timer_addr,
                k_value=k_value,
                comment=f"{duration}초 타이머 ({current_name}용)",
            )

            # Stage gated output: enable AND NOT timer → output
            for out in timing.outputs:
                if out.name == current_name:
                    out_alloc = allocator.allocate_output(
                        out.name,
                        comment=out.comment or out.name,
                    )
                    builder.add_stage_gated_rung(
                        enable_device=current_enable,
                        gate_device=timer_addr,
                        output_device=out_alloc.address.to_string(),
                        comment=f"{out.name} 출력",
                    )
                    break

            last_timer_addr = timer_addr

            # If flicker/completion entries found, this is the last chain stage
            if flicker_entries or completion_entries:
                if chain_next:
                    current_enable = timer_addr
                    current_name = chain_next[1]
                    continue
                break

            if chain_next:
                current_enable = timer_addr
                current_name = chain_next[1]
            else:
                break

        # Handle the last stage (the one that triggers flicker/completion)
        if last_timer_addr and current_name != chain_starter:
            # Check if last stage still needs its timer+output
            trigger_key = f"{current_name} ON"
            if trigger_key in trigger_map:
                # Already handled in the loop above
                pass
            elif trigger_key not in trigger_map:
                # This is a terminal stage with no further triggers
                # It was the target of the last chain_next but has no entries
                # Its output was already gated in the loop; nothing more to do
                pass

        if not last_timer_addr:
            return

        # Post-chain: completion relay, flicker, completion outputs
        if flicker_entries or completion_entries:
            # Allocate completion relay
            complete_alloc = allocator.allocate_relay(
                "M_COMPLETE",
                comment="완료 릴레이",
            )
            complete_addr = complete_alloc.address.to_string()

            # Completion relay rung: last_timer → M_COMPLETE
            builder.add_output_rung(
                contact_device=last_timer_addr,
                output_device=complete_addr,
                comment="완료 릴레이",
            )

            # Flicker outputs
            for _delay, action_name in flicker_entries:
                self._generate_flicker_circuit(
                    timing, allocator, builder,
                    enable_device=complete_addr,
                    output_name=action_name,
                )

            # Completion outputs (direct from completion relay)
            for _delay, action_name in completion_entries:
                for out in timing.outputs:
                    if out.name == action_name:
                        out_alloc = allocator.allocate_output(
                            out.name,
                            comment=out.comment or out.name,
                        )
                        builder.add_output_rung(
                            contact_device=complete_addr,
                            output_device=out_alloc.address.to_string(),
                            comment=f"{out.name} 출력",
                        )
                        break

    @staticmethod
    def _generate_flicker_circuit(
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
        enable_device: str,
        output_name: str,
        flicker_seconds: float = 0.5,
    ) -> None:
        """Generate a cross-coupled flicker circuit for a single output."""
        k_value = int(flicker_seconds * 10)
        if k_value <= 0:
            k_value = 5

        # Allocate flicker timers
        t_on_alloc = allocator.allocate_timer(
            f"T_FLICKER_{output_name}_ON",
            seconds=flicker_seconds,
            comment=f"점멸 ON ({output_name}용)",
        )
        t_off_alloc = allocator.allocate_timer(
            f"T_FLICKER_{output_name}_OFF",
            seconds=flicker_seconds,
            comment=f"점멸 OFF ({output_name}용)",
        )

        t_on = t_on_alloc.address.to_string()
        t_off = t_off_alloc.address.to_string()

        # Allocate output
        out_alloc = None
        for out in timing.outputs:
            if out.name == output_name:
                out_alloc = allocator.allocate_output(
                    out.name,
                    comment=out.comment or out.name,
                )
                break

        if out_alloc is None:
            return

        y = out_alloc.address.to_string()

        # Rung: enable AND NOT t_off → t_on
        rung1 = Rung(
            number=builder._rung_counter,
            comment=f"점멸 타이머 ON ({output_name}용)",
            input_section=SeriesConnection(elements=[
                ContactElement(device=enable_device, mode=ContactMode.NO),
                ContactElement(device=t_off, mode=ContactMode.NC),
            ]),
            output_section=[TimerElement(device=t_on, k_value=k_value)],
        )
        builder.add_rung(rung1)
        builder._rung_counter += 1

        # Rung: t_on → t_off
        rung2 = Rung(
            number=builder._rung_counter,
            comment=f"점멸 타이머 OFF ({output_name}용)",
            input_section=SeriesConnection(elements=[
                ContactElement(device=t_on, mode=ContactMode.NO),
            ]),
            output_section=[TimerElement(device=t_off, k_value=k_value)],
        )
        builder.add_rung(rung2)
        builder._rung_counter += 1

        # Rung: t_on AND NOT t_off → output
        rung3 = Rung(
            number=builder._rung_counter,
            comment=f"{output_name} 점멸 출력",
            input_section=SeriesConnection(elements=[
                ContactElement(device=t_on, mode=ContactMode.NO),
                ContactElement(device=t_off, mode=ContactMode.NC),
            ]),
            output_section=[CoilElement(device=y)],
        )
        builder.add_rung(rung3)
        builder._rung_counter += 1
