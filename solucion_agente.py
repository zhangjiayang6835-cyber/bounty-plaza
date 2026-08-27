<think>
The user is asking me to solve a GitHub bounty for implementing CosyVoice2 (HiFT Vocoder + iSTFT + Streaming Pipeline) using TTNN APIs on Tenstorrent hardware.

Let me analyze what needs to be done:
1. Implement the iSTFT operation in TTNN as a matmul-based inverse DFT
2. Complete the HiFT vocoder bring-up (ResBlock backbone, F0 predictor, NSF source module, iSTFT synthesis head)
3. Bring up LLM and flow-matching decoder components
4. Integrate into a streaming pipeline
5. Provide correctness validation

The Stage 1 specifically mentions implementing iSTFT as a matmul-based inverse DFT (real/imaginary component matmuls against precomputed weight matrices).

Since this is a very complex task involving hardware-specific TTNN APIs for Tenstorrent hardware, I need to provide Python code that:
1. Implements iSTFT using matrix multiplication approach
2. Implements the HiFT vocoder components
3. Provides the streaming pipeline integration

Let me write the code for this. The key insight for iSTFT is that it can be computed as FFT of imaginary input, which can be expressed as matrix multiplication against DFT matrices.

The iSTFT takes overlap-add of windowed FFT frames. The approach is:
1. For each frame, apply window, zero-pad if needed, compute inverse FFT
2. Overlap-add the results

For the matmul-based approach:
- Precompute DFT/IDFT weight matrices
- Express the inverse FFT as matrix multiplication of real and imaginary parts
- The iSTFT with overlap-add can be expressed as a single large matrix multiplication

Let me write comprehensive Python code for this implementation.
</think>


import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np
from typing import Tuple, List, Optional
import warnings

# ==============================================================================
# Stage 1: iSTFT Operation — Matmul-based Inverse DFT
# ==============================================================================

