"""Unified voxel entity representation and cluster spawner implementation."""

from typing import Dict, List, Optional, Any
from packages.voxel_optimizer.models import Vector3D
from packages.voxel_optimizer.atlas_manager import TextureAtlasManager


class UnifiedVoxelEntity:
    """Unified entity representation decoupled from individual attachables."""

    ENTITY_IDENTIFIER: str = "contraption:unified_voxel_display"

    def __init__(
        self,
        entity_id: str,
        location: Vector3D,
        block_id: str,
        atlas_manager: TextureAtlasManager,
        cluster_id: str = "default",
    ) -> None:
        """Initialize unified voxel entity instance.

        :param entity_id: Unique runtime entity identifier.
        :param location: Spatial position coordinates in world.
        :param block_id: Initial namespaced block identifier.
        :param atlas_manager: Reference to shared texture atlas manager.
        :param cluster_id: Cluster grouping identifier.
        """
        self._entity_id: str = entity_id
        self._location: Vector3D = location
        self._block_id: str = block_id
        self._atlas_manager: TextureAtlasManager = atlas_manager
        self._cluster_id: str = cluster_id
        self._atlas_index: int = atlas_manager.get_atlas_index(block_id)
        self._is_active: bool = True

    @property
    def entity_id(self) -> str:
        """Return unique runtime entity identifier.

        :return: String entity id.
        """
        return self._entity_id

    @property
    def type_identifier(self) -> str:
        """Return unified Bedrock entity type identifier.

        :return: Constant unified entity type string.
        """
        return self.ENTITY_IDENTIFIER

    @property
    def location(self) -> Vector3D:
        """Return current spatial coordinates of the entity.

        :return: Vector3D location.
        """
        return self._location

    @property
    def block_id(self) -> str:
        """Return active namespaced block identifier.

        :return: Namespaced block identifier.
        """
        return self._block_id

    @property
    def atlas_index(self) -> int:
        """Return current atlas slot index for texture lookup.

        :return: Integer atlas index.
        """
        return self._atlas_index

    @property
    def cluster_id(self) -> str:
        """Return parent cluster grouping identifier.

        :return: String cluster ID.
        """
        return self._cluster_id

    @property
    def is_active(self) -> bool:
        """Return whether entity is currently active in the simulation.

        :return: Boolean flag indicating active status.
        """
        return self._is_active

    def set_block_type(self, new_block_id: str) -> None:
        """Update block type at runtime in O(1) without entity recreation.

        :param new_block_id: Target namespaced block identifier.
        """
        if self._block_id == new_block_id:
            return
        self._block_id = new_block_id
        self._atlas_index = self._atlas_manager.get_atlas_index(new_block_id)

    def get_dynamic_properties(self) -> Dict[str, Any]:
        """Retrieve simulated Bedrock dynamic property state dictionary.

        :return: Dictionary containing Bedrock dynamic properties.
        """
        return {
            "contraption:block_id": self._block_id,
            "contraption:atlas_index": self._atlas_index,
            "contraption:cluster_id": self._cluster_id,
        }

    def remove(self) -> None:
        """Mark entity as inactive and simulate destruction."""
        self._is_active = False


class UnifiedVoxelSpawner:
    """Manages spawning, lifecycle, and mutation of dynamic voxel clusters."""

    def __init__(self, atlas_manager: Optional[TextureAtlasManager] = None) -> None:
        """Initialize cluster spawner.

        :param atlas_manager: Optional shared TextureAtlasManager instance.
        """
        self._atlas_manager: TextureAtlasManager = (
            atlas_manager if atlas_manager is not None else TextureAtlasManager()
        )
        self._clusters: Dict[str, List[UnifiedVoxelEntity]] = {}
        self._entity_counter: int = 0

    @property
    def atlas_manager(self) -> TextureAtlasManager:
        """Retrieve active texture atlas manager instance.

        :return: TextureAtlasManager instance.
        """
        return self._atlas_manager

    def spawn_cluster_block(
        self,
        loc: Vector3D,
        block_id: str,
        cluster_id: str = "default",
    ) -> UnifiedVoxelEntity:
        """Spawn a unified display entity representing an arbitrary block type.

        :param loc: Spatial coordinate vector.
        :param block_id: Target namespaced block identifier.
        :param cluster_id: Cluster grouping identifier.
        :return: UnifiedVoxelEntity instance.
        """
        self._entity_counter += 1
        entity_id = f"unified_voxel_{self._entity_counter}"

        entity = UnifiedVoxelEntity(
            entity_id=entity_id,
            location=loc,
            block_id=block_id,
            atlas_manager=self._atlas_manager,
            cluster_id=cluster_id,
        )

        if cluster_id not in self._clusters:
            self._clusters[cluster_id] = []
        self._clusters[cluster_id].append(entity)

        return entity

    def update_cluster_block_type(
        self, entity: UnifiedVoxelEntity, new_block_id: str
    ) -> None:
        """Update existing block entity to a new block type at runtime.

        :param entity: Target UnifiedVoxelEntity instance.
        :param new_block_id: New namespaced block identifier.
        """
        entity.set_block_type(new_block_id)

    def get_cluster_entities(self, cluster_id: str) -> List[UnifiedVoxelEntity]:
        """Retrieve all active entities belonging to a specific cluster.

        :param cluster_id: Cluster identifier string.
        :return: List of active UnifiedVoxelEntity instances.
        """
        entities = self._clusters.get(cluster_id, [])
        return [e for e in entities if e.is_active]

    def remove_cluster(self, cluster_id: str) -> int:
        """Remove and clean up all entities within a cluster.

        :param cluster_id: Cluster identifier string.
        :return: Count of destroyed entities.
        """
        entities = self._clusters.get(cluster_id, [])
        count = 0
        for entity in entities:
            if entity.is_active:
                entity.remove()
                count += 1
        self._clusters.pop(cluster_id, None)
        return count
