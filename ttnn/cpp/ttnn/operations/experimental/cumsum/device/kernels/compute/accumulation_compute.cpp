// SPDX-FileCopyrightText: © 2024-2026 Tenstorrent AI ULC
//
// SPDX-License-Identifier: Apache-2.0

#include <cstdint>
#include "api/compute/compute_kernel_api.h"
#include "api/compute/add_int_sfpu.h"
#include "api/compute/mul_int_sfpu.h"
#include "api/compute/eltwise_binary.h"
#include "api/compute/eltwise_unary/eltwise_unary.h"
#include "api/compute/eltwise_unary/isinf_isnan.h"
#include "api/compute/eltwise_unary/where.h"
#include "api/compute/eltwise_unary/fill.h"
#include "api/compute/pack.h"
#include "api/compute/reconfig_data_format.h"

namespace NAMESPACE {
void kernel_main() {
    constexpr uint32_t num_tiles = get_compile_time_arg_val(0);
    constexpr uint32_t num_accumulations = get_compile_time_arg_val(1);

    constexpr auto dfb_in_obj = get_compile_time_arg_val(2);
    constexpr auto dfb_out_obj = get_compile_time_arg_val(3);
    constexpr auto dfb_acc_obj = get_compile_time_arg_val(4);
#ifdef COMPENSATED_SUM
    constexpr auto dfb_comp_obj = get_compile_time_arg_val(5);
#endif

    constexpr uint32_t ONE_TILE = 1;

    constexpr uint32_t DST_IN = 0;
    constexpr uint32_t DST_ACC = 1;
#ifdef COMPENSATED_SUM
    constexpr uint32_t DST_COMP = 2;
    constexpr uint32_t DST_T = 3;
#endif

    compute_kernel_hw_tile_init();
    binary_op_init_common(dfb::in, dfb::acc, dfb::out);
    BINARY_OP_INIT();

    for (uint32_t i = 0; i < num_tiles; ++i) {
        for (uint32_t j = 0; j < num_accumulations; ++j) {
            // Synchronize unpacker-packer between iterations
            dfb_acc_obj.wait_front(ONE_TILE);
#ifdef COMPENSATED_SUM
            dfb_comp_obj.wait_front(ONE_TILE);
#endif

            tile_regs_acquire();
            dfb_in_obj.wait_front(ONE_TILE);

            reconfig_data_format(dfb::in, dfb::in);
            copy_init(dfb::in);
            copy_tile(dfb::in, 0, DST_IN);

            reconfig_data_format(dfb::acc, dfb::acc);
            copy_init(dfb::acc);
            copy_tile(dfb::acc, 0, DST_ACC);

#ifdef COMPENSATED_SUM
            reconfig_data_format(dfb::comp, dfb::comp);
            copy_init(dfb::comp);
            copy_tile(dfb::comp, 0, DST_COMP);

            // Compensated (Kahan) summation on the running total:
            // y = in - c
            // t = acc + y
            // c = (t - acc) - y
            sub_binary_tile(DST_IN, DST_COMP, DST_IN);    // y = in - c
            add_binary_tile(DST_ACC, DST_IN, DST_T);      // t = acc + y
            sub_binary_tile(DST_T, DST_ACC, DST_COMP);    // (t - acc)
            sub_binary_tile(DST_COMP, DST_IN, DST_COMP);  // c = (t - acc) - y

            // Non-finite guard (Fix for issue #58986 / bounty-plaza #1728):
            // Once t is +-inf or NaN, c no longer represents low-order truncation.
            // When t is non-finite, compensation is reset to +0 in those lanes;
            // finite lanes keep the exact Kahan compensation term.
            // t itself is untouched, preserving IEEE/PyTorch behavior:
            //   - (+inf, +1) -> +inf
            //   - (-inf, -1) -> -inf
            //   - (+inf, -inf) -> NaN
            //   - NaN input -> NaN
            sub_binary_tile(DST_T, DST_T, DST_ACC);
            isfinite_tile_init();
            isfinite_tile(DST_ACC);
            where_tile_init();
            where_tile<DataFormat::Float32>(DST_ACC, DST_COMP, DST_ACC, DST_ACC);
            BINARY_OP_INIT();  // restore SFPU state for the next tile
            constexpr uint32_t DST_COMP_OUT = DST_ACC;
            constexpr uint32_t DST_RESULT = DST_T;
            dfb_comp_obj.pop_front(ONE_TILE);
#else
            BINARY_OP(DST_IN, DST_ACC, DST_ACC);
            constexpr uint32_t DST_RESULT = DST_ACC;
#endif
            dfb_acc_obj.pop_front(ONE_TILE);
            dfb_in_obj.pop_front(ONE_TILE);

            tile_regs_commit();
            tile_regs_wait();

            dfb_out_obj.reserve_back(ONE_TILE);
            pack_reconfig_data_format(dfb::acc, dfb::out);
            pack_tile(DST_RESULT, dfb::out);
            dfb_out_obj.push_back(ONE_TILE);

            dfb_acc_obj.reserve_back(ONE_TILE);
            pack_reconfig_data_format(dfb::out, dfb::acc);
            pack_tile(DST_RESULT, dfb::acc);
#ifdef COMPENSATED_SUM
            dfb_comp_obj.reserve_back(ONE_TILE);
            pack_reconfig_data_format(dfb::acc, dfb::comp);
            pack_tile(DST_COMP_OUT, dfb::comp);
#endif

            tile_regs_release();
            dfb_acc_obj.push_back(ONE_TILE);
#ifdef COMPENSATED_SUM
            dfb_comp_obj.push_back(ONE_TILE);
#endif
        }
    }

    dfb_acc_obj.wait_front(ONE_TILE);
    dfb_acc_obj.pop_front(ONE_TILE);
#ifdef COMPENSATED_SUM
    dfb_comp_obj.wait_front(ONE_TILE);
    dfb_comp_obj.pop_front(ONE_TILE);
#endif
}
} // namespace NAMESPACE
