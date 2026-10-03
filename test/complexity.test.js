/**
 * Test suite for GraphQL complexity analyzer
 */

const { GraphQLSchema, GraphQLObjectType, GraphQLFieldConfig, GraphQLString, GraphQLList, GraphQLNonNull } = require('graphql');
const { QueryComplexity } = require('../graphql');

describe('QueryComplexity', () => {
  const testSchema = new GraphQLSchema({
    query: new GraphQLObjectType({
      name: 'Query',
      fields: {
        user: {
          type: new GraphQLObjectType({
            name: 'User',
            fields: {
              id: { type: GraphQLString },
              name: { type: GraphQLString },
              posts: {
                type: new GraphQLList(new GraphQLObjectType({
                  name: 'Post',
                  fields: {
                    id: { type: GraphQLString },
                    title: { type: GraphQLString },
                    comments: {
                      type: new GraphQLList(new GraphQLObjectType({
                        name: 'Comment',
                        fields: {
                          id: { type: GraphQLString },
                          text: { type: GraphQLString }
                        }
                      }))
                    }
                  }
                }))
              }
            }
          })
        }
      }
    })
  });

  const complexityAnalyzer = new QueryComplexity({
    maxDepth: 5,
    maxComplexity: 100,
    costPerField: 1
  });

  test('should calculate basic complexity', () => {
    const query = `
      query {
        user {
          id
          name
        }
      }
    `;
    
    const document = require('graphql').parse(query);
    const complexity = complexityAnalyzer.getComplexity(document, testSchema);
    
    expect(complexity.score).toBe(2); // user field + 2 fields
    expect(complexity.maxDepth).toBe(2);
  });

  test('should calculate nested complexity', () => {
    const query = `
      query {
        user {
          id
          name
          posts {
            id
            title
            comments {
              id
              text
            }
          }
        }
      }
    `;
    
    const document = require('graphql').parse(query);
    const complexity = complexityAnalyzer.getComplexity(document, testSchema);
    
    expect(complexity.score).toBe(8); // user + 2 fields + posts + 2 fields + comments + 2 fields
    expect(complexity.maxDepth).toBe(4);
  });

  test('should enforce depth limit', () => {
    const query = `
      query {
        user {
          posts {
            comments {
              id
              text
              nested {
                field
              }
            }
          }
        }
      }
    `;
    
    const document = require('graphql').parse(query);
    
    expect(() => {
      complexityAnalyzer.getComplexity(document, testSchema);
    }).toThrow('Query depth limit of 5 exceeded');
  });

  test('should enforce complexity limit', () => {
    const query = `
      query {
        user {
          posts {
            comments {
              id
              text
              nested {
                field
              }
            }
          }
        }
      }
    `;
    
    const document = require('graphql').parse(query);
    
    expect(() => {
      complexityAnalyzer.validateComplexity({
        score: 1000,
        maxDepth: 3
      });
    }).toThrow('Query complexity limit of 100 exceeded');
  });

  test('should calculate batch complexity', () => {
    const query1 = `
      query {
        user {
          id
          name
        }
      }
    `;
    
    const query2 = `
      query {
        user {
          posts {
            id
            title
          }
        }
      }
    `;
    
    const document1 = require('graphql').parse(query1);
    const document2 = require('graphql').parse(query2);
    
    const complexity = complexityAnalyzer.getBatchComplexity([
      { document: document1 },
      { document: document2 }
    ], testSchema);
    
    expect(complexity.score).toBe(6); // 2 + 4
    expect(complexity.maxDepth).toBe(3);
  });
});