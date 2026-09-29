import { describe, expect, it } from "vitest";
import { escapeHighlight } from "@/lib/text";

describe("escapeHighlight", () => {
  it("keeps only the highlight tags", () => {
    expect(escapeHighlight("severe <b>migraine</b> with aura")).toBe(
      "severe <mark>migraine</mark> with aura",
    );
  });
  it("neutralises any other markup from record text", () => {
    const out = escapeHighlight('<img src=x onerror="alert(1)"><script>x</script> <b>hit</b>');
    expect(out).not.toContain("<img");
    expect(out).not.toContain("<script");
    expect(out).toContain("&lt;img");
    expect(out).toContain("<mark>hit</mark>");
  });
  it("escapes ampersands", () => {
    expect(escapeHighlight("a & b")).toBe("a &amp; b");
  });
});
