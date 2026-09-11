import { BedrockUVValidator, GeometryGenerator } from './geometry/index.js';

export function initializeCustomNpcGeometry(): void {
  const classic = GeometryGenerator.createHumanoid('geometry.custom_npc', 'classic');
  const slim = GeometryGenerator.createHumanoid('geometry.custom_npc.slim', 'slim');

  const validator = new BedrockUVValidator();
  const classicReport = validator.validateDocument(classic, 'classic');
  const slimReport = validator.validateDocument(slim, 'slim');

  if (!classicReport.isValid || !slimReport.isValid) {
    throw new Error('Failed to validate initial humanoid geometries');
  }
}

initializeCustomNpcGeometry();
