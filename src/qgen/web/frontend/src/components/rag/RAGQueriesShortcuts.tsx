import { useKeyboardShortcuts } from '../../hooks/use-keyboard-shortcuts'

interface RAGQueriesShortcutsProps {
  isActive: boolean
  isModalOpen: boolean
  getApprovedFactsCount: () => number
  getGeneratedQueriesCount: () => number
  onGenerateStandardQueries: () => void
  onGenerateMultihopQueries: () => void
  onStartQueryReview: () => void
}

export const RAGQueriesShortcuts: React.FC<RAGQueriesShortcutsProps> = ({
  isActive,
  isModalOpen,
  getApprovedFactsCount,
  getGeneratedQueriesCount,
  onGenerateStandardQueries,
  onGenerateMultihopQueries,
  onStartQueryReview
}) => {
  useKeyboardShortcuts({
    shortcuts: [
      { keys: ['T'], handler: onGenerateStandardQueries, description: 'Generate standard queries', enabled: isActive && !isModalOpen && getApprovedFactsCount() > 0 },
      { keys: ['M'], handler: onGenerateMultihopQueries, description: 'Generate multi-hop queries', enabled: isActive && !isModalOpen && getApprovedFactsCount() > 0 },
      { keys: ['↵'], handler: onStartQueryReview, description: 'Start query review', enabled: isActive && !isModalOpen && getGeneratedQueriesCount() > 0 }
    ],
    enabled: isActive && !isModalOpen
  })

  return null // This component only provides keyboard shortcuts
}