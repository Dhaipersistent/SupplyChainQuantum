import ScrollHero from '../components/ScrollHero'

export default function Hero() {
  return (
    <div>
      <ScrollHero>
        {/* 100vh spacer so the canvas plays during scroll */}
        <div style={{ height: '200vh' }} />
      </ScrollHero>

      {/* Hero text overlay — absolutely positioned over the canvas */}
      <div style={{
        position: 'relative',
        marginTop: '-200vh',
        height: '200vh',
        pointerEvents: 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        zIndex: 2,
      }}>
        {/* First screen: Title */}
        <div style={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '2rem',
        }}>
          <div style={{
            fontSize: '0.9rem',
            letterSpacing: '0.25em',
            textTransform: 'uppercase',
            color: '#38bdf8',
            marginBottom: '1.5rem',
            fontWeight: 600,
          }}>
            Persistent Systems Semicolons 2026
          </div>
          <h1 style={{
            fontSize: 'clamp(2.5rem, 7vw, 6rem)',
            fontWeight: 900,
            margin: 0,
            lineHeight: 1.1,
            background: 'linear-gradient(135deg, #ffffff 40%, #38bdf8 70%, #818cf8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            Quantum-Ready<br />Supply Chain
          </h1>
        </div>

        {/* Second screen: Scroll cue */}
        <div style={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'flex-end',
          paddingBottom: '5rem',
        }}>
          <div style={{ color: '#475569', textAlign: 'center' }}>
            <div style={{ fontSize: '0.875rem', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>SCROLL TO EXPLORE</div>
            <div style={{ fontSize: '1.5rem', animation: 'bounce 1.5s infinite' }}>↓</div>
          </div>
        </div>
      </div>

      {/* Team Section — below canvas animation */}
      <div style={{
        background: '#0f172a',
        position: 'relative',
        zIndex: 10,
        padding: '6rem 2rem',
        textAlign: 'center',
      }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <div style={{
            fontSize: '0.875rem',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            color: '#38bdf8',
            marginBottom: '1rem',
          }}>The Team</div>
          <h2 style={{
            fontSize: '2.5rem',
            fontWeight: 800,
            color: '#f8fafc',
            margin: '0 0 1rem',
          }}>The Team</h2>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '0.5rem',
            maxWidth: '600px',
            margin: '0 auto 3rem',
          }}>
            {['Hari Krishnan', 'Rinku', 'Aastha', 'Rishika', 'Mrutyunjaya', 'Jatin', 'Kirti Salunkhe'].map(name => (
              <span key={name} style={{
                padding: '0.3rem 0.9rem',
                borderRadius: '999px',
                background: 'rgba(56,189,248,0.08)',
                border: '1px solid rgba(56,189,248,0.2)',
                color: '#94a3b8',
                fontSize: '0.9rem',
              }}>{name}</span>
            ))}
          </div>
          <div style={{
            borderRadius: '20px',
            overflow: 'hidden',
            border: '1px solid rgba(56, 189, 248, 0.15)',
            boxShadow: '0 0 80px rgba(56, 189, 248, 0.08)',
          }}>
            <img
              src="/group-photo.jpeg"
              alt="Team Semicolons at the IBM Quantum Hackathon"
              style={{ width: '100%', display: 'block', objectFit: 'cover' }}
            />
          </div>
          <p style={{ color: '#334155', marginTop: '1rem', fontSize: '0.875rem' }}>
            Persistent Systems Semicolons 2026
          </p>
        </div>
      </div>
    </div>
  )
}
