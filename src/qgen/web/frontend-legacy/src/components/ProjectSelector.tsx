import { useState, useEffect } from 'react'
import { useNotification } from './shared/Notification'

// Base project interface
interface BaseProject {
  name: string
  path: string
  created_at?: string
  last_modified?: string
}

// Dimension project interface
interface DimensionProject extends BaseProject {
  type: 'dimension'
  domain: string
  dimensions_count: number
  data_status: {
    generated_tuples: number
    approved_tuples: number
    generated_queries: number
    approved_queries: number
  }
}

// RAG project interface
interface RAGProject extends BaseProject {
  type: 'rag'
  domain: string
  chunks_count: number
  data_status: {
    generated_facts: number
    approved_facts: number
    generated_queries: number
    generated_multihop: number
    approved_queries: number
  }
}

// Union type for all project types
type Project = DimensionProject | RAGProject

interface ProjectSelectorProps {
  onProjectSelect: (project: Project) => void
}

export default function ProjectSelector({ onProjectSelect }: ProjectSelectorProps) {
  const [projectType, setProjectType] = useState<'dimension' | 'rag'>('dimension')
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDomain, setNewProjectDomain] = useState('general')
  const [creating, setCreating] = useState(false)
  const [templates, setTemplates] = useState<string[]>([])
  const { showNotification, NotificationContainer } = useNotification()

  useEffect(() => {
    loadProjects()
    if (projectType === 'dimension') {
      loadTemplates()
    }
  }, [projectType])

  const loadProjects = async () => {
    setLoading(true)
    try {
      const endpoint = projectType === 'dimension' ? '/api/projects' : '/api/rag-projects'
      const response = await fetch(endpoint)
      const data = await response.json()
      
      // Add type to projects if not present
      const typedProjects = data.projects.map((p: any) => ({
        ...p,
        type: projectType
      }))
      
      setProjects(typedProjects)
    } catch (error) {
      console.error('Failed to load projects:', error)
      showNotification('Failed to load projects', 'error')
    } finally {
      setLoading(false)
    }
  }

  const loadTemplates = async () => {
    try {
      const response = await fetch('/api/templates')
      const data = await response.json()
      setTemplates(data.templates)
      if (data.templates.length > 0 && !newProjectDomain) {
        setNewProjectDomain(data.templates[0])
      }
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  const createProject = async () => {
    if (!newProjectName.trim()) {
      showNotification('Please enter a project name', 'error')
      return
    }

    setCreating(true)
    try {
      const endpoint = projectType === 'dimension' ? '/api/projects' : '/api/rag-projects'
      const payload = projectType === 'dimension' 
        ? { name: newProjectName, template: newProjectDomain }
        : { name: newProjectName, domain: newProjectDomain }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        await response.json()
        showNotification(`${projectType === 'dimension' ? 'Project' : 'RAG project'} '${newProjectName}' created successfully`, 'success')
        setShowCreateModal(false)
        setNewProjectName('')
        setNewProjectDomain(projectType === 'dimension' ? (templates[0] || 'general') : 'general')
        loadProjects()
      } else {
        const error = await response.json()
        showNotification(`Failed to create project: ${error.detail}`, 'error')
      }
    } catch (error) {
      console.error('Failed to create project:', error)
      showNotification('Failed to create project', 'error')
    } finally {
      setCreating(false)
    }
  }

  const getProjectTypeIcon = (type: 'dimension' | 'rag') => {
    return type === 'dimension' ? '📊' : '🧠'
  }

  const getProjectStatusSummary = (project: Project) => {
    if (project.type === 'dimension') {
      const { data_status } = project
      if (!data_status) return 'No data available'
      return `${data_status.approved_queries || 0} queries • ${data_status.approved_tuples || 0} tuples approved`
    } else {
      const { data_status } = project
      if (!data_status) return 'No data available'
      return `${data_status.approved_queries || 0} queries • ${data_status.approved_facts || 0} facts approved`
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <NotificationContainer />
      
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to QGen
        </h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Generate high-quality synthetic queries for your domain using either dimension-based systematic generation or RAG-based content extraction.
        </p>
      </div>

      {/* Project Type Toggle */}
      <div className="mb-8 flex justify-center">
        <div className="bg-white rounded-lg p-1 shadow-sm border border-gray-200">
          <button 
            className={`px-6 py-3 rounded-md transition-all flex items-center space-x-3 ${
              projectType === 'dimension' 
                ? 'bg-blue-500 text-white shadow-sm' 
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            }`}
            onClick={() => setProjectType('dimension')}
          >
            <span className="text-xl">📊</span>
            <div className="text-left">
              <div className="font-medium">Dimension-Based</div>
              <div className="text-xs opacity-75">Systematic query generation</div>
            </div>
          </button>
          <button 
            className={`px-6 py-3 rounded-md transition-all flex items-center space-x-3 ${
              projectType === 'rag' 
                ? 'bg-purple-500 text-white shadow-sm' 
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            }`}
            onClick={() => setProjectType('rag')}
          >
            <span className="text-xl">🧠</span>
            <div className="text-left">
              <div className="font-medium">RAG-Based</div>
              <div className="text-xs opacity-75">Content-driven generation</div>
            </div>
          </button>
        </div>
      </div>

      {/* Projects Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center space-x-2">
            <span>{getProjectTypeIcon(projectType)}</span>
            <span>
              {projectType === 'dimension' ? 'Dimension Projects' : 'RAG Projects'}
            </span>
          </h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2 ${
              projectType === 'dimension'
                ? 'bg-blue-500 hover:bg-blue-600 text-white'
                : 'bg-purple-500 hover:bg-purple-600 text-white'
            }`}
          >
            <span>+</span>
            <span>New Project</span>
          </button>
        </div>

        {/* Projects Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow border border-gray-200 p-6">
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                </div>
              </div>
            ))}
          </div>
        ) : projects.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <div
                key={project.name}
                onClick={() => onProjectSelect(project)}
                className={`bg-white rounded-lg shadow border border-gray-200 p-6 cursor-pointer transition-all hover:shadow-md hover:border-gray-300 ${
                  projectType === 'dimension' ? 'hover:border-blue-300' : 'hover:border-purple-300'
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-xl">{getProjectTypeIcon(project.type)}</span>
                    <h3 className="font-semibold text-gray-900">{project.name}</h3>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    projectType === 'dimension'
                      ? 'bg-blue-50 text-blue-700'
                      : 'bg-purple-50 text-purple-700'
                  }`}>
                    {project.domain}
                  </span>
                </div>
                
                <p className="text-sm text-gray-600 mb-4">
                  {getProjectStatusSummary(project)}
                </p>
                
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>{project.path.split('/').pop()}</span>
                  <span>→</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <span className="text-4xl mb-4 block">{getProjectTypeIcon(projectType)}</span>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No {projectType} projects yet
            </h3>
            <p className="text-gray-600 mb-6">
              Create your first {projectType} project to get started with query generation.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                projectType === 'dimension'
                  ? 'bg-blue-500 hover:bg-blue-600 text-white'
                  : 'bg-purple-500 hover:bg-purple-600 text-white'
              }`}
            >
              Create Project
            </button>
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-4">
              Create New {projectType === 'dimension' ? 'Dimension' : 'RAG'} Project
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="Enter project name"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {projectType === 'dimension' ? 'Template' : 'Domain'}
                </label>
                <select
                  value={newProjectDomain}
                  onChange={(e) => setNewProjectDomain(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {projectType === 'dimension' ? (
                    templates.map((template) => (
                      <option key={template} value={template}>
                        {template.charAt(0).toUpperCase() + template.slice(1)}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="general">General</option>
                      <option value="library">Library</option>
                      <option value="apartment">Apartment</option>
                      <option value="software">Software</option>
                      <option value="healthcare">Healthcare</option>
                    </>
                  )}
                </select>
              </div>
            </div>
            
            <div className="flex items-center justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  setNewProjectName('')
                  setNewProjectDomain(projectType === 'dimension' ? (templates[0] || 'general') : 'general')
                }}
                className="px-4 py-2 text-gray-700 hover:text-gray-900"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                onClick={createProject}
                disabled={creating || !newProjectName.trim()}
                className={`px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  projectType === 'dimension'
                    ? 'bg-blue-500 hover:bg-blue-600 text-white'
                    : 'bg-purple-500 hover:bg-purple-600 text-white'
                }`}
              >
                {creating ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export type { Project, DimensionProject, RAGProject }