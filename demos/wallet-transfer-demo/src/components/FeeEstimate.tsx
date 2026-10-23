import { useEffect } from "react";
import type { ChainId, TransferSpeed, Network, FeeEstimate as FeeEstimateType } from "@asctp/parabola";

interface Props {
  from: ChainId;
  to: ChainId;
  amount: string;
  speed: TransferSpeed;
  network: Network;
  feeEstimate: FeeEstimateType | null;
  estimating: boolean;
  onEstimate: (params: { from: ChainId; to: ChainId; amount: string; speed: TransferSpeed; network: Network }) => void;
}

const DEBOUNCE_MS = 400;

export function FeeEstimate({ from, to, amount, speed, network, feeEstimate, estimating, onEstimate }: Props) {
  useEffect(() => {
    if (!(Number(amount) > 0)) return;
    const timer = setTimeout(() => onEstimate({ from, to, amount, speed, network }), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [from, to, amount, speed, network, onEstimate]);

  if (!(Number(amount) > 0)) return null;

  return (
    <div className="fee-estimate">
      {estimating && <span className="hint">Estimating fee...</span>}
      {!estimating && feeEstimate && (
        <>
          <span>
            Protocol fee: <strong>{feeEstimate.protocolFee} USDC</strong>
          </span>
          <span>
            Mode: <strong>{feeEstimate.transferMode}</strong>
          </span>
          <span>
            Est. duration: <strong>~{feeEstimate.estimatedDurationSeconds}s</strong>
          </span>
        </>
      )}
    </div>
  );
}
