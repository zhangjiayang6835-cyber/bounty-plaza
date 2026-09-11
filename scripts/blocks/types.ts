export type BedrockRenderMethod =
  | 'opaque'
  | 'alpha_test'
  | 'alpha_test_single_sided'
  | 'blend'
  | 'double_sided';

export type DirectionalFace =
  | 'up'
  | 'down'
  | 'north'
  | 'south'
  | 'east'
  | 'west'
  | '*';

export interface MaterialInstanceDefinition {
  texture: string;
  render_method?: BedrockRenderMethod;
  face_dimming?: boolean;
  ambient_occlusion?: number | boolean;
  isotropic?: boolean;
}

export interface BlockDescription {
  identifier: string;
  menu_category?: {
    category?: string;
    group?: string;
    is_hidden_in_commands?: boolean;
  };
  states?: Record<string, boolean[] | number[] | string[]>;
}

export interface BlockComponents {
  'minecraft:material_instances'?: Record<string, MaterialInstanceDefinition>;
  'minecraft:geometry'?: string | { identifier: string };
  'minecraft:collision_box'?: boolean | { origin: number[]; size: number[] };
  'minecraft:selection_box'?: boolean | { origin: number[]; size: number[] };
  'minecraft:destructible_by_mining'?: { seconds_to_destroy: number };
  'minecraft:destructible_by_explosion'?: { explosion_resistance: number };
  'minecraft:friction'?: number;
  'minecraft:map_color'?: string;
  [componentName: string]: unknown;
}

export interface BlockDefinitionDocument {
  format_version: string;
  'minecraft:block': {
    description: BlockDescription;
    components: BlockComponents;
    permutations?: Array<{
      condition: string;
      components: Partial<BlockComponents>;
    }>;
  };
}

export interface SchemaValidationResult {
  valid: boolean;
  errors: string[];
}
