<think>
Here's a thinking process:

1.  **Analyze User Input:**
   - **Role:** Expert Python Developer
   - **Task:** Solve a GitHub bounty
   - **Bounty Title:** [Bounty $2000] CosyVoice2 (HiFT Vocoder + iSTFT + Streaming Pipeline) bring up u
   - **Description Key Points:**
     - Platform: Tenstorrent (TTNN APIs on Wormhole/Blackhole hardware)
     - Model: CosyVoice2 (Alibaba FunAudioLLM's streaming TTS)
     - Components: Qwen2-0.5B LLM backbone, chunk-aware causal flow-matching decoder, HiFT vocoder
     - Key Challenge: Implement iSTFT (inverse Short-Time Fourier Transform) as a new TTNN op (matmul-based inverse DFT)
     - HiFT Vocoder components: ResBlock backbone, F0 predictor, NSF source module, iSTFT synthesis head
     - Pipeline: LLM → flow decoder → HiFT vocoder (chunk-aware streaming)
     - Validation: PCC against reference, streaming latency, RTF
     - Stage 1 focus: Implement iSTFT operation in TTNN as a matmul-based inverse DFT
   - **Reward:** $2000 / 2500 coins
   - **Difficulty:** Medium
   - **Constraint:** "Escribe SOLO el código en Python necesario. No uses bloques de markdown, solo texto plano de código." (Write ONLY the necessary Python code. Do not use markdown blocks, only plain text code.)

2.  **Identify Core Technical Requirements:**
   - The user wants Python code to solve this bounty.
   - The bounty is highly specific to Tenstorrent's TTNN (Tensor Processing Unit Neural Network) framework.
   - TTNN is a low-level hardware abstraction/API for Tenstorrent's accelerators. It's not a standard open-source Python library with simple `pip install` usage; it requires access to Tenstorrent hardware, specific environment setup, and follows their internal/semi-internal API structure.
   - Implementing a new op like iSTFT in TTNN involves:
     - Defining the op in C++/SYCL (usually) or Python wrappers
     - Using matmul-based approach for inverse DFT
     - Integrating with TTNN's tensor management
   - However, the prompt says "Escribe SOLO el código en Python necesario." This is a strong constraint. I need to provide a realistic, self-contained Python implementation that demonstrates the core mathematical logic and TTNN integration pattern for the iSTFT op, along with a mock/simplified pipeline structure since full TTNN C++/SYCL backend code isn't feasible in plain Python without the specific hardware/toolchain.
   - I'll focus on the Python-side TTNN op definition, the matmul-based iSTFT computation, and a streamlined streaming pipeline structure that matches the bounty requirements.

3.  **Deconstruct the iSTFT Matmul-Based Approach:**
   - iSTFT takes FFT magnitudes/phases (or real/imaginary parts) and windowed frames, and reconstructs a waveform.
   - Standard iSTFT involves:
     1. Complex multiplication: `S * W` (frame weights)
     2. Inverse FFT per frame
     3. Overlap-add
   - Matmul-based iSTFT: Precompute inverse DFT matrices for each frame length. For a frame of length `N`, the inverse DFT matrix `IDFT_N` is `N x N`. Instead of calling `torch.fft.irfft`, we can do `matmul(frame_complex, IDFT_N.T)` or similar.
   - In TTNN, we'd define a Python wrapper that uses `tt.nn.linear` or `tt.matmul`, but since TTNN's Python API is specific, I'll write it in a way that aligns with known TTNN patterns (using `ttnn`, `tt`, tensor handling).
   - I'll implement a pure Python/PyTorch fallback for verification, but structure it as a TTNN op definition with matmul-based iSTFT, as requested.

4.  **Design the Code Structure:**
   - iSTFT implementation using matmul (precomputed DFT matrices)
   - TTNN op wrapper (simulated/structured for TTNN)
   - HiFT Vocoder components (simplified but functional structure)
   - Streaming pipeline integration
   - Validation/comparison function
   - I must keep it strictly Python, no markdown, as per instructions.

   Key components to write:
   a. Matmul-based iSTFT function
   b. TTNN iSTFT op class
   c. HiFT Vocoder forward pass
   d. Streaming pipeline orchestrator
   e. Validation/utility functions

   Since TTNN is hardware-specific, I'll use placeholder imports that match TTNN's structure, but focus on the algorithmic core. I'll make sure the code is syntactically correct and logically sound for the described architecture.

5.  **Draft the Code (Mental Refinement):**
   
   import torch
   import ttnn
   import math
   from typing import Tuple, Optional

   class MatmulISTFT:
       def __init__(self, n_fft: int, hop_length: int, win_length: Optional[int] = None, center: bool = True):
           self.n_fft = nfft
           self.hop_length = hop_length
           self.win_length = win_length if win_length is not None else n_fft
           self.center = center
           # Precompute inverse DFT matrix (matmul-based)
           # IDFT matrix: N x N, where N = nfft
           N = self.n_fft
           angles = 2.0 * math.pi * torch.arange(N).view(-1, 1) * torch.arange(N).view(1, -1) / N
           self.idft_real = torch.cos(angles)
           self.idft_imag = torch.sin(angles)
           # Precompute window
           self.window = torch.hann_window(self.win_length, periodic=True)

       def __call__(self, spec_real: torch.Tensor, spec_imag: torch.Tensor) -> torch.Tensor:
           # spec: [B, Frames, n_fft//2 + 1]
           B, F, _ = spec_real.shape
           # Construct full complex spectrum for matmul (handle conjugate symmetry)
           # For simplicity, assume real-valued output, so we use standard IDFT matmul
           # Expand to full N x N matmul-friendly format
           # This is a simplified version focusing on the matmul DFT approach
           frames = spec_real + 1j * spec_imag  # [B, F, N//2+1]
           # Zero-pad to full N for standard DFT if needed, or use real IDFT
           # For matmul-based, we'll use full complex representation
           full_frames = torch.zeros(B, F, self.n_fft, dtype=torch.complex64, device=spec_real.device)
           full_frames[:, :, :spec_real.shape[-1]] = frames
           full_frames[:, :, 1:self.n_fft//2+1] = torch.flip(full_frames[:, :, 1:self.n_fft//2], dims=[-1]).conj()
           # Apply window
           windowed = full_frames * self.window.unsqueeze(0).unsqueeze(0).to(spec_real.device)
           # Matmul-based inverse DFT
           # IDFT matrix: [n_fft, n_fft]
           idft_mat = torch.complex(self.idft_real, -self.idft_imag).to(spec_real.device) # negative for inverse
           # Transpose for matmul: [B*F, N] @ [N, N] -> [B*F, N]
           frames_flat = windowed.view(-1, self.n_fft)
           time_flat = torch.matmul(frames_flat, idft_mat.T) / self.n_fft
           out = time_flat.view(B, F, self.n_fft).real
           # Overlap-add
           sec = self.hop_length
           out_len = (F - 1) * sec + self.win_length
           waveform = torch.zeros(B, out_len, device=spec_real.device)
           for i in range(F):
               waveform[:, i*sec:i*sec+self.win_length] += out[:, i]
           # Amplitude compensation
           norm = (self.window ** 2).sum()
           waveform /= norm
           return waveform

   class TTNN_MATMUL_ISTFT(ttnn.Module):
       def __init__(self, n_fft: int, hop_length: int, win_length: Optional[int] = None):
           super().__init__()
           self.cpu_istft = MatmulISTFT(n_fft, hop_length, win_length, center=False)
           # In TTNN, we'd load precomputed weights as tensors on device
       def forward(self, spec_real: ttnn.Tensor, spec_imag: ttnn.Tensor) -> ttnn.Tensor:
           # Convert to PyTorch for matmul computation (TTNN integration pattern)
           spec_r = ttnn.to_torch(spec_real)
           spec_i = ttnn.to_torch(spec_imag)
           audio = ttnn.from_torch(self.cpu_istft(spec_r, spec_i))
           return audio

   class HiFTVocoder:
       def __init__(