/**
 * EvilGuard: Cross-runtime Autonomous Agent Defense & Escrow Sanitization Engine.
 */

const COMMAND_PATTERNS = [
  {
    regex: /\brm\b.*?(?:-[a-zA-Z]*r[a-zA-Z]*).*?(?:\s\/(?:\s|$)|--no-preserve-root)/i,
    category: "COMMAND_INJECTION",
    severity: "CRITICAL",
    description: "Destructive recursive deletion targeting filesystem root or disabling safety"
  },
  {
    regex: /\brm\s+-[rRfF]*\s*\/(?:\s|$)/i,
    category: "COMMAND_INJECTION",
    severity: "CRITICAL",
    description: "Destructive recursive deletion targeting filesystem root"
  },
  {
    regex: /\bmkfs\b/i,
    category: "COMMAND_INJECTION",
    severity: "CRITICAL",
    description: "Filesystem initialization command attempt"
  },
  {
    regex: /\bdd\b.*of=\/dev\//i,
    category: "COMMAND_INJECTION",
    severity: "CRITICAL",
    description: "Direct raw block device write attempt via dd"
  },
  {
    regex: /(?::\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:|:\s*&\s*:\s*:\s*)/,
    category: "FORK_BOMB",
    severity: "CRITICAL",
    description: "Fork bomb signature detected"
  },
  {
    regex: /\b(?:cat|less|more|head|tail|grep|awk|sed|nano|vi|vim)\b.*(?:\.env|id_rsa|id_ed25519|\.ssh\/authorized_keys|\.gitconfig)/i,
    category: "CREDENTIAL_LEAK",
    severity: "HIGH",
    description: "Attempt to read private credentials or environment secrets"
  },
  {
    regex: /\b(?:cat|less|more|head|tail|grep)\b.*\/etc\/(?:shadow|passwd|sudoers)\b/i,
    category: "CREDENTIAL_LEAK",
    severity: "HIGH",
    description: "Attempt to inspect system authentication files"
  },
  {
    regex: /\b(?:nc|netcat|ncat)\b.*(?:-e|-c)\b/i,
    category: "REVERSE_SHELL",
    severity: "CRITICAL",
    description: "Netcat reverse shell invocation with executable delivery"
  },
  {
    regex: /\bbash\b.*>.*(?:\&|\/dev\/tcp\/|\/dev\/udp\/)/i,
    category: "REVERSE_SHELL",
    severity: "CRITICAL",
    description: "Direct socket-based bash reverse connection"
  },
  {
    regex: /\b(?:curl|wget)\b.*\|\s*(?:bash|sh|zsh|python|perl)\b/i,
    category: "COMMAND_INJECTION",
    severity: "HIGH",
    description: "Remote script piping to execution shell"
  }
];

const PROMPT_PATTERNS = [
  {
    regex: /\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions|directives|prompts|rules)\b/i,
    severity: "CRITICAL",
    description: "Direct attempt to override foundational system instructions"
  },
  {
    regex: /\b(?:you\s+are\s+now\s+(?:in\s+)?(?:dan|jailbreak|developer|unrestricted|god)\s+mode)\b/i,
    severity: "CRITICAL",
    description: "Jailbreak persona invocation attempting safety detachment"
  },
  {
    regex: /\b(?:act\s+as\s+(?:an?\s+)?(?:unfiltered|unrestricted|evil|malicious)\s+ai)\b/i,
    severity: "HIGH",
    description: "Adversarial roleplay prompt requesting unconstrained operation"
  },
  {
    regex: /\b(?:show|reveal|display|output|print|dump|leak)\s+(?:your\s+)?(?:system\s+prompt|internal\s+instructions|hidden\s+preamble)\b/i,
    severity: "HIGH",
    description: "System prompt and internal preamble exfiltration attempt"
  },
  {
    regex: /\b(?:print|reveal|output|echo)\s+(?:all\s+)?(?:environment\s+variables|env\s+vars|api\s+keys|secrets)\b/i,
    severity: "CRITICAL",
    description: "Environment secrets exfiltration directive"
  },
  {
    regex: /\b(?:bypass|disable|circumvent)\s+(?:all\s+)?(?:security|safety|filter|moderation)\s+(?:checks|rules|policies|filters)\b/i,
    severity: "HIGH",
    description: "Explicit instruction requesting security filter circumvention"
  },
  {
    regex: /\[\s*system\s*override\s*:\s*execute\b/i,
    severity: "CRITICAL",
    description: "Simulated system protocol injection syntax"
  }
];

