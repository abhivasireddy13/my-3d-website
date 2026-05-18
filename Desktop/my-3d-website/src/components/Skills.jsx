import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import Matter from 'matter-js'

const TECHS = [
  'Python', 'PyTorch', 'TensorFlow', 'LangChain', 'LangGraph',
  'HuggingFace', 'OpenAI API', 'FastAPI', 'Docker', 'Kubernetes',
  'MLflow', 'FAISS', 'LlamaIndex', 'Airflow', 'Pinecone',
  'PostgreSQL', 'AWS Bedrock', 'Azure OpenAI', 'GCP Vertex AI',
]

const STACK_GROUPS = [
  { label: 'Languages',       items: ['Python', 'SQL', 'C++', 'Bash/Shell'] },
  { label: 'ML / DL',         items: ['PyTorch', 'TensorFlow', 'Keras', 'Scikit-learn', 'XGBoost', 'OpenCV'] },
  { label: 'LLMs & GenAI',    items: ['LangChain', 'LangGraph', 'LlamaIndex', 'OpenAI API', 'Anthropic API', 'Groq', 'vLLM', 'Ollama'] },
  { label: 'Vector DBs',      items: ['FAISS', 'Pinecone', 'Weaviate', 'ChromaDB', 'pgvector'] },
  { label: 'MLOps / LLMOps',  items: ['MLflow', 'W&B', 'Evidently AI', 'RAGAS', 'LangSmith', 'Prometheus', 'DVC', 'BentoML'] },
  { label: 'Cloud',           items: ['Azure OpenAI', 'AWS Bedrock', 'AWS SageMaker', 'GCP Vertex AI', 'BigQuery', 'HF Hub'] },
  { label: 'Infra & DevOps',  items: ['Docker', 'Kubernetes', 'FastAPI', 'Flask', 'Streamlit', 'GitHub Actions', 'Linux'] },
  { label: 'Data Engineering',items: ['Airflow', 'Spark', 'Kafka', 'PostgreSQL', 'MongoDB', 'Snowflake', 'Pandas', 'NumPy'] },
]

