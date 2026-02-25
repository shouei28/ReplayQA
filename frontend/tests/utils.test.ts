/**
 * Tests for utility functions (lib/utils.ts).
 */
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("joins multiple class names", () => {
    expect(cn("foo", "bar", "baz")).toBe("foo bar baz");
  });

  it("filters out undefined values", () => {
    expect(cn("foo", undefined, "bar")).toBe("foo bar");
  });

  it("filters out null values", () => {
    expect(cn("foo", null, "bar")).toBe("foo bar");
  });

  it("filters out false values", () => {
    expect(cn("foo", false, "bar")).toBe("foo bar");
  });

  it("filters out empty strings", () => {
    expect(cn("foo", "", "bar")).toBe("foo bar");
  });

  it("returns empty string when all inputs are falsy", () => {
    expect(cn(undefined, null, false, "")).toBe("");
  });

  it("handles single class name", () => {
    expect(cn("only")).toBe("only");
  });

  it("handles no arguments", () => {
    expect(cn()).toBe("");
  });
});
