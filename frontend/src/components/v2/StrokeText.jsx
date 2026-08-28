import { useId } from 'react'

const cssValue = (value, fallback, unit = 'px') => {
  if (value === undefined || value === null) return fallback
  return typeof value === 'number' ? `${value}${unit}` : value
}

export default function StrokeText({
  text,
  strokeColor = '#A78BFA',
  fillColor = '#625A70',
  strokeWidth = 1.2,
  drawDuration = 1.2,
  fillDelay = 0.18,
  stagger = 0.04,
  fontSize = '1em',
  fontWeight = 650,
  letterSpacing = '-0.03em',
  reverse = false,
  className = '',
}) {
  const id = useId()
  const characters = [...text]

  return (
    <span
      className={`stroke-text ${reverse ? 'reverse' : ''} ${className}`.trim()}
      aria-label={text}
      role="text"
      style={{
        '--stroke-color': strokeColor,
        '--fill-color': fillColor,
        '--stroke-width': cssValue(strokeWidth, '1.2px'),
        '--draw-duration': `${drawDuration}s`,
        '--stroke-font-size': cssValue(fontSize, '1em'),
        '--stroke-font-weight': fontWeight,
        '--stroke-letter-spacing': cssValue(letterSpacing, '-0.03em'),
      }}
    >
      {characters.map((character, index) => {
        const order = reverse ? characters.length - index - 1 : index
        const drawDelay = order * stagger
        const fillStart = fillDelay + order * stagger
        return (
          <span
            className="stroke-text-letter"
            aria-hidden="true"
            key={`${id}-${index}`}
            style={{
              '--draw-delay': `${drawDelay}s`,
              '--fill-delay': `${fillStart}s`,
            }}
          >
            <span className="stroke-text-outline">{character}</span>
            <span className="stroke-text-fill">{character}</span>
          </span>
        )
      })}
    </span>
  )
}
