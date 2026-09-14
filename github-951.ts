// src/lib/claimMapper.ts
type ClaimStatus = 'pending' | 'approved' | 'rejected' | 'completed';
type NextAction = 'submit_pr' | 'review_pr' | 'merge_pr' | 'none';

interface BountyClaim {
  id: string;
  issueId: number;
  claimant: string;
  status: ClaimStatus;
  submittedAt?: Date;
  reviewedAt?: Date;
  mergedAt?: Date;
}

/**
 * Maps a bounty claim to its appropriate next action based on current status and timestamps.
 * Fixes issue #951: incorrect mapping for approved claims that haven't had PRs submitted yet.
 */
export function mapClaimToNextAction(claim: BountyClaim): NextAction {
  switch (claim.status) {
    case 'pending':
      return 'none';
    case 'approved':
      // Before fix: incorrectly returned 'submit_pr' even when PR already submitted
      // After fix: check if PR was submitted (submittedAt exists)
      if (!claim.submittedAt) {
        return 'submit_pr';
      }
      if (!claim.reviewedAt) {
        return 'review_pr';
      }
      if (!claim.mergedAt) {
        return 'merge_pr';
      }
      return 'none';
    case 'rejected':
      return 'none';
    case 'completed':
      return 'none';
    default:
      return 'none';
  }
}

// Example usage in a component or service
export function getNextActionForClaim(claimId: string): NextAction {
  // In real implementation, fetch claim from DB/API
  const claim: BountyClaim = {
    id: claimId,
    issueId: 951,
    claimant: 'user123',
    status: 'approved',
    submittedAt: new Date(),
    reviewedAt: undefined,
    mergedAt: undefined,
  };
  return mapClaimToNextAction(claim);
}