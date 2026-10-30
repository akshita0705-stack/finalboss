/**
 * Returns the normalised hostname for http(s) URLs only, otherwise null.
 * `new URL().hostname` is already punycode-encoded for IDNs. The path, query and fragment are discarded here
 * and never leave this function.
 */
export function hostFromUrl(url: string): string | null {
  let u: URL
  try { u = new URL(url) } catch { return null }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return null
  const h = u.hostname.toLowerCase().replace(/\.$/, '')
  return h || null
}

export function isExcluded(host: string, excluded: string[]): boolean {
  return excluded.some((e) => host === e || host.endsWith(`.${e}`))
}

export function parseExcluded(text: string): string[] {
  return [...new Set(text.split(/[\s,]+/).map((s) => s.trim().toLowerCase().replace(/^\*\./, '')).filter(Boolean))]
}
