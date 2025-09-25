import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface RAGOverviewShortcutsProps {
  isActive: boolean
  getChunksCount: () => number
  getApprovedFactsCount: () => number
  getApprovedQueriesCount: () => number
  onUploadChunks: () => void
  onExtractFacts: () => void
  onGenerateQueries: () => void
  onExportDataset: () => void
}

export const RAGOverviewShortcuts: React.FC<RAGOverviewShortcutsProps> = ({
  isActive,
  getChunksCount,
  getApprovedFactsCount,
  getApprovedQueriesCount,
  onUploadChunks,
  onExtractFacts,
  onGenerateQueries,
  onExportDataset
}) => {
  useKeyboardShortcuts({
    shortcuts: [
      { keys: ['U'], handler: onUploadChunks, description: 'Upload chunks', enabled: isActive },
      { keys: ['F'], handler: onExtractFacts, description: 'Extract facts', enabled: isActive && getChunksCount() > 0 },
      { keys: ['G'], handler: onGenerateQueries, description: 'Generate queries', enabled: isActive && getApprovedFactsCount() > 0 },
      { keys: ['X'], handler: onExportDataset, description: 'Export dataset', enabled: isActive && getApprovedQueriesCount() > 0 }
    ],
    enabled: isActive
  })

  return null // This component only provides keyboard shortcuts
}