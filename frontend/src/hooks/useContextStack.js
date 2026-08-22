import { useCallback, useEffect, useRef, useState } from 'react'
import { ContextStack } from '../lib/contextStack'

// 将 ContextStack 与浏览器返回键/系统返回键统一：
// - push 时写入 history.pushState；
// - popstate 时按栈深回退（不会静默丢失上下文）；
// - 到达应用根层后交给浏览器默认行为（允许离开应用）。
export function useContextStack(rootCtx) {
  const stackRef = useRef(null)
  if (stackRef.current === null) {
    stackRef.current = new ContextStack(rootCtx)
  }
  const [, setVersion] = useState(0)
  const bump = useCallback(() => setVersion((v) => v + 1), [])

  const push = useCallback((ctx) => {
    const next = stackRef.current.push(ctx)
    window.history.pushState({ ctxIndex: stackRef.current.length - 1 }, '')
    bump()
    return next
  }, [bump])

  const pop = useCallback(() => {
    const popped = stackRef.current.pop()
    bump()
    return popped
  }, [bump])

  const replace = useCallback((ctx) => {
    stackRef.current.replace(ctx)
    bump()
  }, [bump])

  useEffect(() => {
    const onPopState = (e) => {
      const idx = e.state?.ctxIndex
      // 无 state：回到进入应用之前，交给浏览器默认行为离开应用
      if (idx == null) return
      while (stackRef.current.length - 1 > idx) {
        stackRef.current.pop()
      }
      bump()
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [bump])

  return {
    current: stackRef.current.current,
    root: stackRef.current.root,
    length: stackRef.current.length,
    canGoBack: stackRef.current.canGoBack(),
    push,
    pop,
    replace,
  }
}
