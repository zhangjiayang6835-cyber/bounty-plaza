"""Texture atlas management and UV mapping for dynamic voxel entities."""

from typing import Dict, Optional, Tuple
from packages.voxel_optimizer.models import AtlasCoordinate


class TextureAtlasManager:
    """Manages unified texture atlas coordinate allocation and UV calculation."""

    DEFAULT_BLOCKS: Tuple[str, ...] = (
        "minecraft:stone",
        "minecraft:dirt",
        "minecraft:grass_block",
        "minecraft:cobblestone",
        "minecraft:oak_planks",
        "minecraft:iron_block",
        "minecraft:gold_block",
        "minecraft:diamond_block",
        "minecraft:obsidian",
        "minecraft:glass",
        "minecraft:sand",
        "minecraft:gravel",
        "minecraft:bricks",
        "minecraft:mossy_cobblestone",
        "minecraft:netherrack",
        "minecraft:soul_sand",
    )

    def __init__(self, grid_dimension: int = 64) -> None:
        """Initialize texture atlas manager with given grid resolution.

        :param grid_dimension: Number of discrete cells per axis in the atlas.
        """
        self._grid_dimension: int = grid_dimension
        self._registry: Dict[str, AtlasCoordinate] = {}
        self._next_slot: int = 0
        self._initialize_default_registry()

    def _initialize_default_registry(self) -> None:
        """Populate initial set of common bedrock block types."""
        for block_id in self.DEFAULT_BLOCKS:
            self.register_block(block_id)

    @property
    def capacity(self) -> int:
        """Return total slot capacity of the texture atlas grid.

        :return: Maximum number of addressable block types.
        """
        return self._grid_dimension * self._grid_dimension

    @property
    def registered_count(self) -> int:
        """Return total number of currently registered blocks.

        :return: Integer count of registered entries.
        """
        return len(self._registry)

    def register_block(self, block_id: str) -> AtlasCoordinate:
        """Register a block type and compute normalized UV coordinates.

        :param block_id: Namespaced block identifier.
        :return: AtlasCoordinate containing assigned index and UV bounds.
        :raises ValueError: If atlas grid capacity is exceeded.
        """
        if block_id in self._registry:
            return self._registry[block_id]

        if self._next_slot >= self.capacity:
            raise ValueError(
                f"Texture atlas capacity exceeded: maximum {self.capacity} slots."
            )

        slot = self._next_slot
        self._next_slot += 1

        cell_size = 1.0 / self._grid_dimension
        col = slot % self._grid_dimension
        row = slot // self._grid_dimension

        coord = AtlasCoordinate(
            atlas_index=slot,
            u_min=col * cell_size,
            v_min=row * cell_size,
            u_max=(col + 1) * cell_size,
            v_max=(row + 1) * cell_size,
        )

        self._registry[block_id] = coord
        return coord

    def get_atlas_index(self, block_id: str) -> int:
        """Resolve the atlas slot index for a block identifier.

        :param block_id: Namespaced block identifier.
        :return: Integer slot index.
        """
        if block_id in self._registry:
            return self._registry[block_id].atlas_index
        return self.register_block(block_id).atlas_index

    def get_coordinate(self, block_id: str) -> Optional[AtlasCoordinate]:
        """Retrieve full UV coordinate definition for a registered block.

        :param block_id: Namespaced block identifier.
        :return: AtlasCoordinate instance if found, None otherwise.
        """
        return self._registry.get(block_id)
