import { useEffect, useRef, useState } from 'react'

const TOTAL_FRAMES = 192
const FRAME_DIR = '/scrolleffect2'

// Preload all frames
function getFrameUrl(i) {
  return `${FRAME_DIR}/frame_${String(i).padStart(6, '0')}.webp`
}

export default function ScrollHero({ children }) {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const imagesRef = useRef([])
  const [loaded, setLoaded] = useState(false)
  const [loadProgress, setLoadProgress] = useState(0)
  const currentFrameRef = useRef(0)

  useEffect(() => {
    const images = []
    let loadedCount = 0

    for (let i = 1; i <= TOTAL_FRAMES; i++) {
      const img = new Image()
      img.src = getFrameUrl(i)
      img.onload = () => {
        loadedCount++
        setLoadProgress(Math.round((loadedCount / TOTAL_FRAMES) * 100))
        if (loadedCount === TOTAL_FRAMES) {
          setLoaded(true)
          drawFrame(0)
        }
      }
      images.push(img)
    }
    imagesRef.current = images

    function drawFrame(index) {
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      const img = imagesRef.current[index]
      if (!img || !img.complete) return
      canvas.width = img.naturalWidth || 1456
      canvas.height = img.naturalHeight || 816
      ctx.drawImage(img, 0, 0)
    }

    const handleScroll = () => {
      const container = containerRef.current
      if (!container) return
      const scrollTop = window.scrollY
      const maxScroll = container.scrollHeight - window.innerHeight
      const progress = Math.min(scrollTop / (maxScroll * 0.5), 1)
      const frameIndex = Math.min(
        Math.floor(progress * (TOTAL_FRAMES - 1)),
        TOTAL_FRAMES - 1
      )
      if (frameIndex !== currentFrameRef.current) {
        currentFrameRef.current = frameIndex
        drawFrame(frameIndex)
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      {/* Sticky scroll canvas */}
      <div style={{
        position: 'sticky',
        top: 0,
        width: '100%',
        height: '100vh',
        overflow: 'hidden',
        zIndex: 0,
      }}>
        {!loaded && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            background: '#050a12',
            color: '#38bdf8',
            fontSize: '1.1rem',
            gap: '1rem',
            zIndex: 10,
          }}>
            <div style={{ fontSize: '2rem', fontWeight: 700 }}>Initializing Quantum Visualization</div>
            <div style={{ width: '300px', height: '4px', background: '#1e293b', borderRadius: '2px' }}>
              <div style={{ width: `${loadProgress}%`, height: '100%', background: 'linear-gradient(90deg, #38bdf8, #818cf8)', borderRadius: '2px', transition: 'width 0.1s' }} />
            </div>
            <div style={{ color: '#64748b' }}>{loadProgress}% loaded</div>
          </div>
        )}
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
        {/* Gradient overlay to blend into page */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(to bottom, transparent 60%, #0f172a 100%)',
          pointerEvents: 'none',
        }} />
      </div>

      {/* Scrollable content layered over canvas */}
      <div style={{ position: 'relative', zIndex: 1, marginTop: '-100vh' }}>
        {children}
      </div>
    </div>
  )
}
