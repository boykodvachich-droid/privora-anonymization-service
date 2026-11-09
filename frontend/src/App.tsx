import { useEffect, useState } from 'react'
import {
  ShieldCheck, LayoutDashboard, FileText, Clock3, Settings,
  LockKeyhole, Sparkles, ArrowRight, Copy, Check, Trash2,
  Zap, Activity, Mail, Phone, CreditCard, UserRound,
  Fingerprint, MapPin, CalendarDays, FileSearch
} from 'lucide-react'

type TaskItem = {
  task_id: string
  status: string
  created_at: string
  processing_time_ms: number | null
}

type ApiResult = {
  anonymized_text: string
  detected: Record<string, number>
  processing_time_ms: number
}

const categoryIcons: Record<string, typeof UserRound> = {
  PERSON: UserRound,
  EMAIL: Mail,
  PHONE: Phone,
  BANK_CARD: CreditCard,
  INN: Fingerprint,
  PASSPORT: FileText,
  SNILS: ShieldCheck,
  ADDRESS: MapPin,
  DATE: CalendarDays
}

const ALL_CATEGORIES = [
  'PERSON',
  'EMAIL',
  'PHONE',
  'ADDRESS',
  'BANK_CARD',
  'INN',
  'PASSPORT',
  'SNILS',
  'DATE'
] as const

type Category = typeof ALL_CATEGORIES[number]

const categoryLabels: Record<Category, string> = {
  PERSON: 'Person names',
  EMAIL: 'Email addresses',
  PHONE: 'Phone numbers',
  ADDRESS: 'Physical addresses',
  BANK_CARD: 'Bank card numbers',
  INN: 'INN',
  PASSPORT: 'Passport numbers',
  SNILS: 'SNILS',
  DATE: 'Dates'
}

