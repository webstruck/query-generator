import { useState, useEffect } from 'react'
import { useNotification } from './shared/Notification'
import { Button } from '@/components/ui/button'
import { ButtonWithShortcut } from '@/components/ui/button-with-shortcut'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
import { BarChart3, Brain } from 'lucide-react'

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

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      {
        keys: ['1'],
        handler: () => setProjectType('dimension'),
        description: 'Switch to dimension projects',
        enabled: !showCreateModal
      },
      {
        keys: ['2'],
        handler: () => setProjectType('rag'),
        description: 'Switch to RAG projects',
        enabled: !showCreateModal
      },
      {
        keys: ['N'],
        handler: () => setShowCreateModal(true),
        description: 'New project',
        enabled: !showCreateModal
      },
      {
        keys: ['Esc'],
        handler: () => setShowCreateModal(false),
        description: 'Close modal',
        enabled: showCreateModal
      }
    ],
    enabled: true
  })

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
    return type === 'dimension' ? <BarChart3 className="h-4 w-4" /> : <Brain className="h-4 w-4" />
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
        <h1 className="text-3xl font-bold mb-4">
          Welcome to QGen
        </h1>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Generate high-quality synthetic queries for your domain using either dimension-based systematic generation or RAG-based content extraction.
        </p>
      </div>

      {/* Project Type Toggle */}
      <div className="mb-8 flex justify-center">
        <Tabs value={projectType} onValueChange={(value) => setProjectType(value as 'dimension' | 'rag')}>
          <TabsList className="grid w-full grid-cols-2 max-w-md">
            <TabsTrigger value="dimension" className="flex items-center space-x-2">
              <BarChart3 className="h-4 w-4" />
              <span>Dimension-Based</span>
            </TabsTrigger>
            <TabsTrigger value="rag" className="flex items-center space-x-2">
              <Brain className="h-4 w-4" />
              <span>RAG-Based</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Projects Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold flex items-center space-x-2">
            <span>{getProjectTypeIcon(projectType)}</span>
            <span>
              {projectType === 'dimension' ? 'Dimension Projects' : 'RAG Projects'}
            </span>
          </h2>
          <ButtonWithShortcut 
            onClick={() => setShowCreateModal(true)}
            variant={projectType === 'dimension' ? 'default' : 'secondary'}
            shortcut={['N']}
          >
            <span className="mr-2">+</span>
            <span>New Project</span>
          </ButtonWithShortcut>
        </div>

        {/* Projects Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="animate-pulse space-y-3">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-3 bg-muted rounded w-1/2"></div>
                    <div className="h-3 bg-muted rounded w-2/3"></div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : projects.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Card
                key={project.name}
                className="cursor-pointer transition-all hover:shadow-md"
                onClick={() => onProjectSelect(project)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-xl">{getProjectTypeIcon(project.type)}</span>
                      <CardTitle className="text-base">{project.name}</CardTitle>
                    </div>
                    <Badge variant={projectType === 'dimension' ? 'default' : 'secondary'}>
                      {project.domain}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-sm text-muted-foreground mb-4">
                    {getProjectStatusSummary(project)}
                  </p>
                  
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{project.path.split('/').pop()}</span>
                    <span>→</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="text-center py-12">
              <span className="text-4xl mb-4 block">{getProjectTypeIcon(projectType)}</span>
              <h3 className="text-lg font-medium mb-2">
                No {projectType} projects yet
              </h3>
              <p className="text-muted-foreground mb-6">
                Create your first {projectType} project to get started with query generation.
              </p>
              <Button
                onClick={() => setShowCreateModal(true)}
                variant={projectType === 'dimension' ? 'default' : 'secondary'}
              >
                Create Project
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Create Project Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Create New {projectType === 'dimension' ? 'Dimension' : 'RAG'} Project
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Project Name
              </label>
              <Input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="Enter project name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">
                {projectType === 'dimension' ? 'Template' : 'Domain'}
              </label>
              <Select value={newProjectDomain} onValueChange={setNewProjectDomain}>
                <SelectTrigger>
                  <SelectValue placeholder="Select domain" />
                </SelectTrigger>
                <SelectContent>
                  {projectType === 'dimension' ? (
                    templates.map((template) => (
                      <SelectItem key={template} value={template}>
                        {template.charAt(0).toUpperCase() + template.slice(1)}
                      </SelectItem>
                    ))
                  ) : (
                    <>
                      <SelectItem value="general">General</SelectItem>
                      <SelectItem value="library">Library</SelectItem>
                      <SelectItem value="apartment">Apartment</SelectItem>
                      <SelectItem value="software">Software</SelectItem>
                      <SelectItem value="healthcare">Healthcare</SelectItem>
                    </>
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="flex items-center justify-end space-x-3 mt-6">
            <ButtonWithShortcut
              variant="outline"
              onClick={() => {
                setShowCreateModal(false)
                setNewProjectName('')
                setNewProjectDomain(projectType === 'dimension' ? (templates[0] || 'general') : 'general')
              }}
              disabled={creating}
              shortcut="cancel"
            >
              Cancel
            </ButtonWithShortcut>
            <ButtonWithShortcut
              onClick={createProject}
              disabled={creating || !newProjectName.trim()}
              variant={projectType === 'dimension' ? 'default' : 'secondary'}
              shortcut="save"
            >
              {creating ? 'Creating...' : 'Create Project'}
            </ButtonWithShortcut>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export type { Project, DimensionProject, RAGProject }