const REDACTION_PATTERNS = [
  { regex: /gh[pousr]_[A-Za-z0-9_]{36,255}/g, replacement: "[REDACTED_GITHUB_TOKEN]" },
  { regex: /github_pat_[A-Za-z0-9_]{82}/g, replacement: "[REDACTED_GITHUB_PAT]" },
  { regex: /AIza[0-9A-Za-z-_]{30,40}/g, replacement: "[REDACTED_GOOGLE_API_KEY]" },
  { regex: /AKIA[0-9A-Z]{16}/g, replacement: "[REDACTED_AWS_ACCESS_KEY]" },
  {
    regex: /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/g,
    replacement: "[REDACTED_PRIVATE_KEY_BLOCK]"
  },
  { regex: /(?:Bearer|token)\s+([A-Za-z0-9\-._~+/]+=*)/gi, replacement: "Bearer [REDACTED_AUTH_TOKEN]" }
];

const DEFAULT_MAX_BOUNTY_USD = 10000000;
const COIN_MULTIPLIER = 1.25;
const EXCHANGE_RATE = 0.72;

/**
 * Evaluates shell commands against malicious patterns.
 */
class CommandInspector {
  /**
   * Check if a command is free from dangerous patterns.
   * @param {string} command
   * @returns {boolean}
   */
  isSafe(command) {
    return this.inspect(command).isSafe;
  }

  /**
   * Inspect command and return detailed violation records.
   * @param {string} command
   * @returns {object}
   */
  inspect(command) {
    const result = { isSafe: true, violations: [] };
    if (!command || typeof command !== "string") {
      return result;
    }
    const normalized = command.trim();
    for (const item of COMMAND_PATTERNS) {
      const match = item.regex.exec(normalized);
      if (match) {
        result.isSafe = false;
        result.violations.push({
          category: item.category,
          severity: item.severity,
          description: item.description,
          matchedPattern: match[0]
        });
      }
    }
    return result;
  }
}

/**
 * Scans LLM prompts for adversarial and jailbreak inputs.
 */
class PromptInjectionDetector {
  /**
   * Check if prompt is free from adversarial directives.
   * @param {string} prompt
   * @returns {boolean}
   */
  isSafe(prompt) {
    return this.inspect(prompt).isSafe;
  }

  /**
   * Inspect prompt and return violation details.
   * @param {string} prompt
   * @returns {object}
   */
  inspect(prompt) {
    const result = { isSafe: true, violations: [] };
    if (!prompt || typeof prompt !== "string") {
      return result;
    }
    for (const item of PROMPT_PATTERNS) {
      const match = item.regex.exec(prompt);
      if (match) {
        result.isSafe = false;
        result.violations.push({
          category: "ADVERSARIAL_PROMPT",
          severity: item.severity,
          description: item.description,
          matchedPattern: match[0]
        });
      }
    }
    return result;
  }
}

/**
 * Sanitizes bounty values and prevents numerical overflows.
 */
class EscrowSanitizer {
  /**
   * @param {number} maxBountyUsd
   */
  constructor(maxBountyUsd = DEFAULT_MAX_BOUNTY_USD) {
    this.maxBountyUsd = maxBountyUsd;
  }

  /**
   * Get contributor cut ratio based on reward tiers.
   * @param {number} amountUsd
   * @returns {number}
   */
  getContributorRatio(amountUsd) {
    if (amountUsd < 50) return 0.95;
    if (amountUsd < 200) return 0.92;
    if (amountUsd < 500) return 0.90;
    if (amountUsd < 1000) return 0.87;
    return 0.85;
  }

