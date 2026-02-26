"""GXW (GX Works2 project) file builder.

Generates binary .gxw files from IL instructions by:
1. Encoding IL instructions to MELSEC-Q binary ladder format
2. Modifying the template .gxw via raw OLE2 byte patching

Uses raw byte manipulation to preserve the exact OLE2/CFBF structure,
ensuring GX Works2 can open the resulting files without corruption errors.
"""

from __future__ import annotations

import io
import re
import struct
from pathlib import Path

import olefile

from melsec_ladder_mcp.models.instructions import Instruction, InstructionType

# ── Device type codes ────────────────────────────────────────────────────

DEVICE_CODES: dict[str, int] = {
    "X": 0x9C,
    "Y": 0x9D,
    "M": 0x90,
    "T": 0xC2,
    "C": 0xC5,
    "D": 0xA8,
}

# ── Instruction opcodes (03-prefix, 2-byte) ──────────────────────────────

_CONTACT_OPCODES: dict[InstructionType, int] = {
    InstructionType.LD: 0x00,
    InstructionType.LDI: 0x01,
    InstructionType.OR: 0x06,
    InstructionType.ORI: 0x07,
    InstructionType.AND: 0x0C,
    InstructionType.ANI: 0x0D,
}

_COIL_OPCODES: dict[InstructionType, int] = {
    InstructionType.OUT: 0x20,
    InstructionType.SET: 0x22,
    InstructionType.RST: 0x24,
}

_STANDALONE_OPCODES: dict[InstructionType, int] = {
    InstructionType.ORB: 0x08,
    InstructionType.ANB: 0x0E,
    InstructionType.MPS: 0x18,
    InstructionType.MRD: 0x19,
    InstructionType.MPP: 0x1A,
}

# ── Stream structure constants ───────────────────────────────────────────

_STREAM12_HEADER_SIZE = 54
_STREAM12_BLOCK_SIZE_BYTES = 4
_STREAM12_PADDING = b"\x00" * 20
_STREAM12_TRAILER = (
    b"\x01\x00\x00\x00"  # block count = 1
    b"\x05\x00\x00\x00"  # name length = 5 wchars
    b"M\x00A\x00I\x00N\x00\x00\x00"  # "MAIN\0" UTF-16LE
    b"\x04\x00\x00\x00"  # unknown (maybe entry type)
    b"\x01\x00\x00\x00"  # unknown
)

_STREAM16_HEADER_SIZE = 79
_STREAM16_PADDING_SIZE = 24
_STREAM16_SIZE_OFFSET_A = 0x37
_STREAM16_SIZE_OFFSET_B = 0x3B

TEMPLATE_PATH = Path(__file__).parent / "template.gxw"


def _parse_device(device_str: str) -> tuple[int, int]:
    """Parse device string like 'X0', 'M100', 'T0' into (type_code, address).

    Returns (device_type_byte, address_int).
    """
    prefix = ""
    for ch in device_str:
        if ch.isalpha():
            prefix += ch
        else:
            break
    addr_str = device_str[len(prefix):]
    prefix = prefix.upper()

    if prefix not in DEVICE_CODES:
        raise ValueError(f"Unknown device prefix: {prefix!r} in {device_str!r}")

    type_code = DEVICE_CODES[prefix]
    address = int(addr_str, 16) if prefix in ("X", "Y") else int(addr_str)
    return type_code, address


def _encode_device(type_code: int, address: int) -> bytes:
    """Encode a device reference as binary token.

    1-byte address (0-255):  03 04 DD AA 04
    2-byte address (256+):   03 05 DD AA_lo AA_hi 05
    """
    if address <= 0xFF:
        return bytes([0x03, 0x04, type_code, address, 0x04])
    else:
        lo = address & 0xFF
        hi = (address >> 8) & 0xFF
        return bytes([0x03, 0x05, type_code, lo, hi, 0x05])


def _encode_k_value(k: int) -> bytes:
    """Encode a K constant value.

    1-byte (0-255):  04 e8 KK 04
    2-byte (256+):   04 e9 KK_lo KK_hi 04  (estimated)
    """
    if k <= 0xFF:
        return bytes([0x04, 0xE8, k, 0x04])
    else:
        lo = k & 0xFF
        hi = (k >> 8) & 0xFF
        return bytes([0x04, 0xE9, lo, hi, 0x04])


