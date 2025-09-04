import React, { useState } from 'react'
import { ChunkHighlighter, type HighlightSpan, HighlightLegend, type HighlightType } from './ChunkHighlighter'

export interface FactCardProps {
  /** Fact information */
  fact: {
    fact_id: string
    chunk_id: string
    fact_text: string
    extraction_confidence: number
    source_text?: string // The original chunk text
  }
  /** Index for display */
  index: number
  /** Whether this fact is selected */
  isSelected?: boolean
  /** Selection handler */
  onSelect?: (factId: string) => void
  /** Individual action handlers */
  onApprove?: (factId: string) => void
  onReject?: (factId: string) => void
  /** Whether to show individual action buttons */
  showActions?: boolean
  /** Whether to show the source chunk with highlighting */
  showSourceChunk?: boolean
  /** Additional highlights to show in the source chunk */
  additionalHighlights?: HighlightSpan[]
}

/**
 * Enhanced fact card with chunk highlighting capabilities
 */
export const FactCard: React.FC<FactCardProps> = ({
  fact,
  index,
  isSelected = false,
  onSelect,
  onApprove,
  onReject,
  showActions = true,
  showSourceChunk: _showSourceChunk = false,
  additionalHighlights = []
}) => {
  const [isExpanded, setIsExpanded] = useState(false)
  
  const handleCardClick = () => {
    onSelect?.(fact.fact_id)
  }

  const handleApprove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onApprove?.(fact.fact_id)
  }

  const handleReject = (e: React.MouseEvent) => {
    e.stopPropagation()
    onReject?.(fact.fact_id)
  }

  const toggleExpanded = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsExpanded(!isExpanded)
  }

  // Create highlight for the extracted fact
  const factHighlight: HighlightSpan = {
    id: `fact-${fact.fact_id}`,
    text: fact.fact_text,
    type: 'fact' as HighlightType,
    metadata: {
      factId: fact.fact_id,
      confidence: fact.extraction_confidence,
      chunkId: fact.chunk_id
    }
  }

  // Combine all highlights
  const allHighlights = [factHighlight, ...additionalHighlights]

  const getCardStyle = () => {
    const baseClasses = "p-4 rounded-lg border-2 mb-3 transition-all cursor-pointer"
    
    if (isSelected) {
      return `${baseClasses} border-blue-500 bg-blue-50 shadow-md`
    }
    
    return `${baseClasses} border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm`
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High'
    if (confidence >= 0.6) return 'Medium'
    return 'Low'
  }

  return (
    <div className={getCardStyle()} onClick={handleCardClick}>
      <div className="flex items-start space-x-4">
        {/* Checkbox */}
        {onSelect && (
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onSelect(fact.fact_id)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-1"
            onClick={(e) => e.stopPropagation()}
          />
        )}
        
        {/* Fact Number */}
        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded font-medium text-sm shrink-0">
          #{index + 1}
        </span>
        
        {/* Fact Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between mb-2">
            <p className="text-sm font-medium text-gray-900 leading-relaxed">
              {fact.fact_text}
            </p>
            
            {/* Confidence Badge */}
            <div className="ml-3 shrink-0">
              <span className={`text-xs font-medium px-2 py-1 rounded-full bg-gray-100 ${getConfidenceColor(fact.extraction_confidence)}`}>
                {getConfidenceLabel(fact.extraction_confidence)} ({(fact.extraction_confidence * 100).toFixed(1)}%)
              </span>
            </div>
          </div>
          
          {/* Metadata */}
          <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
            <span>Chunk: {fact.chunk_id}</span>
            
            {fact.source_text && (
              <button
                onClick={toggleExpanded}
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {isExpanded ? 'Hide' : 'Show'} Source Context
              </button>
            )}
          </div>

          {/* Expanded Source Context */}
          {isExpanded && fact.source_text && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg border">
              <div className="mb-2">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-gray-700">Source Chunk Context</h4>
                  <HighlightLegend 
                    types={allHighlights.map(h => h.type)}
                    className="text-xs"
                  />
                </div>
              </div>
              
              <ChunkHighlighter
                text={fact.source_text}
                highlights={allHighlights}
                className="text-sm leading-relaxed"
                onHighlightClick={(highlight) => {
                  console.log('Clicked highlight:', highlight)
                  // Could trigger additional actions like showing fact details
                }}
              />
            </div>
          )}
        </div>

        {/* Individual Actions */}
        {showActions && (
          <div className="flex flex-col space-y-2 shrink-0">
            <button
              onClick={handleApprove}
              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition-colors"
              title="Approve this fact"
            >
              Approve
            </button>
            <button
              onClick={handleReject}
              className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
              title="Reject this fact"
            >
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Grid layout for displaying multiple fact cards with highlighting
 */
export interface FactGridProps {
  facts: Array<{
    fact_id: string
    chunk_id: string
    fact_text: string
    extraction_confidence: number
    source_text?: string
  }>
  selectedFactIds?: Set<string>
  onFactSelect?: (factId: string) => void
  onFactApprove?: (factId: string) => void
  onFactReject?: (factId: string) => void
  showActions?: boolean
  showSourceChunks?: boolean
  /** Common highlights to show across all facts */
  globalHighlights?: HighlightSpan[]
}

export const FactGrid: React.FC<FactGridProps> = ({
  facts,
  selectedFactIds = new Set(),
  onFactSelect,
  onFactApprove,
  onFactReject,
  showActions = true,
  showSourceChunks = false,
  globalHighlights = []
}) => {
  if (facts.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No facts to display</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {facts.map((fact, index) => (
        <FactCard
          key={fact.fact_id}
          fact={fact}
          index={index}
          isSelected={selectedFactIds.has(fact.fact_id)}
          onSelect={onFactSelect}
          onApprove={onFactApprove}
          onReject={onFactReject}
          showActions={showActions}
          showSourceChunk={showSourceChunks}
          additionalHighlights={globalHighlights}
        />
      ))}
    </div>
  )
}