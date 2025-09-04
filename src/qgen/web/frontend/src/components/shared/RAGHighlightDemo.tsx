import React, { useState } from 'react'
import { ChunkViewer, type ChunkData } from './ChunkViewer'
import { FactGrid } from './FactCard'
import { type HighlightSpan, type HighlightType } from './ChunkHighlighter'
import { FileText, Search, Lightbulb } from 'lucide-react'

/**
 * Demo component showing RAG highlighting in action
 * This demonstrates how to integrate highlighting into your existing workflow
 */
export const RAGHighlightDemo: React.FC = () => {
  // Sample data that would come from your API
  const [_selectedHighlightId, setSelectedHighlightId] = useState<string | null>(null)
  const [selectedFactIds, setSelectedFactIds] = useState<Set<string>>(new Set())

  // Sample chunk data
  const sampleChunks: ChunkData[] = [
    {
      chunk_id: "library_policy_001",
      text: "The library is open Monday through Friday from 9 AM to 8 PM, and weekends from 10 AM to 6 PM. Holiday hours may vary and are posted on our website. Students can access the library 24/7 with their student ID card during exam periods.",
      source_document: "library_policy.pdf",
      section: "Operating Hours",
      metadata: {
        page: 1,
        confidence: 0.95,
        word_count: 45
      }
    },
    {
      chunk_id: "library_policy_002", 
      text: "Library members can borrow up to 10 books at a time for a period of 3 weeks. Books can be renewed online or at the circulation desk if no holds are placed. Late fees are $0.50 per day for regular books and $2.00 per day for reserve materials.",
      source_document: "library_policy.pdf",
      section: "Borrowing Rules",
      metadata: {
        page: 2,
        confidence: 0.88,
        word_count: 52
      }
    },
    {
      chunk_id: "library_services_001",
      text: "The reference section contains academic journals, encyclopedias, and specialized databases. Staff assistance is available during all operating hours. Research consultations can be scheduled in advance for complex projects requiring extensive database searches.",
      source_document: "library_services.pdf", 
      section: "Reference Services",
      metadata: {
        page: 1,
        confidence: 0.92,
        word_count: 38
      }
    }
  ]

  // Sample extracted facts
  const sampleFacts = [
    {
      fact_id: "fact_001",
      chunk_id: "library_policy_001", 
      fact_text: "The library is open Monday through Friday from 9 AM to 8 PM",
      extraction_confidence: 0.95,
      source_text: sampleChunks[0].text
    },
    {
      fact_id: "fact_002",
      chunk_id: "library_policy_001",
      fact_text: "Students can access the library 24/7 with their student ID card during exam periods", 
      extraction_confidence: 0.90,
      source_text: sampleChunks[0].text
    },
    {
      fact_id: "fact_003",
      chunk_id: "library_policy_002",
      fact_text: "Library members can borrow up to 10 books at a time for a period of 3 weeks",
      extraction_confidence: 0.88,
      source_text: sampleChunks[1].text
    },
    {
      fact_id: "fact_004", 
      chunk_id: "library_policy_002",
      fact_text: "Late fees are $0.50 per day for regular books",
      extraction_confidence: 0.85,
      source_text: sampleChunks[1].text
    },
    {
      fact_id: "fact_005",
      chunk_id: "library_services_001",
      fact_text: "Research consultations can be scheduled in advance for complex projects",
      extraction_confidence: 0.87,
      source_text: sampleChunks[2].text
    }
  ]

  // Create highlights from facts
  const factHighlights: HighlightSpan[] = sampleFacts.map(fact => ({
    id: fact.fact_id,
    text: fact.fact_text,
    type: 'fact' as HighlightType,
    metadata: {
      factId: fact.fact_id,
      confidence: fact.extraction_confidence,
      chunkId: fact.chunk_id
    }
  }))

  // Additional highlights for entities and relationships
  const entityHighlights: HighlightSpan[] = [
    {
      id: 'entity_001',
      text: 'student ID card',
      type: 'entity' as HighlightType,
      metadata: { type: 'credential' }
    },
    {
      id: 'entity_002', 
      text: 'circulation desk',
      type: 'entity' as HighlightType,
      metadata: { type: 'location' }
    },
    {
      id: 'entity_003',
      text: 'reference section', 
      type: 'entity' as HighlightType,
      metadata: { type: 'location' }
    }
  ]

  const allHighlights = [...factHighlights, ...entityHighlights]

  const handleHighlightClick = (highlight: HighlightSpan, chunkId?: string) => {
    console.log('Highlight clicked:', highlight, 'in chunk:', chunkId)
    setSelectedHighlightId(highlight.id)
    
    // If it's a fact highlight, you could automatically select the corresponding fact
    if (highlight.metadata?.factId) {
      const newSelected = new Set(selectedFactIds)
      if (newSelected.has(highlight.metadata.factId)) {
        newSelected.delete(highlight.metadata.factId)
      } else {
        newSelected.add(highlight.metadata.factId)
      }
      setSelectedFactIds(newSelected)
    }
  }

  const handleFactSelect = (factId: string) => {
    const newSelected = new Set(selectedFactIds)
    if (newSelected.has(factId)) {
      newSelected.delete(factId)
    } else {
      newSelected.add(factId)
    }
    setSelectedFactIds(newSelected)
  }

  const handleFactApprove = (factId: string) => {
    console.log('Approving fact:', factId)
    // Your approval logic here
  }

  const handleFactReject = (factId: string) => {
    console.log('Rejecting fact:', factId) 
    // Your rejection logic here
  }

  const handleChunkClick = (chunk: ChunkData) => {
    console.log('Chunk clicked:', chunk.chunk_id)
    // Could show detailed chunk view or navigate to chunk details
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          RAG Chunk Highlighting Demo
        </h1>
        <p className="text-gray-600">
          Interactive highlighting system for fact extraction and review
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border shadow-sm text-center">
          <div className="text-2xl font-bold text-blue-600">{sampleChunks.length}</div>
          <div className="text-sm text-gray-600 flex items-center justify-center space-x-1">
            <FileText className="h-4 w-4" />
            <span>Document Chunks</span>
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg border shadow-sm text-center">
          <div className="text-2xl font-bold text-green-600">{sampleFacts.length}</div>
          <div className="text-sm text-gray-600 flex items-center justify-center space-x-1">
            <Search className="h-4 w-4" />
            <span>Extracted Facts</span>
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg border shadow-sm text-center">
          <div className="text-2xl font-bold text-purple-600">{allHighlights.length}</div>
          <div className="text-sm text-gray-600">Total Highlights</div>
        </div>
        <div className="bg-white p-4 rounded-lg border shadow-sm text-center">
          <div className="text-2xl font-bold text-yellow-600">{selectedFactIds.size}</div>
          <div className="text-sm text-gray-600">Selected Facts</div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Left: Chunk Viewer */}
        <div>
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-gray-900 mb-2 flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>Document Chunks with Highlighting</span>
            </h2>
            <p className="text-sm text-gray-600">
              Source chunks with extracted facts and entities highlighted. 
              Click on highlights to see details.
            </p>
          </div>
          
          <ChunkViewer
            chunks={sampleChunks}
            highlights={allHighlights}
            showMetadata={true}
            onHighlightClick={handleHighlightClick}
            onChunkClick={handleChunkClick}
            initialChunkLimit={10}
          />
        </div>

        {/* Right: Fact Review */}
        <div>
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-gray-900 mb-2 flex items-center space-x-2">
              <Search className="h-5 w-5" />
              <span>Extracted Facts Review</span>
            </h2>
            <p className="text-sm text-gray-600">
              Review and approve extracted facts. Expand cards to see source context with highlighting.
            </p>
          </div>

          {/* Selection Controls */}
          <div className="bg-white rounded-lg border p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {selectedFactIds.size} of {sampleFacts.length} facts selected
              </div>
              <div className="space-x-2">
                <button
                  onClick={() => setSelectedFactIds(new Set(sampleFacts.map(f => f.fact_id)))}
                  className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
                >
                  Select All
                </button>
                <button
                  onClick={() => setSelectedFactIds(new Set())}
                  className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
                >
                  Clear
                </button>
                {selectedFactIds.size > 0 && (
                  <button
                    onClick={() => {
                      console.log('Bulk approving:', Array.from(selectedFactIds))
                      setSelectedFactIds(new Set())
                    }}
                    className="text-sm px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Approve Selected
                  </button>
                )}
              </div>
            </div>
          </div>

          <FactGrid
            facts={sampleFacts}
            selectedFactIds={selectedFactIds}
            onFactSelect={handleFactSelect}
            onFactApprove={handleFactApprove}
            onFactReject={handleFactReject}
            showActions={true}
            showSourceChunks={true}
            globalHighlights={entityHighlights} // Show entity highlights across all facts
          />
        </div>
      </div>

      {/* Usage Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center space-x-2">
          <Lightbulb className="h-5 w-5" />
          <span>How to Use This Interface</span>
        </h3>
        <div className="grid md:grid-cols-2 gap-4 text-sm text-blue-800">
          <div>
            <h4 className="font-medium mb-2">Chunk Viewer Features:</h4>
            <ul className="space-y-1 list-disc list-inside">
              <li>Search across all chunks</li>
              <li>Click highlights to see details</li>
              <li>View chunk metadata</li>
              <li>Expand long chunks</li>
              <li>Color-coded highlight types</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">Fact Review Features:</h4>
            <ul className="space-y-1 list-disc list-inside">
              <li>Select multiple facts</li>
              <li>Individual approve/reject actions</li>
              <li>View source context with highlighting</li>
              <li>Confidence scoring</li>
              <li>Bulk operations</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}