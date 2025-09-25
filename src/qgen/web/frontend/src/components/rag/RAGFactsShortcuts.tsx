import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface RAGFactsShortcutsProps {
  isActive: boolean
  isModalOpen: boolean
  getChunksCount: () => number
  getGeneratedFactsCount: () => number
  selectedFactsSize: number
  onExtractFacts: () => void
  onStartFactReview: () => void
  onSelectAllFacts: () => void
  onSelectNoneFacts: () => void
  onBulkApproveFacts: () => void
}

export const RAGFactsShortcuts: React.FC<RAGFactsShortcutsProps> = ({
  isActive,
  isModalOpen,
  getChunksCount,
  getGeneratedFactsCount,
  selectedFactsSize,
  onExtractFacts,
  onStartFactReview,
  onSelectAllFacts,
  onSelectNoneFacts,
  onBulkApproveFacts
}) => {
  useKeyboardShortcuts({
    shortcuts: [
      { keys: ['F'], handler: onExtractFacts, description: 'Extract facts', enabled: isActive && !isModalOpen && getChunksCount() > 0 },
      { keys: ['↵'], handler: onStartFactReview, description: 'Start fact review', enabled: isActive && !isModalOpen && getGeneratedFactsCount() > 0 },
      { keys: ['⌘', '⇧', 'A'], handler: selectedFactsSize === getGeneratedFactsCount() ? onSelectNoneFacts : onSelectAllFacts, description: 'Toggle select all/none', enabled: isActive && !isModalOpen && getGeneratedFactsCount() > 0 },
      { keys: ['A'], handler: onBulkApproveFacts, description: 'Approve selected facts', enabled: isActive && !isModalOpen && selectedFactsSize > 0 }
    ],
    enabled: isActive && !isModalOpen
  })

  return null // This component only provides keyboard shortcuts
}