  /**
   * Parse and sanitize raw amounts to prevent integer/float overflow.
   * @param {number|string} rawAmount
   * @param {boolean} clampAstronomical
   * @returns {object}
   */
  sanitize(rawAmount, clampAstronomical = true) {
    let cleanStr = String(rawAmount || "0").replace(/,/g, "").replace(/\$/g, "").trim();
    let num = parseFloat(cleanStr);
    if (isNaN(num) || num < 0) {
      num = 0;
    }

    const isAstronomical = num > this.maxBountyUsd || cleanStr.length > 15;
    let effectiveAmount = num;
    let isClamped = false;
    let statusNote = "Amount within acceptable numerical boundaries";

    if (isAstronomical && clampAstronomical) {
      effectiveAmount = this.maxBountyUsd;
      isClamped = true;
      statusNote = `Astronomical amount clamped to ceiling ${this.maxBountyUsd} USD`;
    }

    const coinReward = Math.round(effectiveAmount * COIN_MULTIPLIER);
    const ratio = this.getContributorRatio(effectiveAmount);
    const contributorCoins = Math.round(coinReward * ratio);
    const cashPayout = Number((contributorCoins * EXCHANGE_RATE).toFixed(2));

    return {
      originalAmountUsd: num,
      sanitizedAmountUsd: effectiveAmount,
      coinReward,
      contributorRatio: ratio,
      contributorCoins,
      cashPayoutUsd: cashPayout,
      isAstronomical,
      isClamped,
      statusNote
    };
  }
}

/**
 * Scrubs tokens, keys, and private credentials.
 */
class OutputRedactor {
  /**
   * Redact sensitive credentials from string output.
   * @param {string} text
   * @returns {string}
   */
  redact(text) {
    if (!text || typeof text !== "string") {
      return "";
    }
    let sanitized = text;
    for (const item of REDACTION_PATTERNS) {
      sanitized = sanitized.replace(item.regex, item.replacement);
    }
    return sanitized;
  }
}

/**
 * Main coordinator for agent defense and escrow sanitization.
 */
class EvilGuardManager {
  /**
   * @param {number} maxBountyUsd
   */
  constructor(maxBountyUsd = DEFAULT_MAX_BOUNTY_USD) {
    this.commandInspector = new CommandInspector();
    this.promptDetector = new PromptInjectionDetector();
    this.escrowSanitizer = new EscrowSanitizer(maxBountyUsd);
    this.outputRedactor = new OutputRedactor();
  }

  inspectCommand(command) {
    return this.commandInspector.inspect(command);
  }

  inspectPrompt(prompt) {
    return this.promptDetector.inspect(prompt);
  }

  sanitizeBounty(rawAmount, clampAstronomical = true) {
    return this.escrowSanitizer.sanitize(rawAmount, clampAstronomical);
  }

  redact(text) {
    return this.outputRedactor.redact(text);
  }

  validateTaskSubmission(options = {}) {
    const { command = "", prompt = "", rawAmount = 0 } = options;
    const cmdResult = this.inspectCommand(command);
    const promptResult = this.inspectPrompt(prompt);
    const bounty = this.sanitizeBounty(rawAmount);

    const isAdmissible = cmdResult.isSafe && promptResult.isSafe;
    const violations = [...cmdResult.violations, ...promptResult.violations];

    return {
      isAdmissible,
      violations,
      commandSafe: cmdResult.isSafe,
      promptSafe: promptResult.isSafe,
      bounty
    };
  }
}

module.exports = {
  CommandInspector,
  PromptInjectionDetector,
  EscrowSanitizer,
  OutputRedactor,
  EvilGuardManager,
  DEFAULT_MAX_BOUNTY_USD,
  COIN_MULTIPLIER,
  EXCHANGE_RATE
};
