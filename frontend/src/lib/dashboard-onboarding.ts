const STORAGE_PREFIX = "cogito-dashboard-onboarding-dismissed"

export function onboardingDismissKey(userId: string): string {
  return `${STORAGE_PREFIX}:${userId}`
}

export function isOnboardingDismissed(userId: string): boolean {
  try {
    return localStorage.getItem(onboardingDismissKey(userId)) === "1"
  } catch {
    return false
  }
}

export function dismissOnboarding(userId: string): void {
  try {
    localStorage.setItem(onboardingDismissKey(userId), "1")
  } catch {
    // Ignore storage failures.
  }
}

export function resetOnboardingDismiss(userId: string): void {
  try {
    localStorage.removeItem(onboardingDismissKey(userId))
  } catch {
    // Ignore storage failures.
  }
}
