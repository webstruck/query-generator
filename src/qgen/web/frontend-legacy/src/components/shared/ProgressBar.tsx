interface ProgressBarProps {
  value: number
  max?: number
  status?: string
  visible?: boolean
  color?: 'blue' | 'green' | 'purple' | 'red' | 'yellow'
  size?: 'sm' | 'md' | 'lg'
  showPercentage?: boolean
}

export default function ProgressBar({ 
  value, 
  max = 100, 
  status = '', 
  visible = true,
  color = 'blue',
  size = 'md',
  showPercentage = true
}: ProgressBarProps) {
  if (!visible) return null

  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  
  const getColorClasses = () => {
    switch (color) {
      case 'green':
        return 'bg-green-500'
      case 'purple':
        return 'bg-purple-500'
      case 'red':
        return 'bg-red-500'
      case 'yellow':
        return 'bg-yellow-500'
      default:
        return 'bg-blue-500'
    }
  }

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'h-1'
      case 'lg':
        return 'h-4'
      default:
        return 'h-2'
    }
  }

  return (
    <div className="w-full">
      {(status || showPercentage) && (
        <div className="flex justify-between items-center mb-2">
          {status && (
            <span className="text-sm text-gray-600">{status}</span>
          )}
          {showPercentage && (
            <span className="text-sm font-medium text-gray-900">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${getSizeClasses()}`}>
        <div
          className={`h-full ${getColorClasses()} transition-all duration-300 ease-out rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

// Circular progress variant
export function CircularProgress({ 
  value, 
  max = 100, 
  size = 48,
  color = 'blue',
  showPercentage = true 
}: {
  value: number
  max?: number
  size?: number
  color?: 'blue' | 'green' | 'purple' | 'red' | 'yellow'
  showPercentage?: boolean
}) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  const strokeWidth = 4
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const strokeDasharray = circumference
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  const getColorClasses = () => {
    switch (color) {
      case 'green':
        return 'text-green-500'
      case 'purple':
        return 'text-purple-500'
      case 'red':
        return 'text-red-500'
      case 'yellow':
        return 'text-yellow-500'
      default:
        return 'text-blue-500'
    }
  }

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-gray-200"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={`transition-all duration-300 ease-out ${getColorClasses()}`}
        />
      </svg>
      {showPercentage && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-medium text-gray-900">
            {Math.round(percentage)}%
          </span>
        </div>
      )}
    </div>
  )
}