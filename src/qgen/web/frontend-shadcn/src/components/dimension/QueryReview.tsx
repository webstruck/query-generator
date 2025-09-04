import { useState, useEffect } from 'react'
import { useNotification } from '../shared/Notification'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ButtonWithShortcut } from '@/components/ui/button-with-shortcut'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { CheckCircle, XCircle, FileText } from 'lucide-react'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'

interface Query {
  id: number
  text: string
  status: string
  tuple_data: Record<string, string>
}

interface QueryReviewProps {
  projectName: string
  onUpdate?: () => void
}

export default function QueryReview({ projectName, onUpdate }: QueryReviewProps) {
  const [queries, setQueries] = useState<Query[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedQueries, setSelectedQueries] = useState<Set<number>>(new Set())
  const [filter, setFilter] = useState<string>('all')
  const [editingQuery, setEditingQuery] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const { showNotification, NotificationContainer } = useNotification()

  useEffect(() => {
    loadQueries()
  }, [projectName])

  const loadQueries = async () => {
    try {
      const response = await fetch(`/api/projects/${projectName}/queries/generated`)
      const data = await response.json()
      setQueries(data.queries)
    } catch (error) {
      console.error('Failed to load queries:', error)
    }
  }

  const updateQueryStatus = async (queryId: number, status: string, text?: string) => {
    try {
      const response = await fetch(`/api/projects/${projectName}/queries/${queryId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status, text })
      })
      
      if (!response.ok) {
        throw new Error('Failed to update query')
      }
      
      // Update local state immediately
      setQueries(prevQueries => 
        prevQueries.map(q => 
          q.id === queryId 
            ? { ...q, status, text: text || q.text }
            : q
        )
      )
    } catch (error) {
      console.error('Failed to update query:', error)
      throw error // Re-throw so bulk operations can handle the error
    }
  }

  const bulkApprove = async () => {
    setLoading(true)
    try {
      await fetch(`/api/projects/${projectName}/queries/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(Array.from(selectedQueries))
      })
      
      await loadQueries()
      setSelectedQueries(new Set())
      onUpdate?.() // Update parent dashboard
      showNotification('Selected queries approved successfully!', 'success')
    } catch (error) {
      showNotification(`Failed to approve queries: ${error}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const bulkReject = async () => {
    setLoading(true)
    try {
      // Update all selected queries to rejected status
      await Promise.all(
        Array.from(selectedQueries).map(queryId => 
          updateQueryStatus(queryId, 'rejected')
        )
      )
      setSelectedQueries(new Set())
      onUpdate?.() // Update parent dashboard
      showNotification('Selected queries rejected successfully!', 'success')
    } catch (error) {
      showNotification(`Failed to reject queries: ${error}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const startEdit = (query: Query) => {
    setEditingQuery(query.id)
    setEditText(query.text)
  }

  const saveEdit = async () => {
    if (editingQuery !== null) {
      await updateQueryStatus(editingQuery, 'approved', editText)
      setEditingQuery(null)
      setEditText('')
      onUpdate?.() // Update parent dashboard
    }
  }

  const cancelEdit = () => {
    setEditingQuery(null)
    setEditText('')
  }

  const toggleQuerySelection = (queryId: number) => {
    const newSelected = new Set(selectedQueries)
    if (newSelected.has(queryId)) {
      newSelected.delete(queryId)
    } else {
      newSelected.add(queryId)
    }
    setSelectedQueries(newSelected)
  }

  const selectAll = () => {
    const filteredIds = new Set(
      queries
        .filter(q => filter === 'all' || q.status === filter)
        .map(q => q.id)
    )
    setSelectedQueries(filteredIds)
  }

  const selectNone = () => {
    setSelectedQueries(new Set())
  }

  // Filter queries
  const filteredQueries = queries.filter(q => 
    filter === 'all' || q.status === filter
  )

  // Status counts
  const statusCounts = {
    all: queries.length,
    pending: queries.filter(q => q.status === 'pending').length,
    approved: queries.filter(q => q.status === 'approved').length,
    rejected: queries.filter(q => q.status === 'rejected').length,
  }

  const getQueryStatusStyle = (status: string, isSelected: boolean) => {
    const baseClasses = "p-4 rounded-lg border-2 mb-4 transition-all cursor-pointer"
    
    if (isSelected) {
      return `${baseClasses} border-primary bg-primary/5 shadow-md`
    }
    
    switch (status) {
      case 'approved':
        return `${baseClasses} border-green-500/50 bg-green-50/50 dark:bg-green-950/20`
      case 'rejected':
        return `${baseClasses} border-red-500/50 bg-red-50/50 dark:bg-red-950/20`
      default:
        return `${baseClasses} border-border bg-muted/50 hover:border-muted-foreground/50`
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved': return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'rejected': return <XCircle className="h-4 w-4 text-red-600" />
      default: return <FileText className="h-4 w-4 text-blue-600" />
    }
  }

  // Handler functions for keyboard shortcuts
  const bulkEdit = () => {
    if (selectedQueries.size === 1) {
      const queryId = Array.from(selectedQueries)[0]
      const query = queries.find(q => q.id === queryId)
      if (query) startEdit(query)
    }
  }

  const isEditing = editingQuery !== null

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      // Selection
      { keys: ['⌘', 'A'], handler: selectAll, description: 'Select all queries' },
      { keys: ['⌘', 'D'], handler: selectNone, description: 'Select none' },
      
      // Bulk actions (when queries selected)
      { keys: ['A'], handler: bulkApprove, description: 'Approve selected', enabled: selectedQueries.size > 0 },
      { keys: ['R'], handler: bulkReject, description: 'Reject selected', enabled: selectedQueries.size > 0 },
      { keys: ['E'], handler: bulkEdit, description: 'Edit selected', enabled: selectedQueries.size === 1 },
      
      // Edit mode
      { keys: ['⌘', 'S'], handler: saveEdit, description: 'Save edit', enabled: isEditing },
      { keys: ['Esc'], handler: cancelEdit, description: 'Cancel edit', enabled: isEditing }
    ],
    enabled: true
  })

  return (
    <>
      <NotificationContainer />
      <div>
      {/* Floating Action Bar */}
      <Card className="mb-6 sticky top-4 z-10">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Selection Controls */}
            <div className="flex items-center space-x-4">
              <div className="flex space-x-2">
                <ButtonWithShortcut
                  onClick={selectAll}
                  variant="outline"
                  size="sm"
                  shortcut={['⌘', 'A']}
                >
                  All
                </ButtonWithShortcut>
                <ButtonWithShortcut
                  onClick={selectNone}
                  variant="outline"
                  size="sm"
                  shortcut={['⌘', 'D']}
                >
                  None
                </ButtonWithShortcut>
              </div>
              
              <span className="text-sm text-muted-foreground">
                {selectedQueries.size === 0 
                  ? 'No queries selected' 
                  : `${selectedQueries.size} selected`
                }
              </span>
            </div>

          {/* Action Buttons */}
          {selectedQueries.size > 0 && (
            <div className="flex space-x-2">
              <ButtonWithShortcut
                onClick={bulkApprove}
                disabled={loading}
                variant="default"
                shortcut={['A']}
              >
                Approve
              </ButtonWithShortcut>
              <ButtonWithShortcut
                onClick={bulkReject}
                disabled={loading}
                variant="destructive"
                shortcut={['R']}
              >
                Reject
              </ButtonWithShortcut>
              {selectedQueries.size === 1 && (
                <ButtonWithShortcut
                  onClick={() => {
                    const queryId = Array.from(selectedQueries)[0]
                    const query = queries.find(q => q.id === queryId)
                    if (query) startEdit(query)
                  }}
                  variant="secondary"
                  shortcut={['E']}
                >
                  Edit
                </ButtonWithShortcut>
              )}
            </div>
          )}

          {/* Filter */}
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All ({statusCounts.all})</SelectItem>
              <SelectItem value="pending">
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4 text-blue-600" />
                  <span>Pending ({statusCounts.pending})</span>
                </div>
              </SelectItem>
              <SelectItem value="approved">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span>Approved ({statusCounts.approved})</span>
                </div>
              </SelectItem>
              <SelectItem value="rejected">
                <div className="flex items-center space-x-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span>Rejected ({statusCounts.rejected})</span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
          </div>
        </CardContent>
      </Card>

      {/* Query List */}
      <div className="space-y-4">
        {filteredQueries.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {queries.length === 0 
              ? 'No queries generated yet' 
              : `No ${filter} queries found`
            }
          </div>
        ) : (
          filteredQueries.map((query) => {
            const isSelected = selectedQueries.has(query.id)
            const isEditing = editingQuery === query.id
            
            return (
              <div
                key={query.id}
                className={getQueryStatusStyle(query.status, isSelected)}
              >
                <div className="flex items-start space-x-3">
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleQuerySelection(query.id)}
                    className="mt-1 h-4 w-4 rounded border-input text-primary focus:ring-primary"
                  />
                  
                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      {getStatusIcon(query.status)}
                      <Badge variant="secondary" className="font-medium">
                        Query #{query.id + 1}
                      </Badge>
                    </div>
                    
                    {isEditing ? (
                      <div className="space-y-3">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                          rows={3}
                        />
                        <div className="flex space-x-2">
                          <ButtonWithShortcut
                            onClick={saveEdit}
                            variant="default"
                            shortcut={['⌘', 'S']}
                          >
                            Save
                          </ButtonWithShortcut>
                          <ButtonWithShortcut
                            onClick={cancelEdit}
                            variant="outline"
                            shortcut={['Esc']}
                          >
                            Cancel
                          </ButtonWithShortcut>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p className="mb-2">{query.text}</p>
                        
                        {/* Tuple Information */}
                        <div className="text-sm text-muted-foreground mb-3">
                          <span className="font-medium">From tuple:</span>{' '}
                          <div className="flex flex-wrap gap-2 mt-1">
                            {Object.entries(query.tuple_data).map(([key, value]) => (
                              <Badge key={key} variant="outline" className="text-xs">
                                {key}={value}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        
                        {/* Individual Action Buttons */}
                        {!isSelected && (
                          <div className="flex space-x-2 mt-3">
                            <ButtonWithShortcut
                              onClick={async () => {
                                await updateQueryStatus(query.id, 'approved')
                                onUpdate?.()
                              }}
                              variant="secondary"
                              size="sm"
                              shortcut={['A']}
                              showShortcut={false}
                            >
                              Approve
                            </ButtonWithShortcut>
                            <ButtonWithShortcut
                              onClick={async () => {
                                await updateQueryStatus(query.id, 'rejected')
                                onUpdate?.()
                              }}
                              variant="outline"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              shortcut={['R']}
                              showShortcut={false}
                            >
                              Reject
                            </ButtonWithShortcut>
                            <ButtonWithShortcut
                              onClick={() => startEdit(query)}
                              variant="outline"
                              size="sm"
                              shortcut={['E']}
                              showShortcut={false}
                            >
                              Edit
                            </ButtonWithShortcut>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
      </div>
    </>
  )
}