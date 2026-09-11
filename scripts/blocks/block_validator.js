import { VALID_RENDER_METHODS } from './types.js';

/**
 * Validates a Bedrock block definition document against modern 1.21+ schema specifications.
 * @param {unknown} document Candidate block definition object to validate.
 * @returns {{ valid: boolean, errors: string[] }} Validation outcome containing boolean status and error messages.
 */
export function validateBlockDefinition(document) {
  const errors = [];

  if (!document || typeof document !== 'object') {
    return { valid: false, errors: ['Document must be a non-null JSON object'] };
  }

  const doc = document;

  if (typeof doc.format_version !== 'string') {
    errors.push("Missing or invalid 'format_version' string");
  }

  const block = doc['minecraft:block'];
  if (!block || typeof block !== 'object') {
    errors.push("Missing 'minecraft:block' root object");
    return { valid: false, errors };
  }

  const description = block.description;
  if (!description || typeof description !== 'object') {
    errors.push("Missing 'description' object under 'minecraft:block'");
  } else {
    if (
      typeof description.identifier !== 'string' ||
      !description.identifier.includes(':')
    ) {
      errors.push(
        "Invalid 'description.identifier': must be a namespaced identifier (e.g. namespace:name)"
      );
    }
    if ('isotropic' in description) {
      errors.push(
        "Property 'isotropic' is not allowed in 'description'. It must be declared inside 'minecraft:material_instances' face definitions."
      );
    }
  }

  const components = block.components;
  if (!components || typeof components !== 'object') {
    errors.push("Missing 'components' object under 'minecraft:block'");
    return { valid: false, errors };
  }

  const materialInstances = components['minecraft:material_instances'];

  if (materialInstances) {
    if (typeof materialInstances !== 'object') {
      errors.push("'minecraft:material_instances' must be an object");
    } else {
      for (const [faceKey, instanceValue] of Object.entries(materialInstances)) {
        if (!instanceValue || typeof instanceValue !== 'object') {
          errors.push(`Material instance '${faceKey}' must be an object`);
          continue;
        }

        const instance = instanceValue;

        if (typeof instance.texture !== 'string' || instance.texture.trim() === '') {
          errors.push(
            `Material instance '${faceKey}' must specify a valid 'texture' string`
          );
        }

        if (instance.render_method !== undefined) {
          if (!VALID_RENDER_METHODS.includes(instance.render_method)) {
            errors.push(
              `Render method '${instance.render_method}' is unsupported under schema ${doc.format_version}. Valid options: ${VALID_RENDER_METHODS.join(', ')}`
            );
          }
          if (faceKey === '*' && instance.render_method === 'alpha_test') {
            errors.push(
              "Property 'minecraft:material_instances' contains invalid face specifier '*' with render method 'alpha_test'."
            );
          }
        }

        if (
          instance.isotropic !== undefined &&
          typeof instance.isotropic !== 'boolean'
        ) {
          errors.push(
            `Material instance '${faceKey}' property 'isotropic' must be a boolean`
          );
        }

        if (instance.ambient_occlusion !== undefined) {
          if (
            typeof instance.ambient_occlusion !== 'number' ||
            Number.isNaN(instance.ambient_occlusion)
          ) {
            errors.push(
              `Material instance '${faceKey}' property 'ambient_occlusion' must be a float number`
            );
          }
        }
      }
    }
  }

  const geometry = components['minecraft:geometry'];
  if (geometry !== undefined) {
    if (typeof geometry === 'string') {
      if (!geometry.trim()) {
        errors.push("Component 'minecraft:geometry' identifier string cannot be empty");
      }
    } else if (typeof geometry === 'object' && geometry !== null) {
      if (typeof geometry.identifier !== 'string' || !geometry.identifier.trim()) {
        errors.push(
          "Component 'minecraft:geometry' object must provide a valid 'identifier' string"
        );
      }
    } else {
      errors.push("Component 'minecraft:geometry' must be a string or object");
    }
  }

  if (geometry && !materialInstances) {
    errors.push(
      "Blocks specifying 'minecraft:geometry' must also declare 'minecraft:material_instances'"
    );
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Validates the custom compressed basalt block definition file.
 * @param {unknown} document The parsed JSON document for compressed basalt.
 * @returns {{ valid: boolean, errors: string[] }} Schema validation result.
 */
export function validateCompressedBasaltDefinition(document) {
  const baseResult = validateBlockDefinition(document);
  if (!baseResult.valid) {
    return baseResult;
  }

  const doc = document;
  const components = doc['minecraft:block'].components;
  const matInstances = components['minecraft:material_instances'] || {};

  const requiredFaces = [
    'up',
    'down',
    'north',
    'south',
    'east',
    'west',
  ];

  const missingFaces = requiredFaces.filter((f) => !(f in matInstances));
  if (missingFaces.length > 0) {
    return {
      valid: false,
      errors: [
        `Missing explicit directional face definitions in material_instances: ${missingFaces.join(', ')}`,
      ],
    };
  }

  const topInstance = matInstances['up'];
  if (!topInstance?.isotropic) {
    return {
      valid: false,
      errors: [
        "Expected face 'up' to configure 'isotropic: true' for natural basalt distribution",
      ],
    };
  }

  const bottomInstance = matInstances['down'];
  if (!bottomInstance?.isotropic) {
    return {
      valid: false,
      errors: [
        "Expected face 'down' to configure 'isotropic: true' for natural basalt distribution",
      ],
    };
  }

  return { valid: true, errors: [] };
}
