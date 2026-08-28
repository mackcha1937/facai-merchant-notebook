import Icon from './Icons.jsx'

export default function WorkspaceFrame({ title, onBack, onClose, children }) {
  return (
    <>
      <header className="v2-workspace-head">
        <button className="v2-workspace-action" onClick={onBack} aria-label="返回上一步" title="返回上一步">
          <Icon name="back" size={22} />
        </button>
        <div className="v2-workspace-title" title={title}>{title}</div>
        <button className="v2-workspace-action close" onClick={onClose} aria-label="关闭工作区" title="关闭工作区">
          <Icon name="close" size={22} />
        </button>
      </header>
      <div className="v2-workspace-content">{children}</div>
    </>
  )
}
