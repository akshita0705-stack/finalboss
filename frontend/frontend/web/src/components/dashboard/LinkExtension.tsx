import { useState } from 'react'
import { Link2 } from 'lucide-react'
import { ApiError, keysApi, type ApiKeyInfo } from '@/services/api'
import { GlowButton } from '@/components/ui/GlowButton'
import { HauntedCard } from '@/components/ui/HauntedCard'

async function copy(text: string) {
  try { await navigator.clipboard.writeText(text) } catch { /* clipboard unavailable: user can select the text */ }
}

/** Creates an extension key tied to this account. The raw key is shown once and never stored in the page. */
export function LinkExtension({ onLinked }: { onLinked: () => void }) {
  const [created, setCreated] = useState<ApiKeyInfo | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function generate() {
    setBusy(true); setError(null)
    try {
      setCreated(await keysApi.create(crypto.randomUUID()))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not create a key.')
    } finally { setBusy(false) }
  }

  return (
    <HauntedCard aria-labelledby="link-h">
      <h2 id="link-h" className="mb-2 flex items-center gap-2 font-tech text-lg text-moon"><Link2 size={18} aria-hidden /> Link your extension</h2>
      {!created ? (
        <>
          <p className="mb-4 text-sm text-fog">
            No extension is linked to this account yet, so there is nothing to show. Generate a key, then paste it into
            the extension&apos;s settings. Only data from extensions linked to your account appears here.
          </p>
          {error && <p role="alert" className="mb-3 text-sm text-[#FF6B86]">{error}</p>}
          <GlowButton onClick={generate} disabled={busy}>{busy ? 'Creating…' : 'Generate extension key'}</GlowButton>
        </>
      ) : (
        <div className="flex flex-col gap-3 text-sm">
          <p className="text-[#FF9A4D]">Copy this key now. It is shown only once.</p>
          <div>
            <p className="text-fog">Extension key</p>
            <code className="block break-all rounded-lg border border-ghost bg-void px-3 py-2 text-moon">{created.api_key}</code>
            <button className="mt-1 text-xs text-pumpkin hover:underline" onClick={() => copy(created.api_key ?? '')}>Copy key</button>
          </div>
          <div>
            <p className="text-fog">Installation ID</p>
            <code className="block break-all rounded-lg border border-ghost bg-void px-3 py-2 text-moon">{created.installation_id}</code>
            <button className="mt-1 text-xs text-pumpkin hover:underline" onClick={() => copy(created.installation_id)}>Copy ID</button>
          </div>
          <GlowButton variant="outline" onClick={onLinked}>I&apos;ve saved it, refresh</GlowButton>
        </div>
      )}
    </HauntedCard>
  )
}
