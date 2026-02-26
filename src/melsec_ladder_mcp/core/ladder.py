"""Fluent API for building ladder programs."""

from __future__ import annotations

from melsec_ladder_mcp.models.devices import DeviceMap
from melsec_ladder_mcp.models.ladder import (
    ApplicationElement,
    CoilElement,
    ContactElement,
    ContactMode,
    CounterElement,
    LadderProgram,
    ParallelBranch,
    Rung,
    SeriesConnection,
    SetResetElement,
    TimerElement,
)


class RungBuilder:
    """Fluent builder for a single rung."""

    def __init__(self, number: int, comment: str = "") -> None:
        self._number = number
        self._comment = comment
        self._input_elements: list = []
        self._parallel_groups: list[list] = []
        self._output_elements: list = []
        self._in_parallel = False

    def no_contact(self, device: str) -> RungBuilder:
        """Add a NO (a접점) contact."""
        self._input_elements.append(
            ContactElement(device=device, mode=ContactMode.NO)
        )
        return self

    def nc_contact(self, device: str) -> RungBuilder:
        """Add a NC (b접점) contact."""
        self._input_elements.append(
            ContactElement(device=device, mode=ContactMode.NC)
        )
        return self

    def or_contact(self, device: str, mode: ContactMode = ContactMode.NO) -> RungBuilder:
        """Add a parallel (OR) contact to the previous contact."""
        if not self._parallel_groups:
            # Move last input element to first parallel group
            if self._input_elements:
                last = self._input_elements.pop()
                self._parallel_groups.append([last])
        self._parallel_groups.append(
            [ContactElement(device=device, mode=mode)]
        )
        return self

    def coil(self, device: str) -> RungBuilder:
        """Add a coil output."""
        self._output_elements.append(CoilElement(device=device))
        return self

    def timer(self, device: str, k_value: int) -> RungBuilder:
        """Add a timer output."""
        self._output_elements.append(TimerElement(device=device, k_value=k_value))
        return self

    def counter(self, device: str, k_value: int) -> RungBuilder:
        """Add a counter output."""
        self._output_elements.append(CounterElement(device=device, k_value=k_value))
        return self

    def set_output(self, device: str) -> RungBuilder:
        """Add a SET output."""
        self._output_elements.append(SetResetElement(type="set", device=device))
        return self

    def reset_output(self, device: str) -> RungBuilder:
        """Add a RST output."""
        self._output_elements.append(SetResetElement(type="reset", device=device))
        return self

    def application(self, instruction: str, operands: list[str]) -> RungBuilder:
        """Add an application instruction output (MOV, +, -, INC, etc.)."""
        self._output_elements.append(
            ApplicationElement(instruction=instruction, operands=operands)
        )
        return self

    def build(self) -> Rung:
        """Build the rung."""
        if self._parallel_groups:
            # Build parallel branch for input section
            branches = []
            for group in self._parallel_groups:
                branches.append(SeriesConnection(elements=group))
            input_section = ParallelBranch(branches=branches)
            # If there are remaining series elements after the parallel section,
            # wrap in a series with the parallel branch
            if self._input_elements:
                input_section = SeriesConnection(
                    elements=[input_section] + self._input_elements
                )
        else:
            input_section = SeriesConnection(elements=self._input_elements)

        return Rung(
            number=self._number,
            comment=self._comment,
            input_section=input_section,
            output_section=self._output_elements,
        )


