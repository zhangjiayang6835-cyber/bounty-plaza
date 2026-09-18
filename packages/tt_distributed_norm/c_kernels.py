"""C++ kernel patch generators and validation utilities for upstream tt-metal."""

from typing import Dict, List


def _build_preallgather_reader_lines() -> List[str]:
    """Assemble source code lines for patched 2D pre-allgather reader kernel."""
    lines: List[str] = []
    lines.append("// SPDX-FileCopyrightText: © 2025 Tenstorrent USA, Inc.")
    lines.append("// SPDX-License-Identifier: Apache-2.0")
    lines.append("#include <stdint.h>")
    lines.append('#include "api/dataflow/dataflow_api.h"')
    lines.append('#include "api/dataflow/noc.h"')
    lines.append('#include "api/dataflow/dataflow_buffer.h"')
    lines.append('#include "experimental/kernel_args.h"')
    lines.append("")
    lines.append("void kernel_main() {")
    lines.append("    const auto NCHt = get_arg(args::NCHt);")
    lines.append("    const auto tile_offset = get_arg(args::tile_offset);")
    lines.append("    const auto is_merge_core = get_arg(args::is_merge_core);")
    lines.append("    const auto reduce_core_noc_x = get_arg(args::reduce_core_noc_x);")
    lines.append("    const auto reduce_core_noc_y = get_arg(args::reduce_core_noc_y);")
    lines.append("    const auto y = get_arg(args::y);")
    lines.append("    constexpr auto blk = get_arg(args::blk);")
    lines.append("    constexpr auto Wt = get_arg(args::Wt);")
    lines.append("    const auto row_stride = get_arg(args::row_stride);")
    lines.append("")
    lines.append("    const auto src_a = TensorAccessor(tensor::src);")
    lines.append("    Noc noc;")
    lines.append("    DataflowBuffer dfb_inp_buf(dfb::inp);")
    lines.append("    const uint32_t src0_tile_bytes = dfb_inp_buf.get_tile_size();")
    lines.append("    uint32_t inp_tile_idx = tile_offset;")
    lines.append("")
    lines.append("    for (uint32_t ncht = 0; ncht < NCHt; ncht++) {")
    lines.append("        for (uint32_t wt = 0; wt < Wt; wt += blk) {")
    lines.append("            dfb_inp_buf.reserve_back(blk);")
    lines.append("            for (uint32_t r = 0; r < blk; r++) {")
    lines.append("                noc.async_read(src_a, dfb_inp_buf, src0_tile_bytes,")
    lines.append("                               {.page_id = inp_tile_idx},")
    lines.append("                               {.offset_bytes = r * src0_tile_bytes});")
    lines.append("                inp_tile_idx++;")
    lines.append("            }")
    lines.append("            noc.async_read_barrier();")
    lines.append("            dfb_inp_buf.push_back(blk);")
    lines.append("        }")
    lines.append("        inp_tile_idx += row_stride;")
    lines.append("    }")
    lines.append("}")
    return lines


def _build_postallgather_reader_lines() -> List[str]:
    """Assemble source code lines for patched shared post-allgather reader kernel."""
    lines: List[str] = []
    lines.append("// SPDX-FileCopyrightText: © 2024 Tenstorrent USA, Inc.")
    lines.append("// SPDX-License-Identifier: Apache-2.0")
    lines.append("#include <stdint.h>")
    lines.append('#include "api/dataflow/dataflow_api.h"')
    lines.append('#include "api/dataflow/noc.h"')
    lines.append('#include "api/dataflow/dataflow_buffer.h"')
    lines.append('#include "experimental/kernel_args.h"')
    lines.append("")
    lines.append("void kernel_main() {")
    lines.append("    const auto NCHt = get_arg(args::NCHt);")
    lines.append("    const auto tile_offset = get_arg(args::tile_offset);")
    lines.append("    const auto stats_tile_offset = get_arg(args::stats_tile_offset);")
    lines.append("    const auto y_offset = get_arg(args::y_offset);")
    lines.append("    const auto row_stride = get_arg(args::row_stride);")
    lines.append("    constexpr auto Wt = get_arg(args::Wt);")
    lines.append("    constexpr auto dfb_length = get_arg(args::dfb_length);")
    lines.append("")
    lines.append("    const auto src_a = TensorAccessor(tensor::src);")
    lines.append("    const auto src_stats = TensorAccessor(tensor::stats_src);")
    lines.append("    Noc noc;")
    lines.append("    DataflowBuffer dfb_inp_buf(dfb::inp);")
    lines.append("    DataflowBuffer dfb_stats_buf(dfb::stats);")
    lines.append("    const uint32_t src0_tile_bytes = dfb_inp_buf.get_tile_size();")
    lines.append("    uint32_t inp_tile_idx = tile_offset;")
    lines.append("    uint32_t stats_tile_idx = stats_tile_offset;")
    lines.append("")
    lines.append("    for (uint32_t ncht = 0; ncht < NCHt; ncht++) {")
    lines.append("        dfb_inp_buf.reserve_back(Wt);")
    lines.append("        for (uint32_t wt = 0; wt < Wt; wt++) {")
    lines.append("            noc.async_read(src_a, dfb_inp_buf, src0_tile_bytes,")
    lines.append("                           {.page_id = inp_tile_idx}, {.offset_bytes = 0});")
    lines.append("            inp_tile_idx++;")
    lines.append("        }")
    lines.append("        noc.async_read_barrier();")
    lines.append("        dfb_inp_buf.push_back(Wt);")
    lines.append("        inp_tile_idx += row_stride;")
    lines.append("    }")
    lines.append("}")
    return lines


class CppPatchGenerator:
    """Generates and validates C++ patches for tt-metal normalization kernels."""

    @staticmethod
    def get_preallgather_reader_source() -> str:
        """Return full patched C++ source for reader_layernorm_preallgather_2d.cpp."""
        lines = _build_preallgather_reader_lines()
        return "\n".join(lines)

    @staticmethod
    def get_postallgather_reader_source() -> str:
        """Return full patched C++ source for reader_unary_interleaved_ln_rm_gb_post_allgather.cpp."""
        lines = _build_postallgather_reader_lines()
        return "\n".join(lines)

    @staticmethod
    def verify_patch_invariants(source_code: str) -> Dict[str, bool]:
        """Verify presence of required synchronization, parameters, and striding."""
        has_stride = "inp_tile_idx += row_stride" in source_code
        has_barrier = "noc.async_read_barrier()" in source_code
        has_ncht_loop = "for (uint32_t ncht = 0; ncht < NCHt; ncht++)" in source_code
        has_arg_row_stride = "args::row_stride" in source_code

        all_passed = has_stride and has_barrier and has_ncht_loop and has_arg_row_stride
        return {
            "has_stride_jump": has_stride,
            "has_async_barrier": has_barrier,
            "has_ncht_loop": has_ncht_loop,
            "has_arg_row_stride": has_arg_row_stride,
            "is_valid": all_passed,
        }