class ILBinaryEncoder:
    """Encodes IL instructions to MELSEC-Q binary ladder bytes."""

    def encode(self, instructions: list[Instruction]) -> bytes:
        """Encode a list of IL instructions to binary program bytes."""
        parts: list[bytes] = []
        for inst in instructions:
            parts.append(self._encode_one(inst))
        return b"".join(parts)

    def _encode_one(self, inst: Instruction) -> bytes:
        itype = inst.instruction

        # END instruction — fixed 4-byte token
        if itype == InstructionType.END:
            return bytes([0x04, 0x34, 0x02, 0x04])

        # Contact instructions (LD, LDI, AND, ANI, OR, ORI) — opcode + device
        if itype in _CONTACT_OPCODES:
            opcode = _CONTACT_OPCODES[itype]
            header = bytes([0x03, opcode])
            if inst.device is None:
                raise ValueError(f"{itype.value} requires a device operand")
            tc, addr = _parse_device(inst.device)
            return header + _encode_device(tc, addr)

        # Coil instructions (OUT, SET, RST) — may have device + optional K
        if itype in _COIL_OPCODES:
            if inst.device is None:
                raise ValueError(f"{itype.value} requires a device operand")

            tc, addr = _parse_device(inst.device)

            # Timer/Counter OUT: special 04-prefix format
            if itype == InstructionType.OUT and tc in (DEVICE_CODES["T"], DEVICE_CODES["C"]):
                if inst.k_value is None:
                    raise ValueError(f"OUT {inst.device} requires K value")
                # 04 21 04 04  +  device_token(04-prefix)  +  k_token
                header = bytes([0x04, 0x21, 0x04, 0x04])
                dev_token = bytes([0x04, tc, addr & 0xFF, 0x04])
                if addr > 0xFF:
                    dev_token = bytes([0x04, tc, addr & 0xFF, (addr >> 8) & 0xFF, 0x04])
                k_token = _encode_k_value(inst.k_value)
                return header + dev_token + k_token

            # Regular bit OUT / SET / RST
            opcode = _COIL_OPCODES[itype]
            header = bytes([0x03, opcode])
            return header + _encode_device(tc, addr)

        # Standalone instructions (ORB, ANB, MPS, MRD, MPP) — 2-byte, no operand
        if itype in _STANDALONE_OPCODES:
            opcode = _STANDALONE_OPCODES[itype]
            return bytes([0x03, opcode])

        raise ValueError(f"Unsupported instruction type: {itype.value}")


# ── Raw OLE2/CFBF patcher ────────────────────────────────────────────────


