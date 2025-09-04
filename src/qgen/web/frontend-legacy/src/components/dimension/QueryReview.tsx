import { useState, useEffect } from 'react'
import { useNotification } from '../shared/Notification'

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
      showNotification('Selected queries approved successfully! ✅', 'success')
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
      showNotification('Selected queries rejected successfully! ❌', 'success')
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
    const baseClasses = "p-4 rounded-lg border-2 mb-4 transition-all"
    
    if (isSelected) {
      return `${baseClasses} border-blue-500 bg-blue-50 shadow-md`
    }
    
    switch (status) {
      case 'approved':
        return `${baseClasses} border-green-200 bg-green-50`
      case 'rejected':
        return `${baseClasses} border-red-200 bg-red-50`
      default:
        return `${baseClasses} border-gray-200 bg-white`
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved': return '✅'
      case 'rejected': return '❌'
      default: return '📝'
    }
  }

  return (
    <>
      <NotificationContainer />
      <div>
      {/* Floating Action Bar */}
      <div className="bg-white rounded-lg shadow-sm border p-4 mb-6 sticky top-4 z-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Selection Controls */}
          <div className="flex items-center space-x-4">
            <div className="flex space-x-2">
              <button
                onClick={selectAll}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
              >
                ☑️ All
              </button>
              <button
                onClick={selectNone}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
              >
                ☐ None
              </button>
            </div>
            
            <span className="text-sm text-gray-600">
              {selectedQueries.size === 0 
                ? 'No queries selected' 
                : `${selectedQueries.size} selected`
              }
            </span>
          </div>

          {/* Action Buttons */}
          {selectedQueries.size > 0 && (
            <div className="flex space-x-2">
              <button
                onClick={bulkApprove}
                disabled={loading}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                ✅ Approve
              </button>
              <button
                onClick={bulkReject}
                disabled={loading}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                ❌ Reject
              </button>
              {selectedQueries.size === 1 && (
                <button
                  onClick={() => {
                    const queryId = Array.from(selectedQueries)[0]
                    const query = queries.find(q => q.id === queryId)
                    if (query) startEdit(query)
                  }}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
                >
                  ✏️ Edit
                </button>
              )}
            </div>
          )}

          {/* Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All ({statusCounts.all})</option>
            <option value="pending">Pending ({statusCounts.pending}) 📝</option>
            <option value="approved">Approved ({statusCounts.approved}) ✅</option>
            <option value="rejected">Rejected ({statusCounts.rejected}) ❌</option>
          </select>
        </div>
      </div>

      {/* Query List */}
      <div className="space-y-4">
        {filteredQueries.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
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
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  
                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="text-lg">{getStatusIcon(query.status)}</span>
                      <span className="font-medium text-gray-900">
                        Query {query.id + 1}
                      </span>
                    </div>
                    
                    {isEditing ? (
                      <div className="space-y-3">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          className="w-full p-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                          rows={3}
                        />
                        <div className="flex space-x-2">
                          <button
                            onClick={saveEdit}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
                          >
                            💾 Save
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition-colors"
                          >
                            ❌ Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p className="text-gray-900 mb-2">{query.text}</p>
                        
                        {/* Tuple Information */}
                        <div className="text-sm text-gray-600">
                          <span className="font-medium">From tuple:</span>{' '}
                          {Object.entries(query.tuple_data).map(([key, value]) => (
                            <span key={key} className="mr-3">
                              {key}={value}
                            </span>
                          ))}
                        </div>
                        
                        {/* Individual Action Buttons */}
                        {!isSelected && (
                          <div className="flex space-x-2 mt-3">
                            <button
                              onClick={async () => {
                                await updateQueryStatus(query.id, 'approved')
                                onUpdate?.()
                              }}
                              className="text-sm bg-green-100 text-green-700 px-3 py-1 rounded hover:bg-green-200 transition-colors"
                            >
                              ✅ Approve
                            </button>
                            <button
                              onClick={async () => {
                                await updateQueryStatus(query.id, 'rejected')
                                onUpdate?.()
                              }}
                              className="text-sm bg-red-100 text-red-700 px-3 py-1 rounded hover:bg-red-200 transition-colors"
                            >
                              ❌ Reject
                            </button>
                            <button
                              onClick={() => startEdit(query)}
                              className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded hover:bg-blue-200 transition-colors"
                            >
                              ✏️ Edit
                            </button>
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