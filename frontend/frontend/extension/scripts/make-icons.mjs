// Generates simple pumpkin PNG icons with no dependencies (RGBA raster + zlib).
import { deflateSync, crc32 } from 'node:zlib'
import { mkdirSync, writeFileSync } from 'node:fs'

const chunk = (type, data) => {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length)
  const body = Buffer.concat([Buffer.from(type), data])
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body))
  return Buffer.concat([len, body, crc])
}

const inTri = (px, py, [ax, ay], [bx, by], [cx, cy]) => {
  const d = (x1, y1, x2, y2, x3, y3) => (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)
  const d1 = d(px, py, ax, ay, bx, by), d2 = d(px, py, bx, by, cx, cy), d3 = d(px, py, cx, cy, ax, ay)
  return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0))
}

// Returns [r,g,b,a] for a normalised point.
function shade(x, y) {
  if (x > 0.46 && x < 0.55 && y > 0.06 && y < 0.2) return [57, 255, 136, 255] // stem
  const body = ((x - 0.5) / 0.47) ** 2 + ((y - 0.58) / 0.38) ** 2 < 1
  if (!body) return [0, 0, 0, 0]
  if (inTri(x, y, [0.2, 0.58], [0.33, 0.4], [0.45, 0.58]) || inTri(x, y, [0.55, 0.58], [0.67, 0.4], [0.8, 0.58])) return [7, 6, 11, 255]
  if (((x - 0.5) / 0.24) ** 2 + ((y - 0.75) / 0.08) ** 2 < 1) return [7, 6, 11, 255]
  return [255, 122, 26, 255]
}

function png(size) {
  const SS = 3, raw = Buffer.alloc(size * (size * 4 + 1))
  for (let y = 0; y < size; y++) {
    raw[y * (size * 4 + 1)] = 0
    for (let x = 0; x < size; x++) {
      let r = 0, g = 0, b = 0, a = 0
      for (let sy = 0; sy < SS; sy++) for (let sx = 0; sx < SS; sx++) {
        const [pr, pg, pb, pa] = shade((x + (sx + 0.5) / SS) / size, (y + (sy + 0.5) / SS) / size)
        r += pr * pa; g += pg * pa; b += pb * pa; a += pa
      }
      const o = y * (size * 4 + 1) + 1 + x * 4, n = SS * SS
      raw[o] = a ? r / a : 0; raw[o + 1] = a ? g / a : 0; raw[o + 2] = a ? b / a : 0; raw[o + 3] = a / n
    }
  }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4); ihdr[8] = 8; ihdr[9] = 6
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(raw)), chunk('IEND', Buffer.alloc(0))])
}

mkdirSync('public/icons', { recursive: true })
for (const s of [16, 48, 128]) writeFileSync(`public/icons/icon${s}.png`, png(s))
console.log('icons written')
