import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

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
  color: _color = 'blue',
  actions 
}: StatusCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">
            {title}
          </CardTitle>
          {actions && (
            <div className="flex items-center space-x-2">
              {actions}
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="space-y-3">
          {stats.map((stat, index) => (
            <div key={index} className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {stat.icon && (
                  <span className="text-sm">{stat.icon}</span>
                )}
                <span className="text-sm text-muted-foreground">{stat.label}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-sm font-semibold">
                  {stat.value}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Compact variant for smaller spaces
export function CompactStatusCard({ 
  title, 
  value, 
  icon, 
  color: _color = 'blue',
  subtitle
}: {
  title: string
  value: number | string
  icon?: string
  color?: 'blue' | 'green' | 'purple' | 'red' | 'yellow' | 'gray'
  subtitle?: string
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2">
              {icon && <span className="text-lg">{icon}</span>}
              <h4 className="text-sm font-medium">{title}</h4>
            </div>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
            )}
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold">{value}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}