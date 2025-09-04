import { useState, useEffect } from 'react'
import { useNotification } from '../shared/Notification'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ButtonWithShortcut } from '@/components/ui/button-with-shortcut'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Target } from 'lucide-react'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'

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
      showNotification('Selected tuples approved successfully!', 'success')
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
      showNotification('Selected tuples rejected successfully!', 'success')
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
      return `${baseClasses} border-primary bg-primary/5 shadow-md`
    }
    
    return `${baseClasses} border-border bg-muted/50 hover:border-muted-foreground/50 hover:shadow-sm`
  }

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      // Selection (only for generated tuples)
      { keys: ['⌘', 'A'], handler: selectAll, description: 'Select all tuples', enabled: stage === 'generated' },
      { keys: ['⌘', 'D'], handler: selectNone, description: 'Select none', enabled: stage === 'generated' },
      
      // Bulk actions (when tuples selected)
      { keys: ['A'], handler: bulkApprove, description: 'Approve selected', enabled: selectedTuples.size > 0 && stage === 'generated' },
      { keys: ['R'], handler: bulkReject, description: 'Reject selected', enabled: selectedTuples.size > 0 && stage === 'generated' }
    ],
    enabled: true
  })

  return (
    <>
      <NotificationContainer />
      <div>
        {/* Header with Stage Selection */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center">
                <Target className="mr-2 h-4 w-4" />
                Tuple Review
              </CardTitle>
              <Select value={stage} onValueChange={(value: 'generated' | 'approved') => setStage(value)}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="generated">Generated Tuples</SelectItem>
                  <SelectItem value="approved">Approved Tuples</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
        </Card>

        {/* Floating Action Bar - Only for Generated */}
        {stage === 'generated' && (
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
                    {selectedTuples.size === 0 
                      ? 'No tuples selected' 
                      : `${selectedTuples.size} selected`
                    }
                  </span>
                </div>

                {/* Action Buttons */}
                {selectedTuples.size > 0 && (
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
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tuple List */}
        <div className="space-y-3">
          {tuples.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
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
                        className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
                        onClick={(e) => e.stopPropagation()}
                      />
                    )}
                    
                    {/* Tuple Number */}
                    <Badge variant="secondary" className="font-medium">
                      #{index + 1}
                    </Badge>
                    
                    {/* Tuple Values */}
                    <div className="flex flex-wrap gap-3 flex-1">
                      {Object.entries(tuple.values).map(([key, value]) => (
                        <div key={key} className="flex items-center space-x-1">
                          <span className="text-muted-foreground text-sm">{key}:</span>
                          <Badge variant="outline" className="font-medium">
                            {value}
                          </Badge>
                        </div>
                      ))}
                    </div>

                    {/* Individual Actions - Only for Generated */}
                    {stage === 'generated' && !isSelected && (
                      <div className="flex space-x-2">
                        <ButtonWithShortcut
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedTuples(new Set([index]))
                            bulkApprove()
                          }}
                          variant="secondary"
                          size="sm"
                          className="text-sm"
                          shortcut={['A']}
                          showShortcut={false}
                        >
                          Approve
                        </ButtonWithShortcut>
                        <ButtonWithShortcut
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedTuples(new Set([index]))
                            bulkReject()
                          }}
                          variant="outline"
                          size="sm"
                          className="text-sm text-destructive hover:text-destructive"
                          shortcut={['R']}
                          showShortcut={false}
                        >
                          Reject
                        </ButtonWithShortcut>
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