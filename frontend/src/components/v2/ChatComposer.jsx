// 输入区：文字 + 浏览器真实语音识别 + 发送。
// 语音转写实时进入普通输入框，可修改后发送，并与文字走同一处理函数。
import { useEffect, useRef, useState } from 'react'
import Icon from './Icons.jsx'

export const VOICE_STATES = {
  IDLE: 'idle',
  STARTING: 'starting',
  LISTENING: 'listening',
  DONE: 'done',
  ERROR: 'error',
}

export function speechErrorMessage(error) {
  const code = error?.error || error
  if (code === 'not-allowed' || code === 'service-not-allowed') return '麦克风权限未开启，请在浏览器地址栏允许后重试'
  if (code === 'audio-capture') return '没有检测到可用麦克风，请检查设备连接'
  if (code === 'no-speech') return '没有听清，请靠近麦克风后重试'
  if (code === 'network') return '语音识别网络不可用，请稍后重试或改用文字'
  if (code === 'aborted') return '语音输入已取消'
  return '语音识别失败，请重试或改用文字输入'
}

function recognitionConstructor() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export default function ChatComposer({ input, onInputChange, onSend, sending, onStop }) {
  const [voiceState, setVoiceState] = useState(VOICE_STATES.IDLE)
  const [voiceMessage, setVoiceMessage] = useState('')
  const recognitionRef = useRef(null)
  const startTimerRef = useRef(null)
  const originalInputRef = useRef('')
  const transcriptRef = useRef('')
  const voiceErrorRef = useRef(false)

  useEffect(() => () => {
    window.clearTimeout(startTimerRef.current)
    recognitionRef.current?.abort?.()
    recognitionRef.current = null
  }, [])

  const submit = () => {
    if (!input.trim() || sending) return
    onSend(input)
  }

  const mergeTranscript = (speechText) => {
    const original = originalInputRef.current.trim()
    return [original, speechText.trim()].filter(Boolean).join(original ? ' ' : '')
  }

  const startVoice = () => {
    if (sending) return
    const Recognition = recognitionConstructor()
    if (!Recognition) {
      setVoiceState(VOICE_STATES.ERROR)
      setVoiceMessage('当前浏览器不支持语音识别，请使用最新版 Chrome 或 Edge')
      return
    }

    const recognition = new Recognition()
    recognition.lang = 'zh-CN'
    recognition.continuous = false
    recognition.interimResults = true
    recognition.maxAlternatives = 1
    originalInputRef.current = input
    transcriptRef.current = ''
    voiceErrorRef.current = false
    recognitionRef.current = recognition

    recognition.onstart = () => {
      window.clearTimeout(startTimerRef.current)
      setVoiceState(VOICE_STATES.LISTENING)
      setVoiceMessage('正在聆听，说完后点击停止')
    }
    recognition.onresult = (event) => {
      let interim = ''
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const text = event.results[index][0]?.transcript || ''
        if (event.results[index].isFinal) transcriptRef.current += text
        else interim += text
      }
      const combined = `${transcriptRef.current}${interim}`.trim()
      if (combined) onInputChange(mergeTranscript(combined))
    }
    recognition.onerror = (event) => {
      window.clearTimeout(startTimerRef.current)
      voiceErrorRef.current = true
      setVoiceState(VOICE_STATES.ERROR)
      setVoiceMessage(speechErrorMessage(event))
    }
    recognition.onend = () => {
      window.clearTimeout(startTimerRef.current)
      recognitionRef.current = null
      if (voiceErrorRef.current) return
      const transcript = transcriptRef.current.trim()
      if (transcript) {
        onInputChange(mergeTranscript(transcript))
        setVoiceState(VOICE_STATES.DONE)
        setVoiceMessage('已转成文字，可修改后发送')
      } else {
        setVoiceState(VOICE_STATES.ERROR)
        setVoiceMessage('没有听清，请重试或直接输入文字')
      }
    }

    setVoiceState(VOICE_STATES.STARTING)
    setVoiceMessage('正在连接麦克风…')
    startTimerRef.current = window.setTimeout(() => {
      if (recognitionRef.current !== recognition) return
      voiceErrorRef.current = true
      recognition.abort?.()
      recognitionRef.current = null
      setVoiceState(VOICE_STATES.ERROR)
      setVoiceMessage('麦克风连接超时，请检查浏览器权限后重试')
    }, 10000)
    try {
      recognition.start()
    } catch {
      window.clearTimeout(startTimerRef.current)
      recognitionRef.current = null
      setVoiceState(VOICE_STATES.ERROR)
      setVoiceMessage('麦克风启动失败，请刷新页面后重试')
    }
  }

  const stopVoice = () => {
    window.clearTimeout(startTimerRef.current)
    recognitionRef.current?.stop?.()
  }

  const cancelVoice = () => {
    voiceErrorRef.current = true
    window.clearTimeout(startTimerRef.current)
    recognitionRef.current?.abort?.()
    recognitionRef.current = null
    onInputChange(originalInputRef.current)
    setVoiceState(VOICE_STATES.IDLE)
    setVoiceMessage('')
  }

  const dismissVoice = () => {
    setVoiceState(VOICE_STATES.IDLE)
    setVoiceMessage('')
  }

  const isListening = voiceState === VOICE_STATES.STARTING || voiceState === VOICE_STATES.LISTENING

  return (
    <div className="v2-composer-wrap">
      {voiceState !== VOICE_STATES.IDLE && (
        <div className={`v2-voice-panel ${voiceState}`} data-testid="voice-panel" role="status">
          <span className={`v2-voice-indicator ${isListening ? 'active' : ''}`} aria-hidden="true" />
          <span className="v2-voice-status">{voiceMessage}</span>
          {isListening && <button className="v2-voice-text-btn" onClick={stopVoice}>停止</button>}
          <button className="v2-voice-text-btn muted" onClick={isListening ? cancelVoice : dismissVoice}>
            {isListening ? '取消' : '知道了'}
          </button>
        </div>
      )}

      <div className="v2-composer">
        <input
          placeholder="输入消息，或使用语音"
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={(event) => { if (event.key === 'Enter') submit() }}
          disabled={sending}
          aria-label="消息输入"
        />
        <button
          className={`v2-mic ${isListening ? 'recording' : ''}`}
          onClick={isListening ? stopVoice : startVoice}
          disabled={sending}
          aria-label={isListening ? '停止语音输入' : '语音输入'}
          title={isListening ? '停止语音输入' : '语音输入'}
        >
          <Icon name="microphone" size={20} />
        </button>
        {sending ? (
          <button className="v2-send" onClick={onStop} aria-label="停止生成"><Icon name="stop" size={19} /></button>
        ) : (
          <button className="v2-send" onClick={submit} disabled={!input.trim()} aria-label="发送"><Icon name="send" size={20} /></button>
        )}
      </div>
      <p className="v2-composer-hint">AI 可能会出错，重要账本操作仍需你确认。</p>
    </div>
  )
}
