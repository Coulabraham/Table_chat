import { afterEach, describe, expect, it, vi } from "vitest";

import { createClientId } from "./clientId";

describe("createClientId", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the browser UUID implementation when available", () => {
    const randomUUID = vi.fn(() => "123e4567-e89b-42d3-a456-426614174000");
    vi.stubGlobal("crypto", { randomUUID });

    expect(createClientId()).toBe("123e4567-e89b-42d3-a456-426614174000");
    expect(randomUUID).toHaveBeenCalledOnce();
  });

  it("creates a valid UUID when randomUUID is unavailable", () => {
    vi.stubGlobal("crypto", {
      getRandomValues: (bytes: Uint8Array) => bytes.fill(0),
    });

    expect(createClientId()).toBe("00000000-0000-4000-8000-000000000000");
  });
});
