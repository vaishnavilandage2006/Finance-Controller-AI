import { beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom polyfills required by recharts / browsers not present in jsdom.
// ResizeObserver is used by ResponsiveContainer; matchMedia by some layout
// helpers. Both are stubbed as no-ops that never crash.

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof globalThis.ResizeObserver === "undefined") {
  (globalThis as any).ResizeObserver = ResizeObserverStub;
}

if (typeof window.matchMedia === "undefined") {
  (window as any).matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

// Unmount rendered trees between tests (required when vitest globals are
// disabled, otherwise testing-library's auto-cleanup never registers).
afterEach(() => {
  cleanup();
});

// Ensure a clean storage surface between tests.
beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});