import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface OverviewShortcutsProps {
  isActive: boolean
  loading: boolean
  editingDimensions: boolean
  projectData: any
  onEditDimensions: () => void
  onGenerateTuples: () => void
  onApproveTuples: () => void
  onGenerateQueries: () => void
  onReviewQueries: () => void
  onExportDataset: () => void
}

export const OverviewShortcuts: React.FC<OverviewShortcutsProps> = ({
  isActive,
  loading,
  editingDimensions,
  projectData,
  onEditDimensions,
  onGenerateTuples,
  onApproveTuples,
  onGenerateQueries,
  onReviewQueries,
  onExportDataset
}) => {
  useKeyboardShortcuts({
    shortcuts: [
      { keys: ['E'], handler: onEditDimensions, description: 'Edit dimensions', enabled: isActive && !editingDimensions },
      { keys: ['G'], handler: onGenerateTuples, description: 'Generate tuples', enabled: isActive && !loading && !editingDimensions },
      { keys: ['⌘', 'A'], handler: onApproveTuples, description: 'Approve all tuples', enabled: isActive && !loading && (projectData?.data_status?.generated_tuples || 0) > 0 && !editingDimensions },
      { keys: ['Q'], handler: onGenerateQueries, description: 'Generate queries', enabled: isActive && !loading && (projectData?.data_status?.approved_tuples || 0) > 0 && !editingDimensions },
      { keys: ['⌘', 'R'], handler: onReviewQueries, description: 'Review queries', enabled: isActive && (projectData?.data_status?.generated_queries || 0) > 0 && !editingDimensions },
      { keys: ['X'], handler: onExportDataset, description: 'Export dataset', enabled: isActive && (projectData?.data_status?.approved_queries || 0) > 0 && !editingDimensions }
    ],
    enabled: isActive
  })

  return null // This component only provides keyboard shortcuts
}