class _RawOle2:
    """Minimal OLE2/CFBF raw byte patcher for in-place stream modification.

    Preserves the exact binary layout of the file — only modifies
    stream data bytes, mini-FAT entries, and directory entry sizes.
    No sectors are added or removed.
    """

    _END = 0xFFFFFFFE  # ENDOFCHAIN
    _FREE = 0xFFFFFFFF  # FREESECT

    def __init__(self, data: bytes | bytearray):
        self.buf = bytearray(data)
        self.ss = 1 << struct.unpack_from("<H", self.buf, 0x1E)[0]
        self.ms = 1 << struct.unpack_from("<H", self.buf, 0x20)[0]
        self._epr = self.ss // 4  # FAT/mini-FAT entries per sector
        self._load()

    def _off(self, sid: int) -> int:
        """Byte offset of sector SID in the file."""
        return (sid + 1) * self.ss

    def _load(self) -> None:
        # Load FAT from DIFAT (header 0x4C, max 109 entries)
        self.fat: list[int] = []
        for i in range(109):
            s = struct.unpack_from("<I", self.buf, 0x4C + i * 4)[0]
            if s >= self._END:
                break
            o = self._off(s)
            self.fat.extend(
                struct.unpack_from(f"<{self._epr}I", self.buf, o)
            )

        # Load directory entries
        self.dirs: list[dict | None] = []
        for s in self._chain(struct.unpack_from("<I", self.buf, 0x30)[0]):
            o = self._off(s)
            for k in range(self.ss // 128):
                eo = o + k * 128
                ns = struct.unpack_from("<H", self.buf, eo + 0x40)[0]
                t = self.buf[eo + 0x42]
                if ns == 0 or t == 0:
                    self.dirs.append(None)
                else:
                    nm = self.buf[eo : eo + ns - 2].decode("utf-16-le")
                    st = struct.unpack_from("<I", self.buf, eo + 0x74)[0]
                    sz = struct.unpack_from("<I", self.buf, eo + 0x78)[0]
                    self.dirs.append(
                        {"n": nm, "t": t, "s": st, "z": sz, "o": eo}
                    )

        # Load mini-FAT
        mfs = struct.unpack_from("<I", self.buf, 0x3C)[0]
        self._mfc: list[int] = (
            self._chain(mfs) if mfs < self._END else []
        )
        self.mfat: list[int] = []
        for s in self._mfc:
            o = self._off(s)
            self.mfat.extend(
                struct.unpack_from(f"<{self._epr}I", self.buf, o)
            )

    def _chain(self, start: int) -> list[int]:
        """Follow a FAT chain."""
        c: list[int] = []
        s = start
        while 0 <= s < len(self.fat) and s < self._END:
            c.append(s)
            s = self.fat[s]
            if len(c) > 50000:
                break
        return c

    def _mchain(self, start: int) -> list[int]:
        """Follow a mini-FAT chain."""
        c: list[int] = []
        s = start
        while 0 <= s < len(self.mfat) and s < self._END:
            c.append(s)
            s = self.mfat[s]
            if len(c) > 50000:
                break
        return c

    def find(self, name: str) -> dict:
        """Find a directory entry by stream name."""
        e = next((e for e in self.dirs if e and e["n"] == name), None)
        if e is None:
            raise KeyError(f"Stream {name!r} not found")
        return e

    def _flush_mfat(self) -> None:
        """Write the in-memory mini-FAT back to the file buffer."""
        for i, s in enumerate(self._mfc):
            o = self._off(s)
            for j in range(self._epr):
                ei = i * self._epr + j
                v = self.mfat[ei] if ei < len(self.mfat) else self._FREE
                struct.pack_into("<I", self.buf, o + j * 4, v)

    def write_mini(self, entry: dict, data: bytes) -> None:
        """Write data to a mini-stream, extending chain if needed."""
        ch = self._mchain(entry["s"])
        need = max(1, (len(data) + self.ms - 1) // self.ms)
        root = self.dirs[0]
        rch = self._chain(root["s"])
        cap = len(rch) * self.ss // self.ms

        # Extend mini-sector chain as needed
        while len(ch) < need:
            fr = next(
                (i for i in range(len(self.mfat)) if self.mfat[i] == self._FREE),
                None,
            )
            if fr is None:
                if len(self.mfat) < cap:
                    fr = len(self.mfat)
                    self.mfat.append(self._FREE)
                else:
                    raise ValueError("No free mini-sectors available")
            self.mfat[ch[-1]] = fr
            self.mfat[fr] = self._END
            ch.append(fr)

        # Write data across mini-sectors
        pad = data + b"\x00" * (len(ch) * self.ms - len(data))
        for i, mid in enumerate(ch):
            byte_off = mid * self.ms
            ri = byte_off // self.ss
            so = byte_off % self.ss
            fo = self._off(rch[ri]) + so
            self.buf[fo : fo + self.ms] = pad[i * self.ms : (i + 1) * self.ms]

        # Update directory entry size
        struct.pack_into("<I", self.buf, entry["o"] + 0x78, len(data))
        entry["z"] = len(data)

        # Update root entry size so mini-stream covers the new mini-sectors
        max_msid = max(ch)
        needed_root_size = (max_msid + 1) * self.ms
        root = self.dirs[0]
        if needed_root_size > root["z"]:
            struct.pack_into("<I", self.buf, root["o"] + 0x78, needed_root_size)
            root["z"] = needed_root_size

        self._flush_mfat()

    def write_regular(self, entry: dict, data: bytes) -> None:
        """Write data to a regular-stream sector chain (must fit)."""
        ch = self._chain(entry["s"])
        if len(data) > len(ch) * self.ss:
            raise ValueError("Data exceeds sector chain capacity")
        pos = 0
        for s in ch:
            o = self._off(s)
            chunk = data[pos : pos + self.ss]
            if len(chunk) < self.ss:
                chunk += b"\x00" * (self.ss - len(chunk))
            self.buf[o : o + self.ss] = chunk
            pos += self.ss

        struct.pack_into("<I", self.buf, entry["o"] + 0x78, len(data))
        entry["z"] = len(data)


# ── GXW Builder ──────────────────────────────────────────────────────────


class GXWBuilder:
    """Builds .gxw project files from IL instructions.

    Uses raw OLE2 byte patching to modify the template .gxw file,
    preserving the exact binary structure for GX Works2 compatibility.
    """

    def __init__(self, template_path: str | Path | None = None):
        self._template_path = Path(template_path) if template_path else TEMPLATE_PATH
        self._encoder = ILBinaryEncoder()

    def build(
        self,
        instructions: list[Instruction],
        project_name: str = "MAIN",
    ) -> bytes:
        """Build a .gxw file from IL instructions.

        Args:
            instructions: List of IL Instruction objects.
            project_name: Project name for projectlist.xml.

        Returns:
            Complete .gxw file as bytes.
        """
        program_bytes = self._encoder.encode(instructions)
        return self._build_from_program_bytes(program_bytes, project_name)

    def _build_from_program_bytes(
        self,
        program_bytes: bytes,
        project_name: str,
    ) -> bytes:
        """Inject program bytes into template and produce .gxw."""
        # Read template stream headers using olefile (read-only)
        outer_ole = olefile.OleFileIO(str(self._template_path))
        hdb_data = outer_ole.openstream("_hdb").read()
        xml_bytes = outer_ole.openstream("projectlist.xml").read()
        outer_ole.close()

        inner_ole = olefile.OleFileIO(io.BytesIO(hdb_data))
        s12_header = inner_ole.openstream("12").read()[:_STREAM12_HEADER_SIZE]
        s16_header = inner_ole.openstream("16").read()[:_STREAM16_HEADER_SIZE]
        inner_ole.close()

        # Build new stream content
        new_s12 = self._build_stream12(s12_header, program_bytes)
        new_s16 = self._build_stream16(s16_header, program_bytes)
        new_xml = self._patch_project_name(xml_bytes, project_name)

        # Raw-patch inner _hdb (preserves exact OLE2 structure)
        inner = _RawOle2(hdb_data)
        inner.write_mini(inner.find("12"), new_s12)
        inner.write_mini(inner.find("16"), new_s16)
        new_hdb = bytes(inner.buf)

        # Raw-patch outer .gxw (same-size _hdb, mini-stream XML)
        outer = _RawOle2(self._template_path.read_bytes())
        outer.write_regular(outer.find("_hdb"), new_hdb)
        outer.write_mini(outer.find("projectlist.xml"), new_xml)
        return bytes(outer.buf)

    @staticmethod
    def _build_stream12(header: bytes, program_bytes: bytes) -> bytes:
        """Build Stream 12 (MAIN.res): header + block_size + program + padding + trailer."""
        block_size = struct.pack("<I", len(program_bytes))
        return (
            header
            + block_size
            + program_bytes
            + _STREAM12_PADDING
            + _STREAM12_TRAILER
        )

    @staticmethod
    def _build_stream16(header: bytes, program_bytes: bytes) -> bytes:
        """Build Stream 16 (MAIN.Program.pou): header + program + padding.

        Updates the two size fields at offsets 0x37 and 0x3B.
        """
        data_size = len(program_bytes) + 20
        new_header = bytearray(header)
        struct.pack_into("<I", new_header, _STREAM16_SIZE_OFFSET_A, data_size)
        struct.pack_into("<I", new_header, _STREAM16_SIZE_OFFSET_B, data_size)
        padding = b"\x00" * _STREAM16_PADDING_SIZE
        return bytes(new_header) + program_bytes + padding

    @staticmethod
    def _patch_project_name(xml_bytes: bytes, name: str) -> bytes:
        """Replace the project name in projectlist.xml."""
        text = xml_bytes.decode("utf-8", errors="replace")
        text = re.sub(
            r"<szName>.*?</szName>",
            f"<szName>{name}</szName>",
            text,
        )
        return text.encode("utf-8")
