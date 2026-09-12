"""Bit-accurate emulator for Tenstorrent SFPU hardware instructions and registers."""

from typing import List
from packages.ttnn_quantize_saturation.types import Architecture, RequantConfig

WH_QUANT_REPLAY_LEN_UINT8_OUT = 6
WH_REQUANT_REPLAY_LEN_UINT8_OUT = 7

BH_QUANT_REPLAY_LEN_UINT8_OUT = 5
BH_REQUANT_REPLAY_LEN_UINT8_2S_COMP = 8
BH_REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN = 6


class SFPURegisterState:
    """State of SFPU vector registers for a single SIMD lane."""

    def __init__(self) -> None:
        """Initializes register bank, condition codes, and instruction logs."""
        self.regs: List[float] = [0.0] * 5
        self.lconst_0: float = 0.0
        self.condition_code: bool = False
        self.recorded_instructions: List[str] = []

    @property
    def lreg0(self) -> float:
        """Returns value in primary accumulator register LREG0."""
        return self.regs[0]

    @lreg0.setter
    def lreg0(self, val: float) -> None:
        """Sets value in primary accumulator register LREG0."""
        self.regs[0] = val

    @property
    def lreg1(self) -> float:
        """Returns value in multiplier operand register LREG1."""
        return self.regs[1]

    @lreg1.setter
    def lreg1(self, val: float) -> None:
        """Sets value in multiplier operand register LREG1."""
        self.regs[1] = val

    @property
    def lreg2(self) -> float:
        """Returns value in addend operand register LREG2."""
        return self.regs[2]

    @lreg2.setter
    def lreg2(self, val: float) -> None:
        """Sets value in addend operand register LREG2."""
        self.regs[2] = val

    def tti_sfpmad(self) -> None:
        """Executes fused multiply-add: lreg0 = lreg0 * lreg1 + lreg2."""
        self.lreg0 = self.lreg0 * self.lreg1 + self.lreg2
        self.recorded_instructions.append("TTI_SFPMAD")

    def tti_sfpcast_int32_to_fp32(self) -> None:
        """Converts integer register to floating point representation."""
        self.lreg0 = float(int(self.lreg0))
        self.recorded_instructions.append("TTI_SFPCAST")

    def tti_sfpsetcc_lt0(self) -> None:
        """Evaluates whether lreg0 is strictly less than 0.0."""
        self.condition_code = self.lreg0 < 0.0
        self.recorded_instructions.append("TTI_SFPSETCC")

    def tti_sfpmov(self) -> None:
        """Moves lconst_0 into lreg0 if condition code is asserted."""
        if self.condition_code:
            self.lreg0 = self.lconst_0
        self.recorded_instructions.append("TTI_SFPMOV")

    def tti_sfpencc(self) -> None:
        """Clears condition code assertion state."""
        self.condition_code = False
        self.recorded_instructions.append("TTI_SFPENCC")

    def tti_sfpnop(self) -> None:
        """Pipeline bubble instruction."""
        self.recorded_instructions.append("TTI_SFPNOP")

    def uint8_clamp_negatives(self) -> None:
        """Hardware instruction sequence clamping negative values to zero."""
        self.tti_sfpsetcc_lt0()
        self.tti_sfpmov()
        self.tti_sfpencc()

    def raw_fp32_to_uint8_without_clamp(self) -> int:
        """Hardware conversion behavior without clamp reproducing magnitude bug."""
        mag = abs(self.lreg0)
        rounded = int(mag + 0.5)
        return min(255, rounded)

    def uint8_round(self) -> int:
        """Executes negative clamping followed by saturating uint8 conversion."""
        self.uint8_clamp_negatives()
        rounded = int(self.lreg0 + 0.5)
        self.recorded_instructions.append("TTI_SFP_STOCH_RND_UINT8")
        return max(0, min(255, rounded))

    def int8_pack_fixup(self) -> int:
        """Executes uint8 round followed by bitwise inversion into signed int8."""
        u8_val = self.uint8_round()
        self.recorded_instructions.append("TTI_SFPXOR_0x80")
        return u8_val ^ 0x80


class SFPUSimulator:
    """SFPU execution simulator across target hardware architectures."""

    def __init__(self, arch: Architecture = Architecture.WORMHOLE_B0) -> None:
        """Initializes simulator for specified architecture."""
        self.arch = arch

    def get_quant_replay_length(self) -> int:
        """Returns the replay buffer instruction length for uint8 quantization."""
        if self.arch == Architecture.WORMHOLE_B0:
            return WH_QUANT_REPLAY_LEN_UINT8_OUT
        return BH_QUANT_REPLAY_LEN_UINT8_OUT

    def get_requant_replay_length(self, int8_input: bool = False) -> int:
        """Returns the replay buffer instruction length for uint8 requantization."""
        if self.arch == Architecture.WORMHOLE_B0:
            return WH_REQUANT_REPLAY_LEN_UINT8_OUT
        if int8_input:
            return BH_REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN
        return BH_REQUANT_REPLAY_LEN_UINT8_2S_COMP

    def execute_quant_element(
        self,
        input_fp: float,
        scale: float,
        zero_point: int
    ) -> int:
        """Executes simulated SFPU hardware pipeline for quantize operation."""
        state = SFPURegisterState()
        state.lreg0 = input_fp
        state.lreg1 = 1.0 / scale
        state.lreg2 = float(zero_point)

        state.tti_sfpmad()
        if self.arch == Architecture.WORMHOLE_B0:
            state.tti_sfpnop()

        result = state.uint8_round()
        expected_len = self.get_quant_replay_length()
        if len(state.recorded_instructions) != expected_len:
            msg = f"Instruction count {len(state.recorded_instructions)} != {expected_len}"
            raise RuntimeError(msg)

        return result

    def execute_requant_element(
        self,
        input_int: int,
        config: RequantConfig,
        int8_input: bool = False
    ) -> int:
        """Executes simulated SFPU hardware pipeline for requantize operation."""
        state = SFPURegisterState()
        state.lreg0 = float(input_int)

        effective_mult = config.in_scale / config.out_scale
        effective_bias = float(config.out_zero_point) - float(config.in_zero_point) * effective_mult

        state.lreg1 = effective_mult
        state.lreg2 = effective_bias

        state.tti_sfpcast_int32_to_fp32()
        state.tti_sfpmad()
        if self.arch == Architecture.WORMHOLE_B0:
            state.tti_sfpnop()

        result = state.uint8_round()
        expected_len = self.get_requant_replay_length(int8_input=int8_input)
        if len(state.recorded_instructions) != expected_len:
            msg = f"Instruction count {len(state.recorded_instructions)} != {expected_len}"
            raise RuntimeError(msg)

        return result
