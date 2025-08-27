import { useState, useEffect } from 'react'
import { useNotification } from '../shared/Notification'

interface Tuple {
  values: Record<string, string>
}

interface TupleReviewProps {
  projectName: string
}

export default function TupleReview({ projectName }: TupleReviewProps) {
  const [tuples, setTuples] = useState<Tuple[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedTuples, setSelectedTuples] = useState<Set<number>>(new Set())
  const [stage, setStage] = useState<'generated' | 'approved'>('generated')
  const { showNotification, NotificationContainer } = useNotification()

  useEffect(() => {
    loadTuples()
  }, [projectName, stage])

  const loadTuples = async () => {
    try {
      const response = await fetch(`/api/projects/${projectName}/tuples/${stage}`)
      const data = await response.json()
      setTuples(data.tuples || [])
    } catch (error) {
      console.error('Failed to load tuples:', error)
    }
  }

  const bulkApprove = async () => {
    setLoading(true)
    try {
      // Get selected tuples
      const selectedTupleData = Array.from(selectedTuples).map(index => tuples[index])
      
      await fetch(`/api/projects/${projectName}/tuples/approved`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tuples: selectedTupleData })
      })
      
      await loadTuples()
      setSelectedTuples(new Set())
      showNotification('Selected tuples approved successfully! ✅', 'success')
    } catch (error) {
      showNotification(`Failed to approve tuples: ${error}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const bulkReject = async () => {
    setLoading(true)
    try {
      // For simplicity, rejecting means removing from generated list
      const remainingTuples = tuples.filter((_, index) => !selectedTuples.has(index))
      
      await fetch(`/api/projects/${projectName}/tuples/generated`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tuples: remainingTuples })
      })
      
      await loadTuples()
      setSelectedTuples(new Set())
      showNotification('Selected tuples rejected successfully! ❌', 'success')
    } catch (error) {
      showNotification(`Failed to reject tuples: ${error}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const toggleTupleSelection = (index: number) => {
    const newSelected = new Set(selectedTuples)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedTuples(newSelected)
  }

  const selectAll = () => {
    const allIndices = new Set(tuples.map((_, index) => index))
    setSelectedTuples(allIndices)
  }

  const selectNone = () => {
    setSelectedTuples(new Set())
  }

  const getTupleStatusStyle = (isSelected: boolean) => {
    const baseClasses = "p-4 rounded-lg border-2 mb-3 transition-all cursor-pointer"
    
    if (isSelected) {
      return `${baseClasses} border-blue-500 bg-blue-50 shadow-md`
    }
    
    return `${baseClasses} border-gray-200 bg-gray-50 hover:border-gray-300 hover:shadow-sm`
  }

  return (
    <>
      <NotificationContainer />
      <div>
        {/* Header with Stage Selection */}
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-gray-900">🎯 Tuple Review</h3>
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value as 'generated' | 'approved')}
            className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="generated">Generated Tuples</option>
            <option value="approved">Approved Tuples</option>
          </select>
        </div>

        {/* Floating Action Bar - Only for Generated */}
        {stage === 'generated' && (
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
                  {selectedTuples.size === 0 
                    ? 'No tuples selected' 
                    : `${selectedTuples.size} selected`
                  }
                </span>
              </div>

              {/* Action Buttons */}
              {selectedTuples.size > 0 && (
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
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tuple List */}
        <div className="space-y-3">
          {tuples.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No {stage} tuples found
            </div>
          ) : (
            tuples.map((tuple, index) => {
              const isSelected = selectedTuples.has(index)
              
              return (
                <div
                  key={index}
                  className={getTupleStatusStyle(isSelected)}
                  onClick={() => stage === 'generated' && toggleTupleSelection(index)}
                >
                  <div className="flex items-center space-x-4">
                    {/* Checkbox - Only for Generated */}
                    {stage === 'generated' && (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleTupleSelection(index)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        onClick={(e) => e.stopPropagation()}
                      />
                    )}
                    
                    {/* Tuple Number */}
                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded font-medium text-sm">
                      #{index + 1}
                    </span>
                    
                    {/* Tuple Values */}
                    <div className="flex flex-wrap gap-3 flex-1">
                      {Object.entries(tuple.values).map(([key, value]) => (
                        <div key={key} className="flex items-center space-x-1">
                          <span className="text-gray-600 text-sm">{key}:</span>
                          <span className="bg-white px-2 py-1 rounded border text-gray-900 font-medium text-sm">
                            {value}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Individual Actions - Only for Generated */}
                    {stage === 'generated' && !isSelected && (
                      <div className="flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedTuples(new Set([index]))
                            bulkApprove()
                          }}
                          className="text-sm bg-green-100 text-green-700 px-3 py-1 rounded hover:bg-green-200 transition-colors"
                        >
                          ✅ Approve
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedTuples(new Set([index]))
                            bulkReject()
                          }}
                          className="text-sm bg-red-100 text-red-700 px-3 py-1 rounded hover:bg-red-200 transition-colors"
                        >
                          ❌ Reject
                        </button>
                      </div>
                    )}
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