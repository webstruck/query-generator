import { useState } from 'react'
import ProjectSelector from './components/ProjectSelector'
import ProjectDashboard from './components/ProjectDashboard'

interface Project {
  name: string
  path: string
  domain: string
  dimensions_count: number
}

function App() {
  const [currentProject, setCurrentProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      <header className="bg-white/80 backdrop-blur-sm shadow-sm border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-sm font-bold">Q</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">QGen</h1>
                  <span className="text-xs text-gray-500">Query Generation Tool</span>
                </div>
              </div>
            </div>
            {currentProject && (
              <div className="flex items-center space-x-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-1">
                  <span className="text-sm text-blue-700">
                    <span className="font-medium">{currentProject.name}</span>
                    <span className="ml-2 text-blue-500">({currentProject.domain})</span>
                  </span>
                </div>
                <button
                  onClick={() => setCurrentProject(null)}
                  className="text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 px-3 py-1 rounded-lg transition-colors"
                >
                  Switch Project
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {!currentProject ? (
          <ProjectSelector 
            onProjectSelect={setCurrentProject}
            loading={loading}
            setLoading={setLoading}
          />
        ) : (
          <ProjectDashboard 
            project={currentProject}
            loading={loading}
            setLoading={setLoading}
          />
        )}
      </main>
    </div>
  )
}

export default App
