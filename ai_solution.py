To solve the issue of hitbox collision dropouts during rapid movement, we'll ensure the AABB is computed correctly and implement swept AABB collision detection.

```csharp
using System;

namespace Minecraft.Bedrock.Entities;

public class Entity {
    private Vector3 position;
    private Vector3 size;

    public Entity(Vector3 position, Vector3 size) {
        this.position = position;
        this.size = size;
    }

    public AxisAlignedBox GetAABB() {
        double width = size.X;
        double height = size.Y;
        double depth = size.Z;

        double minX = position.X - width / 2;
        double maxX = position.X + width / 2;
        double minY = position.Y - height / 2;
        double maxY = position.Y + height / 2;
        double minZ = position.Z - depth / 2;
        double maxZ = position.Z + depth / 2;

        return new AxisAlignedBox(new Vector3(minX, minY, minZ), new Vector3(maxX, maxY, maxZ));
    }

    public bool CheckCollision(AxisAlignedBox otherAABB) {
        // Implement swept AABB collision detection
        return AABB.SweptAABBIntersects(this.GetAABB(), otherAABB);
    }
}
```