function App() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState<ApiResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [activePage, setActivePage] = useState('overview')
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [tasksLoading, setTasksLoading] = useState(false)
  const [tasksError, setTasksError] = useState('')
  const [taskSearch, setTaskSearch] = useState('')
  const [taskStatusFilter, setTaskStatusFilter] = useState('all')
  const [taskDateFilter, setTaskDateFilter] = useState('')
  const [selectedCategories, setSelectedCategories] = useState<Category[]>(() => {
    try {
      const saved = window.localStorage.getItem('datamask-enabled-categories')
      if (!saved) return [...ALL_CATEGORIES]

      const parsed: unknown = JSON.parse(saved)
      if (!Array.isArray(parsed)) return [...ALL_CATEGORIES]

      return ALL_CATEGORIES.filter(category => parsed.includes(category))
    } catch {
      return [...ALL_CATEGORIES]
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(
        'datamask-enabled-categories',
        JSON.stringify(selectedCategories)
      )
    } catch {
      // Keep the current selection even if browser storage is unavailable.
    }
  }, [selectedCategories])

  function toggleCategory(category: Category) {
    setSelectedCategories(current =>
      current.includes(category)
        ? current.filter(item => item !== category)
        : ALL_CATEGORIES.filter(item => item === category || current.includes(item))
    )
  }

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.task_id.toLowerCase().includes(taskSearch.trim().toLowerCase())
    const matchesStatus = taskStatusFilter === 'all' || task.status.toLowerCase() === taskStatusFilter
    const date = new Date(task.created_at)
    const localDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    const matchesDate = !taskDateFilter || localDate === taskDateFilter
    return matchesSearch && matchesStatus && matchesDate
  })
  const [backgroundLoading, setBackgroundLoading] = useState(false)
  const [backgroundStatus, setBackgroundStatus] = useState('')
  const [selectedTask, setSelectedTask] = useState<{
    task_id: string
    status: string
    created_at: string
    anonymized_text: string | null
    detected: Record<string, number>
    processing_time_ms: number | null
  } | null>(null)
  const [selectedTaskLoading, setSelectedTaskLoading] = useState(false)
  const [selectedTaskError, setSelectedTaskError] = useState('')
  const [taskCopied, setTaskCopied] = useState(false)

  const completedTasks = tasks.filter(task => task.status.toLowerCase() === 'completed')
  const failedTasks = tasks.filter(task => task.status.toLowerCase() === 'failed')
  const completedTimes = completedTasks
    .map(task => task.processing_time_ms)
    .filter((time): time is number => time != null)
  const averageProcessingTime = completedTimes.length
    ? completedTimes.reduce((sum, time) => sum + time, 0) / completedTimes.length
    : null

  const detectedTotal = result
    ? Object.values(result.detected).reduce((sum, count) => sum + count, 0)
    : 0

  async function anonymize() {
    if (!input.trim() || loading) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await fetch('/api/v1/anonymize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input, categories: selectedCategories })
      })

      if (!response.ok) {
        const detail = await response.text()
        throw new Error(`Request failed (${response.status}): ${detail}`)
      }

      const data: ApiResult = await response.json()
      setResult(data)
      setApiOnline(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function anonymizeInBackground() {
    if (!input.trim() || loading || backgroundLoading) return

    setBackgroundLoading(true)
    setBackgroundStatus('Submitting task...')
    setError('')
    setResult(null)

    try {
      const createResponse = await fetch('/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input, categories: selectedCategories })
      })

      if (!createResponse.ok) {
        const detail = await createResponse.text()
        throw new Error(`Could not create task (${createResponse.status}): ${detail}`)
      }

      const created: { task_id: string; status: string } = await createResponse.json()
      setBackgroundStatus(`Task ${created.task_id.slice(0, 8)} created. Waiting for processing...`)

      for (let attempt = 0; attempt < 150; attempt++) {
        await new Promise(resolve => window.setTimeout(resolve, 2000))

        const statusResponse = await fetch(`/api/v1/tasks/${created.task_id}`)
        if (!statusResponse.ok) {
          throw new Error(`Could not check task status (${statusResponse.status})`)
        }

        const task: {
          task_id: string
          status: string
          anonymized_text: string | null
          detected: Record<string, number>
          processing_time_ms: number | null
        } = await statusResponse.json()

        if (task.status === 'completed') {
          setResult({
            anonymized_text: task.anonymized_text || '',
            detected: task.detected || {},
            processing_time_ms: task.processing_time_ms ?? 0
          })
          setBackgroundStatus('Background anonymization completed.')
          setApiOnline(true)
          void loadTasks()
          return
        }

        if (task.status === 'failed') {
          throw new Error('Background task failed. Please check task history and try again.')
        }

        setBackgroundStatus(`Task ${created.task_id.slice(0, 8)}: ${task.status}...`)
      }

      throw new Error('Task is taking longer than expected. Check Task history for its status.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Background processing failed.')
      setBackgroundStatus('Background processing stopped.')
      void loadTasks()
    } finally {
      setBackgroundLoading(false)
    }
  }

  async function copyResult() {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result.anonymized_text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setError('Could not access clipboard. Please copy the text manually.')
    }
  }

  function downloadFile(filename: string, content: string, mimeType: string) {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  function exportResultTxt() {
    if (!result) return
    downloadFile('datamask-anonymized-result.txt', result.anonymized_text, 'text/plain;charset=utf-8')
  }

  function exportResultJson() {
    if (!result) return
    const exportData = {
      anonymized_text: result.anonymized_text,
      detected: result.detected,
      processing_time_ms: result.processing_time_ms,
    }
    downloadFile('datamask-anonymized-result.json', JSON.stringify(exportData, null, 2), 'application/json;charset=utf-8')
  }

  function exportTasksCsv() {
    if (!tasks.length) return

    const escapeCsv = (value: string | number) =>
      `"${String(value).replace(/"/g, '""')}"`

    const rows = [
      ['Task ID', 'Status', 'Created at', 'Processing time (ms)'],
      ...tasks.map(task => [
        task.task_id,
        task.status,
        task.created_at,
        task.processing_time_ms ?? ''
      ])
    ]

    const csv = '\uFEFF' + rows
      .map(row => row.map(escapeCsv).join(','))
      .join('\r\n')

    downloadFile('datamask-task-history.csv', csv, 'text/csv;charset=utf-8')
  }

  function clearWorkspace() {
    setInput('')
    setResult(null)
    setError('')
    setCopied(false)
  }

  async function loadTasks() {
    setTasksLoading(true)
    setTasksError('')
    try {
      const response = await fetch('/api/v1/tasks?limit=50&offset=0')
      if (!response.ok) throw new Error(`Request failed (${response.status})`)
      const data: { items: TaskItem[] } = await response.json()
      setTasks(data.items)
    } catch (err) {
      setTasksError(err instanceof Error ? err.message : 'Could not load task history.')
    } finally {
      setTasksLoading(false)
    }
  }

  async function openTask(taskId: string) {
    setSelectedTaskLoading(true)
    setSelectedTaskError('')
    setSelectedTask(null)
    setTaskCopied(false)
    setActivePage('task-detail')

    try {
      const response = await fetch(`/api/v1/tasks/${taskId}`)
      if (!response.ok) throw new Error(`Could not load task (${response.status})`)
      const data = await response.json()
      setSelectedTask(data)
    } catch (err) {
      setSelectedTaskError(err instanceof Error ? err.message : 'Could not load task details.')
    } finally {
      setSelectedTaskLoading(false)
    }
  }

  async function copyTaskResult() {
    if (!selectedTask?.anonymized_text) return
    try {
      await navigator.clipboard.writeText(selectedTask.anonymized_text)
      setTaskCopied(true)
      window.setTimeout(() => setTaskCopied(false), 1800)
    } catch {
      setSelectedTaskError('Could not access clipboard. Please copy the text manually.')
    }
  }

  async function deleteTask() {
    if (!selectedTask) return

    const confirmed = window.confirm(
      `Delete task ${selectedTask.task_id}? This action cannot be undone.`
    )
    if (!confirmed) return

    setSelectedTaskError('')

    try {
      const response = await fetch(`/api/v1/tasks/${selectedTask.task_id}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        const detail = await response.text()
        throw new Error(`Could not delete task (${response.status}): ${detail}`)
      }

      setSelectedTask(null)
      setActivePage('history')
      await loadTasks()
    } catch (err) {
      setSelectedTaskError(
        err instanceof Error ? err.message : 'Could not delete task.'
      )
    }
  }

  async function checkApi() {
    try {
      const response = await fetch('/health')
      setApiOnline(response.ok)
    } catch {
      setApiOnline(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={23} strokeWidth={2.3} /></div>
          <div className="brand-name">data<span>mask</span><small>PRIVACY WORKSPACE</small></div>
        </div>

        <div className="side-label">WORKSPACE</div>
        <nav className="side-nav">
          <div className={`nav-item ${activePage === "overview" ? "active" : ""}`} onClick={() => setActivePage("overview")}><LayoutDashboard size={18} /> <span>Overview</span></div>
          <div className="nav-item"><FileText size={18} /> <span>Anonymization</span><span className="nav-dot" /></div>
          <div className={`nav-item ${activePage === "history" ? "active" : ""}`} onClick={() => { setActivePage("history"); loadTasks() }}><Clock3 size={18} /> <span>Task history</span></div>
        </nav>

        <div className="side-label tools-label">PREFERENCES</div>
        <nav className="side-nav">
          <div className={`nav-item ${activePage === "settings" ? "active" : ""}`} onClick={() => setActivePage("settings")}><Settings size={18} /> <span>Settings</span></div>
        </nav>

        <div className="sidebar-bottom">
          <div className="security-card">
            <div className="security-icon"><LockKeyhole size={17} /></div>
            <strong>Your data, protected.</strong>
            <p>Keep sensitive information safe with intelligent anonymization.</p>
            <div className="security-status"><span /> Privacy protection active</div>
          </div>
          <div className="profile-row">
            <div className="avatar">DM</div>
            <div className="profile-copy"><strong>DataMask</strong><span>Personal workspace</span></div>
            <Settings size={16} className="profile-settings" />
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-slash">/</span><strong>{activePage === "history" ? "Task history" : activePage === "task-detail" ? "Task details" : activePage === "settings" ? "Settings" : "Overview"}</strong></div>
          <div className="topbar-right">
            <button className="api-pill" onClick={checkApi}>
              <span className={`status-dot ${apiOnline === false ? 'offline' : ''}`} />
              {apiOnline === null ? 'Check API status' : apiOnline ? 'API operational' : 'API unavailable'}
            </button>
            <div className="top-avatar">DM</div>
          </div>
        </header>

        {activePage === 'task-detail' ? (
          <div className="page-content">
            <section className="welcome-row">
              <div>
                <div className="eyebrow"><FileSearch size={13} /> TASK INFORMATION</div>
                <h1>Task <span>details.</span></h1>
                <p className="welcome-subtitle">Anonymization result and processing information.</p>
              </div>
              <button className="anonymize-button" onClick={() => { setActivePage('history'); loadTasks() }}>
                <ArrowRight size={16} style={{ transform: 'rotate(180deg)' }} /> Back to history
              </button>
            </section>

            {selectedTaskLoading && <div className="history-card history-empty">Loading task details...</div>}
            {selectedTaskError && <div className="error-banner">{selectedTaskError}</div>}
            {selectedTask && (
              <>
                <section className="history-card task-detail-card">
                  <div className="history-heading"><div><h2>Task information</h2><p>Original text is not displayed or exposed here.</p></div></div>
                  <div className="task-detail-grid">
                    <div><span>Task ID</span><strong className="detail-task-id">{selectedTask.task_id}</strong></div>
                    <div><span>Status</span><strong><span className={`task-status status-${selectedTask.status.toLowerCase()}`}>{selectedTask.status}</span></strong></div>
                    <div><span>Created at</span><strong>{new Date(selectedTask.created_at).toLocaleString()}</strong></div>
                    <div><span>Processing time</span><strong>{selectedTask.processing_time_ms == null ? '—' : `${selectedTask.processing_time_ms.toFixed(1)} ms`}</strong></div>
                  </div>
                </section>

                <section className="history-card task-result-card">
                  <div className="history-heading">
                    <div><h2>Protected output</h2><p>Anonymized text returned by the worker.</p></div>
                    <div className="task-actions">
                      {selectedTask.anonymized_text && (
                        <button className="subtle-button copy-button" onClick={copyTaskResult}>
                          {taskCopied ? <Check size={14} /> : <Copy size={14} />}
                          {taskCopied ? 'Copied' : 'Copy result'}
                        </button>
                      )}
                      {['completed', 'failed'].includes(selectedTask.status.toLowerCase()) && (
                        <button className="subtle-button delete-task-button" onClick={deleteTask}>
                          Delete task
                        </button>
                      )}
                    </div>
                  </div>
                  <pre className="task-result-text">{selectedTask.anonymized_text || 'No anonymized result is available for this task.'}</pre>
                </section>

                <section className="history-card task-result-card">
                  <div className="history-heading"><div><h2>Detection summary</h2><p>Categories found during anonymization.</p></div></div>
                  {Object.keys(selectedTask.detected || {}).length > 0 ? (
                    <div className="category-list">
                      {Object.entries(selectedTask.detected).map(([name, count]) => {
                        const Icon = categoryIcons[name] || FileSearch
                        return <div className="category-item" key={name}><span className="category-icon"><Icon size={15} /></span><span className="category-name">{name.replace('_', ' ')}</span><strong>{count}</strong></div>
                      })}
                    </div>
                  ) : <div className="history-empty">No sensitive data categories were detected.</div>}
                </section>
              </>
            )}
            <footer className="page-footer"><span>© 2026 DataMask. Built for privacy.</span><span><span className="footer-dot" /> Task details from API</span></footer>
          </div>
        ) : activePage === 'history' ? (
          <div className="page-content">
            <section className="welcome-row">
              <div>
                <div className="eyebrow"><Clock3 size={13} /> BACKGROUND PROCESSING</div>
                <h1>Task <span>history.</span></h1>
                <p className="welcome-subtitle">Review the status of your background anonymization tasks.</p>
              </div>
              <button className="anonymize-button" onClick={loadTasks} disabled={tasksLoading}>
                <Activity size={16} /> {tasksLoading ? 'Refreshing...' : 'Refresh history'}
              </button>
            </section>

            <section className="history-card">
              <div className="history-heading">
                <div>
                  <h2>Recent tasks</h2>
                  <p>{filteredTasks.length} of {tasks.length} tasks shown · Original text is not displayed</p>
                </div>
                <button
                  className="subtle-button"
                  onClick={exportTasksCsv}
                  disabled={tasks.length === 0}
                >
                  Export CSV
                </button>
              </div>
              {tasksError && <div className="error-banner">{tasksError}</div>}

              <div className="task-filters">
                <input
                  className="task-filter-input"
                  type="text"
                  placeholder="Search by Task ID..."
                  value={taskSearch}
                  onChange={event => setTaskSearch(event.target.value)}
                />
                <select
                  className="task-filter-select"
                  value={taskStatusFilter}
                  onChange={event => setTaskStatusFilter(event.target.value)}
                >
                  <option value="all">All statuses</option>
                  <option value="pending">Pending</option>
                  <option value="processing">Processing</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>
                <input
                  className="task-filter-date"
                  type="date"
                  value={taskDateFilter}
                  onChange={event => setTaskDateFilter(event.target.value)}
                />
                <button
                  className="task-reset-button"
                  onClick={() => {
                    setTaskSearch('')
                    setTaskStatusFilter('all')
                    setTaskDateFilter('')
                  }}
                >
                  Reset filters
                </button>
              </div>

              {tasksLoading && tasks.length === 0 ? (
                <div className="history-empty">Loading task history...</div>
              ) : tasks.length === 0 && !tasksError ? (
                <div className="history-empty">No tasks yet. Background tasks will appear here.</div>
              ) : filteredTasks.length === 0 ? (
                <div className="history-empty">No tasks match your filters.</div>
              ) : (
                <div className="history-table-wrap">
                  <table className="history-table">
                    <thead><tr><th>Task ID</th><th>Status</th><th>Created</th><th>Processing time</th></tr></thead>
                    <tbody>
                      {filteredTasks.map(task => (
                        <tr key={task.task_id} className="history-row" onClick={() => openTask(task.task_id)} title="Open task details">
                          <td className="task-id"><button className="task-open-button" onClick={() => openTask(task.task_id)}>{task.task_id}</button></td>
                          <td><span className={`task-status status-${task.status.toLowerCase()}`}>{task.status}</span></td>
                          <td>{new Date(task.created_at).toLocaleString()}</td>
                          <td>{task.processing_time_ms == null ? '—' : `${task.processing_time_ms.toFixed(1)} ms`}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
            <footer className="page-footer"><span>© 2026 DataMask. Built for privacy.</span><span><span className="footer-dot" /> Task history from PostgreSQL</span></footer>
          </div>
        ) : activePage === 'settings' ? (
          <div className="page-content">
            <section className="welcome-row">
              <div>
                <div className="eyebrow"><Settings size={13} /> CONFIGURATION</div>
                <h1>Settings <span>& Security.</span></h1>
                <p className="welcome-subtitle">Manage your DataMask preferences and privacy information.</p>
              </div>
              <div className="secure-badge"><ShieldCheck size={17} /><span>Secure workspace</span></div>
            </section>

            <section className="history-card">
              <div className="section-heading">
                <div><h2><Fingerprint size={18} /> Detection categories</h2><p>Choose which sensitive data categories you want to review.</p></div>
              </div>
              <p className="welcome-subtitle">Enable the categories DataMask should detect and anonymize. Your choices are saved in this browser.</p>
              <div className="history-heading">
                <div><p>{selectedCategories.length} of {ALL_CATEGORIES.length} categories enabled</p></div>
                <div className="task-actions">
                  <button
                    className="subtle-button"
                    onClick={() => setSelectedCategories([...ALL_CATEGORIES])}
                    disabled={selectedCategories.length === ALL_CATEGORIES.length}
                  >
                    Select all
                  </button>
                  <button
                    className="subtle-button"
                    onClick={() => setSelectedCategories([])}
                    disabled={selectedCategories.length === 0}
                  >
                    Disable all
                  </button>
                </div>
              </div>
              <div className="settings-list">
                {ALL_CATEGORIES.map(category => {
                  const Icon = categoryIcons[category]
                  const enabled = selectedCategories.includes(category)

                  return (
                    <label className="settings-row" key={category}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Icon size={16} />
                        {categoryLabels[category]}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span className={`task-status ${enabled ? 'status-completed' : 'status-failed'}`}>
                          {enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <input
                          type="checkbox"
                          checked={enabled}
                          onChange={() => toggleCategory(category)}
                          aria-label={`Enable ${categoryLabels[category]}`}
                        />
                      </span>
                    </label>
                  )
                })}
              </div>
              <p className="welcome-subtitle">Changes apply to your next synchronous or background anonymization request.</p>
            </section>

            <section className="history-card">
              <div className="section-heading">
                <div><h2><LockKeyhole size={18} /> Data & Privacy</h2><p>How DataMask handles your task history and results.</p></div>
              </div>
              <div className="settings-list">
                <div className="settings-row"><span>Task history</span><span>Stored in PostgreSQL</span></div>
                <div className="settings-row"><span>Exported task data</span><span>Downloaded to your device</span></div>
                <div className="settings-row"><span>Original and anonymized text</span><span>Not included in CSV export</span></div>
              </div>
            </section>

            <footer className="page-footer"><span>© 2026 DataMask. Built for privacy.</span><span><span className="footer-dot" /> Settings</span></footer>
          </div>
        ) : (
        <div className="page-content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><Sparkles size={13} /> INTELLIGENT DATA PROTECTION</div>
              <h1>Privacy starts <span>here.</span></h1>
              <p className="welcome-subtitle">Detect and anonymize sensitive information in seconds.</p>
            </div>
            <div className="secure-badge"><ShieldCheck size={17} /><span>Secure workspace</span></div>
          </section>

          <section className="stats-grid">
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon purple"><FileSearch size={18} /></span><span className="stat-caption">THIS SESSION</span></div>
              <div className="stat-value">{result ? detectedTotal : '—'}</div>
              <div className="stat-label">Items protected</div>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon teal"><ShieldCheck size={18} /></span><span className="stat-caption">DETECTION</span></div>
              <div className="stat-value">{result ? Object.keys(result.detected).length : '—'}</div>
              <div className="stat-label">Data categories found</div>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon amber"><Zap size={18} /></span><span className="stat-caption">PERFORMANCE</span></div>
              <div className="stat-value">{result ? <>{result.processing_time_ms.toFixed(1)}<span className="stat-unit"> ms</span></> : '—'}</div>
              <div className="stat-label">Processing time</div>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon green"><Activity size={18} /></span><span className="stat-caption">SYSTEM</span></div>
              <div className="stat-value stat-system">Ready</div>
              <div className="stat-label">Anonymization engine</div>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon purple"><FileSearch size={18} /></span><span className="stat-caption">TASK HISTORY</span></div>
              <div className="stat-value">{tasks.length}</div>
              <div className="stat-label">Total tasks</div>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon green"><ShieldCheck size={18} /></span><span className="stat-caption">SUCCESS</span></div>
              <div className="stat-value">{completedTasks.length}</div>
              <div className="stat-label">Completed tasks</div>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon amber"><Activity size={18} /></span><span className="stat-caption">ERRORS</span></div>
              <div className="stat-value">{failedTasks.length}</div>
              <div className="stat-label">Failed tasks</div>
            </div>
            <div className="stat-card">
              <div className="stat-top"><span className="stat-icon teal"><Zap size={18} /></span><span className="stat-caption">AVERAGE</span></div>
              <div className="stat-value">
                {averageProcessingTime == null ? '—' : <>{averageProcessingTime.toFixed(1)}<span className="stat-unit"> ms</span></>}
              </div>
              <div className="stat-label">Average processing time</div>
            </div>
          </section>

          <section className="workspace-section">
            <div className="section-heading">
              <div><h2>Anonymize your data</h2><p>Paste your text below and let DataMask handle the sensitive details.</p></div>
              <div className="live-label"><span /> LIVE WORKSPACE</div>
            </div>

            <div className="editor-grid">
              <div className="editor-card">
                <div className="editor-header">
                  <div className="editor-title"><span className="editor-number">01</span><div><strong>Original text</strong><small>INPUT SOURCE</small></div></div>
                  <button className="subtle-button" onClick={clearWorkspace}><Trash2 size={14} /> Clear</button>
                </div>
                <textarea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="Paste or type text containing personal information...

For example:
My name is Ivan Petrov. Contact me at ivan@example.com or +7 999 123-45-67."
                  maxLength={100000}
                />
                <div className="editor-footer">
                  <span><LockKeyhole size={13} /> Your text is sent to your DataMask API</span>
                  <span>{input.length.toLocaleString()} / 100,000</span>
                </div>
              </div>

              <div className="editor-card result-card">
                <div className="editor-header">
                  <div className="editor-title"><span className="editor-number result-number">02</span><div><strong>Protected output</strong><small>ANONYMIZED RESULT</small></div></div>
                  {result && (
                    <div className="export-actions">
                      <button className="subtle-button copy-button" onClick={copyResult}>
                        {copied ? <Check size={14} /> : <Copy size={14} />}
                        {copied ? 'Copied' : 'Copy'}
                      </button>
                      <button className="subtle-button" onClick={exportResultTxt}>Download TXT</button>
                      <button className="subtle-button" onClick={exportResultJson}>Download JSON</button>
                    </div>
                  )}
                </div>
                <div className={`result-area ${result ? 'has-result' : ''}`}>
                  {result ? <pre>{result.anonymized_text}</pre> : <div className="empty-result"><div className="empty-icon"><ShieldCheck size={27} /></div><strong>Your protected text will appear here</strong><p>Run anonymization to see the secured result.</p><div className="empty-lock"><LockKeyhole size={12} /> END-TO-END WORKFLOW</div></div>}
                </div>
                <div className="editor-footer">
                  <span><ShieldCheck size={13} /> Sensitive data masked</span>
                  <span>{result ? `${result.anonymized_text.length.toLocaleString()} characters` : 'Awaiting input'}</span>
                </div>
              </div>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {backgroundStatus && <div className="background-status"><Activity size={14} /> {backgroundStatus}</div>}

            <div className="action-row">
              <div className="helper-text"><Sparkles size={15} /> AI-powered pattern detection <span className="helper-separator">·</span> Instant processing</div>
              <div className="action-buttons">
                <button className="anonymize-button" onClick={anonymize} disabled={!input.trim() || loading || backgroundLoading}>
                  {loading ? <span className="spinner" /> : <><ShieldCheck size={17} /> Anonymize text <ArrowRight size={16} /></>}
                  {loading && 'Processing...'}
                </button>
                <button className="subtle-button background-button" onClick={anonymizeInBackground} disabled={!input.trim() || loading || backgroundLoading}>
                  {backgroundLoading ? <span className="spinner" /> : <Clock3 size={15} />}
                  {backgroundLoading ? 'In queue...' : 'Run in background'}
                </button>
              </div>
            </div>
          </section>

          <section className="bottom-grid">
            <div className="bottom-card detection-card">
              <div className="bottom-heading"><div><h3>Detection summary</h3><p>Personal data identified in your text</p></div><span className="summary-count">{result ? detectedTotal : '0'} found</span></div>
              {result && detectedTotal > 0 ? (
                <div className="category-list">
                  {Object.entries(result.detected).map(([name, count]) => {
                    const Icon = categoryIcons[name] || FileSearch
                    return <div className="category-item" key={name}><span className="category-icon"><Icon size={15} /></span><span className="category-name">{name.replace('_', ' ')}</span><strong>{count}</strong></div>
                  })}
                </div>
              ) : <div className="summary-empty"><FileSearch size={19} /><span>Run an analysis to see detected categories.</span></div>}
            </div>

            <div className="bottom-card tips-card">
              <div className="tips-icon"><LockKeyhole size={18} /></div>
              <div><h3>Privacy by design</h3><p>Use the synchronous workspace for quick anonymization. Background tasks are stored by the API in your PostgreSQL database.</p><span className="tips-link">Your data security matters <ShieldCheck size={13} /></span></div>
            </div>
          </section>

          <footer className="page-footer"><span>© 2026 DataMask. Built for privacy.</span><span><span className="footer-dot" /> All systems operational</span></footer>
        </div>)}
      </main>
    </div>
  )
}

export default App
