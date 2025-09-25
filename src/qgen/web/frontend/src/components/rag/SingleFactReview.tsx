import React, { useState, useCallback, useMemo } from 'react'
import { Edit, FileText, TrendingUp, Filter } from 'lucide-react'
import { useNotification } from '../shared/Notification'
import { ButtonWithShortcut } from '../ui/button-with-shortcut'
import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface Fact {
  fact_id: string
  chunk_id: string
  fact_text: string
  extraction_confidence: number
  source_text?: string
  highlighted_source?: string
  status?: string  // "pending", "approved", "rejected"
}

interface FactReviewResult {
  factId: string
  action: ReviewAction
  editedFact?: Partial<Fact>
}

interface SingleFactReviewProps {
  facts: Fact[]
  projectName: string
  onComplete: (approvedFacts: string[], allReviewResults: FactReviewResult[]) => void
  onCancel: () => void
}

type ReviewAction = 'approved' | 'rejected' | 'edited' | 'skipped'
type StatusFilter = 'all' | 'pending' | 'approved' | 'rejected' | 'skipped'

interface ReviewState {
  [factId: string]: {
    action: ReviewAction
    editedFact?: Partial<Fact>
  }
}

export const SingleFactReview: React.FC<SingleFactReviewProps> = ({
  facts,
  onComplete,
  onCancel
}) => {
  const { showNotification } = useNotification()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [reviewState, setReviewState] = useState<ReviewState>({})
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<Partial<Fact>>({})
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  // Filter facts based on status filter
  const filteredFacts = useMemo(() => {
    if (statusFilter === 'all') return facts
    
    return facts.filter(fact => {
      const dbStatus = fact.status || 'pending'
      const sessionReview = reviewState[fact.fact_id]
      
      if (sessionReview) {
        // Use session review action for filtering
        return sessionReview.action === statusFilter
      }
      
      // Use database status for filtering
      return dbStatus === statusFilter
    })
  }, [facts, statusFilter, reviewState])

  const currentFact = filteredFacts[currentIndex]
  const progress = filteredFacts.length > 0 ? ((currentIndex + 1) / filteredFacts.length) * 100 : 0
  const currentReview = reviewState[currentFact?.fact_id]

  // Navigation functions
  const goToNext = useCallback(() => {
    if (currentIndex < filteredFacts.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setIsEditing(false)
    }
  }, [currentIndex, filteredFacts.length])

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setIsEditing(false)
    }
  }, [currentIndex])

  // Reset current index when filter changes
  const handleFilterChange = useCallback((newFilter: StatusFilter) => {
    setStatusFilter(newFilter)
    setCurrentIndex(0)
    setIsEditing(false)
  }, [])

  // Action handlers
  const handleApprove = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentFact.fact_id]: { action: 'approved' }
    }))
    showNotification('Fact approved!', 'success')
    goToNext()
  }, [currentFact, goToNext, showNotification])

  const handleReject = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentFact.fact_id]: { action: 'rejected' }
    }))
    showNotification('Fact rejected', 'info')
    goToNext()
  }, [currentFact, goToNext, showNotification])

  const handleSkip = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentFact.fact_id]: { action: 'skipped' }
    }))
    showNotification('Fact skipped', 'info')
    goToNext()
  }, [currentFact, goToNext, showNotification])

  const handleEdit = useCallback(() => {
    setEditForm({
      fact_text: currentFact.fact_text,
      extraction_confidence: currentFact.extraction_confidence
    })
    setIsEditing(true)
  }, [currentFact])

  const handleSaveEdit = useCallback(() => {
    setReviewState(prev => ({
      ...prev,
      [currentFact.fact_id]: { 
        action: 'edited',
        editedFact: editForm
      }
    }))
    setIsEditing(false)
    showNotification('Fact edited and approved!', 'success')
    goToNext()
  }, [currentFact, editForm, goToNext, showNotification])

  const handleCancelEdit = useCallback(() => {
    setIsEditing(false)
    setEditForm({})
  }, [])

  const handleQuit = useCallback(() => {
    const approvedFacts = Object.entries(reviewState)
      .filter(([, review]) => review.action === 'approved' || review.action === 'edited')
      .map(([factId]) => factId)

    const allReviewResults = Object.entries(reviewState).map(([factId, review]) => ({
      factId,
      action: review.action,
      editedFact: review.editedFact
    }))

    if (approvedFacts.length > 0 || allReviewResults.length > 0) {
      onComplete(approvedFacts, allReviewResults)
    } else {
      onCancel()
    }
  }, [reviewState, onComplete, onCancel])

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      {
        keys: ['A'],
        handler: () => handleApprove(),
        description: 'Approve fact',
        enabled: !isEditing
      },
      {
        keys: ['R'],
        handler: () => handleReject(),
        description: 'Reject fact',
        enabled: !isEditing
      },
      {
        keys: ['E'],
        handler: () => handleEdit(),
        description: 'Edit fact',
        enabled: !isEditing
      },
      {
        keys: ['S'],
        handler: () => handleSkip(),
        description: 'Skip fact',
        enabled: !isEditing
      },
      {
        keys: ['^', 'S'],
        handler: () => isEditing ? handleSaveEdit() : undefined,
        description: 'Save edit',
        enabled: isEditing
      },
      {
        keys: ['Esc'],
        handler: () => isEditing ? handleCancelEdit() : handleQuit(),
        description: isEditing ? 'Cancel edit' : 'Quit review'
      },
      {
        keys: ['←'],
        handler: () => goToPrevious(),
        description: 'Previous fact',
        enabled: !isEditing
      },
      {
        keys: ['→'],
        handler: () => goToNext(),
        description: 'Next fact',
        enabled: !isEditing
      }
    ],
    enabled: true
  })

  if (!currentFact || filteredFacts.length === 0) {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <div className="bg-background rounded-lg shadow-2xl w-96 p-6 border">
          <h2 className="text-lg font-semibold mb-4">No Facts Found</h2>
          <p className="text-muted-foreground mb-4">
            {statusFilter === 'all' 
              ? 'No facts available for review.'
              : `No facts found with status "${statusFilter}".`
            }
          </p>
          <div className="flex space-x-3">
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-2 bg-muted text-foreground rounded hover:bg-muted/80"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) {
      return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300'
    } else if (confidence >= 0.6) {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300'
    } else {
      return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300'
    }
  }

  const getReviewStatusIndicator = () => {
    // Show current database status first, then local review status
    const dbStatus = currentFact?.status
    const localReview = currentReview
    
    if (localReview) {
      const colors = {
        approved: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
        rejected: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300',
        edited: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300',
        skipped: 'bg-muted text-muted-foreground'
      }
      
      return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${colors[localReview.action]}`}>
          {localReview.action.charAt(0).toUpperCase() + localReview.action.slice(1)} (Session)
        </span>
      )
    }
    
    if (dbStatus && dbStatus !== 'pending') {
      const colors = {
        approved: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
        rejected: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300'
      }
      
      return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${colors[dbStatus as keyof typeof colors] || 'bg-muted text-muted-foreground'}`}>
          {dbStatus.charAt(0).toUpperCase() + dbStatus.slice(1)}
        </span>
      )
    }
    
    return (
      <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300">
        Pending Review
      </span>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-background rounded-lg shadow-2xl w-full max-w-6xl h-full max-h-[90vh] flex flex-col border">
        
        {/* Compact Header */}
        <div className="bg-primary text-primary-foreground p-4 rounded-t-lg">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center space-x-4">
              <h2 className="text-lg font-semibold">Fact Review</h2>
              
              {/* Status Filter Dropdown */}
              <div className="flex items-center space-x-2">
                <Filter className="h-4 w-4" />
                <select
                  value={statusFilter}
                  onChange={(e) => handleFilterChange(e.target.value as StatusFilter)}
                  className="bg-primary-foreground/10 text-primary-foreground border border-primary-foreground/20 rounded px-2 py-1 text-sm"
                >
                  <option value="all">All ({facts.length})</option>
                  <option value="pending">Pending ({facts.filter(f => (f.status || 'pending') === 'pending').length})</option>
                  <option value="approved">Approved ({facts.filter(f => (f.status || 'pending') === 'approved').length})</option>
                  <option value="rejected">Rejected ({facts.filter(f => (f.status || 'pending') === 'rejected').length})</option>
                  <option value="skipped">Skipped ({Object.values(reviewState).filter(r => r.action === 'skipped').length})</option>
                </select>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <span className="text-sm">
                Fact {currentIndex + 1} of {filteredFacts.length}
                {statusFilter !== 'all' && (
                  <span className="text-primary-foreground/80 ml-1">
                    (filtered)
                  </span>
                )}
              </span>
              {getReviewStatusIndicator()}
              <button 
                onClick={handleQuit}
                className="text-primary-foreground hover:text-primary-foreground/80 text-lg leading-none"
                title="Quit (Q)"
              >
                ×
              </button>
            </div>
          </div>
          
          {/* Compact Progress Bar */}
          <div className="w-full bg-primary/20 rounded-full h-2">
            <div 
              className="bg-primary-foreground h-2 rounded-full transition-all duration-300" 
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
          
          {/* Fact Details Panel */}
          {isEditing ? (
            <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded-lg dark:bg-yellow-900/20 dark:border-yellow-600">
              <h3 className="font-semibold text-yellow-800 dark:text-yellow-300 mb-4 flex items-center gap-2">
                <Edit className="h-4 w-4" />
                Editing Fact
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Fact Text</label>
                  <textarea
                    value={editForm.fact_text || ''}
                    onChange={(e) => setEditForm(prev => ({ ...prev, fact_text: e.target.value }))}
                    className="w-full p-3 border border-border rounded-lg focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground"
                    rows={4}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Extraction Confidence (0-1)</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={editForm.extraction_confidence || ''}
                    onChange={(e) => setEditForm(prev => ({ ...prev, extraction_confidence: parseFloat(e.target.value) }))}
                    className="w-full p-2 border border-border rounded focus:ring-2 focus:ring-ring bg-background text-foreground"
                  />
                </div>
                
                <div className="flex space-x-3 pt-4">
                  <ButtonWithShortcut
                    onClick={handleSaveEdit}
                    shortcut="save"
                    className="bg-green-600 text-white hover:bg-green-700 px-6"
                  >
                    Save & Approve
                  </ButtonWithShortcut>
                  <ButtonWithShortcut
                    onClick={handleCancelEdit}
                    shortcut="cancel"
                    variant="outline"
                    className="px-6"
                  >
                    Cancel
                  </ButtonWithShortcut>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Status Warning for already approved/rejected facts */}
              {currentFact.status && currentFact.status !== 'pending' && !currentReview && (
                <div className={`border-l-4 p-4 rounded-lg ${
                  currentFact.status === 'approved' 
                    ? 'bg-green-50 border-green-500 dark:bg-green-900/20 dark:border-green-600' 
                    : 'bg-red-50 border-red-500 dark:bg-red-900/20 dark:border-red-600'
                }`}>
                  <p className={`text-sm font-medium ${
                    currentFact.status === 'approved' 
                      ? 'text-green-800 dark:text-green-300' 
                      : 'text-red-800 dark:text-red-300'
                  }`}>
                    ⚠️ This fact has already been {currentFact.status}. Any changes you make will override the previous decision.
                  </p>
                </div>
              )}
              
              <div className="bg-gradient-to-r from-primary/10 to-primary/5 border-l-4 border-primary p-4 rounded-lg">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <h3 className="font-semibold text-foreground mb-3">Extracted Fact</h3>
                    <p className="text-foreground text-lg leading-relaxed">{currentFact.fact_text}</p>
                  </div>
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-4">
                      <div>
                        <span className="text-sm font-medium text-muted-foreground">Confidence:</span>
                        <span className={`ml-2 px-3 py-1 rounded text-xs font-medium ${getConfidenceColor(currentFact.extraction_confidence)}`}>
                          {(currentFact.extraction_confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      
                      <div>
                        <span className="text-sm font-medium text-muted-foreground">Chunk ID:</span>
                        <span className="ml-2 font-mono text-sm text-primary">{currentFact.chunk_id.slice(0, 8)}...</span>
                      </div>
                    </div>
                    
                    <div className="text-xs text-muted-foreground">
                      Fact ID: {currentFact.fact_id.slice(0, 12)}...
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Source Text */}
          {currentFact.source_text && (
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Source Context
              </h3>
              
              <div className="border border-border rounded-lg overflow-hidden shadow-sm">
                <div className="bg-muted px-4 py-3 border-b border-border flex justify-between items-center">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-medium text-foreground">
                      Original Source Text
                    </span>
                    <span className="bg-primary/20 text-primary px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      Confidence: {(currentFact.extraction_confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  {currentFact.highlighted_source ? (
                    <div 
                      className="text-foreground leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: currentFact.highlighted_source }}
                    />
                  ) : (
                    <div className="text-foreground leading-relaxed">
                      {currentFact.source_text}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Compact Action Bar */}
        <div className="bg-muted border-t border-border p-3">
          <div className="flex justify-between items-center">
            
            {/* Navigation */}
            <div className="flex items-center space-x-2">
              <ButtonWithShortcut
                onClick={goToPrevious}
                disabled={currentIndex === 0}
                shortcut="previous"
                variant="outline"
                size="sm"
                className="disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </ButtonWithShortcut>
              <span className="text-sm text-muted-foreground px-2">
                {currentIndex + 1} of {filteredFacts.length}
              </span>
              <ButtonWithShortcut
                onClick={goToNext}
                disabled={currentIndex === filteredFacts.length - 1}
                shortcut="next"
                variant="outline" 
                size="sm"
                className="disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </ButtonWithShortcut>
            </div>

            {/* Compact Action Buttons */}
            <div className="flex items-center space-x-2">
              <ButtonWithShortcut 
                onClick={handleApprove}
                shortcut="approve"
                className="bg-green-600 text-white hover:bg-green-700"
              >
                Approve
              </ButtonWithShortcut>
              
              <ButtonWithShortcut 
                onClick={handleReject}
                shortcut="reject"
                className="bg-red-600 text-white hover:bg-red-700"
              >
                Reject
              </ButtonWithShortcut>
              
              <ButtonWithShortcut 
                onClick={handleEdit}
                shortcut="edit"
                className="bg-yellow-600 text-white hover:bg-yellow-700"
              >
                Edit
              </ButtonWithShortcut>
              
              <ButtonWithShortcut 
                onClick={handleSkip}
                shortcut="skip"
                variant="outline"
                className="text-muted-foreground hover:bg-muted/80"
              >
                Skip
              </ButtonWithShortcut>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}