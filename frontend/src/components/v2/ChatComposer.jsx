// 输入区：文字 + 语音 + 发送 + 发送中防重复 + 停止 + 失败保留草稿。
// 语音转写文本进入普通输入框，可修改后点击发送，走与文字相同的处理函数。
import { useState } from 'react'
import { MockSpeechController, SPEECH_STATES } from '../../services/mockSpeech.js'
import { mockSpeechUtterances } from '../../fixtures/mock/index.js'

export default function ChatComposer({ input, onInputChange, onSend, sending, onStop }) {
  const [speech, setSpeech] = useState(() => new MockSpeechController())
  const [, setTick] = useState(0)
  const bump = () => setTick((v) => v + 1)
  const [showUtterances, setShowUtterances] = useState(false)

  const submit = () => {
    if (!input.trim() || sending) return
    onSend(input)
  }

  const startVoice = () => {
    setShowUtterances(true)
    speech.startRecording('', 'success')
    bump()
  }

  const speak = async (utterance, scenario = 'success') => {
    speech.startRecording(utterance, scenario)
    setShowUtterances(false)
    bump()
    await speech.finishRecording()
    bump()
    if (speech.state === SPEECH_STATES.DONE) {
      onInputChange(speech.transcript)
    }
  }

  const cancelVoice = () => {
    speech.cancelRecording()
    setShowUtterances(false)
    bump()
  }

  const retryVoice = async () => {
    await speech.retry()
    bump()
    if (speech.state === SPEECH_STATES.DONE) {
      onInputChange(speech.transcript)
    }
  }

  const st = speech.state

  return (
    <div className="v2-composer-wrap">
      {st !== SPEECH_STATES.IDLE && (
        <div className="v2-voice-panel" data-testid="voice-panel">
          {st === SPEECH_STATES.RECORDING && (
            <>
              <span className="v2-voice-status">● 正在录音</span>
              <button className="v2-link" onClick={cancelVoice}>取消</button>
            </>
          )}
          {st === SPEECH_STATES.TRANSCRIBING && <span className="v2-voice-status">正在转写…</span>}
          {st === SPEECH_STATES.ERROR && (
            <>
              <span className="v2-voice-status v2-error">{speech.error}</span>
              <button className="v2-btn secondary" onClick={retryVoice}>重试</button>
              <button className="v2-link" onClick={cancelVoice}>取消</button>
            </>
          )}
          {st === SPEECH_STATES.DONE && (
            <span className="v2-voice-status v2-ok">已转写，可修改后发送</span>
          )}
        </div>
      )}

      {showUtterances && st === SPEECH_STATES.RECORDING && (
        <div className="v2-utterances" data-testid="utterance-picker">
          <div className="v2-muted">（Mock）请选择“说了什么”：</div>
          {mockSpeechUtterances.map((u) => (
            <button key={u} className="v2-chip" onClick={() => speak(u)}>{u}</button>
          ))}
          <button className="v2-chip" onClick={() => speak('网络失败演示', 'network_failure')}>网络失败演示</button>
          <button className="v2-chip" onClick={() => speak('转写失败演示', 'transcribe_failure')}>转写失败演示</button>
        </div>
      )}

      <div className="v2-composer">
        <button className="v2-mic" onClick={startVoice} disabled={sending} aria-label="语音输入">🎤</button>
        <input
          placeholder="输入文字，或用语音输入"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
          disabled={sending}
        />
        {sending ? (
          <button className="v2-send" onClick={onStop} aria-label="停止">■</button>
        ) : (
          <button className="v2-send" onClick={submit} disabled={!input.trim()} aria-label="发送">➜</button>
        )}
      </div>
    </div>
  )
}
