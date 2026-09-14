function nextAction(state) {
  if (state === 'verification_pending') {
    state = 'payment_pending';
    competitionState = 'exclusive_claim';
  }
  return state;
}

function competitionState(state) {
  if (state === 'exclusive_claim') {
    state = 'payment_pending';
  }
  return state;
}