import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface RAGExportShortcutsProps {
  isActive: boolean
  getApprovedQueriesCount: () => number
  onExportJSON: () => void
  onExportCSV: () => void
}

export const RAGExportShortcuts: React.FC<RAGExportShortcutsProps> = ({
  isActive,
  getApprovedQueriesCount,
  onExportJSON,
  onExportCSV
}) => {
  useKeyboardShortcuts({
    shortcuts: [
      { keys: ['⌘', 'J'], handler: onExportJSON, description: 'Export JSON', enabled: isActive && getApprovedQueriesCount() > 0 },
      { keys: ['⌘', 'C'], handler: onExportCSV, description: 'Export CSV', enabled: isActive && getApprovedQueriesCount() > 0 }
    ],
    enabled: isActive
  })

  return null // This component only provides keyboard shortcuts
}