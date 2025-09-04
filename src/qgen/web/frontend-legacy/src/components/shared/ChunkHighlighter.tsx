import React from 'react'
import Highlighter from 'react-highlight-words'

/**
 * Color scheme for different highlight types
 * Follows WCAG accessibility guidelines with sufficient contrast
 */
export const HighlightColors = {
  // Primary fact highlighting
  fact: {
    background: '#fef3c7', // yellow-100
    border: '#f59e0b',     // yellow-500
    text: '#92400e'        // yellow-800
  },
  // Multi-hop relationships
  relationship: {
    background: '#ddd6fe', // violet-200
    border: '#8b5cf6',     // violet-500
    text: '#5b21b6'        // violet-800
  },
  // Key entities
  entity: {
    background: '#d1fae5', // emerald-100
    border: '#10b981',     // emerald-500
    text: '#065f46'        // emerald-800
  },
  // Search matches
  search: {
    background: '#fee2e2', // red-100
    border: '#ef4444',     // red-500
    text: '#991b1b'        // red-800
  },
  // Active/selected highlight
  active: {
    background: '#dbeafe', // blue-100
    border: '#3b82f6',     // blue-500
    text: '#1e40af'        // blue-800
  }
} as const

export type HighlightType = keyof typeof HighlightColors

export interface HighlightSpan {
  /** Unique identifier for this highlight */
  id: string
  /** Text to highlight */
  text: string
  /** Type determines color scheme */
  type: HighlightType
  /** Optional metadata */
  metadata?: {
    factId?: string
    confidence?: number
    chunkId?: string
    [key: string]: any
  }
}

export interface ChunkHighlighterProps {
  /** The full text content to highlight within */
  text: string
  /** Array of text spans to highlight */
  highlights: HighlightSpan[]
  /** Callback when a highlight is clicked */
  onHighlightClick?: (highlight: HighlightSpan) => void
  /** CSS class name for the container */
  className?: string
  /** Whether to show tooltips on hover */
  showTooltips?: boolean
  /** Active highlight ID (for emphasis) */
  activeHighlightId?: string
}

/**
 * Custom highlight component with accessibility features
 */
const CustomHighlight: React.FC<{
  children: React.ReactNode
  highlightIndex: number
  highlight: HighlightSpan
  onClick?: (highlight: HighlightSpan) => void
  isActive?: boolean
  showTooltip?: boolean
}> = ({ children, highlight, onClick, isActive, showTooltip }) => {
  const colors = isActive ? HighlightColors.active : HighlightColors[highlight.type]
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onClick?.(highlight)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick?.(highlight)
    }
  }

  return (
    <mark
      className={`
        inline-block px-1 py-0.5 rounded-sm border transition-all duration-200
        ${onClick ? 'cursor-pointer hover:shadow-sm' : ''}
        ${isActive ? 'ring-2 ring-blue-300 ring-opacity-50' : ''}
      `}
      style={{
        backgroundColor: colors.background,
        borderColor: colors.border,
        color: colors.text
      }}
      onClick={onClick ? handleClick : undefined}
      onKeyDown={onClick ? handleKeyDown : undefined}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : 'mark'}
      aria-label={`Highlighted ${highlight.type}: ${children}`}
      title={showTooltip ? `${highlight.type} (${highlight.metadata?.confidence ? `${Math.round(highlight.metadata.confidence * 100)}% confidence` : 'click for details'})` : undefined}
    >
      {children}
    </mark>
  )
}

/**
 * Main chunk highlighter component
 * Highlights multiple text spans within a larger text block
 */
export const ChunkHighlighter: React.FC<ChunkHighlighterProps> = ({
  text,
  highlights,
  onHighlightClick,
  className = '',
  showTooltips = true,
  activeHighlightId
}) => {
  // Extract search words from highlights
  const searchWords = highlights.map(h => h.text)
  
  // Create a map for quick highlight lookup
  const highlightMap = new Map(highlights.map(h => [h.text, h]))

  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      <Highlighter
        highlightClassName=""  // We handle styling in CustomHighlight
        searchWords={searchWords}
        autoEscape={true}
        textToHighlight={text}
        highlightTag={({ children, highlightIndex }) => {
          const searchWord = searchWords[highlightIndex]
          const highlight = highlightMap.get(searchWord)
          
          if (!highlight) return <span>{children}</span>
          
          return (
            <CustomHighlight
              highlightIndex={highlightIndex}
              highlight={highlight}
              onClick={onHighlightClick}
              isActive={activeHighlightId === highlight.id}
              showTooltip={showTooltips}
            >
              {children}
            </CustomHighlight>
          )
        }}
      />
    </div>
  )
}

/**
 * Simplified component for basic text search highlighting
 */
export const SearchHighlighter: React.FC<{
  text: string
  searchTerm: string
  className?: string
}> = ({ text, searchTerm, className = '' }) => {
  if (!searchTerm.trim()) {
    return <div className={className}>{text}</div>
  }

  return (
    <div className={className}>
      <Highlighter
        highlightClassName="bg-yellow-200 text-yellow-900 px-1 rounded"
        searchWords={[searchTerm]}
        autoEscape={true}
        textToHighlight={text}
      />
    </div>
  )
}

/**
 * Legend component to explain highlight colors
 */
export const HighlightLegend: React.FC<{
  types: HighlightType[]
  className?: string
}> = ({ types, className = '' }) => {
  const typeLabels: Record<HighlightType, string> = {
    fact: 'Extracted Facts',
    relationship: 'Multi-hop Relations',
    entity: 'Key Entities', 
    search: 'Search Matches',
    active: 'Selected'
  }

  return (
    <div className={`flex flex-wrap gap-3 ${className}`}>
      {types.map(type => (
        <div key={type} className="flex items-center gap-2">
          <div 
            className="w-4 h-4 rounded border"
            style={{
              backgroundColor: HighlightColors[type].background,
              borderColor: HighlightColors[type].border
            }}
          />
          <span className="text-sm text-gray-700">{typeLabels[type]}</span>
        </div>
      ))}
    </div>
  )
}