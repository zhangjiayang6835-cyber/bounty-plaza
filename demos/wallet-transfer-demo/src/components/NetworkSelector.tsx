import { useEffect, useRef, useState } from "react";
import type { Network } from "@asctp/parabola";

const NETWORKS: { value: Network; label: string }[] = [
  { value: "mainnet", label: "Mainnet" },
  { value: "testnet", label: "Testnet" },
];

interface Props {
  network: Network;
  onChange: (network: Network) => void;
  disabled: boolean;
}

/**
 * The network picker, in the top-right of the header the way a block explorer carries it.
 * Mainnet is spelled out on the button and tints it red, since picking it means every
 * transfer moves real USDC. Switching is blocked mid-transfer (disabled) and disconnects
 * wallets in the parent, because a connected Arc signer is bound to one chain.
 */
export function NetworkSelector({ network, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Closing on an outside click or Escape is what makes this read as the explorer network
  // picker it copies rather than a popover that traps you until you choose something.
  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  // A transfer in flight locks the selector, and a menu left open across a lock would offer a
  // choice the handler is about to refuse.
  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  const isMainnet = network === "mainnet";

  return (
    <div className="network-select" ref={containerRef}>
      <button
        ref={buttonRef}
        type="button"
        className={`network-select-button${isMainnet ? " mainnet" : ""}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Network: ${isMainnet ? "Mainnet" : "Testnet"}`}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{isMainnet ? "Mainnet" : "Testnet"}</span>
        <svg
          className="network-select-chevron"
          viewBox="0 0 16 16"
          width="12"
          height="12"
          aria-hidden="true"
        >
          <path
            d="M4 6L8 10L12 6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {open && (
        <div className="network-select-menu" role="menu" aria-label="Network">
          {NETWORKS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="menuitemradio"
              aria-checked={option.value === network}
              className="network-select-option"
              onClick={() => {
                setOpen(false);
                onChange(option.value);
              }}
            >
              <span>{option.label}</span>
              <svg
                className="network-select-check"
                viewBox="0 0 16 16"
                width="12"
                height="12"
                aria-hidden="true"
              >
                <path
                  d="M3 8.5L6.5 12L13 4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
