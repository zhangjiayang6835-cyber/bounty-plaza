/**
 * GraphQL Query Complexity Analyzer
 * Implements complexity analysis and depth limiting for GraphQL queries
 */

const { visit, visitInParallel, visitWithTypeInfo, getArgumentValues, getNamedType } = require('graphql');
const { GraphQLObjectType, GraphQLList, GraphQLNonNull, GraphQLScalarType, GraphQLEnumType, GraphQLInterfaceType, GraphQLUnionType } = require('graphql');

class QueryComplexity {
  constructor(options = {}) {
    this.maxDepth = options.maxDepth || 10;
    this.maxComplexity = options.maxComplexity || 100;
    this.variables = options.variables || {};
    this.costPerField = options.costPerField || 1;
    this.costPerNode = options.costPerNode || 0;
    this.ignore = options.ignore || [];
    this.scalars = options.scalars || {};
  }

  /**
   * Calculate complexity for a single query
   */
  getComplexity(document, schema) {
    const complexity = {
      score: 0,
      depth: 0,
      maxDepth: 0
    };

    const typeInfo = new (require('graphql').TypeInfo)(schema);

    visit(document, visitWithTypeInfo(typeInfo, {
      Field(node, key, parent, path, ancestors) {
        const depth = ancestors.filter(a => a.kind === 'Field').length;
        const namedType = getNamedType(typeInfo.getType());
        
        // Track max depth
        complexity.maxDepth = Math.max(complexity.maxDepth, depth);
        
        // Check depth limit
        if (depth > this.maxDepth) {
          throw new Error(`Query depth limit of ${this.maxDepth} exceeded`);
        }

        // Calculate field cost
        let fieldCost = this.costPerField;
        
        // Check if field is in ignore list
        if (this.ignore.includes(node.name.value)) {
          fieldCost = 0;
        }

        // Handle nested queries (lists add complexity)
        if (namedType instanceof GraphQLList || namedType instanceof GraphQLNonNull) {
          fieldCost = fieldCost * (namedType instanceof GraphQLList ? 2 : 1);
        }

        complexity.score += fieldCost;
      },

      OperationDefinition(node) {
        // Reset depth for each operation
        complexity.depth = 0;
      },

      InlineFragment(node) {
        // Track depth for fragments
        const depth = node.selectionSet.selections.reduce((max, selection) => {
          if (selection.kind === 'Field') {
            return Math.max(max, selection.selectionSet.selections.filter(s => s.kind === 'Field').length);
          }
          return max;
        }, 0);
        
        complexity.depth = Math.max(complexity.depth, depth);
      }
    }));

    return complexity;
  }

  /**
   * Calculate complexity for a batch of queries
   */
  getBatchComplexity(queries, schema) {
    let totalComplexity = 0;
    let maxDepth = 0;

    for (const query of queries) {
      const complexity = this.getComplexity(query.document, schema);
      totalComplexity += complexity.score;
      maxDepth = Math.max(maxDepth, complexity.maxDepth);
    }

    return {
      score: totalComplexity,
      maxDepth: maxDepth
    };
  }

  /**
   * Validate complexity against limits
   */
  validateComplexity(complexity) {
    if (complexity.score > this.maxComplexity) {
      throw new Error(`Query complexity limit of ${this.maxComplexity} exceeded. Calculated: ${complexity.score}`);
    }

    if (complexity.maxDepth > this.maxDepth) {
      throw new Error(`Query depth limit of ${this.maxDepth} exceeded. Max depth: ${complexity.maxDepth}`);
    }

    return true;
  }
}

module.exports = QueryComplexity;