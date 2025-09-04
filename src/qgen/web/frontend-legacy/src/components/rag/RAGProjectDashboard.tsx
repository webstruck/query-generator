import React, { useState, useEffect } from 'react'
import { type RAGProject } from '../ProjectSelector'
import { useNotification } from '../shared/Notification'
import Highlighter from 'react-highlight-words'
import { SingleQueryReview } from './SingleQueryReview'

interface RAGProjectDashboardProps {
  project: RAGProject
  onBack: () => void
}

interface OperationStatus {
  operation: string
  current: number
  total: number
  message: string
  progress: number
  completed: boolean
}

interface ChunkFile {
  filename: string
  chunks_count: number
  file_size: number
  error?: string
}

interface Fact {
  fact_id: string
  chunk_id: string
  fact_text: string
  extraction_confidence: number
  source_text?: string
  highlighted_source?: string
}

interface RAGQuery {
  query_id: string
  query_text: string
  answer_fact: string
  source_chunk_ids: string[]
  difficulty: string
  realism_rating?: number
}

type ActiveTab = 'overview' | 'chunks' | 'facts' | 'queries' | 'export'

// Simple inline components for consistent design
const SimpleStatusCard: React.FC<{ title: string; count: number; subtitle: string }> = ({ title, count, subtitle }) => (
  <div className="bg-white p-4 rounded-lg border shadow-sm">
    <h3 className="text-sm font-medium text-gray-500">{title}</h3>
    <p className="text-2xl font-bold text-gray-900">{count}</p>
    <p className="text-sm text-gray-600">{subtitle}</p>
  </div>
)

const SimpleProgressBar: React.FC<{ current: number; total: number; label: string }> = ({ current, total, label }) => {
  const percentage = total > 0 ? (current / total) * 100 : 0
  return (
    <div className="w-full">
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span>{current}/{total}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  )
}

