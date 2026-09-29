/** Postgres ts_headline wraps matches in <b>…</b>; escape everything else so record text can never inject markup. */
export function escapeHighlight(s: string): string {
  const esc = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return esc.replace(/&lt;b&gt;/g, "<mark>").replace(/&lt;\/b&gt;/g, "</mark>");
}
