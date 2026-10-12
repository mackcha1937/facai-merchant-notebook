// Mock 语音转写服务（阶段2）。
// 状态机：idle -> recording -> transcribing -> done | error
// - 录音中可取消（cancelRecording）；
// - 转写文本返回后进入普通输入框，可修改再发送；
// - 语音与文字最终走同一处理函数（send），不绕过确认；
// - 网络失败/转写失败保留错误与可编辑文本，可原地重试。

import { csrfHeaders } from '../api.js'

export const SPEECH_STATES = {
  IDLE: 'idle',
  RECORDING: 'recording',
  TRANSCRIBING: 'transcribing',
  DONE: 'done',
  ERROR: 'error',
}

export async function apiTranscribe(utterance, scenario = 'success') {
  const res = await fetch('/api/v2/stage2/mock-speech', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...csrfHeaders() },
    body: JSON.stringify({ utterance, scenario }),
  })
  if (!res.ok) {
    let detail = '语音转写失败'
    try {
      const data = await res.json()
      if (data && data.detail) detail = data.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}

export class MockSpeechController {
  constructor(transcribeFn = apiTranscribe) {
    this.transcribeFn = transcribeFn
    this.state = SPEECH_STATES.IDLE
    this.transcript = ''
    this.error = ''
    this.utterance = ''
    this.scenario = 'success'
  }

  startRecording(utterance, scenario = 'success') {
    this.utterance = utterance
    this.scenario = scenario
    this.state = SPEECH_STATES.RECORDING
    this.transcript = ''
    this.error = ''
  }

  cancelRecording() {
    this.state = SPEECH_STATES.IDLE
    this.utterance = ''
    this.transcript = ''
    this.error = ''
  }

  async finishRecording() {
    if (this.state !== SPEECH_STATES.RECORDING) return
    await this._transcribe()
  }

  async retry() {
    if (this.state !== SPEECH_STATES.ERROR) return
    await this._transcribe()
  }

  reset() {
    this.state = SPEECH_STATES.IDLE
    this.transcript = ''
    this.error = ''
    this.utterance = ''
    this.scenario = 'success'
  }

  async _transcribe() {
    this.state = SPEECH_STATES.TRANSCRIBING
    try {
      const result = await this.transcribeFn(this.utterance, this.scenario)
      this.transcript = result.transcript || ''
      this.state = SPEECH_STATES.DONE
    } catch (e) {
      this.error = e.message || '语音转写失败'
      this.state = SPEECH_STATES.ERROR
    }
  }
}