class MatmulISTFT(torch.autograd.Function):
    """
    Inverse Short-Time Fourier Transform implemented via precomputed DFT matrices
    and matrix multiplication. Suitable for TTNN deployment where dedicated FFT
    ops may not exist natively.
    
    Forward:
      - Applies window to each STFT frame
      - Computes IDFT via real/imaginary matmuls against precomputed weight matrices
      - Performs overlap-add synthesis
    
    The IDFT matrix is: W[n,k] = (1/N) * exp(j * 2*pi*n*k/N)
    For real output: idft(x)[n] = Re(W @ x) where x is complex frequency bins
    """
    
    @staticmethod
    def forward(
        ctx,
        spec: torch.Tensor,        # [B, F, T] or [B, 2, F, T] for complex
        hop_length: int,
        win_length: int,
        n_fft: int,
        window: Optional[torch.Tensor] = None,
        center: bool = True,
        normalized: bool = False,
        onesided: bool = True,
        return_complex: bool = False,
    ) -> torch.Tensor:
        B = spec.shape[0]
        
        # Handle complex input as [B, 2, F, T] (real, imag)
        if spec.dim() == 4:
            spec_real = spec[:, 0, :, :]   # [B, F, T]
            spec_imag = spec[:, 1, :, :]   # [B, F, T]
        else:
            spec_real = spec.real
            spec_imag = spec.imag
        
        F_size = spec.shape[-2]  # freq bins
        T_frames = spec.shape[-1]  # time frames
        
        if onesided:
            n_fft = self._infer_n_fft(F_size, n_fft)
        else:
            if F_size != n_fft:
                warnings.warn(f"F={F_size} != n_fft={n_fft}, overriding n_fft")
            F_size = n_fft
        
        if window is None:
            window = torch.hann_window(win_length)
        
        device = spec.device
        dtype = spec.dtype
        
        # Precompute IDFT matrix: W[n,k] = (1/F) * exp(j*2*pi*n*k/F)
        # For real-valued output of length F (or n_fft)
        n_fft_eff = n_fft
        
        t_indices = torch.arange(n_fft_eff, device=device, dtype=dtype)
        k_indices = torch.arange(F_size, device=device, dtype=dtype)
        
        angle = 2.0 * math.pi * torch.outer(t_indices, k_indices) / F_size
        
        # IDFT matrix components (normalized)
        dft_real = torch.cos(angle) / F_size if normalized else torch.cos(angle)
        dft_imag = torch.sin(angle) / F_size if normalized else torch.sin(angle)
        
        # Transpose for matmul: we want W @ x, so use W.t() @ x => matmul(W.t(), x)
        dft_real = dft_real.t()  # [F, n_fft]
        dft_imag = dft_imag.t()  # [F, n_fft]
        
        # Compute IDFT per frame via matmul
        # idft[n] = sum_k (Re(x_k) * cos + Im(x_k) * sin)
        # => idft = dft_real @ spec_real + dft_imag @ spec_imag
        # spec: [B, F, T], dft: [F, n_fft] => result: [B, n_fft, T]
        time_frames = dft_real @ spec_real + dft_imag @ spec_imag  # [B, n_fft, T]
        
        # Apply window
        window_expanded = window.unsqueeze(0).unsqueeze(2).to(device).to(dtype)  # [1, win_length, 1]
        time_frames_windowed = time_frames[:, :win_length, :] * window_expanded
        
        # Overlap-add
        if T_frames == 0:
            return torch.zeros(B, 0, device=device, dtype=dtype)
        
        output_length = self._calc_output_length(T_frames, win_length, hop_length, n_fft_eff, center)
        output = torch.zeros(B, output_length, device=device, dtype=dtype)
        window_sq_sum = torch.zeros(output_length, device=device, dtype=dtype)
        
        for t in range(T_frames):
            offset = t * hop_length
            if center:
                pad = win_length // 2
                offset += pad - hop_length // 2
            end_idx = min(offset + win_length, output_length)
            actual_len = end_idx - offset
            if actual_len <= 0:
                continue
            output[:, offset:end_idx] += time_frames_windowed[:, :actual_len, t]
            window_sq_sum[offset:end_idx] += window[:actual_len] ** 2
        
        # Normalize by window squared sum (avoid division by zero)
        window_sq_sum[window_sq_sum < 1e-8] = 1.0
        output = output / window_sq_sum.unsqueeze(0)
        
        ctx.save_for_backward(
            dft_real, dft_imag, window, spec_real, spec_imag
        )
        ctx.hop_length = hop_length
        ctx.win_length = win_length
        ctx.n_fft = n_fft_eff
        ctx.center = center
        ctx.normalized = normalized
        ctx.onesided = onesided
        ctx.output_length = output_length
        ctx.T_frames = T_frames
        
        return output
    
    @staticmethod
    def _infer_n_fft(F_size: int, n_fft: int) -> int:
        if n_fft >= F_size:
            return n_fft
        return (F_size - 1) * 2
    
    @staticmethod
    def _calc_output_length(
        n_fft_frames: int, win_length: int, hop_length: int,
        n_fft: int = None, center: bool = True
    ) -> int:
        """Match torch.stft output length convention."""
        if n_fft is None:
            return n_fft_frames * hop_length + win_length - hop_length
        if center:
            return n_fft_frames * hop_length + win_length
        return n_fft_frames * hop_length
    
    @staticmethod
    def backward(ctx, grad_output):
        dft_real, dft_imag, window, _, _ = ctx.saved_tensors
        hop_length = ctx.hop_length
        win_length = ctx.win_length
        n_fft = ctx.n_fft
        center = ctx.center
        normalized = ctx.normalized
        T_frames = ctx.T_frames
        onesided = ctx.onesided
        
        B = grad_output.shape[0]
        device = grad_output.device
        dtype = grad_output.dtype
        
        output_length = ctx.output_length
        
        # Forward the gradient through overlap-add (which is a strided add)
        # The gradient w.r.t. time_frames is obtained by windowing and stride
        time_frames_grad = torch.zeros(B, win_length, T_frames, device=device, dtype=dtype)
        window_expanded = window.unsqueeze(0).unsqueeze(2).to(device).to(dtype)
        
        for t in range(T_frames):
            offset = t *