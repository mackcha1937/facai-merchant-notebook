import { describe, it, expect } from 'vitest'
import { MockSpeechController, SPEECH_STATES } from '../services/mockSpeech.js'

const okFn = async (utterance, scenario) => ({ transcript: utterance, is_mock: true })
const failFn = async () => { throw new Error('转写失败') }

describe('Mock 语音转写状态机', () => {
  it('录音中可取消，回到 idle', () => {
    const c = new MockSpeechController(okFn)
    c.startRecording('返回客户列表')
    expect(c.state).toBe(SPEECH_STATES.RECORDING)
    c.cancelRecording()
    expect(c.state).toBe(SPEECH_STATES.IDLE)
    expect(c.transcript).toBe('')
  })

  it('录音完成后进入 done，转写文本可编辑', async () => {
    const c = new MockSpeechController(okFn)
    c.startRecording('日期改成昨天')
    await c.finishRecording()
    expect(c.state).toBe(SPEECH_STATES.DONE)
    expect(c.transcript).toBe('日期改成昨天')
  })

  it('转写失败进入 error，可重试成功', async () => {
    let calls = 0
    const flaky = async () => {
      calls += 1
      if (calls === 1) throw new Error('转写失败')
      return { transcript: '取消' }
    }
    const c = new MockSpeechController(flaky)
    c.startRecording('取消')
    await c.finishRecording()
    expect(c.state).toBe(SPEECH_STATES.ERROR)
    expect(c.error).toBe('转写失败')
    await c.retry()
    expect(c.state).toBe(SPEECH_STATES.DONE)
    expect(c.transcript).toBe('取消')
  })

  it('网络失败保留错误，不产生写入', async () => {
    const c = new MockSpeechController(failFn)
    c.startRecording('x')
    await c.finishRecording()
    expect(c.state).toBe(SPEECH_STATES.ERROR)
    expect(c.transcript).toBe('')
  })
})
