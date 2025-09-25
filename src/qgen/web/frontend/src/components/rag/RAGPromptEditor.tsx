import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Save, RotateCcw, FileText, AlertCircle } from 'lucide-react'
import { useNotification } from '../shared/Notification'

interface RAGPromptEditorProps {
  projectName: string
}

interface PromptTemplate {
  name: string
  displayName: string
  description: string
  content: string
  originalContent: string
  modified: boolean
}

const PROMPT_TEMPLATES = [
  {
    name: 'fact_extraction.txt',
    displayName: 'Fact Extraction',
    description: 'Template for extracting salient facts from text chunks'
  },
  {
    name: 'standard_query_generation.txt',
    displayName: 'Standard Query Generation',
    description: 'Template for generating realistic user queries from facts'
  },
  {
    name: 'adversarial_query_generation.txt',
    displayName: 'Adversarial Query Generation',
    description: 'Template for generating challenging queries with distractors'
  },
  {
    name: 'multihop_query_generation.txt',
    displayName: 'Multi-hop Query Generation',
    description: 'Template for generating queries requiring multiple chunks'
  },
  {
    name: 'realism_scoring.txt',
    displayName: 'Realism Scoring',
    description: 'Template for evaluating query realism and quality'
  }
]

export function RAGPromptEditor({ projectName }: RAGPromptEditorProps) {
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [activeTemplate, setActiveTemplate] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { showNotification } = useNotification()

  // Load all prompt templates
  const loadPrompts = async () => {
    setLoading(true)
    try {
      const loadedTemplates: PromptTemplate[] = []
      
      for (const template of PROMPT_TEMPLATES) {
        try {
          const response = await fetch(`/api/rag-projects/${projectName}/prompts/${template.name}`)
          if (response.ok) {
            const data = await response.json()
            loadedTemplates.push({
              ...template,
              content: data.content,
              originalContent: data.content,
              modified: false
            })
          } else {
            // If prompt doesn't exist, create with empty content
            loadedTemplates.push({
              ...template,
              content: '',
              originalContent: '',
              modified: false
            })
          }
        } catch (error) {
          console.error(`Failed to load ${template.name}:`, error)
          loadedTemplates.push({
            ...template,
            content: '',
            originalContent: '',
            modified: false
          })
        }
      }
      
      setTemplates(loadedTemplates)
      if (loadedTemplates.length > 0) {
        setActiveTemplate(loadedTemplates[0].name)
      }
    } catch (error) {
      showNotification('Failed to load prompt templates', 'error')
      console.error('Error loading prompts:', error)
    } finally {
      setLoading(false)
    }
  }

  // Save a specific template
  const saveTemplate = async (templateName: string) => {
    setSaving(true)
    try {
      const template = templates.find(t => t.name === templateName)
      if (!template) return

      const response = await fetch(`/api/rag-projects/${projectName}/prompts/${templateName}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: template.content }),
      })

      if (response.ok) {
        // Update template state to mark as saved
        setTemplates(prev => prev.map(t => 
          t.name === templateName 
            ? { ...t, originalContent: t.content, modified: false }
            : t
        ))
        showNotification(`${template.displayName} saved successfully`, 'success')
      } else {
        const error = await response.json()
        showNotification(`Failed to save ${template.displayName}: ${error.detail}`, 'error')
      }
    } catch (error) {
      showNotification(`Failed to save template`, 'error')
      console.error('Error saving template:', error)
    } finally {
      setSaving(false)
    }
  }

  // Reset a template to original content
  const resetTemplate = (templateName: string) => {
    setTemplates(prev => prev.map(t => 
      t.name === templateName 
        ? { ...t, content: t.originalContent, modified: false }
        : t
    ))
  }

  // Update template content
  const updateTemplateContent = (templateName: string, content: string) => {
    setTemplates(prev => prev.map(t => 
      t.name === templateName 
        ? { ...t, content, modified: content !== t.originalContent }
        : t
    ))
  }

  useEffect(() => {
    loadPrompts()
  }, [projectName])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="text-muted-foreground">Loading prompts...</div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Prompt Templates</h2>
          <p className="text-muted-foreground">
            Customize the AI prompts used for fact extraction and query generation
          </p>
        </div>
      </div>

      <Tabs value={activeTemplate} onValueChange={setActiveTemplate}>
        <TabsList className="grid w-full grid-cols-5">
          {templates.map((template) => (
            <TabsTrigger 
              key={template.name} 
              value={template.name}
              className="relative"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span className="hidden sm:inline">{template.displayName}</span>
                <span className="sm:hidden">{template.displayName.split(' ')[0]}</span>
                {template.modified && (
                  <div className="w-2 h-2 bg-orange-500 rounded-full" />
                )}
              </div>
            </TabsTrigger>
          ))}
        </TabsList>

        {templates.map((template) => (
          <TabsContent key={template.name} value={template.name} className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="w-5 h-5" />
                      {template.displayName}
                      {template.modified && (
                        <Badge variant="outline" className="text-orange-600 border-orange-300">
                          Modified
                        </Badge>
                      )}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {template.description}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {template.modified && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => resetTemplate(template.name)}
                        className="flex items-center gap-2"
                      >
                        <RotateCcw className="w-4 h-4" />
                        Reset
                      </Button>
                    )}
                    <Button
                      onClick={() => saveTemplate(template.name)}
                      disabled={saving || !template.modified}
                      className="flex items-center gap-2"
                    >
                      <Save className="w-4 h-4" />
                      {saving ? 'Saving...' : 'Save'}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <textarea
                    value={template.content}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => updateTemplateContent(template.name, e.target.value)}
                    placeholder={`Enter your ${template.displayName.toLowerCase()} prompt template...`}
                    className="w-full min-h-[400px] font-mono text-sm p-3 border border-gray-300 rounded-md resize-y bg-white text-gray-900 dark:bg-gray-800 dark:text-gray-100 dark:border-gray-600"
                  />
                  
                  {template.content.length === 0 && (
                    <div className="flex items-center gap-2 text-amber-600 bg-amber-50 p-3 rounded-md">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm">
                        This prompt template is empty. The system will use a default template during generation.
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}