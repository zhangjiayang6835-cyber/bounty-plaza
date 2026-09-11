import { ArmModelVariant, BedrockGeometryDocument, BoneDefinition } from './types.js';

export class GeometryGenerator {
  public static createHumanoid(
    identifier: string = 'geometry.custom_npc',
    variant: ArmModelVariant = 'classic',
    outerLayers: boolean = true,
  ): BedrockGeometryDocument {
    const armWidth = variant === 'classic' ? 4 : 3;
    const armPivotY = variant === 'classic' ? 22 : 21.5;
    const rightArmOriginX = variant === 'classic' ? -8 : -7;

    const bones: BoneDefinition[] = [
      { name: 'root', pivot: [0, 0, 0] },
      { name: 'waist', parent: 'root', pivot: [0, 12, 0] },
      {
        name: 'body',
        parent: 'waist',
        pivot: [0, 24, 0],
        cubes: [{ origin: [-4, 12, -2], size: [8, 12, 4], uv: [16, 16] }],
      },
      {
        name: 'head',
        parent: 'body',
        pivot: [0, 24, 0],
        cubes: [{ origin: [-4, 24, -4], size: [8, 8, 8], uv: [0, 0] }],
      },
      {
        name: 'rightArm',
        parent: 'body',
        pivot: [-5, armPivotY, 0],
        cubes: [{ origin: [rightArmOriginX, 12, -2], size: [armWidth, 12, 4], uv: [40, 16] }],
      },
      {
        name: 'leftArm',
        parent: 'body',
        pivot: [5, armPivotY, 0],
        cubes: [{ origin: [4, 12, -2], size: [armWidth, 12, 4], uv: [32, 48], mirror: false }],
      },
      {
        name: 'rightLeg',
        parent: 'root',
        pivot: [-1.9, 12, 0],
        cubes: [{ origin: [-3.9, 0, -2], size: [4, 12, 4], uv: [0, 16] }],
      },
      {
        name: 'leftLeg',
        parent: 'root',
        pivot: [1.9, 12, 0],
        cubes: [{ origin: [-0.1, 0, -2], size: [4, 12, 4], uv: [16, 48], mirror: false }],
      },
    ];

    if (outerLayers) {
      bones.push(
        {
          name: 'hat',
          parent: 'head',
          pivot: [0, 24, 0],
          cubes: [{ origin: [-4, 24, -4], size: [8, 8, 8], uv: [32, 0], inflate: 0.5 }],
        },
        {
          name: 'jacket',
          parent: 'body',
          pivot: [0, 24, 0],
          cubes: [{ origin: [-4, 12, -2], size: [8, 12, 4], uv: [16, 32], inflate: 0.25 }],
        },
        {
          name: 'rightSleeve',
          parent: 'rightArm',
          pivot: [-5, armPivotY, 0],
          cubes: [{ origin: [rightArmOriginX, 12, -2], size: [armWidth, 12, 4], uv: [40, 32], inflate: 0.25 }],
        },
        {
          name: 'leftSleeve',
          parent: 'leftArm',
          pivot: [5, armPivotY, 0],
          cubes: [{ origin: [4, 12, -2], size: [armWidth, 12, 4], uv: [48, 48], inflate: 0.25, mirror: false }],
        },
        {
          name: 'rightPants',
          parent: 'rightLeg',
          pivot: [-1.9, 12, 0],
          cubes: [{ origin: [-3.9, 0, -2], size: [4, 12, 4], uv: [0, 32], inflate: 0.25 }],
        },
        {
          name: 'leftPants',
          parent: 'leftLeg',
          pivot: [1.9, 12, 0],
          cubes: [{ origin: [-0.1, 0, -2], size: [4, 12, 4], uv: [0, 48], inflate: 0.25, mirror: false }],
        },
      );
    }

    return {
      format_version: '1.12.0',
      'minecraft:geometry': [
        {
          description: {
            identifier,
            texture_width: 64,
            texture_height: 64,
            visible_bounds_width: 1.5,
            visible_bounds_height: 2.0,
            visible_bounds_offset: [0, 1, 0],
          },
          bones,
        },
      ],
    };
  }
}
