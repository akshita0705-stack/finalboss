const layers = [
  { h: '34vh', dur: '70s', op: 0.22, bottom: 0 },
  { h: '26vh', dur: '45s', op: 0.28, bottom: '-2vh' },
  { h: '18vh', dur: '30s', op: 0.2, bottom: '-4vh' },
]

const MASK = 'linear-gradient(to top, black, transparent)'

/** Three translucent fog bands scrolling at different speeds. Each is 200% wide and slides by 50% to loop seamlessly. */
export function FogLayer() {
  return (
    <div className="atmos absolute inset-x-0 bottom-0 h-[40vh] overflow-hidden" aria-hidden>
      {layers.map((l, i) => (
        <div key={i} className="absolute left-0 w-[200%] animate-fog-drift will-change-transform"
          style={{
            height: l.h, bottom: l.bottom, animationDuration: l.dur, opacity: l.op,
            animationDirection: i % 2 ? 'reverse' : 'normal',
            background: 'repeating-linear-gradient(90deg, transparent 0, rgba(154,163,178,.9) 12%, transparent 25%), linear-gradient(to top, rgba(154,163,178,.7), transparent)',
            maskImage: MASK, WebkitMaskImage: MASK,
          }} />
      ))}
    </div>
  )
}
