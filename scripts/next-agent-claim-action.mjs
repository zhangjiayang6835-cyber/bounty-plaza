export function getNextAction(claim) {
  switch (claim.state) {
    case 'submitted':
      return 'review';
    case 'under_review':
      return 'approve_or_reject';
    case 'approved':
      return 'pay';
    case 'rejected':
      return 'revise';
    case 'completed':
      return 'none';
    default:
      return 'unknown';
  }
}
