import React, { useState, useEffect, useCallback } from 'react'
import { useNotification } from '../shared/Notification'

interface HighlightedChunk {
  chunk_id: string
  chunk_text: string
  highlighted_html: string
  source_document: string
  highlight_source: 'original_fact' | 'answer_fact' | 'none'
  chunk_index: number
}

interface EnhancedRAGQuery {
  query_id: string
  query_text: string
  answer_fact: string
  source_chunk_ids: string[]
  difficulty?: string
  realism_rating?: number
  highlighted_chunks?: HighlightedChunk[]
}

interface SingleQueryReviewProps {
  queries: EnhancedRAGQuery[]
  projectName: string
  onComplete: (approvedQueries: string[]) => void
  onCancel: () => void
}

type ReviewAction = 'approved' | 'rejected' | 'edited' | 'skipped'

interface ReviewState {
  [queryId: string]: {
    action: ReviewAction
    editedQuery?: Partial<EnhancedRAGQuery>
  }
}

export const SingleQueryReview: React.FC<SingleQueryReviewProps> = ({
  queries,
  projectName,
  onComplete,
  onCancel
}) => {
  const { showNotification } = useNotification()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [reviewState, setReviewState] = useState<ReviewState>({})
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<Partial<EnhancedRAGQuery>>({})

  const currentQuery = queries[currentIndex]
  const progress = ((currentIndex + 1) / queries.length) * 100
  const currentReview = reviewState[currentQuery?.query_id]

  // Navigation functions
  const goToNext = useCallback(() => {
    if (currentIndex < queries.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setIsEditing(false)
    }
  }, [currentIndex, queries.length])

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setIsEditing(false)
    }
  }, [currentIndex])

  // Action handlers
  const handleApprove = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentQuery.query_id]: { action: 'approved' }
    }))
    showNotification('Query approved! ✅', 'success')
    goToNext()
  }, [currentQuery, goToNext, showNotification])

  const handleReject = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentQuery.query_id]: { action: 'rejected' }
    }))
    showNotification('Query rejected ❌', 'info')
    goToNext()
  }, [currentQuery, goToNext, showNotification])

  const handleSkip = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentQuery.query_id]: { action: 'skipped' }
    }))
    showNotification('Query skipped ⏩', 'info')
    goToNext()
  }, [currentQuery, goToNext, showNotification])

  const handleEdit = useCallback(() => {
    setEditForm({
      query_text: currentQuery.query_text,
      answer_fact: currentQuery.answer_fact,
      difficulty: currentQuery.difficulty,
      realism_rating: currentQuery.realism_rating
    })
    setIsEditing(true)
  }, [currentQuery])

  const handleSaveEdit = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentQuery.query_id]: { 
        action: 'edited',
        editedQuery: editForm
      }
    }))
    setIsEditing(false)
    showNotification('Query edited and approved! ✏️✅', 'success')
    goToNext()
  }, [currentQuery, editForm, goToNext, showNotification])

  const handleCancelEdit = useCallback(() => {
    setIsEditing(false)
    setEditForm({})
  }, [])

  const handleQuit = useCallback(() => {
    const approvedQueries = Object.entries(reviewState)
      .filter(([_, review]) => review.action === 'approved' || review.action === 'edited')
      .map(([queryId, _]) => queryId)

    if (approvedQueries.length > 0) {
      onComplete(approvedQueries)
    } else {
      onCancel()
    }
  }, [reviewState, onComplete, onCancel])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Don't handle if user is editing
      if (isEditing || event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return
      }

      const key = event.key.toLowerCase()
      
      switch (key) {
        case 'a':
          event.preventDefault()
          handleApprove()
          break
        case 'r':
          event.preventDefault()
          handleReject()
          break
        case 'e':
          event.preventDefault()
          handleEdit()
          break
        case 's':
          event.preventDefault()
          handleSkip()
          break
        case 'q':
        case 'escape':
          event.preventDefault()
          handleQuit()
          break
        case 'arrowleft':
          event.preventDefault()
          goToPrevious()
          break
        case 'arrowright':
          event.preventDefault()
          goToNext()
          break
      }
    }

    document.addEventListener('keydown', handleKeyPress)
    return () => document.removeEventListener('keydown', handleKeyPress)
  }, [isEditing, handleApprove, handleReject, handleEdit, handleSkip, handleQuit, goToPrevious, goToNext])

  if (!currentQuery) {
    return null
  }

  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty) {
      case 'multi-hop':
        return 'bg-purple-100 text-purple-800'
      case 'adversarial':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-green-100 text-green-800'
    }
  }

  const getReviewStatusIndicator = () => {
    if (!currentReview) return null
    
    const colors = {
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      edited: 'bg-yellow-100 text-yellow-800',
      skipped: 'bg-gray-100 text-gray-800'
    }
    
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colors[currentReview.action]}`}>
        {currentReview.action.charAt(0).toUpperCase() + currentReview.action.slice(1)}
      </span>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-6xl h-full max-h-[90vh] flex flex-col">
        
        {/* Compact Header */}
        <div className="bg-blue-600 text-white p-4 rounded-t-lg">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-lg font-semibold">Query Review</h2>
            <div className="flex items-center space-x-3">
              <span className="text-sm">Query {currentIndex + 1} of {queries.length}</span>
              {getReviewStatusIndicator()}
              <button 
                onClick={handleQuit}
                className="text-white hover:text-gray-200 text-lg leading-none"
                title="Quit (Q)"
              >
                ✕
              </button>
            </div>
          </div>
          
          {/* Compact Progress Bar */}
          <div className="w-full bg-blue-500 rounded-full h-2">
            <div 
              className="bg-white h-2 rounded-full transition-all duration-300" 
              style={{ width: `${progress}%` }}
            />
          </div>
          
          <div className="flex justify-between text-xs mt-1 opacity-90">
            <span>Progress: {Math.round(progress)}%</span>
            <span>
              Approved: {Object.values(reviewState).filter(r => r.action === 'approved' || r.action === 'edited').length}
            </span>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          
          {/* Query Details Panel */}
          {isEditing ? (
            <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded-lg">
              <h3 className="font-semibold text-yellow-800 mb-4">✏️ Editing Query</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Query Text</label>
                  <textarea
                    value={editForm.query_text || ''}
                    onChange={(e) => setEditForm(prev => ({ ...prev, query_text: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Answer Fact</label>
                  <textarea
                    value={editForm.answer_fact || ''}
                    onChange={(e) => setEditForm(prev => ({ ...prev, answer_fact: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={2}
                  />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {currentQuery.difficulty && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Difficulty</label>
                      <select
                        value={editForm.difficulty || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, difficulty: e.target.value }))}
                        className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="standard">Standard</option>
                        <option value="adversarial">Adversarial</option>
                        <option value="multi-hop">Multi-hop</option>
                      </select>
                    </div>
                  )}
                  
                  {currentQuery.realism_rating && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Realism Score (1-5)</label>
                      <input
                        type="number"
                        min="1"
                        max="5"
                        step="0.1"
                        value={editForm.realism_rating || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, realism_rating: parseFloat(e.target.value) }))}
                        className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  )}
                </div>
                
                <div className="flex space-x-3 pt-4">
                  <button
                    onClick={handleSaveEdit}
                    className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
                  >
                    ✅ Save & Approve
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-4 rounded-lg">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold text-gray-800 mb-3">Query</h3>
                  <p className="text-gray-700 text-lg leading-relaxed">{currentQuery.query_text}</p>
                </div>
                <div className="space-y-4">
                  <div>
                    <span className="text-sm font-medium text-gray-600">Answer Fact:</span>
                    <p className="text-gray-800 mt-1">{currentQuery.answer_fact}</p>
                  </div>
                  
                  <div className="flex flex-wrap gap-4">
                    {currentQuery.difficulty && (
                      <div>
                        <span className="text-sm font-medium text-gray-600">Difficulty:</span>
                        <span className={`ml-2 px-3 py-1 rounded text-xs font-medium ${getDifficultyColor(currentQuery.difficulty)}`}>
                          {currentQuery.difficulty}
                        </span>
                      </div>
                    )}
                    
                    {currentQuery.realism_rating && (
                      <div>
                        <span className="text-sm font-medium text-gray-600">Realism Score:</span>
                        <span className="ml-2 font-semibold text-blue-600">{currentQuery.realism_rating}/5</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="text-xs text-gray-500">
                    Query ID: {currentQuery.query_id.slice(0, 12)}...
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Source Chunks with Highlighting */}
          {currentQuery.highlighted_chunks && currentQuery.highlighted_chunks.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">
                📄 Source Context
                {currentQuery.highlighted_chunks.length > 1 && (
                  <span className="text-sm font-normal text-gray-500 ml-2">
                    ({currentQuery.highlighted_chunks.length} chunks)
                  </span>
                )}
              </h3>
              
              <div className="space-y-4">
                {currentQuery.highlighted_chunks.map((chunk, idx) => (
                  <div key={chunk.chunk_id} className="border border-gray-200 rounded-lg overflow-hidden shadow-sm">
                    <div className="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-medium text-gray-700">
                          {chunk.source_document}
                        </span>
                        {currentQuery.highlighted_chunks!.length > 1 && (
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                            Chunk {idx + 1}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-500">
                        Highlighting: {chunk.highlight_source.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="p-4">
                      <div 
                        className="text-gray-700 leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: chunk.highlighted_html }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Multi-hop Indicator */}
              {currentQuery.highlighted_chunks.length > 1 && (
                <div className="mt-4 bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-purple-600 text-lg">🔗</span>
                    <span className="text-purple-800 font-medium">Multi-hop Query</span>
                  </div>
                  <p className="text-purple-700 text-sm mt-2">
                    This query requires information from {currentQuery.highlighted_chunks.length} different chunks to be answered completely.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Compact Action Bar */}
        <div className="bg-gray-50 border-t p-3">
          <div className="flex justify-between items-center">
            
            {/* Navigation */}
            <div className="flex items-center space-x-2">
              <button
                onClick={goToPrevious}
                disabled={currentIndex === 0}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
              >
                ← Previous
              </button>
              <span className="text-sm text-gray-600 px-2">
                {currentIndex + 1} of {queries.length}
              </span>
              <button
                onClick={goToNext}
                disabled={currentIndex === queries.length - 1}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
              >
                Next →
              </button>
            </div>

            {/* Compact Action Buttons */}
            <div className="flex items-center space-x-2">
              <button 
                onClick={handleApprove}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
              >
                [A]pprove
              </button>
              
              <button 
                onClick={handleReject}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
              >
                [R]eject
              </button>
              
              <button 
                onClick={handleEdit}
                className="bg-yellow-600 text-white px-3 py-2 rounded hover:bg-yellow-700 transition-colors"
              >
                [E]dit
              </button>
              
              <button 
                onClick={handleSkip}
                className="bg-gray-600 text-white px-3 py-2 rounded hover:bg-gray-700 transition-colors"
              >
                [S]kip
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}