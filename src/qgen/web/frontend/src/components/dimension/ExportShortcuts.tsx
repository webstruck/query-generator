import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface ExportShortcutsProps {
  isActive: boolean
  hasApprovedQueries: boolean
  onExportCSV: () => void
  onExportJSON: () => void
}

export const ExportShortcuts: React.FC<ExportShortcutsProps> = ({
  isActive,
  hasApprovedQueries,
  onExportCSV,
  onExportJSON
}) => {
  useKeyboardShortcuts({
    shortcuts: [
      { keys: ['⌘', 'C'], handler: onExportCSV, description: 'Export CSV', enabled: isActive && hasApprovedQueries },
      { keys: ['⌘', 'J'], handler: onExportJSON, description: 'Export JSON', enabled: isActive && hasApprovedQueries }
    ],
    enabled: isActive
  })

  return null // This component only provides keyboard shortcuts
}