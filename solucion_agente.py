import math
import torch
import ttnn
from typing import Tuple, Optional

def _create_idft_matrix(n_fft: int, device: ttnn.Device) -> Tuple[ttnn.Tensor, ttnn.Tensor]:
    """
    Create pre‑computed real and imaginary IDFT matrices for a given FFT size.
    The matrices have shape (n_fft, n_fft//2 + 1) and are transposed so that a
    matmul with a spectrogram of shape (batch, n_fft//2 + 1, frames) yields the
    time‑domain frames of shape (batch, n_fft, frames).
    """
    k = torch.arange(n_fft).unsqueeze(1)          # (n_fft, 1)
    n = torch.arange(n_fft // 2 + 1).unsqueeze(0)  # (1, n_fft//2 + 1)
    # IDFT basis: exp(j*2π*k*n / n_fft)
    angle = 2 * math.pi * k * n / n_fft
    idft_real = torch.cos(angle).float()          # (n_fft, n_fft//2+1)
    idft_imag = torch.sin(angle).float()          # (n_fft, n_fft//2+1)

    # Move to TTNN as tiled tensors (row‑major layout works for matmul)
    idft_real_tt = ttnn.from_torch(
        idft_real,
        dtype=ttnn.bfloat16,
        device=device,
        layout=ttnn.ROW_MAJOR_LAYOUT,
    )
    idft_imag_tt = ttnn.from_torch(
        idft_imag,
        dtype=ttnn.bfloat16,
        device=device,
        layout=ttnn.ROW_MAJOR_LAYOUT,
    )
    return idft_real_tt, idft_imag_tt


class iSTFT:
    """
    Inverse Short‑Time Fourier Transform implemented as a series of matmuls
    using TTNN. Supports real‑valued inputs represented by separate magnitude
    (or real) and phase (or imag) tensors.
    """

    def __init__(
        self,
        n_fft: int,
        hop_length: Optional[int] = None,
        win_length: Optional[int] = None,
        window: Optional[torch.Tensor] = None,
        device: Optional[ttnn.Device] = None,
    ):
        self.n_fft = n_fft
        self.hop_length = hop_length if hop_length is not None else n_fft // 4
        self.win_length = win_length if win_length is not None else n_fft
        self.device = device or ttnn.get_default_device()

        # Window function (default: Hann)
        if window is None:
            window = torch.hann_window(self.win_length, periodic=False)
        self.window_tt = ttnn.from_torch(
            window,
            dtype=ttnn.bfloat16,
            device=self.device,
            layout=ttnn.ROW_MAJOR_LAYOUT,
        )

        # Pre‑compute IDFT matrices
        self.idft_real, self.idft_imag = _create_idft_matrix(self.n_fft, self.device)

    def __call__(
        self,
        spec_real: ttnn.Tensor,
        spec_imag: ttnn.Tensor,
    ) -> ttnn.Tensor:
        """
        Perform iSTFT.
        Arguments:
            spec_real: Tensor of shape (B, F, T) where F = n_fft//2+1
            spec_imag: Tensor of shape (B, F, T)
        Returns:
            time‑domain waveform Tensor of shape (B, L) where L = (T-1)*hop_length + n_fft
        """
        # Convert complex spectrogram to time‑domain frames via matmul
        # (B, F, T) @ (F, N) -> (B, N, T)
        frames_real = ttnn.matmul(
            spec_real,
            self.idft_real,
            memory_config=ttnn.L1_MEMORY_CONFIG,
        )
        frames_imag = ttnn.matmul(
            spec_imag,
            self.idft_imag,
            memory_config=ttnn.L1_MEMORY_CONFIG,
        )
        # Sum real & imag contributions (since iSTFT = Σ (real + j*imag)*exp)
        frames = ttnn.add(frames_real, frames_imag)

        # Apply window (broadcast over time dimension)
        # window shape: (N,) -> (1, N, 1) for broadcasting
        window_expanded = ttnn.reshape(self.window_tt, (1, self.n_fft, 1))
        frames_windowed = ttnn.mul(frames, window_expanded)

        # Overlap‑add to reconstruct the waveform
        batch, _, n_frames = frames_windowed.shape.with_tile_padding()
        out_len = (n_frames - 1) * self.hop_length + self.n_fft
        # Allocate output tensor
        output = ttnn.zeros(
            (batch, out_len),
            dtype=ttnn.bfloat16,
            device=self.device,
            layout=ttnn.ROW_MAJOR_LAYOUT,
        )

        # Perform overlap‑add using a simple loop (can be fused later)
        for i in range(n_frames):
            start = i * self.hop_length
            end = start + self.n_fft
            frame_slice = ttnn.slice(
                frames_windowed,
                starts=[0, 0, i],
                ends=[batch, self.n_fft, i + 1],
                step=[1, 1, 1],
            )
            frame_slice = ttnn.reshape(frame_slice, (batch, self.n_fft))
            # output[:, start:end] += frame_slice
            out_segment = ttnn.slice(
                output,
                starts=[0, start],
                ends=[batch, end],
                step=[1, 1],
            )
            out_updated = ttnn.add(out_segment, frame_slice)
            output = ttnn.update_slice(
                output,
                out_updated,
                starts=[0, start],
                ends=[batch, end],
                step=[1, 1],
            )
        return output

# ----------------------------------------------------------------------
# Example usage (to be executed on a TTNN‑enabled environment)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Device initialization (Wormhole/Blackhole)
    dev = ttnn.open_device(0)

    # Dummy spectrogram (batch=1, freq=n_fft//2+1, time=10)
    n_fft = 512
    T = 10
    B = 1
    F = n_fft // 2 + 1
    spec_real_pt = torch.randn(B, F, T, dtype=torch.float32)
    spec_imag_pt = torch.randn(B, F, T, dtype=torch.float32)

    spec_real_tt = ttnn.from_torch(
        spec_real_pt,
        dtype=ttnn.bfloat16,
        device=dev,
        layout=ttnn.ROW_MAJOR_LAYOUT,
    )
    spec_imag_tt = ttnn.from_torch(
        spec_imag_pt,
        dtype=ttnn.bfloat16,
        device=dev,
        layout=ttnn.ROW_MAJOR_LAYOUT,
    )

    istft = iSTFT(n_fft=n_fft, device=dev)
    wav_tt = istft(spec_real_tt, spec_imag_tt)

    # Bring result back to host for verification
    wav_pt = ttnn.to_torch(wav_tt)
    print("Output waveform shape:", wav_pt.shape)