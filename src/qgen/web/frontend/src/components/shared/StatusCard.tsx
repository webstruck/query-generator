interface StatusStat {
  label: string
  value: number | string
  icon?: string
  color?: string
}

interface StatusCardProps {
  title: string
  stats: StatusStat[]
  color?: 'blue' | 'green' | 'purple' | 'red' | 'yellow' | 'gray'
  actions?: React.ReactNode
}

export default function StatusCard({ 
  title, 
  stats, 
  color = 'blue',
  actions 
}: StatusCardProps) {
  const getColorClasses = () => {
    switch (color) {
      case 'green':
        return {
          header: 'bg-green-50 border-green-200',
          title: 'text-green-900',
          accent: 'text-green-600'
        }
      case 'purple':
        return {
          header: 'bg-purple-50 border-purple-200',
          title: 'text-purple-900',
          accent: 'text-purple-600'
        }
      case 'red':
        return {
          header: 'bg-red-50 border-red-200',
          title: 'text-red-900',
          accent: 'text-red-600'
        }
      case 'yellow':
        return {
          header: 'bg-yellow-50 border-yellow-200',
          title: 'text-yellow-900',
          accent: 'text-yellow-600'
        }
      case 'gray':
        return {
          header: 'bg-gray-50 border-gray-200',
          title: 'text-gray-900',
          accent: 'text-gray-600'
        }
      default:
        return {
          header: 'bg-blue-50 border-blue-200',
          title: 'text-blue-900',
          accent: 'text-blue-600'
        }
    }
  }

  const colors = getColorClasses()

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className={`px-4 py-3 border-b ${colors.header}`}>
        <div className="flex items-center justify-between">
          <h3 className={`text-sm font-semibold ${colors.title}`}>
            {title}
          </h3>
          {actions && (
            <div className="flex items-center space-x-2">
              {actions}
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="p-4">
        <div className="space-y-3">
          {stats.map((stat, index) => (
            <div key={index} className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {stat.icon && (
                  <span className="text-sm">{stat.icon}</span>
                )}
                <span className="text-sm text-gray-600">{stat.label}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span 
                  className={`text-sm font-semibold ${
                    stat.color || colors.accent
                  }`}
                >
                  {stat.value}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Compact variant for smaller spaces
export function CompactStatusCard({ 
  title, 
  value, 
  icon, 
  color = 'blue',
  subtitle
}: {
  title: string
  value: number | string
  icon?: string
  color?: 'blue' | 'green' | 'purple' | 'red' | 'yellow' | 'gray'
  subtitle?: string
}) {
  const getColorClasses = () => {
    switch (color) {
      case 'green':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'purple':
        return 'text-purple-600 bg-purple-50 border-purple-200'
      case 'red':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'yellow':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'gray':
        return 'text-gray-600 bg-gray-50 border-gray-200'
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200'
    }
  }

  return (
    <div className={`p-4 rounded-lg border ${getColorClasses()}`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            {icon && <span className="text-lg">{icon}</span>}
            <h4 className="text-sm font-medium text-gray-900">{title}</h4>
          </div>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">{value}</div>
        </div>
      </div>
    </div>
  )
}