export function authorizeGraphQLField(user: any, requiredRole: string = 'USER'): boolean {
  if (!user || !user.id) {
    throw new Error('GraphQL IDOR Security Block: Unauthenticated nested field query (Issue #278).');
  }

  if (requiredRole === 'ADMIN' && user.role !== 'ADMIN') {
    throw new Error('GraphQL IDOR Security Block: Unauthorized admin field query.');
  }

  return true;
}
