// utils/claimNextActionMapper.ts
import { ClaimStatus, ClaimType } from '@/types/claim';

interface NextAction {
  label: string;
  action: 'review' | 'approve' | 'reject' | 'appeal' | 'complete' | null;
  condition: (claim: Claim) => boolean;
}

export interface Claim {
  id: string;
  status: ClaimStatus;
  type: ClaimType;
  reviewer?: string;
  reviewerDecision?: 'approved' | 'rejected';
  appealDeadline?: Date;
}

const isWithinAppealPeriod = (claim: Claim): boolean => {
  if (!claim.appealDeadline) return false;
  return new Date() < new Date(claim.appealDeadline);
};

export const getNextAction = (claim: Claim): NextAction | null => {
  const actions: NextAction[] = [
    {
      label: 'Review Claim',
      action: 'review',
      condition: (c) => c.status === 'submitted' && !c.reviewer,
    },
    {
      label: 'Approve Claim',
      action: 'approve',
      condition: (c) => c.status === 'in_review' && !c.reviewerDecision,
    },
    {
      label: 'Reject Claim',
      action: 'reject',
      condition: (c) => c.status === 'in_review' && !c.reviewerDecision,
    },
    {
      label: 'Appeal Decision',
      action: 'appeal',
      condition: (c) => 
        (c.status === 'rejected' || c.status === 'approved') && 
        isWithinAppealPeriod(claim),
    },
    {
      label: 'Complete Claim',
      action: 'complete',
      condition: (c) => c.status === 'approved' && !c.reviewerDecision,
    },
  ];

  const matchedAction = actions.find((action) => action.condition(claim));
  return matchedAction || null;
};

// Unit tests (Jest)
/*
describe('getNextAction', () => {
  it('returns review action for submitted claim without reviewer', () => {
    const claim = { id: '1', status: 'submitted', type: 'bug' };
    expect(getNextAction(claim)?.action).toBe('review');
  });

  it('returns null for completed claim', () => {
    const claim = { id: '2', status: 'completed', type: 'bug' };
    expect(getNextAction(claim)).toBeNull();
  });
});
*/