class LadderBuilder:
    """Fluent builder for a complete ladder program."""

    def __init__(self, name: str = "MAIN") -> None:
        self._name = name
        self._rungs: list[Rung] = []
        self._device_map = DeviceMap()
        self._detected_patterns: list[str] = []
        self._rung_counter = 0

    def set_device_map(self, device_map: DeviceMap) -> LadderBuilder:
        self._device_map = device_map
        return self

    def add_pattern(self, pattern_name: str) -> LadderBuilder:
        if pattern_name not in self._detected_patterns:
            self._detected_patterns.append(pattern_name)
        return self

    def rung(self, comment: str = "") -> RungBuilder:
        """Start building a new rung."""
        builder = RungBuilder(self._rung_counter, comment)
        self._rung_counter += 1
        return builder

    def add_rung(self, rung: Rung) -> LadderBuilder:
        """Add a pre-built rung."""
        self._rungs.append(rung)
        return self

    def add_self_hold_rung(
        self,
        start_device: str,
        stop_device: str,
        relay_device: str,
        comment: str = "",
    ) -> LadderBuilder:
        """Add a self-hold (자기유지) rung."""
        # LD start / OR relay / ANI stop / OUT relay
        parallel = ParallelBranch(
            branches=[
                SeriesConnection(elements=[
                    ContactElement(device=start_device, mode=ContactMode.NO),
                ]),
                SeriesConnection(elements=[
                    ContactElement(device=relay_device, mode=ContactMode.NO),
                ]),
            ]
        )
        stop_contact = ContactElement(device=stop_device, mode=ContactMode.NC)
        input_section = SeriesConnection(elements=[parallel, stop_contact])

        rung = Rung(
            number=self._rung_counter,
            comment=comment or f"자기유지 회로 ({relay_device})",
            input_section=input_section,
            output_section=[CoilElement(device=relay_device)],
        )
        self._rungs.append(rung)
        self._rung_counter += 1
        return self

    def add_output_rung(
        self, contact_device: str, output_device: str, comment: str = ""
    ) -> LadderBuilder:
        """Add a simple contact → output rung."""
        rung = Rung(
            number=self._rung_counter,
            comment=comment or f"{contact_device} → {output_device}",
            input_section=SeriesConnection(elements=[
                ContactElement(device=contact_device, mode=ContactMode.NO),
            ]),
            output_section=[CoilElement(device=output_device)],
        )
        self._rungs.append(rung)
        self._rung_counter += 1
        return self

    def add_timer_rung(
        self,
        contact_device: str,
        timer_device: str,
        k_value: int,
        comment: str = "",
    ) -> LadderBuilder:
        """Add a timer rung."""
        rung = Rung(
            number=self._rung_counter,
            comment=comment or f"타이머 {timer_device} (K{k_value})",
            input_section=SeriesConnection(elements=[
                ContactElement(device=contact_device, mode=ContactMode.NO),
            ]),
            output_section=[TimerElement(device=timer_device, k_value=k_value)],
        )
        self._rungs.append(rung)
        self._rung_counter += 1
        return self

    def add_stage_gated_rung(
        self,
        enable_device: str,
        gate_device: str,
        output_device: str,
        comment: str = "",
    ) -> LadderBuilder:
        """Add a stage-gated rung: LD enable / ANI gate / OUT output."""
        rung = Rung(
            number=self._rung_counter,
            comment=comment or f"{enable_device} AND NOT {gate_device} → {output_device}",
            input_section=SeriesConnection(elements=[
                ContactElement(device=enable_device, mode=ContactMode.NO),
                ContactElement(device=gate_device, mode=ContactMode.NC),
            ]),
            output_section=[CoilElement(device=output_device)],
        )
        self._rungs.append(rung)
        self._rung_counter += 1
        return self

    def add_counter_rung(
        self,
        contact_device: str,
        counter_device: str,
        k_value: int,
        comment: str = "",
    ) -> LadderBuilder:
        """Add a counter rung: LD contact / OUT Cn Kxx."""
        rung = Rung(
            number=self._rung_counter,
            comment=comment or f"카운터 {counter_device} (K{k_value})",
            input_section=SeriesConnection(elements=[
                ContactElement(device=contact_device, mode=ContactMode.NO),
            ]),
            output_section=[CounterElement(device=counter_device, k_value=k_value)],
        )
        self._rungs.append(rung)
        self._rung_counter += 1
        return self

    def add_counter_reset_rung(
        self,
        contact_device: str,
        counter_device: str,
        comment: str = "",
    ) -> LadderBuilder:
        """Add a counter reset rung: LD contact / RST Cn."""
        rung = Rung(
            number=self._rung_counter,
            comment=comment or f"카운터 리셋 {counter_device}",
            input_section=SeriesConnection(elements=[
                ContactElement(device=contact_device, mode=ContactMode.NO),
            ]),
            output_section=[SetResetElement(type="reset", device=counter_device)],
        )
        self._rungs.append(rung)
        self._rung_counter += 1
        return self

    def add_application_rung(
        self,
        contact_device: str,
        instruction: str,
        operands: list[str],
        comment: str = "",
    ) -> LadderBuilder:
        """Add an application instruction rung: LD contact / MOV K100 D0."""
        rung = Rung(
            number=self._rung_counter,
            comment=comment or f"{instruction} {' '.join(operands)}",
            input_section=SeriesConnection(elements=[
                ContactElement(device=contact_device, mode=ContactMode.NO),
            ]),
            output_section=[ApplicationElement(instruction=instruction, operands=operands)],
        )
        self._rungs.append(rung)
        self._rung_counter += 1
        return self

    def build(self) -> LadderProgram:
        """Build the complete ladder program."""
        return LadderProgram(
            name=self._name,
            device_map=self._device_map,
            rungs=self._rungs,
            detected_patterns=self._detected_patterns,
        )