const SimpleFileUpload: React.FC<{ onFileUpload: (files: FileList) => void; acceptedTypes: string; description: string }> = ({ onFileUpload, acceptedTypes, description }) => {
  const [isDragging, setIsDragging] = useState(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files)
    }
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-6 text-center ${
        isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
      }`}
      onDragOver={(e) => e.preventDefault()}
      onDragEnter={() => setIsDragging(true)}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <p className="text-gray-600 mb-2">{description}</p>
      <input
        type="file"
        accept={acceptedTypes}
        onChange={handleFileSelect}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />
    </div>
  )
}


export const RAGProjectDashboard: React.FC<RAGProjectDashboardProps> = ({ project, onBack: _onBack }) => {
  const { showNotification, NotificationContainer } = useNotification()
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview')
  const [_projectData, setProjectData] = useState<RAGProject>(project)
  const [operationStatus, setOperationStatus] = useState<OperationStatus | null>(null)
  const [provider, setProvider] = useState<string>('')
  const [providers, setProviders] = useState<{available: string[], auto_detected: string}>({available: [], auto_detected: ''})
  const [_loading, _setLoading] = useState(false)
  
  // Data states
  const [chunkFiles, setChunkFiles] = useState<ChunkFile[]>([])
  const [facts, setFacts] = useState<{ [stage: string]: Fact[] }>({})
  const [queries, setQueries] = useState<{ [stage: string]: RAGQuery[] }>({})
  const [selectedFacts, setSelectedFacts] = useState<Set<string>>(new Set())
  const [selectedQueries, setSelectedQueries] = useState<Set<string>>(new Set())
  const [factStage, setFactStage] = useState<'generated' | 'approved'>('generated')
  const [isQueryReviewOpen, setIsQueryReviewOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    loadProjectData()
    loadProviders()
  }, [project.name, refreshKey])

  const loadProviders = async () => {
    try {
      const response = await fetch('/api/providers')
      const data = await response.json()
      setProviders(data)
      setProvider(data.auto_detected || data.available[0] || '')
    } catch (error) {
      console.error('Failed to load providers:', error)
    }
  }

  const loadProjectData = async () => {
    try {
      // Load project details
      const projectResponse = await fetch(`/api/rag-projects/${project.name}`)
      if (projectResponse.ok) {
        const projectData = await projectResponse.json()
        setProjectData(projectData)
      }

      // Load chunks info
      const chunksResponse = await fetch(`/api/rag-projects/${project.name}/chunks`)
      if (chunksResponse.ok) {
        const chunksData = await chunksResponse.json()
        setChunkFiles(chunksData.chunks_files || [])
      }

      // Load facts
      try {
        const [generatedFacts, approvedFacts] = await Promise.all([
          fetch(`/api/rag-projects/${project.name}/facts/generated`).then(r => r.ok ? r.json() : { facts: [] }),
          fetch(`/api/rag-projects/${project.name}/facts/approved`).then(r => r.ok ? r.json() : { facts: [] })
        ])
        setFacts({
          generated: generatedFacts.facts || [],
          approved: approvedFacts.facts || []
        })
      } catch (e) {
        console.warn('Could not load facts:', e)
      }

      // Load queries
      try {
        const [generatedQueries, approvedQueries, multihopQueries] = await Promise.all([
          fetch(`/api/rag-projects/${project.name}/queries/generated`).then(r => r.ok ? r.json() : { queries: [] }),
          fetch(`/api/rag-projects/${project.name}/queries/approved`).then(r => r.ok ? r.json() : { queries: [] }),
          fetch(`/api/rag-projects/${project.name}/queries/generated_multihop`).then(r => r.ok ? r.json() : { queries: [] })
        ])
        
        const newQueries = {
          generated: generatedQueries.queries || [],
          approved: approvedQueries.queries || [],
          multihop: multihopQueries.queries || []
        }
        
        console.log(`📊 Loaded queries - Generated: ${newQueries.generated.length}, Approved: ${newQueries.approved.length}, Multihop: ${newQueries.multihop.length}`)
        setQueries(newQueries)
      } catch (e) {
        console.warn('Could not load queries:', e)
      }

    } catch (error) {
      console.error('Error loading project data:', error)
      showNotification('Failed to load project data', 'error')
    }
  }

  const pollOperationStatus = async (operation: string) => {
    try {
      const response = await fetch(`/api/rag-projects/${project.name}/status/${operation}`)
      if (response.ok) {
        const status = await response.json()
        setOperationStatus(status)
        
        if (status.completed) {
          console.log(`✅ Operation ${operation} completed, refreshing data...`)
          showNotification(status.message, 'success')
          setOperationStatus(null)
          await loadProjectData() // Refresh data and wait for completion
          setRefreshKey(prev => prev + 1) // Force re-render
          console.log(`🔄 Data refresh completed for ${operation}`)
          return true
        }
        return false
      } else {
        setOperationStatus(null)
        return true // Stop polling if no active operation
      }
    } catch (error) {
      console.error('Error polling status:', error)
      setOperationStatus(null)
      return true
    }
  }

  const startStatusPolling = (operation: string) => {
    const poll = async () => {
      const shouldStop = await pollOperationStatus(operation)
      if (!shouldStop) {
        setTimeout(poll, 2000) // Poll every 2 seconds
      }
    }
    poll()
  }

  const handleFileUpload = async (files: FileList) => {
    const file = files[0]
    if (!file.name.endsWith('.jsonl')) {
      showNotification('Please upload a JSONL file', 'error')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`/api/rag-projects/${project.name}/chunks/upload`, {
        method: 'POST',
        body: formData
      })

      const result = await response.json()
      
      if (response.ok) {
        showNotification(result.message, 'success')
        loadProjectData()
      } else {
        showNotification(result.detail || 'Upload failed', 'error')
      }
    } catch (error) {
      console.error('Upload error:', error)
      showNotification('Upload failed', 'error')
    }
  }

  const handleExtractFacts = async () => {
    if (!provider) {
      showNotification('Please select an LLM provider', 'error')
      return
    }

    if (getChunksCount() === 0) {
      showNotification('Please upload document chunks first', 'error')
      return
    }

    try {
      const response = await fetch(`/api/rag-projects/${project.name}/extract-facts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          provider,
          chunks_dir: 'chunks'
        })
      })

      const result = await response.json()
      
      if (response.ok) {
        showNotification('Fact extraction started', 'info')
        startStatusPolling('extract_facts')
        // Switch to facts tab to show progress
        setActiveTab('facts')
      } else {
        showNotification(result.detail || 'Failed to start fact extraction', 'error')
      }
    } catch (error) {
      console.error('Extract facts error:', error)
      showNotification(`Failed to start fact extraction: ${error.message}`, 'error')
    }
  }

  const handleGenerateQueries = async (multihop: boolean = false) => {
    if (!provider) {
      showNotification('Please select an LLM provider', 'error')
      return
    }

    const endpoint = multihop ? 'generate-multihop' : 'generate-queries'
    const operation = multihop ? 'generate_multihop' : 'generate_queries'

    try {
      const response = await fetch(`/api/rag-projects/${project.name}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider })
      })

      const result = await response.json()
      
      if (response.ok) {
        showNotification(`${multihop ? 'Multi-hop q' : 'Q'}uery generation started`, 'info')
        startStatusPolling(operation)
      } else {
        showNotification(result.detail || 'Failed to start query generation', 'error')
      }
    } catch (error) {
      console.error('Generate queries error:', error)
      showNotification('Failed to start query generation', 'error')
    }
  }

  const handleApproveFacts = async () => {
    if (selectedFacts.size === 0) {
      showNotification('Please select facts to approve', 'error')
      return
    }

    try {
      const response = await fetch(`/api/rag-projects/${project.name}/facts/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: Array.from(selectedFacts) })
      })

      const result = await response.json()
      
      if (response.ok) {
        showNotification(result.message, 'success')
        setSelectedFacts(new Set())
        loadProjectData()
      } else {
        showNotification(result.detail || 'Failed to approve facts', 'error')
      }
    } catch (error) {
      console.error('Approve facts error:', error)
      showNotification('Failed to approve facts', 'error')
    }
  }

  const handleApproveQueries = async () => {
    if (selectedQueries.size === 0) {
      showNotification('Please select queries to approve', 'error')
      return
    }

    try {
      const response = await fetch(`/api/rag-projects/${project.name}/queries/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: Array.from(selectedQueries) })
      })

      const result = await response.json()
      
      if (response.ok) {
        showNotification(result.message, 'success')
        setSelectedQueries(new Set())
        loadProjectData()
      } else {
        showNotification(result.detail || 'Failed to approve queries', 'error')
      }
    } catch (error) {
      console.error('Approve queries error:', error)
      showNotification('Failed to approve queries', 'error')
    }
  }

  const handleStartSingleQueryReview = () => {
    setIsQueryReviewOpen(true)
  }

  const handleQueryReviewComplete = async (approvedQueryIds: string[]) => {
    if (approvedQueryIds.length > 0) {
      try {
        const response = await fetch(`/api/rag-projects/${project.name}/queries/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_ids: approvedQueryIds })
        })

        const result = await response.json()
        
        if (response.ok) {
          showNotification(`${result.message} ✅`, 'success')
          loadProjectData()
        } else {
          showNotification(result.detail || 'Failed to approve queries', 'error')
        }
      } catch (error) {
        console.error('Approve queries error:', error)
        showNotification('Failed to approve queries', 'error')
      }
    }
    setIsQueryReviewOpen(false)
  }

  const handleQueryReviewCancel = () => {
    setIsQueryReviewOpen(false)
  }

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const response = await fetch(`/api/rag-projects/${project.name}/export/${format}`)
      const result = await response.json()
      
      if (response.ok) {
        showNotification(result.message, 'success')
      } else {
        showNotification(result.detail || 'Export failed', 'error')
      }
    } catch (error) {
      console.error('Export error:', error)
      showNotification('Export failed', 'error')
    }
  }

  const getChunksCount = () => chunkFiles.reduce((sum, file) => sum + file.chunks_count, 0)
  const getGeneratedFactsCount = () => facts.generated?.length || 0
  const getApprovedFactsCount = () => facts.approved?.length || 0
  const getGeneratedQueriesCount = () => (queries.generated?.length || 0) + (queries.multihop?.length || 0)
  const getApprovedQueriesCount = () => queries.approved?.length || 0

  const renderChunksStage = () => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-gray-900">📄 Upload Chunks</h3>
        <SimpleStatusCard
          title="Total Chunks"
          count={getChunksCount()}
          subtitle={`${chunkFiles.length} files`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h4 className="text-md font-medium text-gray-900 mb-4">Upload JSONL Files</h4>
          <SimpleFileUpload
            onFileUpload={handleFileUpload}
            acceptedTypes=".jsonl"
            description="Upload JSONL files containing your document chunks"
          />
        </div>

        <div>
          <h4 className="text-md font-medium text-gray-900 mb-4">Uploaded Files</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {chunkFiles.length === 0 ? (
              <p className="text-gray-500 italic">No files uploaded yet</p>
            ) : (
              chunkFiles.map((file, index) => (
                <div key={index} className="bg-gray-50 p-3 rounded border">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{file.filename}</p>
                      <p className="text-sm text-gray-600">
                        {file.chunks_count} chunks • {(file.file_size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    {file.error && (
                      <span className="text-red-500 text-sm">⚠️ {file.error}</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )

  const renderFactsStage = () => {
    const currentFacts = factStage === 'generated' ? facts.generated : facts.approved
    
    const selectAllFacts = () => {
      const allFactIds = new Set(currentFacts.map(fact => fact.fact_id))
      setSelectedFacts(allFactIds)
    }

    const selectNoneFacts = () => {
      setSelectedFacts(new Set())
    }

    const handleIndividualApprove = async (factId: string) => {
      try {
        const response = await fetch(`/api/rag-projects/${project.name}/facts/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_ids: [factId] })
        })

        const result = await response.json()
        
        if (response.ok) {
          showNotification('Fact approved successfully! ✅', 'success')
          loadProjectData()
        } else {
          showNotification(result.detail || 'Failed to approve fact', 'error')
        }
      } catch (error) {
        console.error('Individual approve error:', error)
        showNotification('Failed to approve fact', 'error')
      }
    }

    const handleIndividualReject = async (factId: string) => {
      // For now, just remove from selection
      const newSelected = new Set(selectedFacts)
      newSelected.delete(factId)
      setSelectedFacts(newSelected)
      showNotification('Fact rejected', 'info')
    }


    return (
      <div className="space-y-6">
        {/* Header with Stage Selection */}
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-gray-900">🔍 Fact Review</h3>
          <select
            value={factStage}
            onChange={(e) => setFactStage(e.target.value as 'generated' | 'approved')}
            className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="generated">Generated Facts</option>
            <option value="approved">Approved Facts</option>
          </select>
        </div>

        {currentFacts.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">
                {factStage === 'generated' ? 'No facts generated yet' : 'No facts approved yet'}
              </p>
              {factStage === 'generated' && (
                <button
                  onClick={handleExtractFacts}
                  disabled={getChunksCount() === 0 || !provider || !!operationStatus}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  🔍 Extract Facts
                </button>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Floating Action Bar - Only for Generated */}
            {factStage === 'generated' && (
              <div className="bg-white rounded-lg shadow-sm border p-4 mb-6 sticky top-4 z-10">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  {/* Selection Controls */}
                  <div className="flex items-center space-x-4">
                    <div className="flex space-x-2">
                      <button
                        onClick={selectAllFacts}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
                      >
                        ☑️ All
                      </button>
                      <button
                        onClick={selectNoneFacts}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
                      >
                        ☐ None
                      </button>
                    </div>
                    
                    <span className="text-sm text-gray-600">
                      {selectedFacts.size === 0 
                        ? 'No facts selected' 
                        : `${selectedFacts.size} selected`
                      }
                    </span>
                  </div>

                  {/* Action Buttons */}
                  {selectedFacts.size > 0 && (
                    <div className="flex space-x-2">
                      <button
                        onClick={handleApproveFacts}
                        disabled={_loading}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors disabled:opacity-50"
                      >
                        ✅ Approve Selected
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Facts List with Simple Highlighting */}
            <div className="space-y-3">
              {currentFacts.map((fact, index) => {
                const isSelected = selectedFacts.has(fact.fact_id)
                
                const getFactStatusStyle = (isSelected: boolean) => {
                  const baseClasses = "p-4 rounded-lg border-2 mb-3 transition-all cursor-pointer"
                  
                  if (isSelected) {
                    return `${baseClasses} border-blue-500 bg-blue-50 shadow-md`
                  }
                  
                  return `${baseClasses} border-gray-200 bg-gray-50 hover:border-gray-300 hover:shadow-sm`
                }
                
                return (
                  <div
                    key={fact.fact_id}
                    className={getFactStatusStyle(isSelected)}
                    onClick={() => factStage === 'generated' && setSelectedFacts(prev => {
                      const newSelected = new Set(prev)
                      if (newSelected.has(fact.fact_id)) {
                        newSelected.delete(fact.fact_id)
                      } else {
                        newSelected.add(fact.fact_id)
                      }
                      return newSelected
                    })}
                  >
                    <div className="flex items-start space-x-4">
                      {/* Checkbox - Only for Generated */}
                      {factStage === 'generated' && (
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => setSelectedFacts(prev => {
                            const newSelected = new Set(prev)
                            if (newSelected.has(fact.fact_id)) {
                              newSelected.delete(fact.fact_id)
                            } else {
                              newSelected.add(fact.fact_id)
                            }
                            return newSelected
                          })}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-1"
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                      
                      {/* Fact Number */}
                      <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded font-medium text-sm">
                        #{index + 1}
                      </span>
                      
                      {/* Fact Content */}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 mb-2">{fact.fact_text}</p>
                        
                        {/* Source Context with Model2Vec-based Highlighting */}
                        {fact.source_text && (
                          <div className="mt-2 p-3 bg-gray-50 rounded border">
                            <p className="text-xs text-gray-500 mb-1">Source Context (Model2Vec similarity):</p>
                            <div 
                              className="text-sm text-gray-700"
                              dangerouslySetInnerHTML={{ 
                                __html: fact.highlighted_source || fact.source_text 
                              }}
                            />
                          </div>
                        )}
                        
                        <p className="text-xs text-gray-500 mt-2">
                          Chunk: {fact.chunk_id} • Confidence: {(fact.extraction_confidence * 100).toFixed(1)}%
                        </p>
                      </div>

                      {/* Individual Actions - Only for Generated */}
                      {factStage === 'generated' && (
                        <div className="flex space-x-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleIndividualApprove(fact.fact_id)
                            }}
                            className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition-colors"
                          >
                            ✅ Approve
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleIndividualReject(fact.fact_id)
                            }}
                            className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
                          >
                            ❌ Reject
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>
    )
  }

  const renderQueriesStage = () => (
    <div className="space-y-6">
      {!facts.approved || facts.approved.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center py-8">
            <p className="text-gray-500 mb-4">No approved facts yet</p>
            <button
              onClick={() => setActiveTab('facts')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              ← Approve Facts First
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="text-md font-medium text-gray-900 mb-4">Standard Queries</h4>
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-3">Using provider: <span className="font-medium text-blue-600">{provider || 'None selected'}</span></p>
                <button
                  onClick={() => handleGenerateQueries(false)}
                  disabled={!provider || !!operationStatus}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                >
                  Generate Standard Queries
                </button>
              </div>
              
              {operationStatus?.operation === 'generate_queries' && (
                <SimpleProgressBar
                  current={operationStatus.current}
                  total={operationStatus.total}
                  label={operationStatus.message}
                />
              )}
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="text-md font-medium text-gray-900 mb-4">Multi-hop Queries</h4>
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-3">Using provider: <span className="font-medium text-blue-600">{provider || 'None selected'}</span></p>
                <button
                  onClick={() => handleGenerateQueries(true)}
                  disabled={!provider || !!operationStatus}
                  className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
                >
                  Generate Multi-hop Queries
                </button>
              </div>
              
              {operationStatus?.operation === 'generate_multihop' && (
                <SimpleProgressBar
                  current={operationStatus.current}
                  total={operationStatus.total}
                  label={operationStatus.message}
                />
              )}
            </div>
          </div>

          {/* Query Review Interface */}
          {((queries.generated && queries.generated.length > 0) || (queries.multihop && queries.multihop.length > 0)) && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-center">
                <h4 className="text-lg font-medium text-gray-900 mb-4">
                  📝 Query Review Ready
                </h4>
                
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-blue-800">Standard Queries:</span>
                      <div className="text-2xl font-bold text-blue-600">{queries.generated?.length || 0}</div>
                    </div>
                    <div>
                      <span className="font-medium text-purple-800">Multi-hop Queries:</span>
                      <div className="text-2xl font-bold text-purple-600">{queries.multihop?.length || 0}</div>
                    </div>
                    <div>
                      <span className="font-medium text-green-800">Total Ready:</span>
                      <div className="text-2xl font-bold text-green-600">
                        {(queries.generated?.length || 0) + (queries.multihop?.length || 0)}
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleStartSingleQueryReview}
                  className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 font-medium text-lg transition-colors shadow-md"
                >
                  🔍 Start Query Review
                </button>
                
                <div className="mt-4 text-sm text-gray-600 space-y-1">
                  <p>Review queries one at a time with full chunk context</p>
                  <p>⌨️ Use keyboard shortcuts for fast review: A (approve), R (reject), E (edit), S (skip)</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )

  const renderExportStage = () => (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Export Dataset</h3>
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">Export Summary</h4>
          <div className="text-sm text-blue-800">
            <p>• Approved Queries: {getApprovedQueriesCount()}</p>
            <p>• Total Generated: {getGeneratedQueriesCount()}</p>
            <p>• Ready for export: {getApprovedQueriesCount() > 0 ? 'Yes' : 'No approved queries yet'}</p>
          </div>
        </div>
        
        {getApprovedQueriesCount() === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500 mb-4">No approved queries yet</p>
            <button
              onClick={() => setActiveTab('queries')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              ← Approve Queries First
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2">📄 JSON Format</h4>
              <p className="text-sm text-gray-600 mb-3">
                Structured JSON format, perfect for APIs and programmatic use.
              </p>
              <button
                onClick={() => handleExport('json')}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                Export JSON
              </button>
            </div>
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2">📄 CSV Format</h4>
              <p className="text-sm text-gray-600 mb-3">
                Comma-separated values format, ideal for spreadsheets and data analysis.
              </p>
              <button
                onClick={() => handleExport('csv')}
                className="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors"
              >
                Export CSV
              </button>
            </div>
          </div>
        )}
        
        <p className="text-sm text-gray-600">
          Exports will be saved to the project's data/exports directory
        </p>
      </div>
    </div>
  )

  return (
    <>
      <NotificationContainer />
      
      {/* Progress Bar */}
      {operationStatus && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 bg-white rounded-lg shadow-lg border p-6 min-w-96">
          <div className="text-center mb-4">
            <div className="text-lg font-semibold text-gray-900 mb-2">Processing...</div>
            <div className="text-sm text-gray-600">{operationStatus.message}</div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${operationStatus.progress}%` }}
            />
          </div>
          <div className="text-center text-sm text-gray-500">
            {Math.round(operationStatus.progress)}% complete
          </div>
        </div>
      )}
      
      <div>
        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'overview', name: '📋 Overview', count: null },
              { id: 'chunks', name: '📄 Chunks', count: getChunksCount() },
              { id: 'facts', name: '🔍 Facts', count: getGeneratedFactsCount() },
              { id: 'queries', name: '❓ Queries', count: getGeneratedQueriesCount() },
              { id: 'export', name: '📊 Export', count: null }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as ActiveTab)}
                className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.name}
                {tab.count !== null && (
                  <span className="ml-1 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Provider Selection and Stats */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Provider Settings */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <span className="mr-2">🔧</span>
                    LLM Provider
                  </h3>
                  <button
                    onClick={() => {
                      setRefreshKey(prev => prev + 1)
                      loadProjectData()
                    }}
                    className="text-sm bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-md transition-colors"
                    title="Refresh data"
                  >
                    🔄 Refresh
                  </button>
                </div>
                <div className="space-y-4">
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {providers.available.map((p) => (
                      <option key={p} value={p}>
                        {p}
                        {p === providers.auto_detected && ' (Auto-detected)'}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500">
                    Selected provider will be used for fact extraction and query generation
                  </p>
                </div>
              </div>

              {/* Facts Stats */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="mr-2">🔍</span>
                  Facts
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Generated</span>
                    <span className="text-2xl font-bold text-blue-600">{getGeneratedFactsCount()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Approved</span>
                    <span className="text-2xl font-bold text-green-600">{getApprovedFactsCount()}</span>
                  </div>
                </div>
              </div>

              {/* Queries Stats */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="mr-2">❓</span>
                  Queries
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Generated</span>
                    <span className="text-2xl font-bold text-purple-600">{getGeneratedQueriesCount()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Approved</span>
                    <span className="text-2xl font-bold text-emerald-600">{getApprovedQueriesCount()}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Workflow Steps */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">🚀 RAG Workflow</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">1. Upload Document Chunks</h4>
                    <p className="text-sm text-gray-600">Upload JSONL files containing your preprocessed document chunks</p>
                  </div>
                  <button
                    onClick={() => setActiveTab('chunks')}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
                  >
                    📄 Upload
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">2. Extract Facts</h4>
                    <p className="text-sm text-gray-600">Extract structured facts from uploaded chunks using LLM</p>
                  </div>
                  <button
                    onClick={handleExtractFacts}
                    disabled={getChunksCount() === 0 || !provider || !!operationStatus}
                    className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors disabled:opacity-50"
                  >
                    🔍 Extract
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">3. Generate Queries</h4>
                    <p className="text-sm text-gray-600">Generate both standard and multi-hop queries from approved facts</p>
                  </div>
                  <button
                    onClick={() => setActiveTab('queries')}
                    disabled={getApprovedFactsCount() === 0}
                    className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 transition-colors disabled:opacity-50"
                  >
                    ❓ Generate
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <h4 className="font-medium text-gray-900">4. Export Dataset</h4>
                    <p className="text-sm text-gray-600">Download your final approved query dataset</p>
                  </div>
                  <button
                    onClick={() => setActiveTab('export')}
                    disabled={getApprovedQueriesCount() === 0}
                    className="bg-emerald-600 text-white px-4 py-2 rounded-md hover:bg-emerald-700 transition-colors disabled:opacity-50"
                  >
                    📊 Export
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'chunks' && renderChunksStage()}
        {activeTab === 'facts' && renderFactsStage()}
        {activeTab === 'queries' && renderQueriesStage()}
        {activeTab === 'export' && renderExportStage()}
      </div>

      {/* Single Query Review Modal */}
      {isQueryReviewOpen && (
        <SingleQueryReview
          queries={[...(queries.generated || []), ...(queries.multihop || [])]}
          projectName={project.name}
          onComplete={handleQueryReviewComplete}
          onCancel={handleQueryReviewCancel}
        />
      )}
    </>
  )
}