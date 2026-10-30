import { StarField } from './StarField'
import { BatLayer } from './BatLayer'
import { FogLayer } from './FogLayer'
import { Embers } from './Embers'
import { LightningFlash } from './LightningFlash'

type Variant = 'hero' | 'dashboard'

/** Fixed, non-interactive background stack. `dashboard` is dimmer so data stays readable. */
export function Atmosphere({ variant = 'dashboard' }: { variant?: Variant }) {
  const hero = variant === 'hero'
  return (
    <>
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
        <div className="absolute inset-0" style={{
          background: hero
            ? 'linear-gradient(to bottom, #07060B 0%, #0D1117 35%, #1E4D4F 78%, #0D1117 100%)'
            : 'linear-gradient(to bottom, #07060B 0%, #0D1117 60%, #101c20 100%)',
        }} />
        <StarField count={hero ? 90 : 50} />
        <div className={hero ? '' : 'opacity-60'}><BatLayer count={hero ? 7 : 5} /></div>
        <Embers count={hero ? 22 : 10} />
        <FogLayer />
      </div>
      <LightningFlash ambient={!hero} />
    </>
  )
}
