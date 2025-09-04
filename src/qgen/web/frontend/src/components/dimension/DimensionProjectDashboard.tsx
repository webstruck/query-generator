import { useState, useEffect } from 'react'
import QueryReview from './QueryReview'
import TupleReview from './TupleReview'
import { useNotification } from '../shared/Notification'
import { type DimensionProject } from '../ProjectSelector'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ButtonWithShortcut } from '../ui/button-with-shortcut'
import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LayoutDashboard, Settings2, Target, FileText, Download, Settings, Rocket, X, Trash2, File, FileType, AlertTriangle } from 'lucide-react'

interface ProjectData {
  name: string
  domain: string
  dimensions: {
    name: string
    description: string
    values: string[]
  }[]
  example_queries: string[]
  data_status: {
    generated_tuples: number
    approved_tuples: number
    generated_queries: number
    approved_queries: number
  }
}

interface DimensionProjectDashboardProps {
  project: DimensionProject
  loading: boolean
  setLoading: (loading: boolean) => void
}

export default function DimensionProjectDashboard({ project, loading, setLoading }: DimensionProjectDashboardProps) {
  const [projectData, setProjectData] = useState<ProjectData | null>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [providers, setProviders] = useState<{available: string[], auto_detected: string}>({available: [], auto_detected: ''})
  const [selectedProvider, setSelectedProvider] = useState('')
  const [editingDimensions, setEditingDimensions] = useState(false)
  const [tempDimensions, setTempDimensions] = useState<ProjectData['dimensions']>([])
  const [newDimension, setNewDimension] = useState({ name: '', description: '', values: [''] })
  const [tuplesStage] = useState<'generated' | 'approved'>('generated')
  const [generatingTuples, setGeneratingTuples] = useState(false)
  const [generatingQueries, setGeneratingQueries] = useState(false)
  const [approvingTuples, setApprovingTuples] = useState(false)
  const [progress, setProgress] = useState({ value: 0, status: '', visible: false })
  const { showNotification, NotificationContainer } = useNotification()

  useEffect(() => {
    loadProjectData()
    loadProviders()
  }, [project])

  useEffect(() => {
    if (activeTab === 'tuples') {
      loadTuples()
    }
  }, [activeTab, project, tuplesStage])

  const loadProjectData = async () => {
    try {
      const response = await fetch(`/api/projects/${project.name}`)
      const data = await response.json()
      setProjectData(data)
    } catch (error) {
      console.error('Failed to load project data:', error)
    }
  }

  const loadProviders = async () => {
    try {
      const response = await fetch('/api/providers')
      const data = await response.json()
      setProviders(data)
      setSelectedProvider(data.auto_detected || data.available[0] || '')
    } catch (error) {
      console.error('Failed to load providers:', error)
    }
  }

  const loadTuples = async () => {
    // This function can be removed as TupleReview manages its own data
    // Keeping for compatibility with useEffect
  }

  const pollProgress = (operation: string) => {
    setProgress({ value: 0, status: 'Starting...', visible: true })
    
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/projects/${project.name}/status/${operation}`)
        
        if (response.ok) {
          const status = await response.json()
          setProgress({
            value: status.progress,
            status: status.message,
            visible: true
          })
          
          if (status.completed) {
            clearInterval(interval)
            setTimeout(() => {
              setProgress({ value: 0, status: '', visible: false })
            }, 1000)
          }
        } else if (response.status === 404) {
          // No active generation found - might be completed
          clearInterval(interval)
          setTimeout(() => {
            setProgress({ value: 0, status: '', visible: false })
          }, 1000)
        }
      } catch (error) {
        console.error('Error polling progress:', error)
        clearInterval(interval)
        setProgress({ value: 0, status: '', visible: false })
      }
    }, 500) // Poll every 500ms
    
    return () => {
      clearInterval(interval)
      setTimeout(() => setProgress({ value: 0, status: '', visible: false }), 1000)
    }
  }

  const generateTuples = async () => {
    setLoading(true)
    setGeneratingTuples(true)
    
    try {
      const response = await fetch(`/api/projects/${project.name}/generate/tuples`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          count: 20,
          provider: selectedProvider
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail)
      }

      // Start polling for progress
      const cleanup = pollProgress('tuples')
      
      // Wait for completion by polling until done
      const waitForCompletion = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/projects/${project.name}/status/tuples`)
          if (statusResponse.ok) {
            const status = await statusResponse.json()
            if (status.completed) {
              clearInterval(waitForCompletion)
              cleanup()
              await loadProjectData()
              showNotification('Tuples generated successfully!', 'success')
              setLoading(false)
              setGeneratingTuples(false)
            }
          } else if (statusResponse.status === 404) {
            // Generation might be complete but status cleared
            clearInterval(waitForCompletion)
            cleanup()
            await loadProjectData()
            showNotification('Tuples generated successfully!', 'success')
            setLoading(false)
            setGeneratingTuples(false)
          }
        } catch (error) {
          clearInterval(waitForCompletion)
          cleanup()
          showNotification(`Generation error: ${error}`, 'error')
          setLoading(false)
          setGeneratingTuples(false)
        }
      }, 1000)
      
    } catch (error) {
      showNotification(`Failed to start tuple generation: ${error}`, 'error')
      setLoading(false)
      setGeneratingTuples(false)
    }
  }

  const approveTuples = async () => {
    setLoading(true)
    setApprovingTuples(true)
    try {
      // Get generated tuples
      const response = await fetch(`/api/projects/${project.name}/tuples/generated`)
      const data = await response.json()
      
      // For simplicity, approve all tuples (in real app, user would review)
      await fetch(`/api/projects/${project.name}/tuples/approved`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tuples: data.tuples })
      })

      await loadProjectData()
      showNotification('All tuples approved!', 'success')
    } catch (error) {
      showNotification(`Failed to approve tuples: ${error}`, 'error')
    } finally {
      setLoading(false)
      setApprovingTuples(false)
    }
  }

  const generateQueries = async () => {
    setLoading(true)  
    setGeneratingQueries(true)
    
    try {
      const response = await fetch(`/api/projects/${project.name}/generate/queries`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          queries_per_tuple: 3,
          provider: selectedProvider
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail)
      }

      // Start polling for progress
      const cleanup = pollProgress('queries')
      
      // Wait for completion by polling until done
      const waitForCompletion = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/projects/${project.name}/status/queries`)
          if (statusResponse.ok) {
            const status = await statusResponse.json()
            if (status.completed) {
              clearInterval(waitForCompletion)
              cleanup()
              await loadProjectData()
              setActiveTab('queries') // Switch to queries tab
              showNotification('Queries generated successfully!', 'success')
              setLoading(false)
              setGeneratingQueries(false)
            }
          } else if (statusResponse.status === 404) {
            // Generation might be complete but status cleared
            clearInterval(waitForCompletion)
            cleanup()
            await loadProjectData()
            setActiveTab('queries') // Switch to queries tab
            showNotification('Queries generated successfully!', 'success')
            setLoading(false)
            setGeneratingQueries(false)
          }
        } catch (error) {
          clearInterval(waitForCompletion)
          cleanup()
          showNotification(`Generation error: ${error}`, 'error')
          setLoading(false)
          setGeneratingQueries(false)
        }
      }, 1000)
      
    } catch (error) {
      showNotification(`Failed to start query generation: ${error}`, 'error')
      setLoading(false)
      setGeneratingQueries(false)
    }
  }

  const startEditingDimensions = () => {
    if (projectData) {
      setTempDimensions([...projectData.dimensions])
      setEditingDimensions(true)
    }
  }

  const saveDimensions = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${project.name}/dimensions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(tempDimensions)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail?.validation_errors || error.detail)
      }

      await loadProjectData()
      setEditingDimensions(false)
      showNotification('Dimensions updated successfully!', 'success')
    } catch (error) {
      showNotification(`Failed to update dimensions: ${error}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const cancelEditingDimensions = () => {
    setEditingDimensions(false)
    setTempDimensions([])
  }

  const addDimension = () => {
    if (newDimension.name && newDimension.description && newDimension.values[0]) {
      setTempDimensions([...tempDimensions, {
        name: newDimension.name,
        description: newDimension.description,
        values: newDimension.values.filter(v => v.trim())
      }])
      setNewDimension({ name: '', description: '', values: [''] })
    }
  }

  const removeDimension = (index: number) => {
    setTempDimensions(tempDimensions.filter((_, i) => i !== index))
  }

  const updateDimensionValue = (dimIndex: number, valueIndex: number, newValue: string) => {
    const updated = [...tempDimensions]
    updated[dimIndex].values[valueIndex] = newValue
    setTempDimensions(updated)
  }

  const addDimensionValue = (dimIndex: number) => {
    const updated = [...tempDimensions]
    updated[dimIndex].values.push('')
    setTempDimensions(updated)
  }

  const removeDimensionValue = (dimIndex: number, valueIndex: number) => {
    const updated = [...tempDimensions]
    if (updated[dimIndex].values.length > 1) {
      updated[dimIndex].values.splice(valueIndex, 1)
      setTempDimensions(updated)
    }
  }

  const exportData = async (format: 'csv' | 'json') => {
    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${project.name}/export/${format}?stage=approved`)
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Export failed')
      }
      
      const result = await response.json()
      
      // Create download link
      const downloadUrl = `/api/projects/${project.name}/download/${result.path.split('/').pop()}`
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = result.path.split('/').pop() || `${project.name}_queries.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      showNotification(`Dataset exported successfully!`, 'success')
    } catch (error) {
      showNotification(`Failed to export dataset: ${error}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      // Tab navigation
      { keys: ['1'], handler: () => setActiveTab('overview'), description: 'Overview tab' },
      { keys: ['2'], handler: () => setActiveTab('dimensions'), description: 'Dimensions tab' },
      { keys: ['3'], handler: () => setActiveTab('tuples'), description: 'Tuples tab' },
      { keys: ['4'], handler: () => setActiveTab('queries'), description: 'Queries tab' },
      { keys: ['5'], handler: () => setActiveTab('export'), description: 'Export tab' },
      
      // Main workflow actions (only when not editing)
      { keys: ['E'], handler: () => setActiveTab('dimensions'), description: 'Edit dimensions', enabled: !editingDimensions },
      { keys: ['G'], handler: generateTuples, description: 'Generate tuples', enabled: !loading && !editingDimensions },
      { keys: ['A'], handler: approveTuples, description: 'Approve all tuples', enabled: !loading && (projectData?.data_status?.generated_tuples || 0) > 0 && !editingDimensions },
      { keys: ['Q'], handler: generateQueries, description: 'Generate queries', enabled: !loading && (projectData?.data_status?.approved_tuples || 0) > 0 && !editingDimensions },
      { keys: ['R'], handler: () => setActiveTab('queries'), description: 'Review queries', enabled: (projectData?.data_status?.generated_queries || 0) > 0 && !editingDimensions },
      { keys: ['X'], handler: () => setActiveTab('export'), description: 'Export dataset', enabled: (projectData?.data_status?.approved_queries || 0) > 0 && !editingDimensions },
      
      // Dimension editing (only when editing)
      { keys: ['⌘', 'S'], handler: saveDimensions, description: 'Save dimensions', enabled: editingDimensions },
      { keys: ['Esc'], handler: cancelEditingDimensions, description: 'Cancel editing', enabled: editingDimensions },
      
      // Export actions (when on export tab)
      { keys: ['⌘', 'C'], handler: () => exportData('csv'), description: 'Export CSV', enabled: activeTab === 'export' && (projectData?.data_status?.approved_queries || 0) > 0 },
      { keys: ['⌘', 'J'], handler: () => exportData('json'), description: 'Export JSON', enabled: activeTab === 'export' && (projectData?.data_status?.approved_queries || 0) > 0 }
    ],
    enabled: true
  })

  if (!projectData) {
    return <div className="text-center py-8">Loading project...</div>
  }

  return (
    <>
      <NotificationContainer />
      
      {/* Progress Bar */}
      {progress.visible && (
        <Card className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 min-w-96">
          <CardContent className="p-6">
            <div className="text-center mb-4">
              <div className="text-lg font-semibold mb-2">Processing...</div>
              <div className="text-sm text-muted-foreground">{progress.status}</div>
            </div>
            <Progress value={progress.value} className="mb-4" />
            <div className="text-center text-sm text-muted-foreground">
              {Math.round(progress.value)}% complete
            </div>
          </CardContent>
        </Card>
      )}
      
      <div>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <LayoutDashboard className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="dimensions" className="flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            Dimensions
            <Badge variant="secondary" className="ml-1">
              {projectData.dimensions.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="tuples" className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            Tuples
            <Badge variant="secondary" className="ml-1">
              {projectData?.data_status?.generated_tuples || 0}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="queries" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Queries
            <Badge variant="secondary" className="ml-1">
              {projectData?.data_status?.generated_queries || 0}
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
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  LLM Provider
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.available.map((provider) => (
                      <SelectItem key={provider} value={provider}>
                        {provider}
                        {provider === providers.auto_detected && ' (Auto-detected)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Selected provider will be used for tuple and query generation
                </p>
              </CardContent>
            </Card>

            {/* Tuples Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Target className="mr-2 h-4 w-4" />
                  Tuples
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Generated</span>
                  <span className="text-2xl font-bold text-blue-600">{projectData?.data_status?.generated_tuples || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Approved</span>
                  <span className="text-2xl font-bold text-green-600">{projectData?.data_status?.approved_tuples || 0}</span>
                </div>
              </CardContent>
            </Card>

            {/* Queries Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <FileText className="mr-2 h-4 w-4" />
                  Queries
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Generated</span>
                  <span className="text-2xl font-bold text-purple-600">{projectData?.data_status?.generated_queries || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Approved</span>
                  <span className="text-2xl font-bold text-emerald-600">{projectData?.data_status?.approved_queries || 0}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Workflow Steps */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Rocket className="mr-2 h-4 w-4" />
                QGen Workflow
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h4 className="font-medium">1. Review & Edit Dimensions</h4>
                  <p className="text-sm text-muted-foreground">Define and customize the dimensions that will drive query generation</p>
                </div>
                <ButtonWithShortcut
                  onClick={() => setActiveTab('dimensions')}
                  variant="default"
                  shortcut="edit"
                >
                  Edit
                </ButtonWithShortcut>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h4 className="font-medium">2. Generate Tuples</h4>
                  <p className="text-sm text-muted-foreground">Create dimension combinations from your project dimensions</p>
                </div>
                <ButtonWithShortcut
                  onClick={generateTuples}
                  disabled={loading}
                  variant="secondary"
                  className="flex items-center space-x-2"
                  shortcut={['G']}
                >
                  {generatingTuples && (
                    <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                  )}
                  <span>{generatingTuples ? 'Generating...' : 'Generate'}</span>
                </ButtonWithShortcut>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h4 className="font-medium">3. Approve Tuples</h4>
                  <p className="text-sm text-muted-foreground">Review and approve generated tuples (simplified - approves all)</p>
                </div>
                <ButtonWithShortcut
                  onClick={approveTuples}
                  disabled={loading || (projectData?.data_status?.generated_tuples || 0) === 0}
                  variant="default"
                  className="flex items-center space-x-2"
                  shortcut={['A']}
                >
                  {approvingTuples && (
                    <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                  )}
                  <span>{approvingTuples ? 'Approving...' : 'Approve All'}</span>
                </ButtonWithShortcut>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h4 className="font-medium">4. Generate Queries</h4>
                  <p className="text-sm text-muted-foreground">Create natural language queries from approved tuples</p>
                </div>
                <ButtonWithShortcut
                  onClick={generateQueries}
                  disabled={loading || (projectData?.data_status?.approved_tuples || 0) === 0}
                  variant="secondary"
                  className="flex items-center space-x-2"
                  shortcut={['Q']}
                >
                  {generatingQueries && (
                    <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                  )}
                  <span>{generatingQueries ? 'Generating...' : 'Generate'}</span>
                </ButtonWithShortcut>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h4 className="font-medium">5. Review & Approve Queries</h4>
                  <p className="text-sm text-muted-foreground">Review, edit, approve, or reject individual queries</p>
                </div>
                <ButtonWithShortcut
                  onClick={() => setActiveTab('queries')}
                  disabled={(projectData?.data_status?.generated_queries || 0) === 0}
                  variant="outline"
                  shortcut={['R']}
                >
                  Review
                </ButtonWithShortcut>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <h4 className="font-medium">6. Export Dataset</h4>
                  <p className="text-sm text-muted-foreground">Download your final approved query dataset</p>
                </div>
                <ButtonWithShortcut
                  onClick={() => setActiveTab('export')}
                  disabled={(projectData?.data_status?.approved_queries || 0) === 0}
                  variant="outline"
                  shortcut={['X']}
                >
                  Export
                </ButtonWithShortcut>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dimensions" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="flex items-center">
                  <Settings2 className="mr-2 h-4 w-4" />
                  Dimensions
                </CardTitle>
                {!editingDimensions ? (
                  <Button
                    onClick={startEditingDimensions}
                    variant="default"
                  >
                    Edit Dimensions
                  </Button>
                ) : (
                  <div className="space-x-2">
                    <ButtonWithShortcut
                      onClick={saveDimensions}
                      disabled={loading}
                      variant="default"
                      shortcut="save"
                    >
                      Save
                    </ButtonWithShortcut>
                    <ButtonWithShortcut
                      onClick={cancelEditingDimensions}
                      variant="outline"
                      shortcut="cancel"
                    >
                      Cancel
                    </ButtonWithShortcut>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
          
          {!editingDimensions ? (
            <div className="space-y-4">
              {projectData.dimensions.map((dim, index) => (
                <Card key={index}>
                  <CardContent className="p-4">
                    <h4 className="font-medium">{dim.name}</h4>
                    <p className="text-sm text-muted-foreground mt-1">{dim.description}</p>
                    <div className="mt-2">
                      <span className="text-xs text-muted-foreground">Values:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {dim.values.map((value, valueIndex) => (
                          <Badge key={valueIndex} variant="secondary">
                            {value}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              {/* Existing Dimensions */}
              <div className="space-y-4">
                {tempDimensions.map((dim, dimIndex) => (
                  <Card key={dimIndex}>
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1 space-y-2">
                          <Input
                            type="text"
                            value={dim.name}
                            onChange={(e) => {
                              const updated = [...tempDimensions]
                              updated[dimIndex].name = e.target.value
                              setTempDimensions(updated)
                            }}
                            placeholder="Dimension name"
                            className="font-medium"
                          />
                          <Input
                            type="text"
                            value={dim.description}
                            onChange={(e) => {
                              const updated = [...tempDimensions]
                              updated[dimIndex].description = e.target.value
                              setTempDimensions(updated)
                            }}
                            placeholder="Dimension description"
                          />
                        </div>
                        <Button
                          onClick={() => removeDimension(dimIndex)}
                          variant="ghost"
                          size="sm"
                          className="ml-2 text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      
                      <div className="space-y-2">
                        <label className="text-xs text-muted-foreground">Values:</label>
                        {dim.values.map((value, valueIndex) => (
                          <div key={valueIndex} className="flex items-center space-x-2">
                            <Input
                              type="text"
                              value={value}
                              onChange={(e) => updateDimensionValue(dimIndex, valueIndex, e.target.value)}
                              placeholder="Value"
                              className="flex-1"
                            />
                            {dim.values.length > 1 && (
                              <Button
                                onClick={() => removeDimensionValue(dimIndex, valueIndex)}
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive"
                              >
                                <X className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        ))}
                        <Button
                          onClick={() => addDimensionValue(dimIndex)}
                          variant="link"
                          size="sm"
                          className="p-0 h-auto"
                        >
                          + Add Value
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              
              {/* Add New Dimension */}
              <Card className="border-2 border-dashed">
                <CardContent className="p-4">
                  <h4 className="font-medium mb-3">Add New Dimension</h4>
                  <div className="space-y-2">
                    <Input
                      type="text"
                      value={newDimension.name}
                      onChange={(e) => setNewDimension({...newDimension, name: e.target.value})}
                      placeholder="Dimension name"
                    />
                    <Input
                      type="text"
                      value={newDimension.description}
                      onChange={(e) => setNewDimension({...newDimension, description: e.target.value})}
                      placeholder="Dimension description"
                    />
                    <Input
                      type="text"
                      value={newDimension.values[0]}
                      onChange={(e) => setNewDimension({...newDimension, values: [e.target.value]})}
                      placeholder="First value"
                    />
                    <Button
                      onClick={addDimension}
                      variant="default"
                      className="w-full"
                    >
                      + Add Dimension
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="queries" className="mt-6">
          <QueryReview projectName={project.name} onUpdate={loadProjectData} />
        </TabsContent>

        <TabsContent value="tuples" className="mt-6">
          <TupleReview projectName={project.name} />
        </TabsContent>

        <TabsContent value="export" className="mt-6">
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
                <p>• Approved Queries: {projectData?.data_status?.approved_queries || 0}</p>
                <p>• Total Generated: {projectData?.data_status?.generated_queries || 0}</p>
                <p>• Ready for export: {(projectData?.data_status?.approved_queries || 0) > 0 ? 'Yes' : 'No approved queries yet'}</p>
              </div>
            </div>
            
            <div>
              <p className="text-muted-foreground mb-4">
                Export your approved queries to CSV or JSON format for use in training, evaluation, or analysis.
              </p>
              
              <div className="grid md:grid-cols-2 gap-4">
                <Card className="p-4">
                  <h4 className="font-medium text-foreground mb-2 flex items-center">
                    <File className="mr-2 h-4 w-4" />
                    CSV Format
                  </h4>
                  <p className="text-sm text-muted-foreground mb-3">
                    Comma-separated values format, ideal for spreadsheets and data analysis.
                  </p>
                  <ButtonWithShortcut 
                    onClick={() => exportData('csv')}
                    disabled={loading || (projectData?.data_status?.approved_queries || 0) === 0}
                    className="w-full"
                    variant="default"
                    shortcut={['⌘', 'C']}
                  >
                    {loading ? 'Exporting...' : 'Export CSV'}
                  </ButtonWithShortcut>
                </Card>
                
                <Card className="p-4">
                  <h4 className="font-medium text-foreground mb-2 flex items-center">
                    <FileType className="mr-2 h-4 w-4" />
                    JSON Format
                  </h4>
                  <p className="text-sm text-muted-foreground mb-3">
                    Structured JSON format, perfect for APIs and programmatic use.
                  </p>
                  <ButtonWithShortcut 
                    onClick={() => exportData('json')}
                    disabled={loading || (projectData?.data_status?.approved_queries || 0) === 0}
                    className="w-full"
                    variant="secondary"
                    shortcut={['⌘', 'J']}
                  >
                    {loading ? 'Exporting...' : 'Export JSON'}
                  </ButtonWithShortcut>
                </Card>
              </div>
            </div>
            
            {(projectData?.data_status?.approved_queries || 0) === 0 && (
              <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                <p className="text-amber-800 dark:text-amber-200 text-sm flex items-center">
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  No approved queries available for export. Please approve some queries first in the Queries tab.
                </p>
              </div>
            )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      </div>
    </>
  )
}