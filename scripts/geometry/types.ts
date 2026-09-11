export type Vector3 = [number, number, number];
export type Vector2 = [number, number];

export interface FaceUVDefinition {
  uv: Vector2;
  uv_size: Vector2;
}

export type PerFaceUV = Record<string, FaceUVDefinition>;

export interface CubeDefinition {
  origin: Vector3;
  size: Vector3;
  uv: Vector2 | PerFaceUV;
  inflate?: number;
  mirror?: boolean;
}

export interface BoneDefinition {
  name: string;
  parent?: string;
  pivot?: Vector3;
  rotation?: Vector3;
  cubes?: CubeDefinition[];
  neverrender?: boolean;
  mirror?: boolean;
}

export interface GeometryDescriptionDefinition {
  identifier: string;
  texture_width: number;
  texture_height: number;
  visible_bounds_width?: number;
  visible_bounds_height?: number;
  visible_bounds_offset?: Vector3;
}

export interface SingleGeometryDefinition {
  description: GeometryDescriptionDefinition;
  bones: BoneDefinition[];
}

export interface BedrockGeometryDocument {
  format_version: string;
  'minecraft:geometry': SingleGeometryDefinition[];
}

export type ArmModelVariant = 'classic' | 'slim';

export interface DiagnosticsIssue {
  code: string;
  message: string;
  boneName?: string;
  severity: 'error' | 'warning';
}

export interface DiagnosticsReport {
  isValid: boolean;
  issues: DiagnosticsIssue[];
}
