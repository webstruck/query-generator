import { useState } from 'react'
import ProjectSelector, { type Project } from './components/ProjectSelector'
import DimensionProjectDashboard from './components/dimension/DimensionProjectDashboard'
import { RAGProjectDashboard } from './components/rag/RAGProjectDashboard'

function App() {
  const [currentProject, setCurrentProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)

  const renderDashboard = () => {
    if (!currentProject) return null

    switch (currentProject.type) {
      case 'dimension':
        return <DimensionProjectDashboard project={currentProject} loading={loading} setLoading={setLoading} />
      case 'rag':
        return <RAGProjectDashboard project={currentProject} onBack={() => setCurrentProject(null)} />
      default:
        return (
          <div className="text-center py-12">
            <span className="text-4xl mb-4 block">❓</span>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Unknown Project Type</h2>
            <p className="text-gray-600">This project type is not supported.</p>
          </div>
        )
    }
  }


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
            <div className="flex items-center space-x-4">
              {currentProject && (
                <>
                  <div className={`border rounded-lg px-3 py-1 ${
                    currentProject.type === 'dimension' 
                      ? 'bg-blue-50 border-blue-200' 
                      : 'bg-purple-50 border-purple-200'
                  }`}>
                    <span className={`text-sm ${
                      currentProject.type === 'dimension' 
                        ? 'text-blue-700' 
                        : 'text-purple-700'
                    }`}>
                      <span className="mr-2">
                        {currentProject.type === 'dimension' ? '📊' : '🧠'}
                      </span>
                      <span className="font-medium">{currentProject.name}</span>
                      <span className={`ml-2 ${
                        currentProject.type === 'dimension' 
                          ? 'text-blue-500' 
                          : 'text-purple-500'
                      }`}>
                        ({currentProject.domain})
                      </span>
                    </span>
                  </div>
                  <button
                    onClick={() => setCurrentProject(null)}
                    className="text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 px-3 py-1 rounded-lg transition-colors"
                  >
                    Switch Project
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {!currentProject ? (
          <ProjectSelector onProjectSelect={setCurrentProject} />
        ) : (
          renderDashboard()
        )}
      </main>
    </div>
  )
}

export default App