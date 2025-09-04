import { Progress } from '@/components/ui/progress'

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
  color: _color = 'blue',
  size = 'md',
  showPercentage = true
}: ProgressBarProps) {
  if (!visible) return null

  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  
  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'h-2'
      case 'lg':
        return 'h-4'
      default:
        return 'h-3'
    }
  }

  return (
    <div className="w-full space-y-2">
      {(status || showPercentage) && (
        <div className="flex items-center justify-between text-sm">
          {status && (
            <span className="text-muted-foreground">{status}</span>
          )}
          {showPercentage && (
            <span className="font-medium">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      
      <Progress 
        value={percentage} 
        className={getSizeClasses()}
      />
      
      {value !== max && (
        <div className="text-xs text-muted-foreground">
          {value.toLocaleString()} / {max.toLocaleString()}
        </div>
      )}
    </div>
  )
}

// Circular progress variant using shadcn
export function CircularProgress({ 
  value, 
  max = 100, 
  size = 48,
  color: _color = 'blue',
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
          className="text-muted"
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
          className="transition-all duration-300 ease-out text-primary"
        />
      </svg>
      {showPercentage && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-medium">
            {Math.round(percentage)}%
          </span>
        </div>
      )}
    </div>
  )
}