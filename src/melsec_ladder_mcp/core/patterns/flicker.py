"""Flicker (점멸) pattern using cross-coupled timers."""

from __future__ import annotations

from melsec_ladder_mcp.core.devices import DeviceAllocator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.core.patterns.base import BasePattern
from melsec_ladder_mcp.models.ladder import (
    CoilElement,
    ContactElement,
    ContactMode,
    ParallelBranch,
    Rung,
    SeriesConnection,
    TimerElement,
)
from melsec_ladder_mcp.models.timing import TimingDescription


class FlickerPattern(BasePattern):
    """Flicker/blink pattern using two cross-coupled timers.

    Generates a flicker circuit:
        LD  M0      (enable relay)
        ANI T1      (NOT timer 2)
        OUT T0 Kn   (timer 1)
        LD  T0      (timer 1 contact)
        OUT T1 Kn   (timer 2)
        LD  T0      (timer 1 ON period)
        ANI T1      (timer 2 OFF period)
        OUT Y0      (output)

    This creates: ON for Kn time, OFF for Kn time, repeating.
    """

    @property
    def name(self) -> str:
        return "flicker"

    @property
    def description(self) -> str:
        return "점멸 (N초 간격 반복 ON/OFF)"

    @property
    def priority(self) -> int:
        return 15

    def matches(self, timing: TimingDescription) -> bool:
        """Match if description mentions 점멸 or flicker."""
        desc = timing.description.lower()
        keywords = ["점멸", "flicker", "blink", "반복", "깜빡"]
        return any(kw in desc for kw in keywords)

    def generate(
        self,
        timing: TimingDescription,
        allocator: DeviceAllocator,
        builder: LadderBuilder,
    ) -> None:
        """Generate flicker circuit."""
        # Find flicker interval from sequences
        flicker_seconds = 1.0  # default 1 second
        flicker_output = None

        for seq in timing.sequences:
            if seq.delay and seq.delay > 0:
                flicker_seconds = seq.delay
            action_name = seq.action.split()[0]
            for out in timing.outputs:
                if out.name == action_name:
                    flicker_output = out
                    break

        if flicker_output is None and timing.outputs:
            flicker_output = timing.outputs[0]

        if flicker_output is None:
            return

        # Determine enable source
        enable_device = None
        if timing.inputs:
            start_input = timing.inputs[0]
            start_alloc = allocator.allocate_input(
                start_input.name,
                comment=start_input.comment or f"{start_input.name} (시작)",
            )

            if len(timing.inputs) >= 2:
                stop_input = timing.inputs[-1]
                stop_alloc = allocator.allocate_input(
                    stop_input.name,
                    comment=stop_input.comment or f"{stop_input.name} (정지)",
                )

                relay_alloc = allocator.allocate_relay(
                    f"M_{start_input.name}_HOLD",
                    comment=f"{start_input.name} 자기유지",
                )

                builder.add_self_hold_rung(
                    start_device=start_alloc.address.to_string(),
                    stop_device=stop_alloc.address.to_string(),
                    relay_device=relay_alloc.address.to_string(),
                    comment=f"{start_input.name} 자기유지 회로",
                )
                enable_device = relay_alloc.address.to_string()
            else:
                enable_device = start_alloc.address.to_string()

        if enable_device is None:
            return

        k_value = int(flicker_seconds * 10)
        if k_value <= 0:
            k_value = 10

        # Allocate timers and output
        t0_alloc = allocator.allocate_timer(
            f"T_FLICKER_ON",
            seconds=flicker_seconds,
            comment=f"점멸 ON 타이머 ({flicker_seconds}초)",
        )
        t1_alloc = allocator.allocate_timer(
            f"T_FLICKER_OFF",
            seconds=flicker_seconds,
            comment=f"점멸 OFF 타이머 ({flicker_seconds}초)",
        )
        out_alloc = allocator.allocate_output(
            flicker_output.name,
            comment=flicker_output.comment or flicker_output.name,
        )

        t0 = t0_alloc.address.to_string()
        t1 = t1_alloc.address.to_string()
        y = out_alloc.address.to_string()

        # Rung 1: enable AND NOT T1 → T0
        rung1 = Rung(
            number=builder._rung_counter,
            comment=f"점멸 타이머 1 ({flicker_seconds}초)",
            input_section=SeriesConnection(elements=[
                ContactElement(device=enable_device, mode=ContactMode.NO),
                ContactElement(device=t1, mode=ContactMode.NC),
            ]),
            output_section=[TimerElement(device=t0, k_value=k_value)],
        )
        builder.add_rung(rung1)
        builder._rung_counter += 1

        # Rung 2: T0 → T1
        rung2 = Rung(
            number=builder._rung_counter,
            comment=f"점멸 타이머 2 ({flicker_seconds}초)",
            input_section=SeriesConnection(elements=[
                ContactElement(device=t0, mode=ContactMode.NO),
            ]),
            output_section=[TimerElement(device=t1, k_value=k_value)],
        )
        builder.add_rung(rung2)
        builder._rung_counter += 1

        # Rung 3: T0 AND NOT T1 → output
        rung3 = Rung(
            number=builder._rung_counter,
            comment=f"{flicker_output.name} 점멸 출력",
            input_section=SeriesConnection(elements=[
                ContactElement(device=t0, mode=ContactMode.NO),
                ContactElement(device=t1, mode=ContactMode.NC),
            ]),
            output_section=[CoilElement(device=y)],
        )
        builder.add_rung(rung3)
        builder._rung_counter += 1

        builder.add_pattern("flicker")
