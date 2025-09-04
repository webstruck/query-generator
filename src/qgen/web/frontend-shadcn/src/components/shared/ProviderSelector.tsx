import { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Cloud, Settings, Bot, Github, Zap } from 'lucide-react'

interface Provider {
  available: string[]
  auto_detected: string
}

interface ProviderSelectorProps {
  selectedProvider: string
  onChange: (provider: string) => void
  compact?: boolean
  disabled?: boolean
}

export default function ProviderSelector({ 
  selectedProvider, 
  onChange, 
  compact = false,
  disabled = false 
}: ProviderSelectorProps) {
  const [providers, setProviders] = useState<Provider>({ available: [], auto_detected: '' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      const response = await fetch('/api/providers')
      const data = await response.json()
      setProviders(data)
      
      // Set default provider if none selected
      if (!selectedProvider && (data.auto_detected || data.available[0])) {
        onChange(data.auto_detected || data.available[0])
      }
    } catch (error) {
      console.error('Failed to load providers:', error)
    } finally {
      setLoading(false)
    }
  }

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'openai': return <Bot className="h-4 w-4" />
      case 'azure': return <Cloud className="h-4 w-4" />
      case 'github': return <Github className="h-4 w-4" />
      case 'ollama': return <Zap className="h-4 w-4" />
      default: return <Settings className="h-4 w-4" />
    }
  }

  const getProviderName = (provider: string) => {
    switch (provider) {
      case 'openai': return 'OpenAI'
      case 'azure': return 'Azure OpenAI'
      case 'github': return 'GitHub Models'
      case 'ollama': return 'Ollama'
      default: return provider
    }
  }

  if (loading) {
    return (
      <div className={`${compact ? 'w-32' : 'w-full'}`}>
        <div className="animate-pulse bg-muted rounded-lg h-10"></div>
      </div>
    )
  }

  if (compact) {
    return (
      <Select value={selectedProvider} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="w-32">
          <SelectValue>
            <div className="flex items-center space-x-2">
              {getProviderIcon(selectedProvider)}
              <span>{getProviderName(selectedProvider)}</span>
            </div>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {providers.available.map((provider) => (
            <SelectItem key={provider} value={provider}>
              <div className="flex items-center space-x-2">
                {getProviderIcon(provider)}
                <span>{getProviderName(provider)}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }

  return (
    <div className="w-full space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">
          LLM Provider
        </label>
        {providers.auto_detected && (
          <Badge variant="secondary" className="text-xs">
            Auto-detected: {getProviderName(providers.auto_detected)}
          </Badge>
        )}
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {providers.available.map((provider) => (
          <Card 
            key={provider}
            className={`cursor-pointer transition-all ${
              selectedProvider === provider
                ? 'ring-2 ring-primary bg-primary/5'
                : 'hover:bg-muted/50'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={() => !disabled && onChange(provider)}
          >
            <CardContent className="p-3 text-center">
              <div className="space-y-2">
                <div className="flex justify-center">{getProviderIcon(provider)}</div>
                <div className="space-y-1">
                  <div className="text-sm font-medium">{getProviderName(provider)}</div>
                  {provider === providers.auto_detected && (
                    <Badge variant="outline" className="text-xs">Auto</Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

// Hook for provider management
export function useProviders() {
  const [providers, setProviders] = useState<Provider>({ available: [], auto_detected: '' })
  const [selectedProvider, setSelectedProvider] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      const response = await fetch('/api/providers')
      const data = await response.json()
      setProviders(data)
      setSelectedProvider(data.auto_detected || data.available[0] || '')
    } catch (error) {
      console.error('Failed to load providers:', error)
    } finally {
      setLoading(false)
    }
  }

  return {
    providers,
    selectedProvider,
    setSelectedProvider,
    loading
  }
}