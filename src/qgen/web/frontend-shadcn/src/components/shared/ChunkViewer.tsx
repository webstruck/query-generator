import React, { useState, useMemo, useCallback } from 'react'
import { ChunkHighlighter, type HighlightSpan, HighlightLegend, SearchHighlighter } from './ChunkHighlighter'
import { FileText, Folder } from 'lucide-react'

export interface ChunkData {
  chunk_id: string
  text: string
  source_document?: string
  section?: string
  metadata?: Record<string, any>
}

export interface ChunkViewerProps {
  /** Array of chunks to display */
  chunks: ChunkData[]
  /** Highlights to show across chunks */
  highlights: HighlightSpan[]
  /** Search term for additional highlighting */
  searchTerm?: string
  /** Maximum number of chunks to show initially */
  initialChunkLimit?: number
  /** Whether to show chunk metadata */
  showMetadata?: boolean
  /** Callback when a highlight is clicked */
  onHighlightClick?: (highlight: HighlightSpan, chunkId: string) => void
  /** Callback when a chunk is clicked */
  onChunkClick?: (chunk: ChunkData) => void
  /** Additional CSS classes */
  className?: string
}

/**
 * Individual chunk display component with highlighting
 */
const ChunkCard: React.FC<{
  chunk: ChunkData
  highlights: HighlightSpan[]
  searchTerm?: string
  showMetadata?: boolean
  onHighlightClick?: (highlight: HighlightSpan, chunkId: string) => void
  onChunkClick?: (chunk: ChunkData) => void
}> = ({ chunk, highlights, searchTerm, showMetadata, onHighlightClick, onChunkClick }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Filter highlights relevant to this chunk
  const chunkHighlights = useMemo(() => 
    highlights.filter(h => 
      h.metadata?.chunkId === chunk.chunk_id || 
      chunk.text.includes(h.text)
    ), [highlights, chunk]
  )

  const handleHighlightClick = useCallback((highlight: HighlightSpan) => {
    onHighlightClick?.(highlight, chunk.chunk_id)
  }, [onHighlightClick, chunk.chunk_id])

  const handleChunkClick = useCallback(() => {
    onChunkClick?.(chunk)
  }, [onChunkClick, chunk])

  const truncatedText = chunk.text.length > 300 
    ? chunk.text.substring(0, 300) + "..."
    : chunk.text

  const displayText = isExpanded ? chunk.text : truncatedText
  const hasHighlights = chunkHighlights.length > 0

  return (
    <div className="bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div 
        className="p-4 border-b cursor-pointer hover:bg-gray-50"
        onClick={handleChunkClick}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h3 className="text-sm font-medium text-gray-900">
              {chunk.chunk_id}
            </h3>
            {hasHighlights && (
              <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full">
                {chunkHighlights.length} highlight{chunkHighlights.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          
          {showMetadata && (
            <div className="text-xs text-gray-500 space-x-2">
              {chunk.source_document && (
                <span className="flex items-center space-x-1">
                  <FileText className="h-4 w-4" />
                  <span>{chunk.source_document}</span>
                </span>
              )}
              {chunk.section && (
                <span className="flex items-center space-x-1">
                  <Folder className="h-4 w-4" />
                  <span>{chunk.section}</span>
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Highlight Legend */}
        {hasHighlights && (
          <div className="mb-3">
            <HighlightLegend 
              types={[...new Set(chunkHighlights.map(h => h.type))]}
              className="text-xs"
            />
          </div>
        )}

        {/* Text Content with Highlighting */}
        <div className="prose prose-sm max-w-none">
          {hasHighlights || searchTerm ? (
            searchTerm && !hasHighlights ? (
              <SearchHighlighter 
                text={displayText}
                searchTerm={searchTerm}
              />
            ) : (
              <ChunkHighlighter
                text={displayText}
                highlights={chunkHighlights}
                onHighlightClick={handleHighlightClick}
                showTooltips={true}
              />
            )
          ) : (
            <p className="text-gray-700 leading-relaxed">{displayText}</p>
          )}
        </div>

        {/* Expand/Collapse */}
        {chunk.text.length > 300 && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              setIsExpanded(!isExpanded)
            }}
            className="mt-3 text-sm text-blue-600 hover:text-blue-800 underline"
          >
            {isExpanded ? 'Show Less' : 'Show More'}
          </button>
        )}

        {/* Metadata */}
        {showMetadata && chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
          <details className="mt-4">
            <summary className="text-sm font-medium text-gray-600 cursor-pointer hover:text-gray-800">
              Metadata
            </summary>
            <div className="mt-2 p-3 bg-gray-50 rounded text-xs space-y-1">
              {Object.entries(chunk.metadata).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="font-medium text-gray-600">{key}:</span>
                  <span className="text-gray-800">{String(value)}</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}

/**
 * Main chunk viewer component with virtual scrolling for performance
 */
export const ChunkViewer: React.FC<ChunkViewerProps> = ({
  chunks,
  highlights,
  searchTerm,
  initialChunkLimit = 10,
  showMetadata = true,
  onHighlightClick,
  onChunkClick,
  className = ''
}) => {
  const [visibleChunkCount, setVisibleChunkCount] = useState(initialChunkLimit)
  const [searchFilter, setSearchFilter] = useState('')

  // Filter chunks based on search
  const filteredChunks = useMemo(() => {
    if (!searchFilter.trim()) return chunks
    
    return chunks.filter(chunk => 
      chunk.text.toLowerCase().includes(searchFilter.toLowerCase()) ||
      chunk.chunk_id.toLowerCase().includes(searchFilter.toLowerCase()) ||
      chunk.source_document?.toLowerCase().includes(searchFilter.toLowerCase()) ||
      chunk.section?.toLowerCase().includes(searchFilter.toLowerCase())
    )
  }, [chunks, searchFilter])

  const visibleChunks = filteredChunks.slice(0, visibleChunkCount)
  const hasMore = visibleChunkCount < filteredChunks.length

  const loadMore = useCallback(() => {
    setVisibleChunkCount(prev => Math.min(prev + 10, filteredChunks.length))
  }, [filteredChunks.length])

  // Statistics
  const totalHighlights = highlights.length
  const chunksWithHighlights = filteredChunks.filter(chunk => 
    highlights.some(h => 
      h.metadata?.chunkId === chunk.chunk_id || 
      chunk.text.includes(h.text)
    )
  ).length

  if (chunks.length === 0) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <div className="text-gray-500">
          <p className="text-lg mb-2">No chunks available</p>
          <p className="text-sm">Upload some document chunks to get started</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with Search and Stats */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Search */}
          <div className="flex-1 max-w-md">
            <input
              type="text"
              placeholder="Search chunks..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Stats */}
          <div className="flex items-center space-x-6 text-sm text-gray-600">
            <div>
              <span className="font-medium">{filteredChunks.length}</span> chunk{filteredChunks.length !== 1 ? 's' : ''}
            </div>
            <div>
              <span className="font-medium">{totalHighlights}</span> highlight{totalHighlights !== 1 ? 's' : ''}
            </div>
            <div>
              <span className="font-medium">{chunksWithHighlights}</span> highlighted chunk{chunksWithHighlights !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
      </div>

      {/* Global Highlight Legend */}
      {highlights.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Highlight Legend</h4>
          <HighlightLegend 
            types={[...new Set(highlights.map(h => h.type))]}
          />
        </div>
      )}

      {/* Chunks Grid */}
      <div className="grid gap-4">
        {visibleChunks.map(chunk => (
          <ChunkCard
            key={chunk.chunk_id}
            chunk={chunk}
            highlights={highlights}
            searchTerm={searchTerm}
            showMetadata={showMetadata}
            onHighlightClick={onHighlightClick}
            onChunkClick={onChunkClick}
          />
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="text-center">
          <button
            onClick={loadMore}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Load More Chunks ({filteredChunks.length - visibleChunkCount} remaining)
          </button>
        </div>
      )}

      {/* Performance Note */}
      {chunks.length > 50 && (
        <div className="text-xs text-gray-500 text-center p-4 bg-gray-50 rounded">
          Showing {visibleChunks.length} of {filteredChunks.length} chunks for optimal performance
        </div>
      )}
    </div>
  )
}