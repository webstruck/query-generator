import { useState } from 'react'
import ProjectSelector, { type Project } from './components/ProjectSelector'
import DimensionProjectDashboard from './components/dimension/DimensionProjectDashboard'
import { RAGProjectDashboard } from './components/rag/RAGProjectDashboard'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/hooks/use-theme'
import { BarChart3, Brain, HelpCircle } from 'lucide-react'

function App() {
  const [currentProject, setCurrentProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)
  const { theme, toggleTheme } = useTheme()

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
            <HelpCircle className="h-16 w-16 mb-4 mx-auto text-muted-foreground" />
            <h2 className="text-xl font-semibold mb-2">Unknown Project Type</h2>
            <p className="text-muted-foreground">This project type is not supported.</p>
          </div>
        )
    }
  }


  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <span className="text-primary-foreground text-sm font-bold">Q</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold">QGen</h1>
                  <span className="text-xs text-muted-foreground">
                    {theme === 'dark' ? 'Dark Purple Theme' : 'Light Emerald Theme'} - Shadcn/ui Version
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                size="sm"
                onClick={toggleTheme}
              >
                {theme === 'dark' ? 'Light' : 'Dark'}
              </Button>
              
              {currentProject && (
                <>
                  <Badge 
                    variant={currentProject.type === 'dimension' ? 'default' : 'secondary'}
                    className="px-3 py-1 flex items-center gap-2"
                  >
                    {currentProject.type === 'dimension' ? <BarChart3 className="h-3 w-3" /> : <Brain className="h-3 w-3" />}
                    <span className="font-medium">{currentProject.name}</span>
                    <span className="ml-1 opacity-75">
                      ({currentProject.domain})
                    </span>
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentProject(null)}
                  >
                    Switch Project
                  </Button>
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