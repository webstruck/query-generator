interface StageSelectorProps {
  stages: string[]
  currentStage: string
  onChange: (stage: string) => void
  labels?: Record<string, string>
  icons?: Record<string, string>
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export default function StageSelector({ 
  stages, 
  currentStage, 
  onChange, 
  labels = {},
  icons = {},
  disabled = false,
  size = 'md'
}: StageSelectorProps) {
  const getStageLabel = (stage: string) => {
    return labels[stage] || stage.charAt(0).toUpperCase() + stage.slice(1)
  }

  const getStageIcon = (stage: string) => {
    return icons[stage] || ''
  }

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-3 py-1 text-xs'
      case 'lg':
        return 'px-6 py-3 text-base'
      default:
        return 'px-4 py-2 text-sm'
    }
  }

  return (
    <div className="bg-white rounded-lg p-1 shadow-sm border border-gray-200 inline-flex">
      {stages.map((stage) => (
        <button
          key={stage}
          onClick={() => onChange(stage)}
          disabled={disabled}
          className={`${getSizeClasses()} rounded-md transition-all font-medium flex items-center space-x-2 ${
            currentStage === stage
              ? 'bg-blue-500 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          } ${
            disabled
              ? 'opacity-50 cursor-not-allowed'
              : 'cursor-pointer'
          }`}
        >
          {getStageIcon(stage) && (
            <span>{getStageIcon(stage)}</span>
          )}
          <span>{getStageLabel(stage)}</span>
        </button>
      ))}
    </div>
  )
}

// Vertical variant for sidebar navigation
export function VerticalStageSelector({ 
  stages, 
  currentStage, 
  onChange, 
  labels = {},
  icons = {},
  disabled = false
}: Omit<StageSelectorProps, 'size'>) {
  const getStageLabel = (stage: string) => {
    return labels[stage] || stage.charAt(0).toUpperCase() + stage.slice(1)
  }

  const getStageIcon = (stage: string) => {
    return icons[stage] || ''
  }

  return (
    <div className="space-y-1">
      {stages.map((stage) => (
        <button
          key={stage}
          onClick={() => onChange(stage)}
          disabled={disabled}
          className={`w-full px-4 py-2 text-left rounded-lg transition-all font-medium flex items-center space-x-3 ${
            currentStage === stage
              ? 'bg-blue-500 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          } ${
            disabled
              ? 'opacity-50 cursor-not-allowed'
              : 'cursor-pointer'
          }`}
        >
          {getStageIcon(stage) && (
            <span className="text-lg">{getStageIcon(stage)}</span>
          )}
          <span>{getStageLabel(stage)}</span>
        </button>
      ))}
    </div>
  )
}