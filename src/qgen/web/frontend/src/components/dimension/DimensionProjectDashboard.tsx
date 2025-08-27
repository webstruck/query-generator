import { useState, useEffect } from 'react'
import QueryReview from './QueryReview'
import TupleReview from './TupleReview'
import { useNotification } from '../shared/Notification'
import { type DimensionProject } from '../ProjectSelector'

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
              showNotification('Tuples generated successfully! 🎯', 'success')
              setLoading(false)
              setGeneratingTuples(false)
            }
          } else if (statusResponse.status === 404) {
            // Generation might be complete but status cleared
            clearInterval(waitForCompletion)
            cleanup()
            await loadProjectData()
            showNotification('Tuples generated successfully! 🎯', 'success')
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
      showNotification('All tuples approved! ✅', 'success')
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
              showNotification('Queries generated successfully! 📝', 'success')
              setLoading(false)
              setGeneratingQueries(false)
            }
          } else if (statusResponse.status === 404) {
            // Generation might be complete but status cleared
            clearInterval(waitForCompletion)
            cleanup()
            await loadProjectData()
            setActiveTab('queries') // Switch to queries tab
            showNotification('Queries generated successfully! 📝', 'success')
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
      showNotification('Dimensions updated successfully! 🎛️', 'success')
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
      
      showNotification(`Dataset exported successfully! 📊`, 'success')
    } catch (error) {
      showNotification(`Failed to export dataset: ${error}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  if (!projectData) {
    return <div className="text-center py-8">Loading project...</div>
  }

  return (
    <>
      <NotificationContainer />
      
      {/* Progress Bar */}
      {progress.visible && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 bg-white rounded-lg shadow-lg border p-6 min-w-96">
          <div className="text-center mb-4">
            <div className="text-lg font-semibold text-gray-900 mb-2">Processing...</div>
            <div className="text-sm text-gray-600">{progress.status}</div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress.value}%` }}
            />
          </div>
          <div className="text-center text-sm text-gray-500">
            {Math.round(progress.value)}% complete
          </div>
        </div>
      )}
      
      <div>
      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', name: '📋 Overview', count: null },
            { id: 'dimensions', name: '🎛️ Dimensions', count: projectData.dimensions.length },
            { id: 'tuples', name: '🎯 Tuples', count: projectData.data_status.generated_tuples },
            { id: 'queries', name: '📝 Queries', count: projectData.data_status.generated_queries },
            { id: 'export', name: '📊 Export', count: null }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
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
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">🔧</span>
                LLM Provider
              </h3>
              <div className="space-y-4">
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {providers.available.map((provider) => (
                    <option key={provider} value={provider}>
                      {provider}
                      {provider === providers.auto_detected && ' (Auto-detected)'}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500">
                  Selected provider will be used for tuple and query generation
                </p>
              </div>
            </div>

            {/* Tuples Stats */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">🎯</span>
                Tuples
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Generated</span>
                  <span className="text-2xl font-bold text-blue-600">{projectData.data_status.generated_tuples}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Approved</span>
                  <span className="text-2xl font-bold text-green-600">{projectData.data_status.approved_tuples}</span>
                </div>
              </div>
            </div>

            {/* Queries Stats */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">📝</span>
                Queries
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Generated</span>
                  <span className="text-2xl font-bold text-purple-600">{projectData.data_status.generated_queries}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Approved</span>
                  <span className="text-2xl font-bold text-emerald-600">{projectData.data_status.approved_queries}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Workflow Steps */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🚀 QGen Workflow</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 className="font-medium text-gray-900">1. Review & Edit Dimensions</h4>
                  <p className="text-sm text-gray-600">Define and customize the dimensions that will drive query generation</p>
                </div>
                <button
                  onClick={() => setActiveTab('dimensions')}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
                >
                  🎛️ Edit
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 className="font-medium text-gray-900">2. Generate Tuples</h4>
                  <p className="text-sm text-gray-600">Create dimension combinations from your project dimensions</p>
                </div>
                <button
                  onClick={generateTuples}
                  disabled={loading}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {generatingTuples && (
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                  )}
                  <span>{generatingTuples ? 'Generating...' : 'Generate'}</span>
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 className="font-medium text-gray-900">3. Approve Tuples</h4>
                  <p className="text-sm text-gray-600">Review and approve generated tuples (simplified - approves all)</p>
                </div>
                <button
                  onClick={approveTuples}
                  disabled={loading || projectData.data_status.generated_tuples === 0}
                  className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {approvingTuples && (
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                  )}
                  <span>{approvingTuples ? 'Approving...' : '✅ Approve All'}</span>
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 className="font-medium text-gray-900">4. Generate Queries</h4>
                  <p className="text-sm text-gray-600">Create natural language queries from approved tuples</p>
                </div>
                <button
                  onClick={generateQueries}
                  disabled={loading || projectData.data_status.approved_tuples === 0}
                  className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                >
                  {generatingQueries && (
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                  )}
                  <span>{generatingQueries ? 'Generating...' : 'Generate'}</span>
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 className="font-medium text-gray-900">5. Review & Approve Queries</h4>
                  <p className="text-sm text-gray-600">Review, edit, approve, or reject individual queries</p>
                </div>
                <button
                  onClick={() => setActiveTab('queries')}
                  disabled={projectData.data_status.generated_queries === 0}
                  className="bg-orange-600 text-white px-4 py-2 rounded-md hover:bg-orange-700 transition-colors disabled:opacity-50"
                >
                  📝 Review
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 className="font-medium text-gray-900">6. Export Dataset</h4>
                  <p className="text-sm text-gray-600">Download your final approved query dataset</p>
                </div>
                <button
                  onClick={() => setActiveTab('export')}
                  disabled={projectData.data_status.approved_queries === 0}
                  className="bg-emerald-600 text-white px-4 py-2 rounded-md hover:bg-emerald-700 transition-colors disabled:opacity-50"
                >
                  📊 Export
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'dimensions' && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">🎛️ Dimensions</h3>
            {!editingDimensions ? (
              <button
                onClick={startEditingDimensions}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
              >
                ✏️ Edit Dimensions
              </button>
            ) : (
              <div className="space-x-2">
                <button
                  onClick={saveDimensions}
                  disabled={loading}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  💾 Save
                </button>
                <button
                  onClick={cancelEditingDimensions}
                  className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition-colors"
                >
                  ❌ Cancel
                </button>
              </div>
            )}
          </div>
          
          {!editingDimensions ? (
            <div className="space-y-4">
              {projectData.dimensions.map((dim, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900">{dim.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{dim.description}</p>
                  <div className="mt-2">
                    <span className="text-xs text-gray-500">Values:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {dim.values.map((value, valueIndex) => (
                        <span
                          key={valueIndex}
                          className="inline-block bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded"
                        >
                          {value}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              {/* Existing Dimensions */}
              <div className="space-y-4">
                {tempDimensions.map((dim, dimIndex) => (
                  <div key={dimIndex} className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1 space-y-2">
                        <input
                          type="text"
                          value={dim.name}
                          onChange={(e) => {
                            const updated = [...tempDimensions]
                            updated[dimIndex].name = e.target.value
                            setTempDimensions(updated)
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded font-medium"
                          placeholder="Dimension name"
                        />
                        <input
                          type="text"
                          value={dim.description}
                          onChange={(e) => {
                            const updated = [...tempDimensions]
                            updated[dimIndex].description = e.target.value
                            setTempDimensions(updated)
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                          placeholder="Dimension description"
                        />
                      </div>
                      <button
                        onClick={() => removeDimension(dimIndex)}
                        className="ml-2 text-red-600 hover:text-red-800 p-1"
                      >
                        🗑️
                      </button>
                    </div>
                    
                    <div className="space-y-2">
                      <label className="text-xs text-gray-500">Values:</label>
                      {dim.values.map((value, valueIndex) => (
                        <div key={valueIndex} className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={value}
                            onChange={(e) => updateDimensionValue(dimIndex, valueIndex, e.target.value)}
                            className="flex-1 px-3 py-1 border border-gray-300 rounded text-sm"
                            placeholder="Value"
                          />
                          {dim.values.length > 1 && (
                            <button
                              onClick={() => removeDimensionValue(dimIndex, valueIndex)}
                              className="text-red-600 hover:text-red-800 px-2"
                            >
                              ❌
                            </button>
                          )}
                        </div>
                      ))}
                      <button
                        onClick={() => addDimensionValue(dimIndex)}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        + Add Value
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Add New Dimension */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
                <h4 className="font-medium text-gray-700 mb-3">Add New Dimension</h4>
                <div className="space-y-2">
                  <input
                    type="text"
                    value={newDimension.name}
                    onChange={(e) => setNewDimension({...newDimension, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded"
                    placeholder="Dimension name"
                  />
                  <input
                    type="text"
                    value={newDimension.description}
                    onChange={(e) => setNewDimension({...newDimension, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded"
                    placeholder="Dimension description"
                  />
                  <input
                    type="text"
                    value={newDimension.values[0]}
                    onChange={(e) => setNewDimension({...newDimension, values: [e.target.value]})}
                    className="w-full px-3 py-2 border border-gray-300 rounded"
                    placeholder="First value"
                  />
                  <button
                    onClick={addDimension}
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
                  >
                    + Add Dimension
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'queries' && (
        <QueryReview projectName={project.name} onUpdate={loadProjectData} />
      )}

      {activeTab === 'tuples' && (
        <TupleReview projectName={project.name} />
      )}

      {activeTab === 'export' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Export Dataset</h3>
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-2">Export Summary</h4>
              <div className="text-sm text-blue-800">
                <p>• Approved Queries: {projectData.data_status.approved_queries}</p>
                <p>• Total Generated: {projectData.data_status.generated_queries}</p>
                <p>• Ready for export: {projectData.data_status.approved_queries > 0 ? 'Yes' : 'No approved queries yet'}</p>
              </div>
            </div>
            
            <div>
              <p className="text-gray-600 mb-4">
                Export your approved queries to CSV or JSON format for use in training, evaluation, or analysis.
              </p>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">📄 CSV Format</h4>
                  <p className="text-sm text-gray-600 mb-3">
                    Comma-separated values format, ideal for spreadsheets and data analysis.
                  </p>
                  <button 
                    onClick={() => exportData('csv')}
                    disabled={loading || projectData.data_status.approved_queries === 0}
                    className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Exporting...' : 'Export CSV'}
                  </button>
                </div>
                
                <div className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">📋 JSON Format</h4>
                  <p className="text-sm text-gray-600 mb-3">
                    Structured JSON format, perfect for APIs and programmatic use.
                  </p>
                  <button 
                    onClick={() => exportData('json')}
                    disabled={loading || projectData.data_status.approved_queries === 0}
                    className="w-full bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Exporting...' : 'Export JSON'}
                  </button>
                </div>
              </div>
            </div>
            
            {projectData.data_status.approved_queries === 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-yellow-800 text-sm">
                  ⚠️ No approved queries available for export. Please approve some queries first in the Queries tab.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
      </div>
    </>
  )
}