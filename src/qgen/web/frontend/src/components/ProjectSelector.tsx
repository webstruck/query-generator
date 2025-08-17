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
  const [allProjects, setAllProjects] = useState<Project[]>([])
  const [templates, setTemplates] = useState<string[]>([])
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [showAllProjectsModal, setShowAllProjectsModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  
  useEffect(() => {
    loadProjects()
    loadTemplates()
  }, [])

  const loadProjects = async () => {
    try {
      // Load recent projects (limit 3) for main display
      const recentResponse = await fetch('/api/projects?limit=3')
      const recentData = await recentResponse.json()
      setProjects(recentData.projects)
      
      // Load all projects for modal
      const allResponse = await fetch('/api/projects')
      const allData = await allResponse.json()
      setAllProjects(allData.projects)
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

  // Filter projects based on search query
  const filteredProjects = allProjects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.domain.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="max-w-6xl mx-auto px-4">
      {/* Hero Section with Getting Started */}
      <div className="text-center mb-12 py-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6">
          <span className="text-white text-2xl">🔍</span>
        </div>
        <h2 className="text-4xl font-bold text-gray-900 mb-4">Welcome to QGen</h2>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
          Generate synthetic queries for any domain using LLMs - systematic, scalable, and ready for production
        </p>
        
        {/* Getting Started - Horizontal Layout */}
        <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl border border-gray-100 p-6 max-w-4xl mx-auto">
          <div className="flex justify-center items-center space-x-8">
            <div className="text-center group">
              <div className="w-12 h-12 bg-white border border-gray-200 rounded-full flex items-center justify-center mx-auto mb-2 shadow-sm group-hover:shadow-md transition-shadow">
                <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-bold text-xs">1</span>
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 text-sm mb-1">Create or Load</h4>
              <p className="text-xs text-gray-600">Choose template or existing project</p>
            </div>
            
            <div className="text-gray-400 text-xl">→</div>
            
            <div className="text-center group">
              <div className="w-12 h-12 bg-white border border-gray-200 rounded-full flex items-center justify-center mx-auto mb-2 shadow-sm group-hover:shadow-md transition-shadow">
                <div className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-purple-600 font-bold text-xs">2</span>
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 text-sm mb-1">Generate & Review</h4>
              <p className="text-xs text-gray-600">Create and refine with AI</p>
            </div>
            
            <div className="text-gray-400 text-xl">→</div>
            
            <div className="text-center group">
              <div className="w-12 h-12 bg-white border border-gray-200 rounded-full flex items-center justify-center mx-auto mb-2 shadow-sm group-hover:shadow-md transition-shadow">
                <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                  <span className="text-green-600 font-bold text-xs">3</span>
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 text-sm mb-1">Export Dataset</h4>
              <p className="text-xs text-gray-600">Download in CSV or JSON</p>
            </div>
          </div>
        </div>
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
              
              {/* Browse All Projects Button */}
              {allProjects.length > 3 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => setShowAllProjectsModal(true)}
                    className="w-full text-center py-3 px-4 border border-gray-300 rounded-lg text-gray-600 hover:text-gray-800 hover:border-gray-400 hover:bg-gray-50 transition-colors"
                  >
                    Browse All Projects ({allProjects.length - 3} more)
                  </button>
                </div>
              )}
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

      {/* Browse All Projects Modal */}
      {showAllProjectsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[80vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                  📂
                </div>
                <h3 className="text-xl font-semibold text-gray-900">Browse All Projects</h3>
                <span className="ml-2 text-sm text-gray-500">({allProjects.length} total)</span>
              </div>
              <button
                onClick={() => setShowAllProjectsModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Search Bar */}
            <div className="p-6 border-b border-gray-200">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Search projects by name or domain..."
                />
              </div>
            </div>
            
            {/* Projects List */}
            <div className="flex-1 overflow-y-auto p-6">
              {filteredProjects.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-gray-400 text-2xl">🔍</span>
                  </div>
                  <p className="text-gray-500">No projects found</p>
                  <p className="text-sm text-gray-400 mt-1">Try adjusting your search terms</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredProjects.map((project) => (
                    <div
                      key={project.name}
                      className="group p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 cursor-pointer transition-all duration-200 hover:shadow-md"
                      onClick={() => {
                        onProjectSelect(project)
                        setShowAllProjectsModal(false)
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <h4 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors truncate">
                            {project.name}
                          </h4>
                          <p className="text-sm text-gray-600 mt-1 flex items-center">
                            <span className="w-2 h-2 bg-green-400 rounded-full mr-2 flex-shrink-0"></span>
                            <span className="truncate">{project.domain}</span>
                            <span className="mx-2 text-gray-400">•</span>
                            <span className="flex-shrink-0">{project.dimensions_count} dimensions</span>
                          </p>
                        </div>
                        <div className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
                          →
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  )
}