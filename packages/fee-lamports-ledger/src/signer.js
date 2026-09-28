export function lamportsToMicroCeil(lamports, solUsdCeilingPrice = 400.0) {
  if (lamports <= 0) return 0;
  return Math.ceil((lamports * solUsdCeilingPrice) / 1000);
}