export default function Skills() {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const { Engine, Bodies, Composite, Runner, Body, Events } = Matter

    let W = container.clientWidth
    let H = container.clientHeight
    const canvas = canvasRef.current
    canvas.width = W
    canvas.height = H

    const engine = Engine.create({ gravity: { x: 0, y: 1.8 } })
    const runner = Runner.create()

    const makeWalls = (w, h) => [
      Bodies.rectangle(w / 2, h + 50, w + 200, 100, { isStatic: true, friction: 0.5, label: 'ground' }),
      Bodies.rectangle(-50, h / 2, 100, h * 3, { isStatic: true, label: 'wallL' }),
      Bodies.rectangle(w + 50, h / 2, 100, h * 3, { isStatic: true, label: 'wallR' }),
    ]

    const walls = makeWalls(W, H)
    Composite.add(engine.world, walls)

    const getRadius = (name) => {
      const base = 38
      const extra = Math.min(name.length * 3.5, 30)
      return base + extra
    }

    const balls = TECHS.map((tech, i) => {
      const r = getRadius(tech)
      return Bodies.circle(
        r + Math.random() * (W - r * 2),
        -100 - i * 85,
        r,
        {
          restitution: 0.45,
          friction: 0.08,
          frictionAir: 0.012,
          label: tech,
          render: { fillStyle: '#fff' },
        }
      )
    })
    Composite.add(engine.world, balls)

    Runner.run(runner, engine)

    // Mouse repulsion
    let mx = -9999
    let my = -9999
    const onMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect()
      mx = e.clientX - rect.left
      my = e.clientY - rect.top
      balls.forEach(ball => {
        const dx = ball.position.x - mx
        const dy = ball.position.y - my
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 110 && dist > 1) {
          const f = 0.0035 * (1 - dist / 110)
          Body.applyForce(ball, ball.position, { x: (dx / dist) * f, y: (dy / dist) * f })
        }
      })
    }
    const onMouseLeave = () => { mx = -9999; my = -9999 }
    canvas.addEventListener('mousemove', onMouseMove)
    canvas.addEventListener('mouseleave', onMouseLeave)

    // Draw loop
    const ctx = canvas.getContext('2d')
    let animId

    const draw = () => {
      ctx.clearRect(0, 0, W, H)
      const allBodies = Composite.allBodies(engine.world)

      allBodies.forEach(body => {
        if (body.isStatic) return
        const { x, y } = body.position
        const r = body.circleRadius || 40

        // Determine if mouse is near
        const dx = x - mx
        const dy = y - my
        const nearMouse = Math.sqrt(dx * dx + dy * dy) < 100

        // Shadow / glow
        ctx.save()
        ctx.shadowColor = nearMouse ? 'rgba(0,229,255,0.7)' : 'rgba(0,229,255,0.2)'
        ctx.shadowBlur = nearMouse ? 22 : 12

        // Ball
        ctx.beginPath()
        ctx.arc(x, y, r, 0, Math.PI * 2)
        const grad = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r)
        grad.addColorStop(0, nearMouse ? 'rgba(255,255,255,1)' : 'rgba(235,240,255,0.96)')
        grad.addColorStop(1, nearMouse ? 'rgba(200,248,255,0.95)' : 'rgba(210,225,255,0.88)')
        ctx.fillStyle = grad
        ctx.fill()

        // Border
        ctx.strokeStyle = nearMouse ? 'rgba(0,229,255,0.9)' : 'rgba(0,229,255,0.35)'
        ctx.lineWidth = nearMouse ? 2 : 1.5
        ctx.stroke()
        ctx.restore()

        // Label
        const fontSize = r > 62 ? 13 : r > 52 ? 11.5 : 10
        ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillStyle = nearMouse ? '#003344' : '#111827'
        ctx.fillText(body.label, x, y)
      })

      animId = requestAnimationFrame(draw)
    }
    draw()

    // Resize handler
    const onResize = () => {
      W = container.clientWidth
      H = container.clientHeight
      canvas.width = W
      canvas.height = H
      // Reset walls
      walls.forEach(w => Composite.remove(engine.world, w))
      const newWalls = makeWalls(W, H)
      Composite.add(engine.world, newWalls)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      Runner.stop(runner)
      Engine.clear(engine)
      canvas.removeEventListener('mousemove', onMouseMove)
      canvas.removeEventListener('mouseleave', onMouseLeave)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return (
    <section
      id="skills"
      style={{
        position: 'relative',
        padding: 'clamp(5rem, 10vw, 9rem) 0 0',
        background: '#0a0a0f',
        overflow: 'hidden',
      }}
    >
      {/* Section header */}
      <div style={{ padding: '0 clamp(1.5rem, 6vw, 7rem)', marginBottom: '2rem' }}>
        <motion.p
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: '#00e5ff', letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '1rem' }}
        >
          02 — Skills
        </motion.p>

        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          style={{
            fontFamily: 'Space Grotesk',
            fontSize: 'clamp(2.8rem, 7vw, 7rem)',
            fontWeight: 800,
            letterSpacing: '-0.04em',
            lineHeight: 0.95,
            color: 'rgba(255,255,255,0.06)',
            userSelect: 'none',
            pointerEvents: 'none',
            position: 'relative',
            zIndex: 0,
          }}
        >
          MY TECH<br />STACK
        </motion.h2>
      </div>

      {/* Physics canvas */}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          width: '100%',
          height: 'clamp(400px, 55vw, 620px)',
          overflow: 'hidden',
          marginTop: '-3rem',
        }}
      >
        <canvas
          ref={canvasRef}
          style={{ display: 'block', width: '100%', height: '100%', cursor: 'crosshair' }}
        />
      </div>

      {/* Full tech stack legend */}
      <div style={{ padding: 'clamp(2rem, 5vw, 4rem) clamp(1.5rem, 6vw, 7rem)' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3, duration: 0.6 }}
          style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
        >
          {STACK_GROUPS.map((group) => (
            <div key={group.label}>
              <p style={{ fontFamily: 'Inter', fontSize: '0.7rem', color: '#00e5ff', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '0.65rem' }}>
                {group.label}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {group.items.map((item) => (
                  <span key={item} style={{
                    fontFamily: 'Inter',
                    fontSize: '0.78rem',
                    color: '#94a3b8',
                    background: '#111827',
                    border: '1px solid rgba(0,229,255,0.12)',
                    borderRadius: '6px',
                    padding: '0.3rem 0.75rem',
                  }}>
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
