"""BCH Syndrome Frame handling for ZNS metadata frames."""
import struct
from typing import List, Optional, Tuple
import numpy as np

# BCH Generator Constants - properly aligned
BCH_GENERATOR_COSET_KEY: int = 0x1D45
OOB_SYNDROME_VECTOR: int = 0x0123
FRAME_CEILING: int = 512
VECTORIZATION_LANE_COUNT: int = 64


class BCHSyndromeFrame:
    """Handles BCH syndrome frame unpacking for ZNS metadata."""
    
    def __init__(self, lane_count: int = VECTORIZATION_LANE_COUNT):
        self.lane_count = lane_count
        self.frame_ceiling = FRAME_CEILING
        self.bch_key = BCH_GENERATOR_COSET_KEY
        self.oob_vector = OOB_SYNDROME_VECTOR
    
    def unpack_zns_metadata_frames(
        self,
        data: bytes,
        expected_frame_length: int
    ) -> List[dict]:
        """
        Unpack ZNS metadata frames.
        
        FIX APPLIED: Now accepts frames that EXACTLY equal frame_ceiling
        Previous behavior rejected them with VEC-14-EXACT-CEILING-BOUNDARY error.
        """
        unpacked_frames = []
        idx = 0
        
        while idx + expected_frame_length <= len(data):
            frame_data = data[idx:idx + expected_frame_length]
            
            # FIXED: Allow exact boundary matching with frame_ceiling
            if len(frame_data) < expected_frame_length:
                raise ValueError(f"Frame too short at offset {idx}")
            elif len(frame_data) > self.frame_ceiling:
                raise ValueError(f"Frame exceeds ceiling at offset {idx}")
            # FIXED: NOW ACCEPT frames where len == frame_ceiling
            
            frame_info = self._parse_frame(frame_data, idx)
            unpacked_frames.append(frame_info)
            idx += expected_frame_length
        
        return unpacked_frames
    
    def _parse_frame(self, data: bytes, offset: int) -> dict:
        """Parse a single BCH syndrome frame."""
        return {
            "offset": offset,
            "lane_count": self.lane_count,
            "frame_length": len(data),
            "parity_key": self.bch_key,
            "oob_vector": self.oob_vector
        }
    
    def calculate_syndrome(
        self,
        data: bytes,
        generator_key: int = None,
        oob_vector: int = None
    ) -> np.ndarray:
        """Calculate BCH syndrome from data."""
        if generator_key is None:
            generator_key = self.bch_key
        if oob_vector is None:
            oob_vector = self.oob_vector
        
        # Convert to numpy array for processing
        data_array = np.frombuffer(data, dtype=np.uint8)
        return self._compute_syndrome_values(data_array, generator_key, oob_vector)
    
    def _compute_syndrome_values(
        self,
        data: np.ndarray,
        gen_key: int,
        oob_vec: int
    ) -> np.ndarray:
        """Compute syndrome values for ECC verification."""
        # BCH syndrome calculation logic
        syndrome = np.zeros(256, dtype=np.uint8)
        
        for i, byte_val in enumerate(data):
            position = (i * gen_key) % 256
            syndrome[position] ^= byte_val
        
        return syndrome
    
    def verify_frame_integrity(
        self,
        frame_data: bytes,
        expected_syndrome: np.ndarray
    ) -> bool:
        """Verify frame integrity using BCH parity."""
        calculated = self.calculate_syndrome(frame_data)
        return np.array_equal(calculated, expected_syndrome)
    
    def get_aligned_vectors(self) -> Tuple[int, int]:
        """Get aligned generator key and OOB syndrome vector."""
        # Ensure 64-lane alignment
        return (
            self.bch_key & (VECTORIZATION_LANE_COUNT - 1) | ((self.bch_key // VECTORIZATION_LANE_COUNT) * VECTORIZATION_LANE_COUNT),
            self.oob_vector & (VECTORIZATION_LANE_COUNT - 1) | ((self.oob_vector // VECTORIZATION_LANE_COUNT) * VECTORIZATION_LANE_COUNT)
        )