// ---- Backoff Strategies ----

export interface BackoffOptions {
  baseDelay: number;
  maxDelay?: number;
}

export type BackoffStrategy =
  | { type: "fixed" }
  | { type: "linear"; increment?: number }
  | { type: "exponential"; factor?: number }
  | ((attempt: number, options: BackoffOptions) => number);

// ---- Error Types ----

export class RetryError extends Error {
  readonly attempts: number;
  readonly lastError: unknown;
  readonly errors: unknown[];

  constructor(
    message: string,
    options: { attempts: number; lastError: unknown; errors: unknown[] },
  ) {
    super(message, { cause: options.lastError });
    this.name = "RetryError";
    this.attempts = options.attempts;
    this.lastError = options.lastError;
    this.errors = options.errors;
  }
}

// ---- Options ----

export interface RetryOptions {
  /** Maximum number of retry attempts (not counting the initial call). Default: 3 */
  maxRetries?: number;
  /** Backoff strategy configuration. Default: { type: "exponential", factor: 2 } */
  backoff?: BackoffStrategy;
  /** Base delay in ms for built-in strategies. Default: 1000 */
  baseDelay?: number;
  /** Maximum delay cap in ms. Default: 30000 */
  maxDelay?: number;
  /** AbortSignal to cancel retries */
  signal?: AbortSignal;
  /** Predicate to decide whether to retry on a given error. Return false to bail early. */
  retryIf?: (error: unknown, attempt: number) => boolean;
  /** Called before each retry attempt */
  onRetry?: (error: unknown, attempt: number, delay: number) => void;
}

// ---- Internal helpers ----

function computeDelay(
  strategy: BackoffStrategy,
  attempt: number,
  backoffOptions: BackoffOptions,
): number {
  if (typeof strategy === "function") {
    return strategy(attempt, backoffOptions);
  }

  const { baseDelay, maxDelay } = backoffOptions;
  let delay: number;

  switch (strategy.type) {
    case "fixed":
      delay = baseDelay;
      break;
    case "linear":
      delay = baseDelay + (strategy.increment ?? baseDelay) * attempt;
      break;
    case "exponential":
      delay = baseDelay * (strategy.factor ?? 2) ** attempt;
      break;
    default: {
      const _exhaustive: never = strategy;
      throw new Error(`Unknown backoff strategy: ${JSON.stringify(_exhaustive)}`);
    }
  }

  return maxDelay !== undefined ? Math.min(delay, maxDelay) : delay;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason ?? new DOMException("The operation was aborted.", "AbortError"));
      return;
    }

    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);

    function onAbort() {
      clearTimeout(timer);
      reject(signal!.reason ?? new DOMException("The operation was aborted.", "AbortError"));
    }

    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

// ---- Main function ----

export async function retry<T>(
  fn: (attempt: number) => Promise<T>,
  options?: RetryOptions,
): Promise<T> {
  const {
    maxRetries = 3,
    backoff = { type: "exponential" as const, factor: 2 },
    baseDelay = 1000,
    maxDelay = 30_000,
    signal,
    retryIf,
    onRetry,
  } = options ?? {};

  const backoffOptions: BackoffOptions = { baseDelay, maxDelay };
  const errors: unknown[] = [];

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    if (signal?.aborted) {
      throw signal.reason ?? new DOMException("The operation was aborted.", "AbortError");
    }

    try {
      return await fn(attempt);
    } catch (error) {
      errors.push(error);

      const isLastAttempt = attempt === maxRetries;
      if (isLastAttempt) {
        break;
      }

      if (retryIf && !retryIf(error, attempt)) {
        break;
      }

      const delay = computeDelay(backoff, attempt, backoffOptions);
      onRetry?.(error, attempt + 1, delay);

      await sleep(delay, signal);
    }
  }

  const lastError = errors[errors.length - 1];
  throw new RetryError(
    `Retry failed after ${errors.length} attempt(s)`,
    { attempts: errors.length, lastError, errors },
  );
}
