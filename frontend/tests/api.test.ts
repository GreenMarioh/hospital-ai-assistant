import { beforeEach, describe, expect, it } from "vitest";
import { ApiError, clearTokens, errorMessage, getRefreshToken, setTokens, unwrap } from "@/lib/api";

describe("api helpers", () => {
  beforeEach(() => clearTokens());

  it("extracts readable error messages", () => {
    expect(errorMessage({ detail: "Nope" })).toBe("Nope");
    expect(errorMessage({ detail: [{ msg: "field required" }, { msg: "too short" }] })).toBe(
      "field required; too short",
    );
    expect(errorMessage(undefined)).toBe("Something went wrong");
    expect(errorMessage("plain")).toBe("plain");
  });

  it("unwrap returns data or throws ApiError", () => {
    expect(unwrap({ data: { a: 1 }, response: new Response() })).toEqual({ a: 1 });
    try {
      unwrap({ error: { detail: "Locked" }, response: new Response(null, { status: 423 }) });
      throw new Error("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(423);
      expect((e as ApiError).message).toBe("Locked");
    }
  });

  it("keeps the refresh token in sessionStorage only and clears it on logout", () => {
    setTokens({ access_token: "a", refresh_token: "r" });
    expect(getRefreshToken()).toBe("r");
    expect(window.localStorage.getItem("hospital.refresh")).toBeNull();
    clearTokens();
    expect(getRefreshToken()).toBeNull();
  });
});
