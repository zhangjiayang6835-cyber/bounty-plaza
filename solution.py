import os

def create_roblox_engine_docs():
    os.makedirs("engines/roblox", exist_ok=True)
    
    roblox_md = """# Roblox Studio Engine Guide for Goal to Game

This guide provides instructions for coding agents (like Claude Code) when building games in Roblox Studio using the Goal to Game skill and Thrixel assets.

## Core Specifications & Limitations

- **Triangle Limit:** Individual meshes are strictly capped at 20,000 triangles per mesh part. Large assets must be split into modular components or LODs.
- **Geometry Validation:** Meshes must be watertight (manifold) with no exposed holes, self-intersections, or non-manifold geometry, or Roblox's import validator will reject them or corrupt collision hulls.
- **File Formats:** Use `.fbx` or `.obj` for importing 3D models. `.fbx` is preferred for preserving materials and node hierarchies.
- **Units:** 1 Roblox Stud = 1 meter (approximate scale alignment with Unity/Three.js pipelines). Ensure models are exported with correct real-world scale.

## Asset Pipeline & Import Rules

1. **Orientation:** Roblox coordinate system is Y-up, right-handed (same as OpenGL/Three.js, but verify forward vectors). Ensure meshes face -Z or +Z consistently as defined in the Thrixel asset manifest.
2. **Collisions:** 
   - Set `CollisionFidelity` to `Hull` or `PreciseConvexDecomposition` for complex interactive objects, and `Box` or `Cylinder` for simple primitives to optimize physics performance.
   - Ensure `CanCollide` and `Anchored` properties are set correctly upon instantiation via Luau scripts (e.g., environmental props should be anchored; dynamic objects unanchored with proper mass/density).
3. **Materials & Textures:**
   - Apply PBR textures using `SurfaceAppearance` objects rather than legacy brick colors where high fidelity is required.
   - Texture maps required: BaseColor (Albedo), Metalness, Roughness, Normal (OpenGL format, green channel inverted if needed for Roblox).

## Scripting & Architecture (Luau)

- Use standard Roblox Services (`ReplicatedStorage`, `ServerScriptService`, `Players`, `TweenService`, etc.).
- Organize game logic cleanly: Server scripts handle state and persistence; Local scripts handle UI, camera, and client-side effects.
- Asset loading: Reference assets via `rbxassetid://` or pre-imported Model instances stored in `ReplicatedStorage`.

## Pitfalls & Common Mistakes

- **Unanchored Props:** Forgetting to anchor imported environmental models causes them to collapse immediately on play. Always set `Part.Anchored = true` for static scenery.
- **Exceeding Triangle Budgets:** Importing high-poly sculpts directly without decimation leads to physics lag and import failure.
- **Missing SurfaceAppearance Maps:** Applying raw textures as standard decals instead of `SurfaceAppearance` results in flat-looking metallic/roughness properties.
"""

    with open("engines/roblox/roblox.md", "w") as f:
        f.write(roblox_md)

if __name__ == "__main__":
    create_roblox_engine_docs()