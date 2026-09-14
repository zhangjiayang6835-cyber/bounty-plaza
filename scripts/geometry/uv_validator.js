export class BedrockUVValidator {
  validateDocument(doc, expectedVariant) {
    const issues = [];
    if (!doc['minecraft:geometry'] || doc['minecraft:geometry'].length === 0) {
      issues.push({
        code: 'EMPTY_GEOMETRY_DOCUMENT',
        message: "No geometry definitions located in 'minecraft:geometry'",
        severity: 'error',
      });
      return { isValid: false, issues };
    }
    for (const geo of doc['minecraft:geometry']) {
      this.validateSingleGeometry(geo, issues, expectedVariant);
    }
    return {
      isValid: !issues.some((issue) => issue.severity === 'error'),
      issues,
    };
  }

  validateSingleGeometry(geo, issues, expectedVariant) {
    const desc = geo.description;
    if (desc.texture_width === 64 && desc.texture_height === 32) {
      issues.push({
        code: 'LEGACY_32X64_TEXTURE_DETECTED',
        message: 'Legacy 64x32 texture resolution detected. Bedrock 1.21.50+ requires 64x64 layout.',
        severity: 'error',
      });
    } else if (desc.texture_width !== 64 || desc.texture_height !== 64) {
      issues.push({
        code: 'INVALID_TEXTURE_DIMENSIONS',
        message: `Expected 64x64 texture dimensions, received ${desc.texture_width}x${desc.texture_height}.`,
        severity: 'error',
      });
    }

    const boneMap = new Map(geo.bones.map((b) => [b.name, b]));
    const requiredBones = ['root', 'body', 'head', 'rightArm', 'leftArm', 'rightLeg', 'leftLeg'];
    for (const name of requiredBones) {
      if (!boneMap.has(name)) {
        issues.push({
          code: 'MISSING_HUMANOID_BONE',
          message: `Mandatory humanoid bone '${name}' is missing.`,
          boneName: name,
          severity: 'error',
        });
      }
    }

    const mirrorTargets = ['leftArm', 'leftLeg', 'leftSleeve', 'leftPants'];
    for (const boneName of mirrorTargets) {
      const bone = boneMap.get(boneName);
      if (!bone) continue;

      if (bone.mirror === true) {
        issues.push({
          code: `MIRRORED_${boneName.toUpperCase()}_DETECTED`,
          message: `Bone '${boneName}' contains legacy mirror:true flag.`,
          boneName,
          severity: 'error',
        });
      }

      if (bone.cubes) {
        for (let i = 0; i < bone.cubes.length; i++) {
          if (bone.cubes[i].mirror === true) {
            issues.push({
              code: `MIRRORED_${boneName.toUpperCase()}_DETECTED`,
              message: `Cube ${i} in bone '${boneName}' contains legacy mirror:true flag.`,
              boneName,
              severity: 'error',
            });
          }
        }
      }
    }

    const leftArm = boneMap.get('leftArm');
    if (leftArm && leftArm.cubes && leftArm.cubes.length > 0) {
      const cube = leftArm.cubes[0];
      if (Array.isArray(cube.uv)) {
        if (cube.uv[0] === 40 && cube.uv[1] === 16) {
          issues.push({
            code: 'LEGACY_LEFT_ARM_UV_DETECTED',
            message: "Bone 'leftArm' references right arm UV [40, 16] instead of discrete [32, 48].",
            boneName: 'leftArm',
            severity: 'error',
          });
        }
      }
    }

    const leftLeg = boneMap.get('leftLeg');
    if (leftLeg && leftLeg.cubes && leftLeg.cubes.length > 0) {
      const cube = leftLeg.cubes[0];
      if (Array.isArray(cube.uv)) {
        if (cube.uv[0] === 0 && cube.uv[1] === 16) {
          issues.push({
            code: 'LEGACY_LEFT_LEG_UV_DETECTED',
            message: "Bone 'leftLeg' references right leg UV [0, 16] instead of discrete [16, 48].",
            boneName: 'leftLeg',
            severity: 'error',
          });
        }
      }
    }

    if (expectedVariant) {
      const expectedWidth = expectedVariant === 'classic' ? 4 : 3;
      for (const armName of ['rightArm', 'leftArm']) {
        const armBone = boneMap.get(armName);
        if (armBone && armBone.cubes && armBone.cubes.length > 0) {
          const actualWidth = armBone.cubes[0].size[0];
          if (actualWidth !== expectedWidth) {
            issues.push({
              code: 'ARM_DIMENSION_MISMATCH',
              message: `Bone '${armName}' width is ${actualWidth}, expected ${expectedWidth} for ${expectedVariant} model.`,
              boneName: armName,
              severity: 'error',
            });
          }
        }
      }
    }

    for (const bone of geo.bones) {
      if (bone.cubes) {
        for (let i = 0; i < bone.cubes.length; i++) {
          this.validateCubeUVBounds(bone.name, i, bone.cubes[i], desc.texture_width, desc.texture_height, issues);
        }
      }
    }
  }

  validateCubeUVBounds(boneName, index, cube, texWidth, texHeight, issues) {
    if (Array.isArray(cube.uv)) {
      const u = cube.uv[0];
      const v = cube.uv[1];
      const [sx, sy, sz] = cube.size;
      const spanW = 2 * (sz + sx);
      const spanH = sz + sy;

      if (u < 0 || v < 0 || u + spanW > texWidth || v + spanH > texHeight) {
        issues.push({
          code: 'UV_OUT_OF_BOUNDS',
          message: `Cube ${index} in bone '${boneName}' UV coordinates exceed texture boundaries.`,
          boneName,
          severity: 'error',
        });
      }
    }
  }
}
