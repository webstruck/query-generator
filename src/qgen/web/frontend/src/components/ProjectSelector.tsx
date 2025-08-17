import { useState, useEffect } from 'react'

interface Project {
  name: string
  path: string
  domain: string
  dimensions_count: number
}

interface ProjectSelectorProps {
  onProjectSelect: (project: Project) => void
  loading: boolean
  setLoading: (loading: boolean) => void
}

export default function ProjectSelector({ onProjectSelect, loading, setLoading }: ProjectSelectorProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [templates, setTemplates] = useState<string[]>([])
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  
  useEffect(() => {
    loadProjects()
    loadTemplates()
  }, [])

  const loadProjects = async () => {
    try {
      const response = await fetch('/api/projects')
      const data = await response.json()
      setProjects(data.projects)
    } catch (error) {
      console.error('Failed to load projects:', error)
    }
  }

  const loadTemplates = async () => {
    try {
      const response = await fetch('/api/templates')
      const data = await response.json()
      setTemplates(data.templates)
      setSelectedTemplate(data.templates[0] || '')
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  const createProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim() || !selectedTemplate) return

    setLoading(true)
    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newProjectName.trim(),
          template: selectedTemplate
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail)
      }

      // Reload projects and select the new one
      await loadProjects()
      const newProject = projects.find(p => p.name === newProjectName.trim())
      if (newProject) {
        onProjectSelect(newProject)
      }
    } catch (error) {
      alert(`Failed to create project: ${error}`)
    } finally {
      setLoading(false)
      setShowCreateForm(false)
      setNewProjectName('')
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4">
      {/* Hero Section */}
      <div className="text-center mb-12 py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6">
          <span className="text-white text-2xl">🔍</span>
        </div>
        <h2 className="text-4xl font-bold text-gray-900 mb-4">Welcome to QGen</h2>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Generate synthetic queries for any domain using LLMs - systematic, scalable, and ready for production
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Existing Projects */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-8 hover:shadow-xl transition-shadow">
          <div className="flex items-center mb-6">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
              📂
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Load Existing Project</h3>
          </div>
          
          {projects.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-gray-400 text-2xl">📁</span>
              </div>
              <p className="text-gray-500 mb-2">No projects found</p>
              <p className="text-sm text-gray-400">Navigate to a directory with existing QGen projects</p>
            </div>
          ) : (
            <div className="space-y-3">
              {projects.map((project) => (
                <div
                  key={project.name}
                  className="group p-5 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 cursor-pointer transition-all duration-200 hover:shadow-md"
                  onClick={() => onProjectSelect(project)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">{project.name}</h4>
                      <p className="text-sm text-gray-600 mt-1">
                        <span className="inline-flex items-center">
                          <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                          {project.domain} • {project.dimensions_count} dimensions
                        </span>
                      </p>
                    </div>
                    <div className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                      →
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create New Project */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-8 hover:shadow-xl transition-shadow">
          <div className="flex items-center mb-6">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mr-3">
              ➕
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Create New Project</h3>
          </div>
          
          {!showCreateForm ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center mx-auto mb-6">
                <span className="text-white text-2xl">✨</span>
              </div>
              <p className="text-gray-600 mb-6">Start a new query generation project</p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-3 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 transform hover:scale-105 shadow-lg hover:shadow-xl"
              >
                Create Project
              </button>
            </div>
          ) : (
            <form onSubmit={createProject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="my-project"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Template
                </label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {templates.map((template) => (
                    <option key={template} value={template}>
                      {template.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="flex space-x-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Creating...' : 'Create Project'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Getting Started Guide */}
      <div className="mt-16 bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl border border-gray-100 p-8">
        <div className="text-center mb-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-2">🚀 Getting Started</h3>
          <p className="text-gray-600">Three simple steps to generate your query dataset</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="text-center group">
            <div className="w-16 h-16 bg-white border border-gray-200 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm group-hover:shadow-md transition-shadow">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-600 font-bold text-sm">1</span>
              </div>
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">Create or Load Project</h4>
            <p className="text-sm text-gray-600 leading-relaxed">Choose a domain template or load an existing project to get started</p>
          </div>
          <div className="text-center group">
            <div className="w-16 h-16 bg-white border border-gray-200 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm group-hover:shadow-md transition-shadow">
              <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                <span className="text-purple-600 font-bold text-sm">2</span>
              </div>
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">Generate & Review</h4>
            <p className="text-sm text-gray-600 leading-relaxed">Create tuples and queries with AI assistance, then review and refine</p>
          </div>
          <div className="text-center group">
            <div className="w-16 h-16 bg-white border border-gray-200 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm group-hover:shadow-md transition-shadow">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                <span className="text-green-600 font-bold text-sm">3</span>
              </div>
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">Export Dataset</h4>
            <p className="text-sm text-gray-600 leading-relaxed">Download your final query dataset in CSV or JSON format</p>
          </div>
        </div>
      </div>
    </div>
  )
}