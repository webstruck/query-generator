import React, { useState, useEffect } from 'react'
import { type RAGProject } from '../ProjectSelector'
import { useNotification } from '../shared/Notification'
import { SingleQueryReview } from './SingleQueryReview'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ButtonWithShortcut } from '@/components/ui/button-with-shortcut'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { LayoutDashboard, Database, Lightbulb, FileText, Download, Settings, AlertTriangle, File, Search, Rocket, Upload } from 'lucide-react'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'

interface RAGProjectDashboardProps {
  project: RAGProject
  onBack?: () => void
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

// Simple inline components for consistent design using shadcn
const SimpleStatusCard: React.FC<{ title: string; count: number; subtitle: string }> = ({ title, count, subtitle }) => (
  <Card>
    <CardContent className="p-4">
      <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
      <p className="text-2xl font-bold">{count}</p>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
    </CardContent>
  </Card>
)

const SimpleProgressBar: React.FC<{ current: number; total: number; label: string }> = ({ current, total, label }) => {
  const percentage = total > 0 ? (current / total) * 100 : 0
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{current}/{total}</span>
      </div>
      <Progress value={percentage} className="h-2" />
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
        isDragging ? 'border-primary bg-primary/10' : 'border-border'
      }`}
      onDragOver={(e) => e.preventDefault()}
      onDragEnter={() => setIsDragging(true)}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <p className="text-muted-foreground mb-2">{description}</p>
      <input
        type="file"
        accept={acceptedTypes}
        onChange={handleFileSelect}
        className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
      />
    </div>
  )
}


export const RAGProjectDashboard: React.FC<RAGProjectDashboardProps> = ({ project }) => {
  const { showNotification, NotificationContainer } = useNotification()
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview')
  const [operationStatus, setOperationStatus] = useState<OperationStatus | null>(null)
  const [provider, setProvider] = useState<string>('')
  const [providers, setProviders] = useState<{available: string[], auto_detected: string}>({available: [], auto_detected: ''})
  
  // Data states
  const [chunkFiles, setChunkFiles] = useState<ChunkFile[]>([])
  const [facts, setFacts] = useState<{ [stage: string]: Fact[] }>({})
  const [queries, setQueries] = useState<{ [stage: string]: RAGQuery[] }>({})
  const [selectedFacts, setSelectedFacts] = useState<Set<string>>(new Set())
  const [factStage, setFactStage] = useState<'generated' | 'approved'>('generated')
  const [isQueryReviewOpen, setIsQueryReviewOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  // Helper functions and getters
  const getChunksCount = () => chunkFiles.reduce((sum, file) => sum + file.chunks_count, 0)
  const getGeneratedFactsCount = () => facts.generated?.length || 0
  const getApprovedFactsCount = () => facts.approved?.length || 0
  const getGeneratedQueriesCount = () => (queries.generated?.length || 0) + (queries.multihop?.length || 0)
  const getApprovedQueriesCount = () => queries.approved?.length || 0

  // Helper functions for keyboard shortcuts
  const extractFacts = () => handleExtractFacts()
  const generateQueries = () => handleGenerateQueries(false)
  const generateQueriesOfType = (type: 'standard' | 'multihop') => handleGenerateQueries(type === 'multihop')
  const startQueryReview = () => handleStartSingleQueryReview()
  const exportQueries = (format: 'json' | 'csv') => handleExport(format)
  const selectAllFacts = () => {
    const currentFacts = factStage === 'generated' ? facts.generated || [] : facts.approved || []
    const allFactIds = new Set(currentFacts.map(fact => fact.fact_id))
    setSelectedFacts(allFactIds)
  }
  const selectNoneFacts = () => setSelectedFacts(new Set())
  const bulkApproveFacts = () => handleApproveFacts()

  const handleIndividualApprove = async (factId: string) => {
    try {
      const response = await fetch(`/api/rag-projects/${project.name}/facts/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: [factId] })
      })

      const result = await response.json()
      
      if (response.ok) {
        showNotification('Fact approved successfully!', 'success')
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

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      // Tab navigation
      { keys: ['1'], handler: () => setActiveTab('overview'), description: 'Overview tab' },
      { keys: ['2'], handler: () => setActiveTab('chunks'), description: 'Chunks tab' },
      { keys: ['3'], handler: () => setActiveTab('facts'), description: 'Facts tab' },
      { keys: ['4'], handler: () => setActiveTab('queries'), description: 'Queries tab' },
      { keys: ['5'], handler: () => setActiveTab('export'), description: 'Export tab' },
      
      // Main workflow actions
      { keys: ['U'], handler: () => setActiveTab('chunks'), description: 'Upload chunks', enabled: activeTab === 'overview' },
      { keys: ['F'], handler: extractFacts, description: 'Extract facts', enabled: getChunksCount() > 0 },
      { keys: ['G'], handler: generateQueries, description: 'Generate queries', enabled: getApprovedFactsCount() > 0 },
      { keys: ['X'], handler: () => setActiveTab('export'), description: 'Export dataset', enabled: getApprovedQueriesCount() > 0 },
      
      // Facts review (when on facts tab)
      { keys: ['⌘', 'A'], handler: selectAllFacts, description: 'Select all facts', enabled: activeTab === 'facts' && getGeneratedFactsCount() > 0 },
      { keys: ['⌘', 'D'], handler: selectNoneFacts, description: 'Select none', enabled: activeTab === 'facts' },
      { keys: ['A'], handler: bulkApproveFacts, description: 'Approve selected facts', enabled: activeTab === 'facts' && selectedFacts.size > 0 },
      
      // Query generation (when on queries tab)
      { keys: ['S'], handler: () => generateQueriesOfType('standard'), description: 'Generate standard queries', enabled: activeTab === 'queries' && getApprovedFactsCount() > 0 },
      { keys: ['M'], handler: () => generateQueriesOfType('multihop'), description: 'Generate multi-hop queries', enabled: activeTab === 'queries' && getApprovedFactsCount() > 0 },
      { keys: ['↵'], handler: startQueryReview, description: 'Start query review', enabled: getGeneratedQueriesCount() > 0 },
      
      // Export (when on export tab)
      { keys: ['⌘', 'J'], handler: () => exportQueries('json'), description: 'Export JSON', enabled: activeTab === 'export' && getApprovedQueriesCount() > 0 },
      { keys: ['⌘', 'C'], handler: () => exportQueries('csv'), description: 'Export CSV', enabled: activeTab === 'export' && getApprovedQueriesCount() > 0 }
    ],
    enabled: true
  })

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
        // Project data loaded successfully
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
        
        console.log(`Loaded queries - Generated: ${newQueries.generated.length}, Approved: ${newQueries.approved.length}, Multihop: ${newQueries.multihop.length}`)
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
          console.log(`Operation ${operation} completed, refreshing data...`)
          showNotification(status.message, 'success')
          setOperationStatus(null)
          await loadProjectData() // Refresh data and wait for completion
          setRefreshKey(prev => prev + 1) // Force re-render
          console.log(`Data refresh completed for ${operation}`)
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
      showNotification(`Failed to start fact extraction: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error')
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
          showNotification(result.message, 'success')
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

  const renderChunksStage = () => (
    <Card className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-foreground flex items-center">
          <Upload className="h-4 w-4 mr-2" />
          Upload Chunks
        </h3>
        <SimpleStatusCard
          title="Total Chunks"
          count={getChunksCount()}
          subtitle={`${chunkFiles.length} files`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h4 className="text-md font-medium text-foreground mb-4">Upload JSONL Files</h4>
          <SimpleFileUpload
            onFileUpload={handleFileUpload}
            acceptedTypes=".jsonl"
            description="Upload JSONL files containing your document chunks"
          />
        </div>

        <div>
          <h4 className="text-md font-medium text-foreground mb-4">Uploaded Files</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {chunkFiles.length === 0 ? (
              <p className="text-muted-foreground italic">No files uploaded yet</p>
            ) : (
              chunkFiles.map((file, index) => (
                <div key={index} className="bg-muted p-3 rounded border-border border">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{file.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        {file.chunks_count} chunks • {(file.file_size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    {file.error && (
                      <span className="text-destructive text-sm flex items-center">
                        <AlertTriangle className="h-4 w-4 mr-1" />
                        {file.error}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </Card>
  )

  const renderFactsStage = () => {
    const currentFacts = factStage === 'generated' ? facts.generated || [] : facts.approved || []


    return (
      <div className="space-y-6">
        {/* Header with Stage Selection */}
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-foreground flex items-center">
            <Search className="h-4 w-4 mr-2" />
            Fact Review
          </h3>
          <select
            value={factStage}
            onChange={(e) => setFactStage(e.target.value as 'generated' | 'approved')}
            className="px-3 py-2 border border-border rounded focus:outline-none focus:ring-2 focus:ring-ring bg-background text-foreground"
          >
            <option value="generated">Generated Facts</option>
            <option value="approved">Approved Facts</option>
          </select>
        </div>

        {currentFacts.length === 0 ? (
          <Card className="p-6">
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">
                {factStage === 'generated' ? 'No facts generated yet' : 'No facts approved yet'}
              </p>
              {factStage === 'generated' && (
                <ButtonWithShortcut
                  onClick={handleExtractFacts}
                  disabled={getChunksCount() === 0 || !provider || !!operationStatus}
                  shortcut={['F']}
                >
                  Extract Facts
                </ButtonWithShortcut>
              )}
            </div>
          </Card>
        ) : (
          <>
            {/* Floating Action Bar - Only for Generated */}
            {factStage === 'generated' && (
              <Card className="p-4 mb-6 sticky top-4 z-10">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  {/* Selection Controls */}
                  <div className="flex items-center space-x-4">
                    <div className="flex space-x-2">
                      <ButtonWithShortcut
                        onClick={selectAllFacts}
                        className="px-3 py-1 text-sm border border-border rounded hover:bg-accent"
                        variant="outline"
                        size="sm"
                        shortcut={['⌘', 'A']}
                      >
                        All
                      </ButtonWithShortcut>
                      <ButtonWithShortcut
                        onClick={selectNoneFacts}
                        className="px-3 py-1 text-sm border border-border rounded hover:bg-accent"
                        variant="outline"
                        size="sm"
                        shortcut={['⌘', 'D']}
                      >
                        None
                      </ButtonWithShortcut>
                    </div>
                    
                    <span className="text-sm text-muted-foreground">
                      {selectedFacts.size === 0 
                        ? 'No facts selected' 
                        : `${selectedFacts.size} selected`
                      }
                    </span>
                  </div>

                  {/* Action Buttons */}
                  {selectedFacts.size > 0 && (
                    <div className="flex space-x-2">
                      <ButtonWithShortcut
                        onClick={handleApproveFacts}
                        disabled={!!operationStatus}
                        variant="default"
                        shortcut={['A']}
                      >
                        Approve Selected
                      </ButtonWithShortcut>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* Facts List with Simple Highlighting */}
            <div className="space-y-3">
              {currentFacts.map((fact, index) => {
                const isSelected = selectedFacts.has(fact.fact_id)
                
                const getFactStatusStyle = (isSelected: boolean) => {
                  const baseClasses = "p-4 rounded-lg border-2 mb-3 transition-all cursor-pointer"
                  
                  if (isSelected) {
                    return `${baseClasses} border-primary bg-primary/10 shadow-md`
                  }
                  
                  return `${baseClasses} border-border bg-muted hover:border-muted-foreground hover:shadow-sm`
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
                          className="h-4 w-4 text-primary focus:ring-ring border-border rounded mt-1"
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                      
                      {/* Fact Number */}
                      <span className="bg-primary/20 text-primary px-2 py-1 rounded font-medium text-sm">
                        #{index + 1}
                      </span>
                      
                      {/* Fact Content */}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground mb-2">{fact.fact_text}</p>
                        
                        {/* Source Context with Model2Vec-based Highlighting */}
                        {fact.source_text && (
                          <div className="mt-2 p-3 bg-muted rounded border border-border">
                            <p className="text-xs text-muted-foreground mb-1">Source Context (Model2Vec similarity):</p>
                            <div 
                              className="text-sm text-foreground"
                              dangerouslySetInnerHTML={{ 
                                __html: fact.highlighted_source || fact.source_text 
                              }}
                            />
                          </div>
                        )}
                        
                        <p className="text-xs text-muted-foreground mt-2">
                          Chunk: {fact.chunk_id} • Confidence: {(fact.extraction_confidence * 100).toFixed(1)}%
                        </p>
                      </div>

                      {/* Individual Actions - Only for Generated */}
                      {factStage === 'generated' && (
                        <div className="flex space-x-2">
                          <ButtonWithShortcut
                            onClick={(e) => {
                              e.stopPropagation()
                              handleIndividualApprove(fact.fact_id)
                            }}
                            size="sm"
                            variant="default"
                            className="bg-green-600 hover:bg-green-700"
                            shortcut={['A']}
                          >
                            Approve
                          </ButtonWithShortcut>
                          <ButtonWithShortcut
                            onClick={(e) => {
                              e.stopPropagation()
                              handleIndividualReject(fact.fact_id)
                            }}
                            size="sm"
                            variant="destructive"
                            shortcut={['R']}
                          >
                            Reject
                          </ButtonWithShortcut>
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
        <Card className="p-6">
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">No approved facts yet</p>
            <Button
              onClick={() => setActiveTab('facts')}
            >
              ← Approve Facts First
            </Button>
          </div>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h4 className="text-md font-medium text-foreground mb-4">Standard Queries</h4>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground mb-3">Using provider: <span className="font-medium text-primary">{provider || 'None selected'}</span></p>
                <ButtonWithShortcut
                  onClick={() => handleGenerateQueries(false)}
                  disabled={!provider || !!operationStatus}
                  className="bg-green-600 hover:bg-green-700"
                  shortcut={['S']}
                >
                  Generate Standard Queries
                </ButtonWithShortcut>
              </div>
              
              {operationStatus?.operation === 'generate_queries' && (
                <SimpleProgressBar
                  current={operationStatus.current}
                  total={operationStatus.total}
                  label={operationStatus.message}
                />
              )}
            </Card>

            <Card className="p-6">
              <h4 className="text-md font-medium text-foreground mb-4">Multi-hop Queries</h4>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground mb-3">Using provider: <span className="font-medium text-primary">{provider || 'None selected'}</span></p>
                <ButtonWithShortcut
                  onClick={() => handleGenerateQueries(true)}
                  disabled={!provider || !!operationStatus}
                  className="bg-purple-600 hover:bg-purple-700"
                  shortcut={['M']}
                >
                  Generate Multi-hop Queries
                </ButtonWithShortcut>
              </div>
              
              {operationStatus?.operation === 'generate_multihop' && (
                <SimpleProgressBar
                  current={operationStatus.current}
                  total={operationStatus.total}
                  label={operationStatus.message}
                />
              )}
            </Card>
          </div>

          {/* Query Review Interface */}
          {((queries.generated && queries.generated.length > 0) || (queries.multihop && queries.multihop.length > 0)) && (
            <Card className="p-6">
              <div className="text-center">
                <h4 className="text-lg font-medium text-foreground mb-4">
                <div className="flex items-center justify-center">
                  <FileText className="h-5 w-5 mr-2" />
                  Query Review Ready
                </div>
                </h4>
                
                <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 mb-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-primary">Standard Queries:</span>
                      <div className="text-2xl font-bold text-primary">{queries.generated?.length || 0}</div>
                    </div>
                    <div>
                      <span className="font-medium text-purple-600">Multi-hop Queries:</span>
                      <div className="text-2xl font-bold text-purple-600">{queries.multihop?.length || 0}</div>
                    </div>
                    <div>
                      <span className="font-medium text-green-600">Total Ready:</span>
                      <div className="text-2xl font-bold text-green-600">
                        {(queries.generated?.length || 0) + (queries.multihop?.length || 0)}
                      </div>
                    </div>
                  </div>
                </div>

                <ButtonWithShortcut
                  onClick={handleStartSingleQueryReview}
                  className="bg-blue-600 hover:bg-blue-700 font-medium text-lg shadow-md"
                  size="lg"
                  shortcut="submit"
                >
                  Start Query Review
                </ButtonWithShortcut>
                
                <div className="mt-4 text-sm text-muted-foreground space-y-1">
                  <p>Review queries one at a time with full chunk context</p>
                  <p>Use keyboard shortcuts for fast review: A (approve), R (reject), E (edit), S (skip)</p>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )

  const renderExportStage = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Download className="mr-2 h-4 w-4" />
          Export Dataset
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
          <h4 className="font-medium text-foreground mb-2">Export Summary</h4>
          <div className="text-sm text-muted-foreground">
            <p>• Approved Queries: {getApprovedQueriesCount()}</p>
            <p>• Total Generated: {getGeneratedQueriesCount()}</p>
            <p>• Ready for export: {getApprovedQueriesCount() > 0 ? 'Yes' : 'No approved queries yet'}</p>
          </div>
        </div>
        
        {getApprovedQueriesCount() === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">No approved queries yet</p>
            <Button
              onClick={() => setActiveTab('queries')}
              variant="default"
            >
              ← Approve Queries First
            </Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-4">
              <h4 className="font-medium text-foreground mb-2 flex items-center">
                <File className="h-4 w-4 mr-2" />
                JSON Format
              </h4>
              <p className="text-sm text-muted-foreground mb-3">
                Structured JSON format, perfect for APIs and programmatic use.
              </p>
              <ButtonWithShortcut
                onClick={() => handleExport('json')}
                className="w-full"
                variant="default"
                shortcut={['⌘', 'J']}
              >
                Export JSON
              </ButtonWithShortcut>
            </Card>
            <Card className="p-4">
              <h4 className="font-medium text-foreground mb-2 flex items-center">
                <File className="h-4 w-4 mr-2" />
                CSV Format
              </h4>
              <p className="text-sm text-muted-foreground mb-3">
                Comma-separated values format, ideal for spreadsheets and data analysis.
              </p>
              <ButtonWithShortcut
                onClick={() => handleExport('csv')}
                className="w-full"
                variant="secondary"
                shortcut={['⌘', 'C']}
              >
                Export CSV
              </ButtonWithShortcut>
            </Card>
          </div>
        )}
        
        <p className="text-sm text-muted-foreground">
          Exports will be saved to the project's data/exports directory
        </p>
      </CardContent>
    </Card>
  )

  return (
    <>
      <NotificationContainer />
      
      {/* Progress Bar */}
      {operationStatus && (
        <Card className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 p-6 min-w-96">
          <div className="text-center mb-4">
            <div className="text-lg font-semibold text-foreground mb-2">Processing...</div>
            <div className="text-sm text-muted-foreground">{operationStatus.message}</div>
          </div>
          <div className="w-full bg-muted rounded-full h-2 mb-4">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${operationStatus.progress}%` }}
            />
          </div>
          <div className="text-center text-sm text-muted-foreground">
            {Math.round(operationStatus.progress)}% complete
          </div>
        </Card>
      )}
      
      <div>
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as ActiveTab)} className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <LayoutDashboard className="h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="chunks" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              Chunks
              <Badge variant="secondary" className="ml-1">
                {getChunksCount()}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="facts" className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4" />
              Facts
              <Badge variant="secondary" className="ml-1">
                {getGeneratedFactsCount()}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="queries" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Queries
              <Badge variant="secondary" className="ml-1">
                {getGeneratedQueriesCount()}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="export" className="flex items-center gap-2">
              <Download className="h-4 w-4" />
              Export
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6 mt-6">
            {/* Provider Selection and Stats */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Provider Settings */}
              <Card className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-foreground flex items-center">
                    <Settings className="mr-2 h-4 w-4" />
                    LLM Provider
                  </h3>
                  <Button
                    onClick={() => {
                      setRefreshKey(prev => prev + 1)
                      loadProjectData()
                    }}
                    variant="outline"
                    size="sm"
                    title="Refresh data"
                  >
                    Refresh
                  </Button>
                </div>
                <div className="space-y-4">
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-ring bg-background text-foreground"
                  >
                    {providers.available.map((p) => (
                      <option key={p} value={p}>
                        {p}
                        {p === providers.auto_detected && ' (Auto-detected)'}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Selected provider will be used for fact extraction and query generation
                  </p>
                </div>
              </Card>

              {/* Facts Stats */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center">
                  <Search className="h-4 w-4 mr-2" />
                  Facts
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Generated</span>
                    <span className="text-2xl font-bold text-primary">{getGeneratedFactsCount()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Approved</span>
                    <span className="text-2xl font-bold text-green-600">{getApprovedFactsCount()}</span>
                  </div>
                </div>
              </Card>

              {/* Queries Stats */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center">
                  <FileText className="h-4 w-4 mr-2" />
                  Queries
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Generated</span>
                    <span className="text-2xl font-bold text-purple-600">{getGeneratedQueriesCount()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Approved</span>
                    <span className="text-2xl font-bold text-emerald-600">{getApprovedQueriesCount()}</span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Workflow Steps */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center">
                <Rocket className="h-4 w-4 mr-2" />
                RAG Workflow
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div>
                    <h4 className="font-medium text-foreground">1. Upload Document Chunks</h4>
                    <p className="text-sm text-muted-foreground">Upload JSONL files containing your preprocessed document chunks</p>
                  </div>
                  <ButtonWithShortcut
                    onClick={() => setActiveTab('chunks')}
                    shortcut={['U']}
                  >
                    Upload
                  </ButtonWithShortcut>
                </div>

                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div>
                    <h4 className="font-medium text-foreground">2. Extract Facts</h4>
                    <p className="text-sm text-muted-foreground">Extract structured facts from uploaded chunks using LLM</p>
                  </div>
                  <ButtonWithShortcut
                    onClick={handleExtractFacts}
                    disabled={getChunksCount() === 0 || !provider || !!operationStatus}
                    className="bg-indigo-600 hover:bg-indigo-700"
                    shortcut={['F']}
                  >
                    Extract
                  </ButtonWithShortcut>
                </div>

                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div>
                    <h4 className="font-medium text-foreground">3. Generate Queries</h4>
                    <p className="text-sm text-muted-foreground">Generate both standard and multi-hop queries from approved facts</p>
                  </div>
                  <ButtonWithShortcut
                    onClick={() => setActiveTab('queries')}
                    disabled={getApprovedFactsCount() === 0}
                    className="bg-purple-600 hover:bg-purple-700"
                    shortcut={['G']}
                  >
                    Generate
                  </ButtonWithShortcut>
                </div>

                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div>
                    <h4 className="font-medium text-foreground">4. Export Dataset</h4>
                    <p className="text-sm text-muted-foreground">Download your final approved query dataset</p>
                  </div>
                  <ButtonWithShortcut
                    onClick={() => setActiveTab('export')}
                    disabled={getApprovedQueriesCount() === 0}
                    className="bg-emerald-600 hover:bg-emerald-700"
                    shortcut={['X']}
                  >
                    Export
                  </ButtonWithShortcut>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="chunks" className="space-y-6 mt-6">
            {renderChunksStage()}
          </TabsContent>

          <TabsContent value="facts" className="space-y-6 mt-6">
            {renderFactsStage()}
          </TabsContent>

          <TabsContent value="queries" className="space-y-6 mt-6">
            {renderQueriesStage()}
          </TabsContent>

          <TabsContent value="export" className="space-y-6 mt-6">
            {renderExportStage()}
          </TabsContent>
        </Tabs>
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