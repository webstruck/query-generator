import { useEffect, useState } from 'react'

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
      case 'openai': return '🤖'
      case 'azure': return '☁️'
      case 'github': return '🐙'
      case 'ollama': return '🦙'
      default: return '🔧'
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
        <div className="animate-pulse bg-gray-200 rounded-lg h-10"></div>
      </div>
    )
  }

  if (compact) {
    return (
      <select
        value={selectedProvider}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-32 px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
      >
        {providers.available.map((provider) => (
          <option key={provider} value={provider}>
            {getProviderName(provider)}
          </option>
        ))}
      </select>
    )
  }

  return (
    <div className="w-full">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        LLM Provider
        {providers.auto_detected && (
          <span className="ml-2 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
            Auto-detected: {getProviderName(providers.auto_detected)}
          </span>
        )}
      </label>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {providers.available.map((provider) => (
          <button
            key={provider}
            onClick={() => onChange(provider)}
            disabled={disabled}
            className={`p-3 rounded-lg border-2 transition-all flex flex-col items-center space-y-2 ${
              selectedProvider === provider
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 bg-white hover:border-gray-300 text-gray-700'
            } ${
              disabled 
                ? 'opacity-50 cursor-not-allowed' 
                : 'hover:shadow-sm cursor-pointer'
            }`}
          >
            <span className="text-2xl">{getProviderIcon(provider)}</span>
            <span className="text-sm font-medium">{getProviderName(provider)}</span>
            {provider === providers.auto_detected && (
              <span className="text-xs text-blue-600">Auto</span>
            )}
          </button>
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